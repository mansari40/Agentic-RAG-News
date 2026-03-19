"""State types and validation for the agentic pipeline."""

import operator
from collections.abc import Sequence
from typing import Annotated, Any, TypedDict

import structlog
from pydantic import BaseModel, ValidationError, field_validator

logger = structlog.get_logger(__name__)


class NodeStateValidator(BaseModel):
    """
    Checks the pipeline state at each node boundary.
    If a field is missing or has the wrong type, it fills in a safe default
    and logs a warning so the issue is easy to spot.
    """

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    query: str = ""
    intent: str = "domain"
    is_domain_relevant: bool = True
    research_mode: str = "full_research"
    query_type: str = "simple"
    complexity: str = "moderate"
    entities: list[str] = []
    search_angles: list[str] = []
    all_sources: list[dict[str, Any]] = []
    ranked_sources: list[dict[str, Any]] = []
    verified_sources: list[dict[str, Any]] = []
    seen_urls: list[str] = []
    key_facts: list[str] = []
    evidence_summary: str = ""
    confidence_score: float = 0.0
    llm_calls: int = 0
    cost_usd: float = 0.0
    total_tokens: int = 0
    needs_refinement: bool = False
    refinement_hint: str = ""
    refinement_count: int = 0
    steps: list[str] = []

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()

    @field_validator("confidence_score")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


def validate_node_state(state: dict[str, Any], node_name: str) -> dict[str, Any]:
    """
    Run state validation before a node executes.

    Returns the same dict with any missing or bad fields filled in with safe defaults.
    Logs a warning for each problem so you can trace it without crashing the run.
    """
    try:
        validated = NodeStateValidator.model_validate(state)
        # Write defaults back for anything that was missing or invalid
        for field_name, field_val in validated.model_dump(exclude_unset=False).items():
            if field_name not in state or state[field_name] is None:
                state[field_name] = field_val
    except ValidationError as exc:
        for err in exc.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            logger.warning(
                f"[{node_name}] State validation: field='{field}' "
                f"issue='{err['msg']}' — using default"
            )
    return state


class AgenticState(TypedDict):
    # User's question and detected intent
    query: str
    intent: str

    # What the Planner figured out about the query
    query_plan: dict[str, Any] | None
    query_type: str
    entities: list[str]
    search_angles: list[str]
    temporal_info: dict[str, str] | None
    complexity: str
    is_follow_up: bool
    is_domain_relevant: bool
    domain_relevance_reason: str
    research_mode: str
    sub_queries: list[str]
    use_hybrid: bool
    top_k: int
    complexity_score: float

    # Everything the Researcher fetched
    all_sources: list[dict[str, Any]]
    retrieval_count: int
    seen_urls: list[str]

    # Ranker's shortlist
    ranked_sources: list[dict[str, Any]]

    # What the Verifier approved
    verified_sources: list[dict[str, Any]]
    key_facts: list[str]
    evidence_summary: str
    confidence_score: float
    off_topic_indices: list[int]

    # Step-by-step log of what the Researcher did
    researcher_scratchpad: list[dict[str, Any]]

    # Final output
    answer: str
    citations: list[dict[str, Any]]

    # Running totals for cost tracking
    cost_usd: float
    total_tokens: int

    # Pipeline step log and LLM call count
    steps: Annotated[Sequence[str], operator.add]
    llm_calls: int

    # Previous conversation context passed in from memory
    conversation_context: dict[str, Any]

    # Optional per-request overrides from the frontend
    allowed_tools: list[str] | None
    cutoff_date_override: str | None

    # Refinement loop state (synthesizer flags weak answers, researcher retries)
    needs_refinement: bool
    refinement_hint: str
    refinement_count: int
