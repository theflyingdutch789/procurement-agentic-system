"""Query engine orchestration and hybrid fallback logic."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from openai import OpenAI
from pymongo import MongoClient

from langgraph.graph import END, StateGraph

from .executor import QueryExecutor
from .intent_sanitizer import sanitize_intent
from .intent_extractor import IntentExtractor
from .models.intent import AggregateFunction, DimensionField, MetricField, QueryAction, QueryIntent
from .query_builder import QueryBuilder
from .summarizer import ResponseSummarizer
from .validator import QueryValidator
from ..ai_pipeline_agent import GPT5MongoDBAgent, LangGraphMongoDBAgent

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Production-ready query engine with clean architecture.

    Flow:
    1. Intent Extraction (AI) -> Structured Intent
    2. Validation (Code) -> Validated Intent
    3. Query Building (Code) -> MongoDB Pipeline
    4. Pipeline Validation (Code) -> Validated Pipeline
    5. Execution (Code) -> Results
    6. Summarization (AI) -> Natural Language Response
    """

    def __init__(
        self,
        *,
        mongo_client: MongoClient,
        database_name: str,
        collection_name: str,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-5",
        intent_model_name: str = "gpt-5-mini",
        summary_model_name: str = "gpt-5-mini",
        max_results: int = 100,
    ) -> None:
        self._model_name = model
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else OpenAI()
        self.collection = mongo_client[database_name][collection_name]

        self._intent_model_name = intent_model_name
        self._summary_model_name = summary_model_name
        self.intent_extractor = IntentExtractor(self.client, intent_model_name)
        self.query_builder = QueryBuilder()
        self.validator = QueryValidator()
        self.executor = QueryExecutor(self.collection, max_results=max_results)
        self.summarizer = ResponseSummarizer(self.client, summary_model_name)

        self.logger = logging.getLogger(__name__)

    @property
    def model_name(self) -> str:
        return self._model_name

    @model_name.setter
    def model_name(self, value: str) -> None:
        self._model_name = value

    @property
    def intent_model_name(self) -> str:
        return self._intent_model_name

    @intent_model_name.setter
    def intent_model_name(self, value: str) -> None:
        self._intent_model_name = value
        self.intent_extractor.set_model_name(value)

    @property
    def summary_model_name(self) -> str:
        return self._summary_model_name

    @summary_model_name.setter
    def summary_model_name(self, value: str) -> None:
        self._summary_model_name = value
        self.summarizer.set_model_name(value)

    def query(
        self,
        question: str,
        *,
        conversation_context: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        verbosity: str = "medium",
    ) -> Dict[str, Any]:
        try:
            self.logger.info("Extracting intent for: %s", question)
            intent = self.intent_extractor.extract(question, conversation_context)
            self.logger.info("Extracted intent: %s", intent.action)

            if intent.is_ambiguous:
                return self._clarification_response(intent)

            intent = sanitize_intent(question, intent)

            # Check again after sanitization - ambiguity detector may have flagged it
            if intent.is_ambiguous:
                return self._clarification_response(intent)

            valid, error = self.validator.validate_intent(intent)
            if not valid:
                return self._error_response(f"Invalid intent: {error}")

            pipeline = self.query_builder.build(intent)
            self.logger.info("Built pipeline with %d stages", len(pipeline))

            valid, error = self.validator.validate_pipeline(pipeline)
            if not valid:
                return self._error_response(f"Invalid pipeline: {error}")

            results, execution_time = self.executor.execute(pipeline)
            self.logger.info("Query returned %d results in %.2fs", len(results), execution_time)

            answer, response_id = self.summarizer.summarize(
                question,
                results,
                intent,
                verbosity=verbosity,
                previous_response_id=previous_response_id,
            )

            return {
                "success": True,
                "answer": answer,
                "results": results,
                "result_count": len(results),
                "pipeline": pipeline,
                "intent": intent.model_dump(),
                "response_id": response_id,
                "reasoning_summary": None,
                "error": None,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as exc:
            self.logger.error("Query failed: %s", exc, exc_info=True)
            return self._error_response(str(exc))

    def _clarification_response(self, intent: QueryIntent) -> Dict[str, Any]:
        clarification_prompt = intent.ambiguity_reason or "I need clarification to answer that question."
        prompt = clarification_prompt
        if intent.suggested_interpretations:
            suggestions = "\n".join(f"- {item}" for item in intent.suggested_interpretations)
            prompt = f"{prompt}\nPossible interpretations:\n{suggestions}"

        return {
            "success": False,
            "answer": prompt,
            "needs_clarification": True,
            "clarification_prompt": clarification_prompt,
            "suggestions": intent.suggested_interpretations,
            "results": None,
            "result_count": None,
            "pipeline": None,
            "intent": intent.model_dump(),
            "response_id": None,
            "reasoning_summary": None,
            "error": "Ambiguous query",
            "execution_time": None,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _error_response(self, error: str) -> Dict[str, Any]:
        return {
            "success": False,
            "answer": error,
            "results": None,
            "result_count": None,
            "pipeline": None,
            "reasoning_summary": None,
            "error": error,
            "execution_time": None,
            "timestamp": datetime.utcnow().isoformat(),
        }


class _ExecutorProxy:
    def __init__(self, engine: "HybridQueryEngine") -> None:
        self._engine = engine

    @property
    def max_results(self) -> int:
        return self._engine.max_results

    @max_results.setter
    def max_results(self, value: int) -> None:
        self._engine.set_max_results(value)


class HybridAgentState(TypedDict, total=False):
    question: str
    conversation_history: Optional[List[Dict[str, Any]]]
    reasoning_effort: Optional[str]
    verbosity: Optional[str]
    previous_response_id: Optional[str]
    is_clarification_response: bool
    intent: Optional[QueryIntent]
    route: Optional[str]
    response: Optional[Dict[str, Any]]
    error: Optional[str]


class HybridQueryEngine:
    """Hybrid mode: use deterministic query engine when supported, fallback otherwise."""

    SUPPORTED_ACTIONS = {
        QueryAction.LIST,
        QueryAction.COUNT,
        QueryAction.TOP_N,
        QueryAction.BOTTOM_N,
        QueryAction.AGGREGATE,
        QueryAction.SINGLE_VALUE,
        QueryAction.COMPARE,
        QueryAction.TREND,
    }

    def __init__(
        self,
        *,
        mongo_client: MongoClient,
        database_name: str,
        collection_name: str,
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-5",
        reasoning_effort: str = "medium",
        verbosity: str = "medium",
        max_results: int = 100,
    ) -> None:
        self.deterministic_engine = QueryEngine(
            mongo_client=mongo_client,
            database_name=database_name,
            collection_name=collection_name,
            openai_api_key=openai_api_key,
            model=model_name,
            intent_model_name="gpt-5-mini",
            summary_model_name="gpt-5-mini",
            max_results=max_results,
        )

        base_agent = GPT5MongoDBAgent(
            mongo_client=mongo_client,
            database_name=database_name,
            collection_name=collection_name,
            openai_api_key=openai_api_key,
            model_name=model_name,
            reasoning_effort=reasoning_effort,
            verbosity=verbosity,
            max_results=max_results,
        )
        self.fallback_agent = LangGraphMongoDBAgent(base_agent)

        self._model_name = model_name
        self._reasoning_effort = reasoning_effort
        self._verbosity = verbosity
        self._max_results = max_results

        self.executor = _ExecutorProxy(self)
        self.logger = logging.getLogger(__name__)
        self.app = self._build_graph()

    @property
    def model_name(self) -> str:
        return self._model_name

    @model_name.setter
    def model_name(self, value: str) -> None:
        self._model_name = value
        self.fallback_agent.model_name = value

    @property
    def reasoning_effort(self) -> str:
        return self._reasoning_effort

    @reasoning_effort.setter
    def reasoning_effort(self, value: str) -> None:
        self._reasoning_effort = value
        self.fallback_agent.reasoning_effort = value

    @property
    def verbosity(self) -> str:
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value: str) -> None:
        self._verbosity = value
        self.fallback_agent.verbosity = value

    @property
    def max_results(self) -> int:
        return self._max_results

    def set_max_results(self, value: int) -> None:
        self._max_results = value
        self.deterministic_engine.executor.max_results = value
        self.fallback_agent.executor.max_results = value

    def query(
        self,
        question: str,
        reasoning_effort: Optional[str] = None,
        verbosity: Optional[str] = None,
        previous_response_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        is_clarification_response: bool = False,
    ) -> Dict[str, Any]:
        state: HybridAgentState = {
            "question": question,
            "conversation_history": conversation_history,
            "reasoning_effort": reasoning_effort or self.reasoning_effort,
            "verbosity": verbosity or self.verbosity,
            "previous_response_id": previous_response_id,
            "is_clarification_response": is_clarification_response,
        }

        final_state = self.app.invoke(state)
        response = final_state.get("response")
        if response:
            return response

        return {
            "success": False,
            "answer": None,
            "pipeline": None,
            "results": None,
            "reasoning_summary": None,
            "error": final_state.get("error") or "Failed to generate MongoDB pipeline",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _build_graph(self):
        graph = StateGraph(HybridAgentState)

        graph.add_node("decide_route", self._route_node)
        graph.add_node("deterministic", self._deterministic_node)
        graph.add_node("fallback", self._fallback_node)

        graph.set_entry_point("decide_route")

        graph.add_conditional_edges(
            "decide_route",
            self._after_route,
            {
                "deterministic": "deterministic",
                "fallback": "fallback",
                "stop": END,
            },
        )

        graph.add_conditional_edges(
            "deterministic",
            self._after_deterministic,
            {
                "fallback": "fallback",
                "stop": END,
            },
        )

        graph.add_edge("fallback", END)

        return graph.compile()

    def _route_node(self, state: HybridAgentState) -> HybridAgentState:
        conversation_context = self._build_conversation_context(state.get("conversation_history"))
        is_clarification = state.get("is_clarification_response", False)

        try:
            intent = self.deterministic_engine.intent_extractor.extract(state["question"], conversation_context)
        except Exception as exc:
            self.logger.warning("Intent extraction failed, falling back: %s", exc)
            state["route"] = "fallback"
            state["error"] = str(exc)
            return state

        if intent.is_ambiguous:
            state["response"] = self.deterministic_engine._clarification_response(intent)
            state["route"] = "stop"
            return state

        intent = sanitize_intent(state["question"], intent, is_clarification_response=is_clarification)

        # Check again after sanitization - ambiguity detector may have flagged it
        if intent.is_ambiguous:
            state["response"] = self.deterministic_engine._clarification_response(intent)
            state["route"] = "stop"
            return state

        action = intent.action
        if isinstance(action, str):
            try:
                action = QueryAction(action)
            except ValueError:
                self.logger.info("Unsupported action %s, falling back", intent.action)
                state["route"] = "fallback"
                return state

        if action not in self.SUPPORTED_ACTIONS:
            self.logger.info("Unsupported action %s, falling back", intent.action)
            state["route"] = "fallback"
            return state

        state["intent"] = intent
        state["route"] = "deterministic"
        return state

    def _after_route(self, state: HybridAgentState) -> str:
        return state.get("route") or "fallback"

    def _deterministic_node(self, state: HybridAgentState) -> HybridAgentState:
        intent = state.get("intent")
        if not intent:
            state["route"] = "fallback"
            return state

        normalized_intent = self._normalize_intent(intent)
        valid, error = self.deterministic_engine.validator.validate_intent(normalized_intent)
        if not valid:
            self.logger.info("Intent validation failed (%s), falling back", error)
            state["route"] = "fallback"
            return state

        try:
            pipeline = self.deterministic_engine.query_builder.build(normalized_intent)
        except Exception as exc:
            self.logger.info("Pipeline build failed (%s), falling back", exc)
            state["route"] = "fallback"
            return state

        valid, error = self.deterministic_engine.validator.validate_pipeline(pipeline)
        if not valid:
            self.logger.info("Pipeline validation failed (%s), falling back", error)
            state["route"] = "fallback"
            return state

        try:
            results, execution_time = self.deterministic_engine.executor.execute(pipeline)
        except Exception as exc:
            self.logger.info("Pipeline execution failed (%s), falling back", exc)
            state["route"] = "fallback"
            return state

        answer, response_id = self.deterministic_engine.summarizer.summarize(
            state["question"],
            results,
            normalized_intent,
            verbosity=state.get("verbosity", self.verbosity),
            previous_response_id=state.get("previous_response_id"),
        )

        state["response"] = {
            "success": True,
            "answer": answer,
            "pipeline": pipeline,
            "results": results,
            "result_count": len(results),
            "reasoning_summary": None,
            "response_id": response_id,
            "error": None,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat(),
        }
        state["route"] = "stop"
        return state

    def _after_deterministic(self, state: HybridAgentState) -> str:
        return state.get("route") or "fallback"

    def _fallback_node(self, state: HybridAgentState) -> HybridAgentState:
        response = self._fallback(
            state["question"],
            reasoning_effort=state.get("reasoning_effort"),
            verbosity=state.get("verbosity"),
            previous_response_id=state.get("previous_response_id"),
            conversation_history=state.get("conversation_history"),
        )
        state["response"] = response
        state["route"] = "stop"
        return state

    def _normalize_intent(self, intent: QueryIntent) -> QueryIntent:
        updated = intent.model_copy(deep=True)
        action = updated.action
        if isinstance(action, str):
            action = QueryAction(action)

        if action in {
            QueryAction.TOP_N,
            QueryAction.BOTTOM_N,
            QueryAction.AGGREGATE,
            QueryAction.SINGLE_VALUE,
            QueryAction.COMPARE,
            QueryAction.TREND,
        }:
            if updated.metric is None:
                updated.metric = MetricField.SPENDING

        if action == QueryAction.TREND and updated.group_by is None:
            updated.group_by = DimensionField.FISCAL_YEAR_START

        if updated.metric in {MetricField.ORDER_COUNT, MetricField.ORDER_COUNT.value} and updated.aggregate_function not in {
            AggregateFunction.COUNT,
            AggregateFunction.COUNT_DISTINCT,
            AggregateFunction.COUNT.value,
            AggregateFunction.COUNT_DISTINCT.value,
        }:
            updated.aggregate_function = AggregateFunction.COUNT

        return updated

    def _fallback(
        self,
        question: str,
        *,
        reasoning_effort: Optional[str],
        verbosity: Optional[str],
        previous_response_id: Optional[str],
        conversation_history: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        return self.fallback_agent.query(
            question=question,
            reasoning_effort=reasoning_effort or self.reasoning_effort,
            verbosity=verbosity or self.verbosity,
            previous_response_id=previous_response_id,
            conversation_history=conversation_history,
        )

    def reset_conversation(self) -> None:
        if hasattr(self.fallback_agent, "base") and hasattr(self.fallback_agent.base, "reset_conversation"):
            self.fallback_agent.base.reset_conversation()

    def _build_conversation_context(
        self, history: Optional[List[Dict[str, Any]]]
    ) -> Optional[str]:
        if not history:
            return None

        parts: List[str] = ["CONVERSATION HISTORY:"]
        for index, exchange in enumerate(history[-3:], 1):
            question = exchange.get("question") or exchange.get("query") or "N/A"
            response = exchange.get("response", {})
            summary = self._summarize_response(response)
            parts.append(f"{index}. Question: {question}")
            parts.append(f"   Response: {summary}")

        return "\n".join(parts)

    def _summarize_response(self, response: Any) -> str:
        if isinstance(response, dict):
            if response.get("answer"):
                return response.get("answer")
            results = response.get("results", [])
            if results:
                preview = results[0]
                suffix = f" (and {len(results) - 1} more)" if len(results) > 1 else ""
                return f"Result: {preview}{suffix}"
            return "Result: No results"
        return f"Result: {str(response)[:100]}"
