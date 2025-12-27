"""
MongoDB AI Agent Service

Implements a ReAct-based LLM agent for text-to-MongoDB query conversion.
Uses LangChain's MongoDB toolkit for:
- Natural language parsing
- Query generation
- Query validation
- Query execution
- Response formulation
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_community.utilities import MongoDBAtlasVectorSearch
from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

logger = logging.getLogger(__name__)


class MongoDBSchemaContext:
    """Provides schema context about the MongoDB collection."""

    SCHEMA_DESCRIPTION = """
    ## Database Schema: government_procurement.purchase_orders

    This collection contains California state government purchase orders from 2012-2015.
    Total documents: ~346,000 purchase order line items

    ### Main Fields:

    **Identifiers:**
    - purchase_order_number (string): Primary PO identifier
    - requisition_number (string): Requisition ID
    - lpa_number (string): Leveraged Procurement Agreement number
    - cal_card (boolean): California Procurement Card flag

    **Dates (all ISODate):**
    - dates.creation: Order creation date
    - dates.purchase: Purchase date
    - dates.fiscal_year (number): Fiscal year (2012-2015)

    **Department:**
    - department.name (string): Full department name
    - department.normalized_name (string): Standardized name for grouping

    **Acquisition:**
    - acquisition.type (string): "IT" or "Non-IT"
    - acquisition.method (string): e.g. "Leveraged Procurement Agreement"
    - acquisition.sub_category (string): "Goods" or "Services"

    **Item:**
    - item.description (string): Full-text item description
    - item.quantity (number): Quantity ordered
    - item.unit_price (number): Price per unit (USD)
    - item.total_price (number): Total line item price (can be negative for credits/returns)

    **Supplier:**
    - supplier.name (string): Supplier/vendor name
    - supplier.code (string): Unique supplier identifier
    - supplier.address (string): Full address
    - supplier.city (string)
    - supplier.state (string)
    - supplier.zip (string)
    - supplier.location (GeoJSON Point): { type: "Point", coordinates: [lon, lat] }
    - supplier.qualifications (array): e.g. ["DVBE", "Small Business"]

    **Classification (UNSPSC):**
    - classification.unspsc.segment.code (string): e.g. "43000000"
    - classification.unspsc.segment.title (string): e.g. "Information Technology"
    - classification.unspsc.family.code (string): e.g. "43210000"
    - classification.unspsc.family.title (string): e.g. "Software"
    - classification.unspsc.class.code (string)
    - classification.unspsc.class.title (string)
    - classification.unspsc.commodity.code (string)
    - classification.unspsc.commodity.title (string)

    **Metadata:**
    - metadata.source_file (string): Original CSV filename
    - metadata.import_date (ISODate): When imported

    ### Indexes (optimized for queries):
    - idx_fiscal_year_department: { dates.fiscal_year: 1, department.name: 1 }
    - idx_acquisition_type_date: { acquisition.type: 1, dates.creation: -1 }
    - idx_supplier_price: { supplier.name: 1, item.total_price: -1 }
    - idx_creation_date: { dates.creation: -1 }
    - idx_po_number: { purchase_order_number: 1 }
    - idx_total_price: { item.total_price: 1 }
    - idx_text_search: Full-text on item.description, supplier.name, department.name
    - idx_supplier_location: 2dsphere on supplier.location

    ### Common Aggregation Patterns:

    **Total Spending:**
    ```
    db.purchase_orders.aggregate([
      { $group: { _id: null, total: { $sum: "$item.total_price" } } }
    ])
    ```

    **Spending by Department:**
    ```
    db.purchase_orders.aggregate([
      { $group: { _id: "$department.normalized_name", total: { $sum: "$item.total_price" } } },
      { $sort: { total: -1 } },
      { $limit: 10 }
    ])
    ```

    **Spending by Quarter:**
    ```
    db.purchase_orders.aggregate([
      { $group: { _id: { year: { $year: "$dates.creation" }, quarter: { $ceil: { $divide: [{ $month: "$dates.creation" }, 3] } } }, total: { $sum: "$item.total_price" } } },
      { $sort: { "_id.year": 1, "_id.quarter": 1 } }
    ])
    ```

    **Top Suppliers:**
    ```
    db.purchase_orders.aggregate([
      { $group: { _id: "$supplier.name", total: { $sum: "$item.total_price" }, count: { $sum: 1 } } },
      { $sort: { total: -1 } },
      { $limit: 10 }
    ])
    ```

    ### Important Notes:
    - item.total_price can be negative (represents credits, returns, refunds)
    - Always use dates.creation for time-based queries (most reliable)
    - For geospatial queries, use $geoNear or $geoWithin on supplier.location
    - Text search: Use $text operator on indexed fields
    - Fiscal years: 2012, 2013, 2014, 2015
    """

    @classmethod
    def get_schema(cls) -> str:
        """Get the full schema description."""
        return cls.SCHEMA_DESCRIPTION


class QueryValidator:
    """Validates MongoDB queries before execution."""

    def __init__(self, collection):
        self.collection = collection
        self.logger = logging.getLogger(__name__)

    def validate_aggregation_pipeline(self, pipeline: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """
        Validate an aggregation pipeline.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if pipeline is a list
            if not isinstance(pipeline, list):
                return False, "Pipeline must be a list of stages"

            # Check if pipeline is empty
            if len(pipeline) == 0:
                return False, "Pipeline cannot be empty"

            # Check each stage
            for i, stage in enumerate(pipeline):
                if not isinstance(stage, dict):
                    return False, f"Stage {i} must be a dictionary"

                # Check stage has exactly one operator
                if len(stage) != 1:
                    return False, f"Stage {i} must have exactly one operator"

                # Get the operator
                operator = list(stage.keys())[0]

                # Validate operator starts with $
                if not operator.startswith('$'):
                    return False, f"Stage {i}: '{operator}' is not a valid aggregation operator (must start with $)"

            # Try to explain the query (doesn't execute, just validates)
            try:
                self.collection.aggregate(pipeline, maxTimeMS=1000, allowDiskUse=False, comment="validation_check")
                return True, None
            except OperationFailure as e:
                # Query is syntactically valid but may have logical errors
                error_msg = str(e)
                if "unknown operator" in error_msg.lower() or "invalid" in error_msg.lower():
                    return False, f"Invalid query: {error_msg}"
                # Other operation failures might be OK (like timeout on validation)
                return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"


