"""
Research Agent — the main search brain of the system.

Rather than following a fixed search sequence, this agent figures out what
to search next based on what the previous search returned.

It works in a loop: think about what to search → call a tool → look at
what came back → decide what to do next.

"""

import json
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from typing import Any

import structlog
from agentic_rag.configuration import agentic_settings
from agentic_rag.models import ResearchStep
from agentic_rag.prompts.prompts_template import (
    RESEARCHER_REACT_PROMPT,
    RESEARCHER_SYSTEM_PROMPT,
    RESEARCHER_TOOL_INSTRUCTIONS_FULL,
    RESEARCHER_TOOL_INSTRUCTIONS_RESTRICTED,
)
from agentic_rag.state import validate_node_state
from agentic_rag.tools.tool_registry import ToolRegistry, ToolResult
from agentic_rag.utils import extract_token_cost, parse_date, parse_min_date
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

logger = structlog.get_logger(__name__)

# Tools that collect sources
_SOURCE_TOOLS = frozenset(
    {
        "search_baseline",
        "search_tavily_specialist",
        "search_tavily_web",
        "search_mediastack",
    }
)


class ResearchAgent:
    """
    Runs the search loop. Decides which tools to call, in what order, based on
    what each tool returns. Once done, the sources go to Ranker → Verifier → Synthesizer.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
        llm: BaseChatModel | None = None,
    ) -> None:
        self.registry = tool_registry or ToolRegistry()
        self.event_callback = event_callback
        self.base_llm = llm or ChatOpenAI(
            model=agentic_settings.researcher_model_name, temperature=0
        )
        self.llm = self.base_llm.bind_tools(self.registry.tool_schemas)

    def research(self, state: dict[str, Any]) -> dict[str, Any]:
        state = validate_node_state(state, "researcher")
        query = state.get("query", "")
        plan = state.get("query_plan") or {}
        today = datetime.now().strftime("%Y-%m-%d")

        # Date cutoff: prefer per-request override from main.py, otherwise use config default
        cutoff_date = (
            state.get("cutoff_date_override") or agentic_settings.min_allowed_evidence_date
        )
        # Parse it once here — applied as a hard filter to every source we collect
        cutoff_dt = parse_min_date(cutoff_date)
        date_to_str = state.get("date_to_override")
        date_to_dt = parse_min_date(date_to_str) if date_to_str else None

        # Push per-request date bounds into the tool instances so their internal
        # pre-filters also use the correct dates for this request
        self.registry.tavily._min_date = cutoff_dt
        self.registry.mediastack._min_date = cutoff_dt
        raw_allowed_tools = state.get("allowed_tools")
        allowed_tools: list[str] | None = (
            raw_allowed_tools if isinstance(raw_allowed_tools, list) else None
        )

        # These 3 tools must all run in full-research mode.
        # I enforce this in code (not just the prompt) so the LLM can't skip any of them.
        _FULL_MANDATORY = [
            "search_tavily_specialist",
            "search_mediastack",
            "search_tavily_web",
        ]
        # Restricted mode kicks in only when the user has selected a strict subset of tools.
        # If all 4 tools are enabled (the default), I treat it as unrestricted.
        _allowed_set = frozenset(allowed_tools) if allowed_tools else frozenset()
        is_restricted = bool(allowed_tools) and not (_allowed_set >= frozenset(_FULL_MANDATORY))

        if is_restricted:
            allowed_tools_list = allowed_tools or []
            allowed_schemas = [
                s for s in self.registry.tool_schemas if s["function"]["name"] in allowed_tools_list
            ]
            llm = self.base_llm.bind_tools(allowed_schemas) if allowed_schemas else self.llm
            tool_instructions = RESEARCHER_TOOL_INSTRUCTIONS_RESTRICTED.format(
                available_tools_list="\n".join(f"- {t}" for t in allowed_tools_list)
            )
            # Only enforce the tools the user actually enabled
            mandatory_remaining: list[str] = [t for t in _FULL_MANDATORY if t in _allowed_set]
        else:
            llm = self.llm
            tool_instructions = RESEARCHER_TOOL_INSTRUCTIONS_FULL
            # Full mode: all 3 tools must be called
            mandatory_remaining = list(_FULL_MANDATORY)

        # Build optional refinement context injected from the previous synthesis pass
        refinement_hint = (state.get("refinement_hint") or "").strip()
        if refinement_hint:
            refinement_section = (
                "\n REFINEMENT CONTEXT (previous pass found weak evidence):\n"
                f"{refinement_hint}\n"
                "Focus your tool calls on the gaps described above — use different "
                "keywords, German-language terms, or narrower date ranges than last time.\n"
            )
            logger.info(f"Researcher: refinement pass — hint='{refinement_hint[:100]}'")
        else:
            refinement_section = ""

        user_prompt = RESEARCHER_REACT_PROMPT.format(
            query=query,
            query_type=plan.get("query_type", "simple"),
            entities=", ".join(plan.get("entities", [])) or "none identified",
            search_angles="\n  - ".join(plan.get("search_angles", [query])),
            today=today,
            cutoff_date=cutoff_date,
            refinement_section=refinement_section,
        )

        system_prompt = RESEARCHER_SYSTEM_PROMPT.format(
            tool_instructions=tool_instructions,
        )

        messages: list[Any] = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        scratchpad: list[dict[str, Any]] = []
        # Carry over sources from any previous pass; seen_urls keeps us from adding duplicates
        all_sources: list[dict[str, Any]] = list(state.get("all_sources", []))
        seen_urls: set[str] = set(state.get("seen_urls", []))
        total_cost = 0.0
        total_tokens = 0
        max_steps = agentic_settings.max_researcher_steps
        consecutive_zero_new = 0  # tracks how many calls in a row returned zero new sources

        for step_num in range(1, max_steps + 1):
            try:
                response = llm.invoke(messages)
                t_in, t_out, cost = extract_token_cost(
                    response,
                    agentic_settings.researcher_input_cost_per_token,
                    agentic_settings.researcher_output_cost_per_token,
                )
                total_cost += cost
                total_tokens += t_in + t_out
            except Exception as exc:
                logger.error(f"Researcher LLM error step {step_num}: {exc}")
                scratchpad.append(
                    ResearchStep(step=step_num, type="error", summary=str(exc)).model_dump()
                )
                break

            # LLM returned no tool call — it wants to stop
            if not response.tool_calls:
                thought = (response.content or "").strip()

                # Don't let it stop until all required tools have been called.
                # The LLM tends to stop early if the first results look good enough.
                if mandatory_remaining:
                    next_required = mandatory_remaining[0]
                    logger.info(
                        f"Researcher step {step_num}: LLM tried to stop early — "
                        f"mandatory sequence incomplete, forcing {next_required}"
                    )
                    force_msg = (
                        f"[System] You have NOT completed the required research sequence. "
                        f"You MUST still call: {', '.join(mandatory_remaining)}. "
                        f"Call {next_required} now before writing your final answer."
                    )
                    messages.append(HumanMessage(content=force_msg))
                    scratchpad.append(
                        ResearchStep(
                            step=step_num,
                            type="reformulation",
                            summary=(
                                "Forced to continue — mandatory steps remaining: "
                                f"{mandatory_remaining}"
                            ),
                        ).model_dump()
                    )
                    self._emit(
                        {
                            "type": "reformulation",
                            "step": step_num,
                            "summary": (
                                "Mandatory sequence incomplete — forcing " f"{next_required}"
                            ),
                        }
                    )
                    continue  # don't break — let the loop run another step

                logger.info(f"Researcher step {step_num}: mandatory sequence complete, done")
                scratchpad.append(
                    ResearchStep(step=step_num, type="thought", summary=thought[:200]).model_dump()
                )
                self._emit({"type": "thought", "step": step_num, "text": thought[:200]})
                break

            # Tool call
            tool_call = response.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # Mark this tool as completed in the mandatory sequence
            if tool_name in mandatory_remaining:
                mandatory_remaining.remove(tool_name)

            logger.info(f"Researcher step {step_num}: {tool_name}({json.dumps(tool_args)[:80]})")
            scratchpad.append(
                ResearchStep(
                    step=step_num,
                    type="action",
                    tool=tool_name,
                    args=tool_args,
                    summary=f"Calling {tool_name}",
                ).model_dump()
            )
            self._emit(
                {
                    "type": "action",
                    "step": step_num,
                    "tool": tool_name,
                    "args": tool_args,
                }
            )

            # Execute tool
            result: ToolResult = self.registry.call(tool_name, **tool_args)

            # Add new sources — skip anything we've already seen
            # or that's too old
            new_count = 0
            skipped_old = 0
            skipped_seen = 0
            if tool_name in _SOURCE_TOOLS and isinstance(result.data, list):
                for src in result.data:
                    url = src.get("url")
                    if url and url in seen_urls:
                        skipped_seen += 1
                        continue
                    # Drop anything outside the requested date window
                    pub = parse_date(src.get("published_at"))
                    if pub is not None and pub < cutoff_dt:
                        skipped_old += 1
                        continue
                    if date_to_dt is not None and pub is not None and pub > date_to_dt:
                        skipped_old += 1
                        continue
                    all_sources.append(src)
                    if url:
                        seen_urls.add(url)
                    new_count += 1
                logger.info(
                    f"  -> {new_count} new sources (total: {len(all_sources)})"
                    + (f" | skipped_seen={skipped_seen}" if skipped_seen else "")
                    + (f" | skipped_old={skipped_old}" if skipped_old else "")
                )

            # If the tool returned articles but they were all duplicates, tell the LLM that.
            # Otherwise it might act confident about sources it doesn't actually have.
            if result.success and tool_name in _SOURCE_TOOLS:
                if new_count == 0 and result.count > 0:
                    observation_text = (
                        f"{result.summary} — but ALL {result.count} were already seen "
                        f"(duplicate URLs). 0 new sources added. Try a different query or tool."
                    )
                elif new_count < result.count:
                    observation_text = (
                        f"{result.summary} — {new_count} new sources added "
                        f"({result.count - new_count} duplicates skipped)."
                    )
                else:
                    observation_text = f"{result.summary} — {new_count} new sources added."
            else:
                observation_text = result.summary if result.success else f"Error: {result.error}"
            scratchpad.append(
                ResearchStep(
                    step=step_num,
                    type="observation",
                    tool=tool_name,
                    count=result.count,
                    summary=observation_text,
                ).model_dump()
            )
            self._emit(
                {
                    "type": "observation",
                    "step": step_num,
                    "tool": tool_name,
                    "count": result.count,
                    "summary": observation_text,
                }
            )

            messages.append(
                AIMessage(
                    content=response.content or "",
                    tool_calls=[tool_call],
                )
            )
            messages.append(
                ToolMessage(
                    content=observation_text,
                    tool_call_id=tool_call["id"],
                )
            )

            # Track how many source tool calls in a row returned nothing new
            if tool_name in _SOURCE_TOOLS:
                if new_count == 0:
                    consecutive_zero_new += 1
                else:
                    consecutive_zero_new = 0

            # If two calls in a row found zero new sources, We've hit the bottom of what's
            # available. No point spending more LLM calls on reformulations.
            if consecutive_zero_new >= 2 and step_num < max_steps:
                logger.info(
                    f"Researcher: {consecutive_zero_new} consecutive zero-new-source calls "
                    f"— tool pool exhausted, stopping early"
                )
                scratchpad.append(
                    ResearchStep(
                        step=step_num,
                        type="thought",
                        summary=(
                            "Tool exhausted after "
                            f"{consecutive_zero_new} zero-new calls — stopping"
                        ),
                    ).model_dump()
                )
                self._emit(
                    {
                        "type": "thought",
                        "step": step_num,
                        "text": "All available sources already collected — stopping search.",
                    }
                )
                break

            # Nudge the LLM to try different keywords if results were thin.
            # We skip this for MediaStack — it often only returns 1-2 timber articles
            # by design, so nudging it just produces duplicate noise.
            # We check new_count (not raw fetched) so the LLM knows why we're asking
            # it to change tack.
            if (
                tool_name in _SOURCE_TOOLS
                and tool_name != "search_mediastack"
                and new_count < agentic_settings.weak_result_threshold
                and step_num < max_steps - 1
            ):
                search_angles = plan.get("search_angles", [])
                alternatives = (
                    ", ".join(search_angles[:3])
                    if search_angles
                    else "broader or German-language terms"
                )
                reformulation_nudge = (
                    f"[Research Note] {tool_name} fetched {result.count} article(s) but only "
                    f"{new_count} were new (the rest were already seen). "
                    f"Insufficient new coverage. On your next call try a DIFFERENT keyword "
                    f"or angle. Consider: {alternatives}. "
                    f"If you used an English term, try the German equivalent (e.g. 'Holzpreis', "
                    f"'Schnittholz', 'Bauholz', 'Forstwirtschaft')."
                )
                messages.append(HumanMessage(content=reformulation_nudge))
                scratchpad.append(
                    ResearchStep(
                        step=step_num,
                        type="reformulation",
                        summary=(
                            f"Weak results ({new_count} new from {tool_name}) — "
                            "reformulation nudge injected"
                        ),
                    ).model_dump()
                )
                self._emit(
                    {
                        "type": "reformulation",
                        "step": step_num,
                        "summary": (
                            f"Only {new_count} new source(s) from {tool_name} — "
                            "nudging LLM to reformulate"
                        ),
                    }
                )
                logger.info(
                    f"  -> mid-loop reformulation: {new_count} new sources from {tool_name} "
                    f"(threshold={agentic_settings.weak_result_threshold})"
                )

            # Early-stop: enough sources accumulated
            if len(all_sources) >= agentic_settings.max_sources_to_rank:
                logger.info(f"Researcher: reached source cap ({len(all_sources)}), stopping")
                break

        logger.info(
            f"Researcher done: {len(all_sources)} sources | "
            f"{len(scratchpad)} steps | cost=${total_cost:.6f}"
        )

        # Save seen URLs so a second research pass doesn't re-fetch the same articles
        new_seen = list(seen_urls)

        is_refinement_pass = bool(refinement_hint)
        step_label = (
            f"refined_{len(all_sources)}_sources"
            if is_refinement_pass
            else f"researched_{len(all_sources)}_sources"
        )

        return {
            **state,
            "all_sources": all_sources,
            "seen_urls": new_seen,
            "retrieval_count": state.get("retrieval_count", 0) + 1,
            "researcher_scratchpad": scratchpad,
            "needs_refinement": False,
            "refinement_hint": "",
            "steps": state.get("steps", []) + [step_label],
            "llm_calls": state.get("llm_calls", 0)
            + len([s for s in scratchpad if s["type"] == "action"])
            + 1,
            "cost_usd": state.get("cost_usd", 0.0) + total_cost,
            "total_tokens": state.get("total_tokens", 0) + total_tokens,
        }

    def _emit(self, event: dict[str, Any]) -> None:
        """Push a live event to the streaming callback, if one is registered."""
        if self.event_callback:
            with suppress(Exception):
                self.event_callback(event)
