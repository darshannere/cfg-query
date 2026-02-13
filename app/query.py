"""Service for generating and executing SQL queries."""
import httpx
from openai import AsyncOpenAI
from app.grammar import get_clickhouse_grammar

class QueryService:
    """Handles natural language to SQL conversion and query execution."""

    def __init__(self, openai_api_key: str, tinybird_token: str, tinybird_host: str):
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.tinybird_token = tinybird_token
        self.tinybird_host = tinybird_host
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
        Execute SQL query against Tinybird.

        Args:
            sql: Valid ClickHouse SELECT statement

        Returns:
            JSON response with query results
        """
        return await self._call_tinybird(sql)

    async def _call_gpt5(self, query: str) -> str:
        """Call GPT-5 with Lark grammar constraint."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a SQL query generator for a ClickHouse database. "
                            "The database has a single table called 'orders' with columns: "
                            "order_id (String), customer_id (String), product_name (String), "
                            "category (String), quantity (UInt32), unit_price (Float64), "
                            "total_amount (Float64), order_date (DateTime), country (String). "
                            "Convert the user's natural language question into a valid SELECT query."
                        )
                    },
                    {"role": "user", "content": query}
                ],
                response_format={
                    "type": "grammar",
                    "grammar": {
                        "type": "lark",
                        "value": self.grammar
                    }
                }
            )

            content = response.choices[0].message.content
            if content is None:
                raise ValueError("GPT-5 returned empty response")
            return content.strip()
        except Exception as e:
            raise RuntimeError(f"GPT-5 query generation failed: {str(e)}") from e

    async def _call_tinybird(self, sql: str) -> dict:
        """Execute SQL query via Tinybird REST API."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.tinybird_host}/v0/sql",
                    headers={
                        "Authorization": f"Bearer {self.tinybird_token}"
                    },
                    params={"q": sql}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Tinybird query failed: {e.response.text}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Failed to connect to Tinybird: {str(e)}") from e
