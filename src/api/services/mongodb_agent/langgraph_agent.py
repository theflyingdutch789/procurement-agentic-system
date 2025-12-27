"""
LangGraph wrapper around the core GPT MongoDB agent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .agent import GPT5MongoDBAgent
from .executor import MongoDBQueryExecutor
from .validators import QueryValidator


class AgentState(TypedDict, total=False):
    question: str
    conversation_history: Optional[List[Dict[str, Any]]]
    attempt: int
    max_attempts: int
    reasoning_effort: str
    verbosity: str
    pipeline: Optional[List[Dict[str, Any]]]
    pipeline_response_id: Optional[str]
    latest_response: Optional[Any]
    previous_error: Optional[str]
    previous_response_id: Optional[str]
    results: Optional[List[Dict[str, Any]]]
    answer: Optional[str]
    error: Optional[str]
    reasoning_summary: Optional[str]
    response_id: Optional[str]


class LangGraphMongoDBAgent:
    """LangGraph orchestration layer that adds retries and summarisation."""

    def __init__(self, base_agent: GPT5MongoDBAgent, max_attempts: int = 3):
        self.base = base_agent
        self.max_attempts = max_attempts
        self.app = self._build_graph()

    @property
    def model_name(self) -> str:
        return self.base.model_name

    @model_name.setter
    def model_name(self, value: str) -> None:
        self.base.model_name = value

    @property
    def reasoning_effort(self) -> str:
        return self.base.reasoning_effort

    @reasoning_effort.setter
    def reasoning_effort(self, value: str) -> None:
        self.base.reasoning_effort = value

    @property
    def verbosity(self) -> str:
        return self.base.verbosity

    @verbosity.setter
    def verbosity(self, value: str) -> None:
        self.base.verbosity = value

    @property
    def executor(self) -> MongoDBQueryExecutor:
        return self.base.executor

    @property
    def validator(self) -> QueryValidator:
        return self.base.validator

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("generate_pipeline", self._generate_pipeline_node)
        graph.add_node("run_pipeline", self._run_pipeline_node)
        graph.add_node("summarize", self._summarize_node)

        graph.set_entry_point("generate_pipeline")

        graph.add_conditional_edges(
            "generate_pipeline",
            self._after_generate,
            {
                "run": "run_pipeline",
                "retry": "generate_pipeline",
                "stop": END,
            },
        )

        graph.add_conditional_edges(
            "run_pipeline",
            self._after_run,
            {
                "summarize": "summarize",
                "retry": "generate_pipeline",
                "stop": END,
            },
        )

        graph.add_edge("summarize", END)

        return graph.compile()

    def _generate_pipeline_node(self, state: AgentState) -> AgentState:
        attempt = state.get("attempt", 0) + 1
        state["attempt"] = attempt

        pipeline, response_id, latest_response, error = self.base._generate_pipeline_attempt(
            question=state["question"],
            conversation_history=state.get("conversation_history"),
            previous_error=state.get("previous_error"),
            previous_response_id=state.get("previous_response_id"),
            reasoning_effort=state.get("reasoning_effort", self.base.reasoning_effort),
        )

        state["pipeline"] = pipeline
        state["pipeline_response_id"] = response_id
        state["latest_response"] = latest_response
        state["previous_response_id"] = response_id
        state["error"] = error
        state["previous_error"] = error

        return state

    def _after_generate(self, state: AgentState) -> str:
        if state.get("pipeline"):
            return "run"
        if state.get("attempt", 0) >= state.get("max_attempts", self.max_attempts):
            return "stop"
        return "retry"

    def _run_pipeline_node(self, state: AgentState) -> AgentState:
        pipeline = state.get("pipeline")
        if not pipeline:
            return state

        is_valid, validation_error = self.base._validate_pipeline(pipeline)
        if not is_valid:
            state["error"] = validation_error
            state["previous_error"] = validation_error
            state["pipeline"] = None
            return state

        success, result, execution_error = self.base._execute_pipeline(pipeline)
        if not success:
            state["error"] = execution_error
            state["previous_error"] = execution_error
            state["pipeline"] = None
            return state

        state["results"] = result
        state["error"] = None
        state["previous_error"] = None
        return state

    def _after_run(self, state: AgentState) -> str:
        if state.get("error"):
            if state.get("attempt", 0) >= state.get("max_attempts", self.max_attempts):
                return "stop"
            return "retry"
        return "summarize"

    def _summarize_node(self, state: AgentState) -> AgentState:
        pipeline = state.get("pipeline") or []
        results = state.get("results") or []
        pipeline_response_id = state.get("pipeline_response_id")
        latest_response = state.get("latest_response")

        answer, answer_response_id, reasoning_summary = self.base._summarize_answer(
            question=state["question"],
            pipeline=pipeline,
            result=results,
            verbosity=state.get("verbosity", self.base.verbosity),
            pipeline_response_id=pipeline_response_id,
            latest_response=latest_response,
        )

        state["answer"] = answer
        state["response_id"] = answer_response_id
        state["reasoning_summary"] = reasoning_summary
        state["error"] = None
        return state

    def query(
        self,
        question: str,
        reasoning_effort: Optional[str] = None,
        verbosity: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> Dict[str, Any]:
        state: AgentState = {
            "question": question,
            "conversation_history": conversation_history,
            "attempt": 0,
            "max_attempts": self.max_attempts,
            "reasoning_effort": reasoning_effort or self.base.reasoning_effort,
            "verbosity": verbosity or self.base.verbosity,
            "previous_response_id": previous_response_id,
        }

        final_state = self.app.invoke(state)

        if final_state.get("answer"):
            results = final_state.get("results") or []
            return {
                "success": True,
                "answer": final_state.get("answer"),
                "pipeline": final_state.get("pipeline"),
                "results": results,
                "result_count": len(results),
                "reasoning_summary": final_state.get("reasoning_summary"),
                "response_id": final_state.get("response_id"),
                "error": None,
                "timestamp": datetime.utcnow().isoformat(),
            }

        return {
            "success": False,
            "answer": None,
            "pipeline": final_state.get("pipeline"),
            "results": final_state.get("results"),
            "reasoning_summary": final_state.get("reasoning_summary"),
            "error": final_state.get("error") or "Failed to generate MongoDB pipeline",
            "timestamp": datetime.utcnow().isoformat(),
        }
