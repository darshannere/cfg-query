"""FastAPI application for CFG Query."""
import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from app.query import QueryService
from lark import Lark, LarkError
from app.grammar import get_clickhouse_grammar

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

class EvalResults(BaseModel):
    grammar_compliance: dict
    semantic_correctness: dict
    edge_cases: dict
    summary: dict

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

@app.get("/api/evals", response_model=EvalResults)
async def run_evaluations():
    """
    Run comprehensive evaluation suite.

    Returns:
        JSON with results from all three evaluation suites
    """
    try:
        # Load test cases
        test_file = Path(__file__).parent.parent / "evals" / "test_queries.json"
        with open(test_file) as f:
            test_data = json.load(f)

        # Run all three evaluation suites
        grammar_results = await run_grammar_compliance_tests(test_data["grammar_compliance"])
        semantic_results = await run_semantic_correctness_tests(test_data["semantic_correctness"])
        edge_results = await run_edge_case_tests(test_data["edge_cases"])

        # Calculate summary
        total_passed = grammar_results["passed"] + semantic_results["passed"] + edge_results["passed"]
        total_tests = grammar_results["total"] + semantic_results["total"] + edge_results["total"]

        return EvalResults(
            grammar_compliance=grammar_results,
            semantic_correctness=semantic_results,
            edge_cases=edge_results,
            summary={
                "total_passed": total_passed,
                "total_tests": total_tests,
                "pass_rate": round(total_passed / total_tests * 100, 2) if total_tests > 0 else 0,
                "all_passed": total_passed == total_tests
            }
        )

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Test configuration file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

async def run_grammar_compliance_tests(test_cases: list) -> dict:
    """Test that generated SQL parses with the Lark grammar."""
    grammar = get_clickhouse_grammar()
    parser = Lark(grammar, start='start')

    results = {
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "details": []
    }

    for case in test_cases:
        query = case["query"]
        expected_contains = case["expected_contains"]

        try:
            sql = await query_service.generate_sql(query)
            parser.parse(sql)
            contains_all = all(token in sql for token in expected_contains)

            if contains_all:
                results["passed"] += 1
                results["details"].append({
                    "query": query,
                    "sql": sql,
                    "status": "PASS"
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "query": query,
                    "sql": sql,
                    "status": "FAIL",
                    "reason": "Missing expected tokens"
                })

        except LarkError as e:
            results["failed"] += 1
            results["details"].append({
                "query": query,
                "sql": sql if 'sql' in locals() else "N/A",
                "status": "FAIL",
                "reason": f"Grammar parsing failed: {str(e)}"
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "query": query,
                "status": "FAIL",
                "reason": f"Error: {str(e)}"
            })

    return results

async def run_edge_case_tests(test_cases: list) -> dict:
    """Test that adversarial inputs still produce valid SELECT statements."""
    grammar = get_clickhouse_grammar()
    parser = Lark(grammar, start='start')

    results = {
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "details": []
    }

    for case in test_cases:
        query = case["query"]

        try:
            sql = await query_service.generate_sql(query)
            parser.parse(sql)

            sql_upper = sql.upper()
            dangerous = ["DROP", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER"]
            has_dangerous = any(keyword in sql_upper for keyword in dangerous)

            if not has_dangerous:
                results["passed"] += 1
                results["details"].append({
                    "query": query,
                    "sql": sql,
                    "status": "PASS"
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "query": query,
                    "sql": sql,
                    "status": "FAIL",
                    "reason": "Contains dangerous keywords"
                })

        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "query": query,
                "status": "FAIL",
                "reason": f"Error: {str(e)}"
            })

    return results

async def run_semantic_correctness_tests(test_cases: list) -> dict:
    """Test that generated SQL is semantically correct."""
    results = {
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "details": []
    }

    for case in test_cases:
        query = case["query"]
        expected_sql = case.get("expected_sql")

        try:
            sql = await query_service.generate_sql(query)
            sql_normalized = " ".join(sql.upper().split())
            expected_normalized = " ".join(expected_sql.upper().split()) if expected_sql else None

            is_semantically_correct = True
            reason = None

            if expected_normalized:
                expected_parts = expected_normalized.split()
                missing_parts = [part for part in expected_parts if part not in sql_normalized]

                if missing_parts:
                    is_semantically_correct = False
                    reason = f"Missing elements: {', '.join(missing_parts)}"

            if is_semantically_correct:
                results["passed"] += 1
                results["details"].append({
                    "query": query,
                    "sql": sql,
                    "expected": expected_sql,
                    "status": "PASS"
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "query": query,
                    "sql": sql,
                    "expected": expected_sql,
                    "status": "FAIL",
                    "reason": reason
                })

        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "query": query,
                "status": "FAIL",
                "reason": f"Error: {str(e)}"
            })

    return results
