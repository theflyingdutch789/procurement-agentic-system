"""
AI Agent Query Endpoints - GPT-5 Edition

Natural language to MongoDB query conversion using GPT-5 Responses API.
"""

import os
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field

from src.api.dependencies import get_mongo_client, get_database
from src.api.services.mongodb_agent import GPT5MongoDBAgent, LangGraphMongoDBAgent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Agent - GPT-5"],
)


# Pydantic models
class NaturalLanguageQueryRequest(BaseModel):
    """Request model for natural language queries with GPT-5."""
    question: str = Field(
        ...,
        description="Natural language question about the procurement data",
        examples=["What was the total spending in 2014?"]
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Conversation ID to maintain context across queries"
    )
    conversation_history: Optional[list] = Field(
        default=None,
        description="Recent conversation history for context"
    )
    reasoning_effort: str = Field(
        default="medium",
        description="GPT-5 reasoning effort: 'minimal' (fastest), 'low', 'medium' (balanced), 'high' (most thorough)",
        examples=["minimal", "low", "medium", "high"]
    )
    verbosity: str = Field(
        default="medium",
        description="Output verbosity: 'low' (concise), 'medium' (balanced), 'high' (detailed)",
        examples=["low", "medium", "high"]
    )
    max_results: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=1000
    )
    model: str = Field(
        default="gpt-5",
        description="GPT-5 model: 'gpt-5' (best), 'gpt-5-mini' (balanced), 'gpt-5-nano' (fast)",
        examples=["gpt-5", "gpt-5-mini", "gpt-5-nano"]
    )


class AIQueryResponse(BaseModel):
    """Response model for AI queries."""
    success: bool
    answer: Optional[str] = None
    pipeline: Optional[list] = None
    results: Optional[list] = None
    result_count: Optional[int] = None
    reasoning_summary: Optional[str] = None
    error: Optional[str] = None
    timestamp: str
    execution_time_seconds: Optional[float] = None


# Global agent instance (initialized on first request)
_agent_instance: Optional[LangGraphMongoDBAgent] = None

# Per-conversation state tracking (previous_response_id for chain-of-thought)
# Format: {conversation_id: previous_response_id}
_conversation_states: dict[str, Optional[str]] = {}


def get_agent(
    mongo_client=Depends(get_mongo_client),
    database=Depends(get_database)
) -> GPT5MongoDBAgent:
    """
    Get or create the GPT-5 MongoDB Agent instance.

    The agent is created once and reused for subsequent requests.
    NOTE: The agent is now stateless - conversation state is managed separately.
    """
    global _agent_instance

    if _agent_instance is None:
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=500,
                detail="OPENAI_API_KEY environment variable not set. Get your API key from: https://platform.openai.com/api-keys"
            )

        logger.info("Initializing GPT-5 MongoDB AI Agent (LangGraph orchestrated)...")
        base_agent = GPT5MongoDBAgent(
            mongo_client=mongo_client,
            database_name=database.name,
            collection_name="purchase_orders",
            openai_api_key=openai_api_key,
            model_name="gpt-5",  # Default to GPT-5
            reasoning_effort="medium",  # Balanced default
            verbosity="medium",
            max_results=10
        )
        _agent_instance = LangGraphMongoDBAgent(base_agent)
        logger.info("LangGraph GPT-5 MongoDB AI Agent initialized successfully")

    return _agent_instance


def get_conversation_state(conversation_id: str) -> Optional[str]:
    """Get the previous_response_id for a conversation."""
    return _conversation_states.get(conversation_id)


def update_conversation_state(conversation_id: str, response_id: str):
    """Update the previous_response_id for a conversation."""
    _conversation_states[conversation_id] = response_id
    logger.info(f"Updated conversation state for {conversation_id}: {response_id}")


def clear_conversation_state(conversation_id: str):
    """Clear the conversation state for a specific conversation."""
    if conversation_id in _conversation_states:
        del _conversation_states[conversation_id]
        logger.info(f"Cleared conversation state for {conversation_id}")


