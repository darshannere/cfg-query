"""FastAPI application for CFG Query."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from app.query import QueryService

load_dotenv()

app = FastAPI(title="CFG Query App")

# Initialize query service
# Use dummy values for testing - will be mocked in tests
query_service = QueryService(
    openai_api_key=os.getenv("OPENAI_API_KEY", "test-key"),
    tinybird_token=os.getenv("TINYBIRD_TOKEN", "test-token"),
    tinybird_host=os.getenv("TINYBIRD_HOST", "https://api.tinybird.co")
)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    sql: str
    results: dict

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the frontend HTML page."""
    with open("app/static/index.html", "r") as f:
        return f.read()

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
