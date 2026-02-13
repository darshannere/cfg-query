# CFG Query App Design

Natural language to ClickHouse SQL using GPT-5's Context Free Grammar feature.

## Architecture

```
Browser (HTML/JS) → FastAPI (/api/query) → GPT-5 + CFG tool → Tinybird SQL API → JSON results → Browser
```

- FastAPI backend serves a single HTML page and one API endpoint
- GPT-5 Responses API with a custom Lark grammar tool constrains output to valid ClickHouse SELECT statements
- Generated SQL is executed against Tinybird's REST API
- Frontend shows: text input, generated SQL, results table

## Data

- Source: Kaggle "Online Retail" dataset (Carrie1/ecommerce-data)
- Preprocessed to ~1000 rows
- Ingested into Tinybird

### Schema

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

## Grammar

Single Lark grammar covering ClickHouse SELECT syntax:
- SELECT with columns and aggregations (SUM, COUNT, AVG, MIN, MAX)
- FROM orders (hardcoded single table)
- WHERE with comparisons, AND/OR, date functions, intervals
- GROUP BY, ORDER BY (ASC/DESC), LIMIT
- Aliases (AS)

Explicitly prevents: DROP, INSERT, UPDATE, DELETE, subqueries, joins, UNION, writes.

## Evals (evals/run_evals.py)

1. **Grammar Compliance**: 10-15 NL queries → GPT-5 → parse output with Lark locally. Pass = 100% parse success.
2. **Semantic Correctness**: 5-8 queries with known expected results → run SQL → compare output. Pass = results match.
3. **Edge Cases**: Adversarial inputs (gibberish, injection attempts, vague queries) → verify only valid SELECT produced.

## Stack

- Python + FastAPI
- OpenAI Python SDK (gpt-5)
- Tinybird REST API
- Vanilla HTML/CSS/JS frontend
- Lark (Python) for local grammar validation in evals

## Project Structure

```
cfg-query/
├── app/
│   ├── main.py
│   ├── grammar.py
│   ├── query.py
│   └── static/
│       └── index.html
├── data/
│   ├── preprocess.py
│   └── orders.csv
├── evals/
│   └── run_evals.py
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```
