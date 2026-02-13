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