class MongoDBQueryExecutor:
    """Executes validated MongoDB queries."""

    def __init__(self, collection, max_results: int = 100):
        self.collection = collection
        self.max_results = max_results
        self.logger = logging.getLogger(__name__)

    def execute_aggregation(
        self,
        pipeline: List[Dict[str, Any]],
        limit: Optional[int] = None
    ) -> Tuple[bool, Union[List[Dict[str, Any]], str]]:
        """
        Execute an aggregation pipeline.

        Returns:
            Tuple of (success, results_or_error_message)
        """
        try:
            # Add limit if not present in pipeline
            if limit is None:
                limit = self.max_results

            # Check if pipeline already has a $limit stage
            has_limit = any('$limit' in stage for stage in pipeline)

            if not has_limit:
                pipeline.append({'$limit': limit})

            # Execute pipeline
            start_time = datetime.now()
            results = list(self.collection.aggregate(pipeline, maxTimeMS=30000))
            execution_time = (datetime.now() - start_time).total_seconds()

            self.logger.info(f"Query executed in {execution_time:.2f}s, returned {len(results)} results")

            # Convert ObjectId and datetime to strings for JSON serialization
            serialized_results = self._serialize_results(results)

            return True, serialized_results

        except PyMongoError as e:
            error_msg = f"Query execution failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during execution: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _serialize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Serialize MongoDB results to JSON-compatible format."""
        from bson import ObjectId

        def serialize_value(value):
            if isinstance(value, ObjectId):
                return str(value)
            elif isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [serialize_value(item) for item in value]
            else:
                return value

        return [serialize_value(doc) for doc in results]


