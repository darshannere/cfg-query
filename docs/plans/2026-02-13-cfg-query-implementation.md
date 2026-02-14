# CFG Query App Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a natural language to ClickHouse SQL query interface using GPT-5's CFG feature with Tinybird backend.

**Architecture:** FastAPI serves a single-page frontend and `/api/query` endpoint. User inputs natural language → GPT-5 with Lark grammar constraint → valid SELECT statement → Tinybird REST API → JSON results displayed.

**Tech Stack:** Python, FastAPI, OpenAI Python SDK (GPT-5), Tinybird, Lark parser, vanilla HTML/CSS/JS

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

**Step 1: Create requirements.txt**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
openai==1.12.0
lark==1.1.9
python-dotenv==1.0.0
httpx==0.26.0
pytest==8.0.0
pytest-asyncio==0.23.4
```

**Step 2: Create .env.example**

```bash
OPENAI_API_KEY=your_openai_api_key_here
TINYBIRD_TOKEN=your_tinybird_token_here
TINYBIRD_HOST=https://api.tinybird.co
```

**Step 3: Create .gitignore**

```txt
.env
__pycache__/
*.pyc
.pytest_cache/
venv/
.venv/
*.log
.DS_Store
```

**Step 4: Commit project setup**

```bash
git add requirements.txt .env.example .gitignore
git commit -m "feat: initial project setup with dependencies and config

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Data Preprocessing

**Files:**
- Create: `data/preprocess.py`
- Download: `data/online_retail.csv` (from Kaggle)

**Step 1: Create preprocessing script**

Create `data/preprocess.py`:

```python
"""Preprocess Kaggle Online Retail dataset for Tinybird ingestion."""
import pandas as pd
from pathlib import Path

def preprocess_online_retail(input_path: str, output_path: str, max_rows: int = 1000):
    """
    Load, clean, and sample the Online Retail dataset.

    Args:
        input_path: Path to raw CSV file
        output_path: Path to write preprocessed CSV
        max_rows: Maximum number of rows to include
    """
    # Read the dataset
    df = pd.read_csv(input_path, encoding='latin-1')

    # Rename columns to match schema
    df = df.rename(columns={
        'InvoiceNo': 'order_id',
        'CustomerID': 'customer_id',
        'Description': 'product_name',
        'StockCode': 'category',
        'Quantity': 'quantity',
        'UnitPrice': 'unit_price',
        'InvoiceDate': 'order_date',
        'Country': 'country'
    })

    # Calculate total_amount
    df['total_amount'] = df['quantity'] * df['unit_price']

    # Clean data
    df = df.dropna(subset=['customer_id', 'product_name'])
    df['customer_id'] = df['customer_id'].astype(int).astype(str)
    df['order_id'] = df['order_id'].astype(str)
    df['category'] = df['category'].astype(str)

    # Parse dates (format: MM/DD/YYYY HH:MM)
    df['order_date'] = pd.to_datetime(df['order_date'], format='%m/%d/%Y %H:%M')

    # Sample rows
    df = df.head(max_rows)

    # Select final columns
    columns = [
        'order_id', 'customer_id', 'product_name', 'category',
        'quantity', 'unit_price', 'total_amount', 'order_date', 'country'
    ]
    df = df[columns]

    # Write to CSV
    df.to_csv(output_path, index=False)
    print(f"Preprocessed {len(df)} rows to {output_path}")

if __name__ == "__main__":
    input_file = Path(__file__).parent / "online_retail.csv"
    output_file = Path(__file__).parent / "orders.csv"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        print("Download from: https://www.kaggle.com/datasets/carrie1/ecommerce-data")
        exit(1)

    preprocess_online_retail(str(input_file), str(output_file))
```

**Step 2: Add pandas to requirements**

Edit `requirements.txt`, add:
```txt
pandas==2.2.0
```

**Step 3: Commit data preprocessing**

