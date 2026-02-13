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
