# ruff: noqa: E402, E501
"""
Timber Market Intelligence API — aligned with ReAct Agentic RAG pipeline.
Provides endpoints for both baseline and agentic RAG,
with detailed streaming events for the latter.
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from agentic_rag.configuration import agentic_settings
from agentic_rag.utils import is_pure_social, is_temporal_query
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from rag_baseline.orchestration.rag_pipeline import RAGPipeline

APP_VERSION = "6.0.0"

STEP_INFO: dict[str, dict[str, str]] = {
    # Planner
    "planned": {
        "title": "Query Planning",
        "desc": "Classifying intent and planning retrieval strategy",
    },
    # Researcher
    "researched": {
        "title": "Researcher",
        "desc": "ReAct agent selecting and calling retrieval tools",
    },
    # Ranker
    "ranked": {"title": "Source Ranking", "desc": "Triaging sources by likely relevance"},
    "ranked_passthrough": {
        "title": "Source Ranking (passthrough)",
        "desc": "Source count within budget — no ranking needed",
    },
    "ranked_no_sources": {"title": "No Sources to Rank", "desc": "No articles retrieved to rank"},
    # Verifier
    "verified": {
        "title": "Evidence Verification",
        "desc": "LLM reading sources and selecting relevant evidence",
    },
    "verification_no_sources": {
        "title": "No Sources Found",
        "desc": "No articles retrieved to verify",
    },
    # Synthesizer
    "out_of_scope": {"title": "Out of Scope", "desc": "Query outside German timber market scope"},
    "synthesis_no_sources": {
        "title": "No Relevant Sources",
        "desc": "LLM found no sufficiently relevant evidence",
    },
    "answer_synthesized": {
        "title": "Answer Synthesized",
        "desc": "Answer written from verified sources",
    },
    "answer_refined": {
        "title": "Answer Refined",
        "desc": "Answer rewritten after a second research pass",
    },
    # Researcher refinement pass
    "refinement_triggered": {
        "title": "Refinement Triggered",
        "desc": "Evidence was weak — launching targeted second research pass",
    },
    # Special
    "cache_hit": {"title": "Cached Response", "desc": "Returning a previous answer from cache"},
    "conversational": {"title": "Conversational Reply", "desc": "Social message handled directly"},
    "fallback": {"title": "Fallback Response", "desc": "Fallback conversational reply"},
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Fix duplicate log entries: uvicorn and the app both attach handlers to the
    # root logger, causing each agentic_rag log line to appear 2-3 times.
    _rag_logger = logging.getLogger("agentic_rag")
    _rag_logger.propagate = False
    if not _rag_logger.handlers:
        _handler = logging.StreamHandler()
        _handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S,%f"
            )
        )
        _rag_logger.addHandler(_handler)
    _rag_logger.setLevel(logging.INFO)

    print("Initialising RAG pipelines...")

    print("  - Baseline RAG pipeline...")
    app.state.baseline_pipeline = RAGPipeline(use_hybrid=True)
    print("  ✓ Baseline RAG ready")

    print("  - Agentic RAG pipeline...")
    try:
        from agentic_rag.pipeline import AgenticRAGPipeline

        app.state.agentic_pipeline = AgenticRAGPipeline(enable_memory=True)
        print("  ✓ Agentic RAG ready (ReAct Researcher)")
    except Exception as exc:
        logging.getLogger(__name__).error(f"Agentic init failed: {exc}")
        app.state.agentic_pipeline = None

    print("All systems ready!")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Timber Market Intelligence API",
    description="Baseline and Agentic RAG for German timber market intelligence",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request / Response Models


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    mode: str = Field("baseline", pattern="^(baseline|agentic)$")
    use_hybrid: bool = True
    top_k: int = Field(5, ge=1, le=10)
    allowed_tools: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None


class SourceResponse(BaseModel):
    source: str | None = None
    source_type: str | None = None
    title: str | None = None
    url: str | None = None
    content: str
    score: float
    keywords: list[str] = []
    published_at: str | None = None


class BaselineQueryResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    response_time: float
    search_type: str
    timestamp: str
    mode: str = "baseline"
    cost_usd: float = 0.0
    total_tokens: int = 0
    llm_calls: int = 1


class AgenticQueryResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    confidence: float
    reasoning_steps: list[str]
    llm_calls: int
    retrieval_iterations: int
    response_time: float
    cached: bool
    query_type: str
    timestamp: str
    mode: str = "agentic"
    is_domain_relevant: bool = True
    cost_usd: float = 0.0
    total_tokens: int = 0
    evidence_summary: str = ""
    key_facts: list[str] = []
    researcher_scratchpad: list[dict[str, Any]] = []


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    pipelines: dict[str, str]


# Helpers


def _resolve_step_name(step: str) -> str:
    for key in STEP_INFO:
        if step.startswith(key):
            return key
    return step


#  Endpoints


@app.get("/", response_model=dict[str, str])  # type: ignore[misc]
def root() -> dict[str, str]:
    return {
        "message": f"Timber Market Intelligence API v{APP_VERSION}",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)  # type: ignore[misc]
def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version=APP_VERSION,
        pipelines={
            "baseline": "ready",
            "agentic": "ready" if app.state.agentic_pipeline else "unavailable",
        },
    )


@app.get("/coverage")  # type: ignore[misc]
def get_coverage() -> dict[str, Any]:
    if app.state.agentic_pipeline:
        result: dict[str, Any] = app.state.agentic_pipeline.get_coverage_info()
        return result
    return {"note": "Agentic pipeline unavailable"}


@app.post("/query/baseline", response_model=BaselineQueryResponse)  # type: ignore[misc]
async def query_baseline_rag(request: QueryRequest) -> BaselineQueryResponse:
    start_time = time.time()
    try:
        rag: RAGPipeline = app.state.baseline_pipeline
        rag.use_hybrid = request.use_hybrid
        sources = rag.retriever.retrieve(request.question, use_hybrid=request.use_hybrid)
        # Only pass relevant sources to the generator and return to the client.
        # Scores near zero mean the query has no match in the knowledge base.
        # RRF hybrid scores top out at ~0.016; cosine vector scores range 0-1
        MIN_SCORE = 0.005 if request.use_hybrid else 0.10
        relevant_sources = [s for s in sources[: request.top_k] if s.similarity_score >= MIN_SCORE]
        answer, total_tokens, cost_usd = rag.generator.generate(request.question, relevant_sources)
        # If the LLM signals it has no relevant information, suppress all sources.
        _no_info_phrases = (
            "don't have that information",
            "don't have information",
            "no relevant information",
            "cannot answer",
            "not able to answer",
        )
        answer_lower = answer.lower()
        sources_to_return = (
            [] if any(p in answer_lower for p in _no_info_phrases) else relevant_sources
        )
        formatted_sources = [
            SourceResponse(
                source=source.source,
                source_type="baseline",
                title=source.title,
                url=source.url,
                content=source.content[:400] + "..."
                if len(source.content) > 400
                else source.content,
                score=source.similarity_score,
                keywords=source.keywords[:5] if source.keywords else [],
                published_at=str(source.published_at) if source.published_at else None,
            )
            for source in sources_to_return
        ]
        return BaselineQueryResponse(
            answer=answer,
            sources=formatted_sources,
            response_time=round(time.time() - start_time, 2),
            search_type="hybrid" if request.use_hybrid else "vector",
            timestamp=datetime.now().isoformat(),
            cost_usd=cost_usd,
            total_tokens=total_tokens,
            llm_calls=1,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/query/agentic", response_model=AgenticQueryResponse)  # type: ignore[misc]
async def query_agentic_rag(request: QueryRequest) -> AgenticQueryResponse:
    start_time = time.time()
    try:
        if not app.state.agentic_pipeline:
            raise HTTPException(status_code=503, detail="Agentic pipeline unavailable")
        result = app.state.agentic_pipeline.answer(request.question)
        return AgenticQueryResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            confidence=float(result.get("confidence", 0.0)),
            reasoning_steps=result.get("reasoning_steps", []),
            llm_calls=result.get("llm_calls", 0),
            retrieval_iterations=result.get("retrieval_iterations", 0),
            response_time=round(time.time() - start_time, 2),
            cached=result.get("cached", False),
            query_type=result.get("query_type", "unknown"),
            timestamp=datetime.now().isoformat(),
            is_domain_relevant=result.get("is_domain_relevant", True),
            cost_usd=result.get("cost_usd", 0.0),
            total_tokens=result.get("total_tokens", 0),
            evidence_summary=result.get("evidence_summary", ""),
            key_facts=result.get("key_facts", []),
            researcher_scratchpad=result.get("researcher_scratchpad", []),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/query/agentic/stream")  # type: ignore[misc]
async def query_agentic_stream(request: QueryRequest) -> StreamingResponse:
    """
    Agentic RAG with step-by-step SSE streaming.

    Streams three event categories:
    - step events: named pipeline steps (planned, researched, ranked, verified, ...)
    - researcher events: thought / action / observation from the ReAct loop
    - result: final answer and metadata
    """
    if not app.state.agentic_pipeline:

        async def _error() -> AsyncIterator[str]:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Pipeline unavailable'})}\n\n"

        return StreamingResponse(_error(), media_type="text/event-stream")

    async def generate_stream() -> AsyncIterator[str]:
        try:
            pipeline = app.state.agentic_pipeline
            loop = asyncio.get_running_loop()
            queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
            start_time = time.time()

            # Thread-safe put: call_soon_threadsafe schedules put_nowait on the
            # event loop without creating a coroutine — correct pattern for sync→async.
            def _put(item: tuple[str, Any]) -> None:
                loop.call_soon_threadsafe(queue.put_nowait, item)

            def event_callback(event: dict[str, Any]) -> None:
                _put(("researcher", event))

            def run_sync_workflow() -> None:
                try:
                    question = request.question

                    if is_pure_social(question):
                        result = pipeline.conversational_handler.respond(question)
                        if result:
                            result["mode"] = "agentic"
                            result["response_time"] = round(time.time() - start_time, 2)
                            _put(("step", "conversational"))
                            _put(("result", result))
                        return

                    if (
                        pipeline.memory
                        and agentic_settings.enable_query_cache
                        and not is_temporal_query(question)
                    ):
                        cached = pipeline.memory.check_query_cache(question)
                        if cached:
                            result = {
                                "answer": cached["answer"],
                                "sources": [],
                                "confidence": 0.85,
                                "cached": True,
                                "reasoning_steps": ["cache_hit"],
                                "retrieval_iterations": 0,
                                "llm_calls": 0,
                                "query_type": "cached",
                                "intent": "cached",
                                "cost_usd": 0.0,
                                "total_tokens": 0,
                                "mode": "agentic",
                                "response_time": round(time.time() - start_time, 2),
                                "evidence_summary": "",
                                "key_facts": [],
                                "researcher_scratchpad": [],
                            }
                            _put(("step", "cache_hit"))
                            _put(("result", result))
                            return

                    from agentic_rag.graph import create_agentic_graph

                    workflow = create_agentic_graph(
                        memory=pipeline.memory,
                        event_callback=event_callback,
                    )

                    initial_state = pipeline._build_initial_state(question)
                    if request.allowed_tools:
                        initial_state["allowed_tools"] = request.allowed_tools
                    if request.date_from:
                        initial_state["cutoff_date_override"] = request.date_from
                    if request.date_to:
                        initial_state["date_to_override"] = request.date_to

                    prev_step_count = 0
                    last_state: dict[str, Any] = {}

                    for state_snapshot in workflow.stream(initial_state, stream_mode="values"):
                        last_state = state_snapshot
                        current_steps = list(state_snapshot.get("steps", []))
                        for step in current_steps[prev_step_count:]:
                            _put(("step", step))
                        prev_step_count = len(current_steps)

                    if last_state:
                        result = pipeline._extract_result(last_state)
                        result["mode"] = "agentic"
                        result["response_time"] = round(time.time() - start_time, 2)
                        pipeline._save_to_memory(question, result, last_state)
                        _put(("result", result))
                    else:
                        _put(("error", "Workflow produced no state"))

                except Exception as exc:
                    _put(("error", str(exc)))
                finally:
                    _put(("done", None))

            # Run the blocking LangGraph workflow in asyncio's managed thread pool
            asyncio.ensure_future(asyncio.to_thread(run_sync_workflow))

            yield f"data: {json.dumps({'type': 'start', 'message': 'Starting ReAct workflow...'})}\n\n"

            while True:
                try:
                    event_type, data = await asyncio.wait_for(queue.get(), timeout=180.0)
                except TimeoutError:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Request timed out'})}\n\n"
                    break

                if event_type == "step":
                    base_step = _resolve_step_name(data)
                    info = STEP_INFO.get(base_step, {"title": data, "desc": ""})
                    yield f"data: {json.dumps({'type': 'step', 'step': data, 'base_step': base_step, 'title': info['title'], 'desc': info['desc']})}\n\n"

                elif event_type == "researcher":
                    etype = data.get("type")
                    if etype == "thought":
                        yield f"data: {json.dumps({'type': 'thought', 'step': data.get('step', 0), 'text': data.get('text', '')})}\n\n"
                    elif etype == "action":
                        yield f"data: {json.dumps({'type': 'action', 'step': data.get('step', 0), 'tool': data.get('tool', ''), 'args': data.get('args', {})})}\n\n"
                    elif etype == "observation":
                        yield f"data: {json.dumps({'type': 'observation', 'step': data.get('step', 0), 'tool': data.get('tool', ''), 'count': data.get('count', 0), 'summary': data.get('summary', '')})}\n\n"

                elif event_type == "result":
                    yield f"data: {json.dumps({'type': 'result', 'data': data})}\n\n"

                elif event_type == "error":
                    yield f"data: {json.dumps({'type': 'error', 'message': data})}\n\n"
                    break

                elif event_type == "done":
                    yield f"data: {json.dumps({'type': 'complete'})}\n\n"
                    break

        except Exception as exc:
            # Top-level guard: catch errors in the generator itself
            yield f"data: {json.dumps({'type': 'error', 'message': f'Stream error: {exc}'})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Memory & Cost Endpoints


@app.post("/agentic/memory/clear")  # type: ignore[misc]
async def clear_memory() -> dict[str, Any]:
    if not app.state.agentic_pipeline:
        raise HTTPException(status_code=503, detail="Pipeline unavailable")
    app.state.agentic_pipeline.clear_memory()
    return {"status": "success", "message": "Memory cleared"}


@app.get("/agentic/memory/summary")  # type: ignore[misc]
async def get_memory_summary() -> dict[str, Any]:
    if not app.state.agentic_pipeline:
        return {"error": "Pipeline unavailable"}
    result: dict[str, Any] = app.state.agentic_pipeline.get_conversation_summary()
    return result


@app.get("/agentic/cost")  # type: ignore[misc]
async def get_session_cost() -> dict[str, Any]:
    if not app.state.agentic_pipeline:
        return {"error": "Pipeline unavailable"}
    cost_data: dict[str, Any] = app.state.agentic_pipeline.get_session_cost()
    cost_data["researcher_model"] = agentic_settings.researcher_model_name
    cost_data["verifier_model"] = agentic_settings.verifier_model_name
    cost_data["planner_model"] = agentic_settings.chat_model_name
    return cost_data


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