```bash
git add data/preprocess.py requirements.txt
git commit -m "feat: add data preprocessing script for Online Retail dataset

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Step 4: Download and preprocess data (manual)**

Manual steps (document in README later):
1. Download dataset from Kaggle: https://www.kaggle.com/datasets/carrie1/ecommerce-data
2. Save as `data/online_retail.csv`
3. Run: `python data/preprocess.py`
4. Upload `data/orders.csv` to Tinybird with the schema from design doc

---

## Task 3: Lark Grammar Definition

**Files:**
- Create: `app/grammar.py`
- Create: `tests/test_grammar.py`

**Step 1: Write failing test for grammar**

Create `tests/test_grammar.py`:

```python
"""Tests for ClickHouse SELECT grammar."""
import pytest
from lark import Lark, LarkError
from app.grammar import get_clickhouse_grammar

def test_grammar_parses_simple_select():
    grammar = get_clickhouse_grammar()
    parser = Lark(grammar, start='query')

    sql = "SELECT * FROM orders LIMIT 10"
    result = parser.parse(sql)
    assert result is not None

def test_grammar_parses_aggregation():
    grammar = get_clickhouse_grammar()
    parser = Lark(grammar, start='query')

    sql = "SELECT country, SUM(total_amount) AS revenue FROM orders GROUP BY country ORDER BY revenue DESC LIMIT 5"
    result = parser.parse(sql)
    assert result is not None

def test_grammar_parses_where_clause():
    grammar = get_clickhouse_grammar()
    parser = Lark(grammar, start='query')

    sql = "SELECT * FROM orders WHERE quantity > 5 AND country = 'United Kingdom' LIMIT 20"
    result = parser.parse(sql)
    assert result is not None

def test_grammar_rejects_drop():
    grammar = get_clickhouse_grammar()
    parser = Lark(grammar, start='query')

    sql = "DROP TABLE orders"
    with pytest.raises(LarkError):
        parser.parse(sql)

def test_grammar_rejects_insert():
    grammar = get_clickhouse_grammar()
    parser = Lark(grammar, start='query')

    sql = "INSERT INTO orders VALUES (1, 2, 3)"
    with pytest.raises(LarkError):
        parser.parse(sql)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_grammar.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'app.grammar'"

**Step 3: Create grammar module**

Create `app/__init__.py` (empty file)

Create `app/grammar.py`:

```python
"""Lark grammar for ClickHouse SELECT queries."""

def get_clickhouse_grammar() -> str:
    """
    Returns a Lark grammar that constrains GPT-5 output to valid ClickHouse SELECT statements.

    Allows: SELECT with columns, aggregations, WHERE, GROUP BY, ORDER BY, LIMIT
    Prevents: DROP, INSERT, UPDATE, DELETE, subqueries, joins, UNION
    """
    return r"""
    ?query: select_stmt

    select_stmt: "SELECT" select_list "FROM" table_name [where_clause] [group_by_clause] [order_by_clause] [limit_clause]

    select_list: "*" | column_expr ("," column_expr)*

    column_expr: aggregate_func "(" (column_name | "*") ")" [alias]
               | column_name [alias]

    aggregate_func: "SUM" | "COUNT" | "AVG" | "MIN" | "MAX"

    alias: "AS" CNAME

    table_name: "orders"

    where_clause: "WHERE" condition

    condition: comparison
             | condition "AND" condition
             | condition "OR" condition
             | "(" condition ")"

    comparison: column_name op value
              | column_name ">" value
              | column_name "<" value
              | column_name ">=" value
              | column_name "<=" value
              | column_name "=" value
              | column_name "!=" value

    op: ">" | "<" | ">=" | "<=" | "=" | "!="

    value: SIGNED_NUMBER
         | ESCAPED_STRING

    group_by_clause: "GROUP BY" column_name ("," column_name)*

    order_by_clause: "ORDER BY" column_name [sort_order] ("," column_name [sort_order])*

    sort_order: "ASC" | "DESC"

    limit_clause: "LIMIT" INT

    column_name: CNAME

    %import common.CNAME
    %import common.INT
    %import common.SIGNED_NUMBER
    %import common.ESCAPED_STRING
    %import common.WS
    %ignore WS
    """
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_grammar.py -v
```
Expected: All tests PASS

