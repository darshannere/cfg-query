"""FastAPI application for CFG Query."""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from app.query import QueryService

load_dotenv()

app = FastAPI(title="CFG Query App")

# Initialize query service
# Use dummy values for testing - will be mocked in tests
query_service = QueryService(
    openai_api_key=os.getenv("OPENAI_API_KEY", "test-key"),
    clickhouse_key_id=os.getenv("CLICKHOUSE_KEY_ID", "test-key-id"),
    clickhouse_key_secret=os.getenv("CLICKHOUSE_KEY_SECRET", "test-key-secret"),
    clickhouse_url=os.getenv("CLICKHOUSE_URL", "https://queries.clickhouse.cloud"),
)

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500, description="Natural language query")

class QueryResponse(BaseModel):
    sql: str
    results: dict

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the frontend HTML page."""
    html_path = Path(__file__).parent / "static" / "index.html"
    try:
        with open(html_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Frontend not found")

@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """
    Convert natural language query to SQL and execute it.

    Args:
        request: JSON with 'query' field containing natural language question

    Returns:
        JSON with generated SQL and query results
    """
    try:
        # Generate SQL from natural language
        sql = await query_service.generate_sql(request.query)

        # Execute query
        results = await query_service.execute_query(sql)

        return QueryResponse(sql=sql, results=results)

    except RuntimeError as e:
        # RuntimeError from our QueryService error handling
        if "GPT-5" in str(e) or "OpenAI" in str(e):
            raise HTTPException(status_code=503, detail="AI service unavailable")
        elif "ClickHouse" in str(e):
            raise HTTPException(status_code=503, detail="Database service unavailable")
        else:
            raise HTTPException(status_code=500, detail="Internal server error")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