@router.post(
    "/query",
    response_model=AIQueryResponse,
    summary="Natural Language Query (GPT-5)",
    description="""
    Query the procurement database using natural language powered by GPT-5.

    **GPT-5 Features:**
    - **Advanced reasoning**: High reasoning effort for complex multi-step queries
    - **Custom tools**: Freeform MongoDB pipeline generation
    - **Chain-of-thought**: Passes reasoning between turns for better context
    - **Preambles**: Explains why it's generating queries (transparency)
    - **Better performance**: Improved over GPT-4 for coding and query generation

    **Example Questions:**
    - "What was the total spending in 2014?"
    - "Which department had the highest spending in Q4 2013?"
    - "Show me the top 5 suppliers by total contract value"
    - "How many purchase orders were for IT services?"
    - "Compare IT vs Non-IT spending across quarters"

    **Reasoning Effort:**
    - `minimal`: Fastest, best for simple queries (e.g., "total spending in 2014")
    - `low`: Fast with light reasoning (e.g., "top 10 departments")
    - `medium`: Balanced (recommended for most queries)
    - `high`: Most thorough, best for complex multi-step queries

    **Verbosity:**
    - `low`: Concise answers
    - `medium`: Balanced explanations (recommended)
    - `high`: Detailed explanations with context

    **Models:**
    - `gpt-5`: Best for complex reasoning and broad knowledge
    - `gpt-5-mini`: Balanced speed/cost/capability
    - `gpt-5-nano`: Fastest, best for simple queries

    **Note:** Requires OPENAI_API_KEY environment variable.
    """
)
async def natural_language_query(
    request: NaturalLanguageQueryRequest = Body(...),
    agent: LangGraphMongoDBAgent = Depends(get_agent)
) -> AIQueryResponse:
    """
    Process a natural language query using GPT-5.
    """
    start_time = datetime.now()

    try:
        logger.info(f"Processing GPT-5 query: {request.question}")
        logger.info(f"Parameters: model={request.model}, effort={request.reasoning_effort}, verbosity={request.verbosity}, conversation_id={request.conversation_id}")

        # Update agent configuration if needed
        if request.max_results != agent.executor.max_results:
            agent.executor.max_results = request.max_results

        # Update model if different
        if request.model != agent.model_name:
            agent.model_name = request.model

        # Get conversation state for context continuity
        prev_response_id = None
        if request.conversation_id:
            prev_response_id = get_conversation_state(request.conversation_id)
            logger.info(f"Retrieved conversation state: prev_response_id={prev_response_id}")

        # Process query with GPT-5
        result = agent.query(
            question=request.question,
            reasoning_effort=request.reasoning_effort,
            verbosity=request.verbosity,
            previous_response_id=prev_response_id,
            conversation_history=request.conversation_history
        )

        # Store new response_id for conversation continuity
        if request.conversation_id and result.get("response_id"):
            update_conversation_state(request.conversation_id, result["response_id"])

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        # Build response
        response = AIQueryResponse(
            success=result["success"],
            answer=result.get("answer"),
            pipeline=result.get("pipeline"),
            results=result.get("results"),
            result_count=result.get("result_count"),
            reasoning_summary=result.get("reasoning_summary"),
            error=result.get("error"),
            timestamp=result["timestamp"],
            execution_time_seconds=execution_time
        )

        logger.info(f"Query completed in {execution_time:.2f}s")
        return response

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        execution_time = (datetime.now() - start_time).total_seconds()

        return AIQueryResponse(
            success=False,
            answer=None,
            pipeline=None,
            results=None,
            result_count=None,
            reasoning_summary=None,
            error=str(e),
            timestamp=datetime.utcnow().isoformat(),
            execution_time_seconds=execution_time
        )


@router.get(
    "/schema",
    summary="Get Database Schema",
    description="Get the database schema information used by the GPT-5 agent"
)
async def get_schema():
    """
    Get the database schema description.

    This schema is used by GPT-5 to understand the database structure
    and generate appropriate queries.
    """
    from src.api.services.mongodb_agent import MongoDBSchemaContext

    return {
        "collection": "purchase_orders",
        "database": "government_procurement",
        "schema": MongoDBSchemaContext.get_schema(),
        "description": "California state government purchase orders (2012-2015)",
        "record_count": "~346,000 line items",
        "powered_by": "GPT-5 (gpt-5-thinking)"
    }


@router.get(
    "/examples",
    summary="Get Example Queries",
    description="Get example natural language queries optimized for GPT-5"
)
async def get_example_queries():
    """
    Get example natural language queries.

    These examples demonstrate GPT-5's capabilities for different query complexities.
    """
    return {
        "simple_queries": {
            "description": "Use reasoning_effort='minimal' for fastest results",
            "examples": [
                "What was the total spending in 2014?",
                "How many purchase orders were there?",
                "Show me the top 5 departments by spending",
                "Count IT vs Non-IT purchases"
            ]
        },
        "moderate_queries": {
            "description": "Use reasoning_effort='medium' (recommended default)",
            "examples": [
                "Which quarter had the highest spending in 2013?",
                "Compare spending trends across fiscal years",
                "Show me top 10 suppliers by contract value",
                "What was the average order value by department?"
            ]
        },
        "complex_queries": {
            "description": "Use reasoning_effort='high' for best results",
            "examples": [
                "Compare IT vs Non-IT spending by quarter, broken down by department",
                "Find departments with increasing spending trends year-over-year",
                "Analyze supplier concentration in IT services vs goods",
                "Show seasonal patterns in procurement spending"
            ]
        },
        "tips": [
            "GPT-5 excels at multi-step reasoning - try complex questions!",
            "Use 'high' reasoning for coding-heavy or agentic tasks",
            "Start with 'medium' reasoning and tune based on results",
            "GPT-5 can explain its reasoning - check reasoning_summary in response",
            "Chain-of-thought is passed between queries for better context"
        ],
        "model_recommendations": {
            "gpt-5": "Best for complex analysis and broad knowledge queries",
            "gpt-5-mini": "Balanced option for most queries (faster, cheaper)",
            "gpt-5-nano": "Simple queries with high throughput needs"
        }
    }


@router.post(
    "/health",
    summary="Agent Health Check",
    description="Check if the GPT-5 agent is initialized and ready"
)
async def agent_health_check(agent: GPT5MongoDBAgent = Depends(get_agent)):
    """
    Check the health of the GPT-5 agent.
    """
    try:
        # Test database connection
        agent.collection.database.client.admin.command('ping')

        return {
            "status": "healthy",
            "agent_initialized": True,
            "database_connected": True,
            "collection": agent.collection_name,
            "model": agent.model_name,
            "reasoning_effort": agent.reasoning_effort,
            "verbosity": agent.verbosity,
            "powered_by": "OpenAI GPT-5 Responses API",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "agent_initialized": _agent_instance is not None,
            "database_connected": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.post(
    "/reset",
    summary="Reset Conversation State",
    description="Reset the agent's conversation state (clears chain-of-thought history)"
)
async def reset_conversation(agent: GPT5MongoDBAgent = Depends(get_agent)):
    """
    Reset the agent's conversation state.

    This clears the chain-of-thought history, useful when starting a new
    line of inquiry unrelated to previous questions.
    """
    agent.reset_conversation()
    return {
        "success": True,
        "message": "Conversation state reset successfully",
        "timestamp": datetime.utcnow().isoformat()
    }