**Step 5: Commit grammar**

```bash
git add app/__init__.py app/grammar.py tests/test_grammar.py
git commit -m "feat: add Lark grammar for ClickHouse SELECT queries

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Query Service

**Files:**
- Create: `app/query.py`
- Create: `tests/test_query.py`

**Step 1: Write failing test for query service**

Create `tests/test_query.py`:

```python
"""Tests for query service."""
import pytest
from unittest.mock import AsyncMock, patch
from app.query import QueryService

@pytest.mark.asyncio
async def test_generate_sql_returns_valid_select():
    service = QueryService(
        openai_api_key="test-key",
        tinybird_token="test-token",
        tinybird_host="https://api.tinybird.co"
    )

    with patch.object(service, '_call_gpt5', new_callable=AsyncMock) as mock_gpt:
        mock_gpt.return_value = "SELECT * FROM orders LIMIT 10"

        sql = await service.generate_sql("show me 10 orders")

        assert sql == "SELECT * FROM orders LIMIT 10"
        mock_gpt.assert_called_once()

@pytest.mark.asyncio
async def test_execute_query_returns_results():
    service = QueryService(
        openai_api_key="test-key",
        tinybird_token="test-token",
        tinybird_host="https://api.tinybird.co"
    )

    with patch.object(service, '_call_tinybird', new_callable=AsyncMock) as mock_tb:
        mock_tb.return_value = {
            "data": [
                {"order_id": "1", "total_amount": 100.0},
                {"order_id": "2", "total_amount": 200.0}
            ]
        }

        sql = "SELECT order_id, total_amount FROM orders LIMIT 2"
        results = await service.execute_query(sql)

        assert len(results["data"]) == 2
        assert results["data"][0]["order_id"] == "1"
        mock_tb.assert_called_once_with(sql)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_query.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'app.query'"

**Step 3: Create query service**

Create `app/query.py`:

```python
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

        return response.choices[0].message.content.strip()

    async def _call_tinybird(self, sql: str) -> dict:
        """Execute SQL query via Tinybird REST API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.tinybird_host}/v0/sql",
                headers={
                    "Authorization": f"Bearer {self.tinybird_token}"
                },
                params={"q": sql}
            )
            response.raise_for_status()
            return response.json()
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_query.py -v
```
Expected: All tests PASS

**Step 5: Commit query service**

