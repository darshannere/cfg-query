"""Service for generating and executing SQL queries."""
import json
import httpx
from openai import AsyncOpenAI
from app.grammar import get_clickhouse_grammar

class QueryService:
    """Handles natural language to SQL conversion and query execution."""

    def __init__(self, openai_api_key: str, clickhouse_key_id: str, clickhouse_key_secret: str, clickhouse_url: str):
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.clickhouse_key_id = clickhouse_key_id
        self.clickhouse_key_secret = clickhouse_key_secret
        self.clickhouse_url = clickhouse_url
        self.grammar = get_clickhouse_grammar()

    async def generate_sql(self, natural_language_query: str) -> str:
        """
        Convert natural language to ClickHouse SQL using GPT-5 with CFG constraint.

        Args:
            natural_language_query: User's question in natural language

        Returns:
            Valid ClickHouse SELECT statement
        """
        return await self._call_gpt5(natural_language_query)

    async def execute_query(self, sql: str) -> dict:
        """
        Execute SQL query against ClickHouse Cloud.

        Args:
            sql: Valid ClickHouse SELECT statement

        Returns:
            JSON response with query results
        """
        return await self._call_clickhouse(sql)

    async def _call_gpt5(self, query: str) -> str:
        """Call GPT-5 with Lark grammar constraint via Responses API."""
        try:
            response = await self.openai_client.responses.create(
                model="gpt-5",
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are a SQL query generator for a ClickHouse database. "
                            "The database has a single table called 'orders' with columns: "
                            "order_id (String), customer_id (String), product_name (String), "
                            "category (String), quantity (UInt32), unit_price (Float64), "
                            "total_amount (Float64), order_date (DateTime), country (String). "
                            "Convert the user's natural language question into a valid SELECT query. "
                            "Call the sql_grammar tool with your query."
                        )
                    },
                    {"role": "user", "content": query}
                ],
                tools=[
                    {
                        "type": "custom",
                        "name": "sql_grammar",
                        "description": (
                            "Executes read-only ClickHouse SELECT queries on the orders table. "
                            "Only SELECT statements with WHERE, GROUP BY, ORDER BY, and LIMIT are allowed. "
                            "YOU MUST REASON HEAVILY ABOUT THE QUERY AND MAKE SURE IT OBEYS THE GRAMMAR."
                        ),
                        "format": {
                            "type": "grammar",
                            "syntax": "lark",
                            "definition": self.grammar
                        }
                    }
                ],
                parallel_tool_calls=False
            )

            # Extract SQL from the tool call output
            for item in response.output:
                if hasattr(item, 'input'):
                    sql = item.input
                    if sql:
                        return sql.strip()

            raise ValueError("GPT-5 returned no tool call with SQL")
        except Exception as e:
            raise RuntimeError(f"GPT-5 query generation failed: {str(e)}") from e

    async def _call_clickhouse(self, sql: str) -> dict:
        """Execute SQL query via ClickHouse Cloud REST API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.clickhouse_url,
                    auth=(self.clickhouse_key_id, self.clickhouse_key_secret),
                    headers={"Content-Type": "application/json"},
                    params={"format": "JSONEachRow"},
                    json={"sql": sql}
                )
                response.raise_for_status()
                # JSONEachRow returns one JSON object per line
                lines = response.text.strip().split("\n")
                data = [json.loads(line) for line in lines if line.strip()]
                return {"data": data}
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"ClickHouse query failed: {e.response.text}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to connect to ClickHouse: {str(e)}") from e