class MongoDBAgent:
    """
    ReAct-based AI Agent for MongoDB query generation and execution.

    Implements the full pipeline:
    1. Natural language parsing
    2. Query generation
    3. Query validation
    4. Query execution
    5. Response formulation
    """

    def __init__(
        self,
        mongo_client: MongoClient,
        database_name: str,
        collection_name: str,
        openai_api_key: Optional[str] = None,
        model_name: str = "gpt-4",
        max_retries: int = 3,
        max_results: int = 100
    ):
        """
        Initialize the MongoDB Agent.

        Args:
            mongo_client: MongoDB client connection
            database_name: Database name
            collection_name: Collection name
            openai_api_key: OpenAI API key (if not set in env)
            model_name: OpenAI model to use (gpt-4, gpt-3.5-turbo, etc.)
            max_retries: Maximum number of query generation retries
            max_results: Maximum results to return
        """
        self.mongo_client = mongo_client
        self.database = mongo_client[database_name]
        self.collection = self.database[collection_name]
        self.collection_name = collection_name
        self.max_retries = max_retries

        # Set OpenAI API key
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key

        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=0,  # Deterministic for query generation
            request_timeout=60
        )

        # Initialize components
        self.validator = QueryValidator(self.collection)
        self.executor = MongoDBQueryExecutor(self.collection, max_results=max_results)
        self.schema_context = MongoDBSchemaContext.get_schema()

        # Create tools
        self.tools = self._create_tools()

        # Create agent
        self.agent = self._create_agent()

        self.logger = logging.getLogger(__name__)

    def _create_tools(self) -> List[Tool]:
        """Create LangChain tools for the agent."""

        def generate_query_tool(question: str) -> str:
            """Generate a MongoDB aggregation pipeline from natural language."""
            try:
                prompt = f"""Given this question about California government purchase orders:

Question: {question}

Generate a MongoDB aggregation pipeline to answer it. Return ONLY a valid JSON array representing the pipeline.

Database Schema:
{self.schema_context}

Requirements:
- Return ONLY the pipeline array, no explanations
- Use proper MongoDB aggregation operators ($match, $group, $sort, $limit, etc.)
- Limit results to 100 unless specifically asked for more
- Use dates.creation for date queries
- Use item.total_price for spending/cost queries
- For "top N" queries, use $sort and $limit
- For totals/sums, use $group with $sum
- Include only necessary fields in output using $project if needed

Example format:
[{{"$match": {{"dates.fiscal_year": 2014}}}}, {{"$group": {{"_id": "$department.name", "total": {{"$sum": "$item.total_price"}}}}}}, {{"$sort": {{"total": -1}}}}, {{"$limit": 10}}]
"""

                response = self.llm.predict(prompt)

                # Extract JSON from response (might be wrapped in markdown code blocks)
                response = response.strip()
                if response.startswith("```"):
                    # Remove markdown code blocks
                    lines = response.split("\n")
                    response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
                    response = response.replace("```json", "").replace("```", "").strip()

                # Validate it's valid JSON
                try:
                    pipeline = json.loads(response)
                    return json.dumps(pipeline)
                except json.JSONDecodeError:
                    return f"Error: Generated invalid JSON: {response}"

            except Exception as e:
                return f"Error generating query: {str(e)}"

        def validate_query_tool(pipeline_json: str) -> str:
            """Validate a MongoDB aggregation pipeline."""
            try:
                pipeline = json.loads(pipeline_json)
                is_valid, error = self.validator.validate_aggregation_pipeline(pipeline)

                if is_valid:
                    return "Query is valid"
                else:
                    return f"Query validation failed: {error}"
            except json.JSONDecodeError as e:
                return f"Invalid JSON: {str(e)}"
            except Exception as e:
                return f"Validation error: {str(e)}"

        def execute_query_tool(pipeline_json: str) -> str:
            """Execute a validated MongoDB aggregation pipeline."""
            try:
                pipeline = json.loads(pipeline_json)
                success, result = self.executor.execute_aggregation(pipeline)

                if success:
                    return json.dumps({"success": True, "results": result, "count": len(result)})
                else:
                    return json.dumps({"success": False, "error": result})
            except json.JSONDecodeError as e:
                return json.dumps({"success": False, "error": f"Invalid JSON: {str(e)}"})
            except Exception as e:
                return json.dumps({"success": False, "error": f"Execution error: {str(e)}"})

        return [
            Tool(
                name="generate_mongodb_query",
                func=generate_query_tool,
                description="Generate a MongoDB aggregation pipeline from a natural language question. Input: natural language question. Output: JSON array pipeline."
            ),
            Tool(
                name="validate_mongodb_query",
                func=validate_query_tool,
                description="Validate a MongoDB aggregation pipeline for syntax and field names. Input: JSON pipeline string. Output: validation result."
            ),
            Tool(
                name="execute_mongodb_query",
                func=execute_query_tool,
                description="Execute a validated MongoDB aggregation pipeline. Input: JSON pipeline string. Output: query results as JSON."
            )
        ]

    def _create_agent(self) -> AgentExecutor:
        """Create the ReAct agent with MongoDB tools."""

        # Define the prompt template for the agent
        template = """You are an AI agent that helps users query a MongoDB database containing California government purchase orders from 2012-2015.

You have access to these tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Database Schema Context:
{schema_context}

Important Rules:
1. ALWAYS start by using generate_mongodb_query to create a query
2. ALWAYS validate the query using validate_mongodb_query before executing
3. If validation fails, use generate_mongodb_query again with the error feedback
4. Only execute validated queries using execute_mongodb_query
5. Format the final answer in natural language for the user
6. If results are empty, explain why and suggest alternative queries

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools]),
                "tool_names": ", ".join([tool.name for tool in self.tools]),
                "schema_context": self.schema_context[:500] + "..." # Abbreviated for prompt
            }
        )

        # Create the agent
        agent = create_react_agent(self.llm, self.tools, prompt)

        # Create the agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True
        )

        return agent_executor

    def query(self, question: str) -> Dict[str, Any]:
        """
        Process a natural language question and return results.

        Args:
            question: Natural language question

        Returns:
            Dictionary with:
                - success: bool
                - answer: str (natural language response)
                - pipeline: List[Dict] (the generated MongoDB pipeline)
                - results: List[Dict] (raw query results)
                - error: Optional[str]
        """
        try:
            self.logger.info(f"Processing question: {question}")

            # Run the agent
            result = self.agent.invoke({"input": question})

            # Extract the final answer
            answer = result.get("output", "No answer generated")

            return {
                "success": True,
                "answer": answer,
                "pipeline": None,  # Could be extracted from intermediate steps
                "results": None,
                "error": None,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "answer": None,
                "pipeline": None,
                "results": None,
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            }

    def query_direct(
        self,
        question: str,
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Direct query processing without the full agent framework.
        Faster but less flexible than the full agent.

        Args:
            question: Natural language question
            max_retries: Max retries for query generation (default: self.max_retries)

        Returns:
            Dictionary with results
        """
        if max_retries is None:
            max_retries = self.max_retries

        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                # Step 1: Generate query
                self.logger.info(f"Generating query (attempt {retry_count + 1})")
                pipeline_json = self.tools[0].func(question)

                if pipeline_json.startswith("Error:"):
                    last_error = pipeline_json
                    retry_count += 1
                    continue

                pipeline = json.loads(pipeline_json)

                # Step 2: Validate query
                is_valid, validation_error = self.validator.validate_aggregation_pipeline(pipeline)

                if not is_valid:
                    self.logger.warning(f"Validation failed: {validation_error}")
                    last_error = validation_error
                    retry_count += 1
                    # Add error feedback to next generation attempt
                    question = f"{question}\n\nPrevious attempt failed validation: {validation_error}"
                    continue

                # Step 3: Execute query
                success, result = self.executor.execute_aggregation(pipeline)

                if not success:
                    return {
                        "success": False,
                        "answer": None,
                        "pipeline": pipeline,
                        "results": None,
                        "error": result,
                        "timestamp": datetime.utcnow().isoformat()
                    }

                # Step 4: Formulate response
                response_prompt = f"""Given this question and query results, provide a clear, natural language answer.

Question: {question}

Query Results:
{json.dumps(result[:5], indent=2)}  # Show first 5 results
Total Results: {len(result)}

Provide a concise, informative answer that directly addresses the question. Include specific numbers and details from the results."""

                answer = self.llm.predict(response_prompt)

                return {
                    "success": True,
                    "answer": answer,
                    "pipeline": pipeline,
                    "results": result,
                    "error": None,
                    "timestamp": datetime.utcnow().isoformat()
                }

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Error on attempt {retry_count + 1}: {last_error}")
                retry_count += 1

        # All retries failed
        return {
            "success": False,
            "answer": None,
            "pipeline": None,
            "results": None,
            "error": f"Failed after {max_retries} attempts. Last error: {last_error}",
            "timestamp": datetime.utcnow().isoformat()
        }