```bash
git add app/query.py tests/test_query.py
git commit -m "feat: add query service with GPT-5 CFG and Tinybird integration

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: FastAPI Backend

**Files:**
- Create: `app/main.py`
- Create: `tests/test_main.py`

**Step 1: Write failing test for API endpoint**

Create `tests/test_main.py`:

```python
"""Tests for FastAPI application."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_index_returns_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_query_endpoint_returns_results(client):
    with patch("app.main.query_service") as mock_service:
        mock_service.generate_sql = AsyncMock(return_value="SELECT * FROM orders LIMIT 5")
        mock_service.execute_query = AsyncMock(return_value={
            "data": [{"order_id": "1", "total_amount": 100.0}]
        })

        response = client.post(
            "/api/query",
            json={"query": "show me 5 orders"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "sql" in data
        assert "results" in data
        assert data["sql"] == "SELECT * FROM orders LIMIT 5"
        assert len(data["results"]["data"]) == 1

def test_query_endpoint_validates_input(client):
    response = client.post("/api/query", json={})
    assert response.status_code == 422  # Validation error
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/test_main.py -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'app.main'"

**Step 3: Create FastAPI application**

Create `app/main.py`:

```python
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
query_service = QueryService(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    tinybird_token=os.getenv("TINYBIRD_TOKEN"),
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
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_main.py -v
```
Expected: All tests PASS

**Step 5: Commit FastAPI backend**

```bash
git add app/main.py tests/test_main.py
git commit -m "feat: add FastAPI backend with query endpoint

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Frontend HTML

**Files:**
- Create: `app/static/index.html`

**Step 1: Create frontend HTML**

Create `app/static/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CFG Query - Natural Language to SQL</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 2rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 2rem;
        }

        h1 {
            color: #333;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            color: #666;
            margin-bottom: 2rem;
        }

        .query-form {
            margin-bottom: 2rem;
        }

        .input-group {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        input[type="text"] {
            flex: 1;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }

        button {
            padding: 0.75rem 2rem;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.2s;
        }

        button:hover {
            background: #0056b3;
        }

        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }

        .sql-output {
            background: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 1rem;
            margin-bottom: 1rem;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .results-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }

        .results-table th,
        .results-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }

        .results-table th {
            background: #f8f9fa;
            font-weight: 600;
        }

        .error {
            background: #fff3cd;
            border: 1px solid #ffc107;
            color: #856404;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }

        .loading {
            color: #666;
            font-style: italic;
        }

        .section-title {
            color: #333;
            margin: 1.5rem 0 0.5rem 0;
            font-size: 1.1rem;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>CFG Query</h1>
        <p class="subtitle">Natural language to ClickHouse SQL using GPT-5</p>

        <div class="query-form">
            <div class="input-group">
                <input
                    type="text"
                    id="queryInput"
                    placeholder="e.g., Show me top 5 countries by revenue"
                    autocomplete="off"
                />
                <button id="submitBtn" onclick="executeQuery()">Query</button>
            </div>
        </div>

        <div id="output"></div>
    </div>

    <script>
        async function executeQuery() {
            const input = document.getElementById('queryInput');
            const output = document.getElementById('output');
            const submitBtn = document.getElementById('submitBtn');
            const query = input.value.trim();

            if (!query) {
                output.innerHTML = '<div class="error">Please enter a query</div>';
                return;
            }

            // Disable button and show loading
            submitBtn.disabled = true;
            output.innerHTML = '<div class="loading">Generating SQL and fetching results...</div>';

            try {
                const response = await fetch('/api/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ query })
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Query failed');
                }

                const data = await response.json();

                // Display SQL
                let html = '<h2 class="section-title">Generated SQL</h2>';
                html += `<div class="sql-output">${escapeHtml(data.sql)}</div>`;

                // Display results
                html += '<h2 class="section-title">Results</h2>';

                if (data.results.data && data.results.data.length > 0) {
                    const rows = data.results.data;
                    const columns = Object.keys(rows[0]);

                    html += '<table class="results-table">';
                    html += '<thead><tr>';
                    columns.forEach(col => {
                        html += `<th>${escapeHtml(col)}</th>`;
                    });
                    html += '</tr></thead><tbody>';

                    rows.forEach(row => {
                        html += '<tr>';
                        columns.forEach(col => {
                            html += `<td>${escapeHtml(String(row[col]))}</td>`;
                        });
                        html += '</tr>';
                    });

                    html += '</tbody></table>';
                } else {
                    html += '<p>No results found</p>';
                }

                output.innerHTML = html;

            } catch (error) {
                output.innerHTML = `<div class="error">Error: ${escapeHtml(error.message)}</div>`;
            } finally {
                submitBtn.disabled = false;
            }
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Allow Enter key to submit
        document.getElementById('queryInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                executeQuery();
            }
        });
    </script>
</body>
</html>
```

**Step 2: Commit frontend**

```bash
git add app/static/index.html
git commit -m "feat: add frontend HTML with query interface

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Evaluation Script

**Files:**
- Create: `evals/run_evals.py`
- Create: `evals/test_queries.json`

**Step 1: Create test queries file**

Create `evals/test_queries.json`:

```json
{
  "grammar_compliance": [
    {
      "query": "Show me 10 orders",
      "expected_contains": ["SELECT", "FROM orders", "LIMIT"]
    },
    {
      "query": "What are the top 5 countries by revenue?",
      "expected_contains": ["SELECT", "SUM", "GROUP BY", "ORDER BY", "DESC"]
    },
    {
      "query": "Find orders with quantity greater than 10",
      "expected_contains": ["SELECT", "WHERE", "quantity", ">"]
    },
    {
      "query": "Average unit price by category",
      "expected_contains": ["SELECT", "AVG", "GROUP BY category"]
    }
  ],
  "semantic_correctness": [
    {
      "query": "Count total orders",
      "expected_sql": "SELECT COUNT(*) FROM orders",
      "validate_result": "row_count"
    }
  ],
  "edge_cases": [
    {
      "query": "asdfghjkl",
      "expect_valid_select": true
    },
    {
      "query": "DROP TABLE orders; SELECT * FROM orders",
      "expect_valid_select": true
    }
  ]
}
```

**Step 2: Create evaluation script**

Create `evals/run_evals.py`:

```python
"""Evaluation script for CFG Query app."""
import asyncio
import json
import sys
from pathlib import Path
from lark import Lark, LarkError

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.query import QueryService
from app.grammar import get_clickhouse_grammar
import os
from dotenv import load_dotenv

load_dotenv()

async def run_grammar_compliance_tests(service: QueryService, test_cases: list) -> dict:
    """Test that generated SQL parses with the Lark grammar."""
    grammar = get_clickhouse_grammar()
    parser = Lark(grammar, start='query')

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
            # Generate SQL
            sql = await service.generate_sql(query)

            # Try to parse
            parser.parse(sql)

            # Check expected tokens
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
                "reason": f"Grammar parsing failed: {e}"
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "query": query,
                "status": "FAIL",
                "reason": f"Error: {e}"
            })

    return results

async def run_edge_case_tests(service: QueryService, test_cases: list) -> dict:
    """Test that adversarial inputs still produce valid SELECT statements."""
    grammar = get_clickhouse_grammar()
    parser = Lark(grammar, start='query')

    results = {
        "total": len(test_cases),
        "passed": 0,
        "failed": 0,
        "details": []
    }

    for case in test_cases:
        query = case["query"]

        try:
            sql = await service.generate_sql(query)

            # Must parse as valid SELECT
            parser.parse(sql)

            # Must not contain dangerous keywords
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
                "reason": f"Error: {e}"
            })

    return results

async def main():
    """Run all evaluation tests."""
    # Load test cases
    test_file = Path(__file__).parent / "test_queries.json"
    with open(test_file) as f:
        test_data = json.load(f)

    # Initialize service
    service = QueryService(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        tinybird_token=os.getenv("TINYBIRD_TOKEN"),
        tinybird_host=os.getenv("TINYBIRD_HOST", "https://api.tinybird.co")
    )

    print("=" * 60)
    print("CFG Query Evaluation Suite")
    print("=" * 60)

    # Run grammar compliance tests
    print("\n[1/2] Grammar Compliance Tests")
    print("-" * 60)
    grammar_results = await run_grammar_compliance_tests(
        service,
        test_data["grammar_compliance"]
    )
    print(f"Passed: {grammar_results['passed']}/{grammar_results['total']}")
    for detail in grammar_results["details"]:
        print(f"  {detail['status']}: {detail['query']}")
        if detail["status"] == "FAIL":
            print(f"    Reason: {detail['reason']}")

    # Run edge case tests
    print("\n[2/2] Edge Case Tests")
    print("-" * 60)
    edge_results = await run_edge_case_tests(
        service,
        test_data["edge_cases"]
    )
    print(f"Passed: {edge_results['passed']}/{edge_results['total']}")
    for detail in edge_results["details"]:
        print(f"  {detail['status']}: {detail['query'][:50]}...")
        if detail["status"] == "FAIL":
            print(f"    Reason: {detail['reason']}")

    # Summary
    print("\n" + "=" * 60)
    total_passed = grammar_results["passed"] + edge_results["passed"]
    total_tests = grammar_results["total"] + edge_results["total"]
    print(f"Overall: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
```

**Step 3: Commit evaluation script**

```bash
git add evals/run_evals.py evals/test_queries.json
git commit -m "feat: add evaluation suite for grammar and edge cases

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: README Documentation

**Files:**
- Create: `README.md`

**Step 1: Create README**

Create `README.md`:

```markdown
# CFG Query App

Natural language to ClickHouse SQL using GPT-5's Context Free Grammar feature.

## Architecture

```
Browser → FastAPI → GPT-5 + CFG → Tinybird → Results
```

- **Frontend**: Vanilla HTML/CSS/JS single page
- **Backend**: FastAPI with `/api/query` endpoint
- **AI**: GPT-5 Responses API with Lark grammar constraint
- **Database**: Tinybird (ClickHouse-compatible) with Online Retail dataset

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in:

```bash
OPENAI_API_KEY=your_openai_api_key
TINYBIRD_TOKEN=your_tinybird_token
TINYBIRD_HOST=https://api.tinybird.co
```

### 3. Prepare Data

1. Download dataset from [Kaggle](https://www.kaggle.com/datasets/carrie1/ecommerce-data)
2. Save as `data/online_retail.csv`
3. Run preprocessing:

```bash
python data/preprocess.py
```

4. Upload `data/orders.csv` to Tinybird with schema:

```sql
CREATE TABLE orders (
    order_id      String,
    customer_id   String,
    product_name  String,
    category      String,
    quantity       UInt32,
    unit_price    Float64,
    total_amount  Float64,
    order_date    DateTime,
    country        String
)
```

### 4. Run Application

```bash
uvicorn app.main:app --reload
```

Visit: http://localhost:8000

## Usage

Enter natural language queries like:

- "Show me 10 orders"
- "What are the top 5 countries by revenue?"
- "Find orders with quantity greater than 10"
- "Average unit price by category"

The app will generate valid ClickHouse SQL and display results.

## Testing

Run unit tests:

```bash
pytest tests/ -v
```

Run evaluation suite:

```bash
python evals/run_evals.py
```

## Grammar

The Lark grammar constrains GPT-5 output to:

**Allowed:**
- SELECT with columns and aggregations (SUM, COUNT, AVG, MIN, MAX)
- FROM orders (single table)
- WHERE with comparisons, AND/OR
- GROUP BY, ORDER BY, LIMIT
- Aliases (AS)

**Prevented:**
- DROP, INSERT, UPDATE, DELETE
- Subqueries, joins, UNION
- Any write operations

## Project Structure

```
cfg-query/
├── app/
│   ├── main.py          # FastAPI application
│   ├── grammar.py       # Lark grammar definition
│   ├── query.py         # Query service (GPT-5 + Tinybird)
│   └── static/
│       └── index.html   # Frontend
├── data/
│   ├── preprocess.py    # Data preprocessing script
│   └── orders.csv       # Preprocessed dataset
├── evals/
│   ├── run_evals.py     # Evaluation suite
│   └── test_queries.json # Test cases
├── tests/               # Unit tests
├── .env                 # Environment variables (gitignored)
├── requirements.txt     # Python dependencies
└── README.md
```

## License

MIT
```

**Step 2: Commit README**

```bash
git add README.md
git commit -m "docs: add comprehensive README with setup and usage instructions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Verification Steps

After completing all tasks:

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Run tests**: `pytest tests/ -v` (all should pass)
3. **Set up .env**: Copy `.env.example` to `.env` and add real API keys
4. **Prepare data**: Download, preprocess, upload to Tinybird
5. **Start server**: `uvicorn app.main:app --reload`
6. **Test frontend**: Visit http://localhost:8000 and try queries
7. **Run evals**: `python evals/run_evals.py`

---

## Notes

- Each task follows TDD: test → fail → implement → pass → commit
- Frequent commits with descriptive messages
- Grammar prevents SQL injection and destructive operations
- Frontend is minimal but functional
- Evals validate grammar compliance and safety
