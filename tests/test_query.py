"""Tests for query service."""
import pytest
from unittest.mock import AsyncMock, patch
from app.query import QueryService

@pytest.mark.asyncio
async def test_generate_sql_returns_valid_select():
    service = QueryService(
        openai_api_key="test-key",
        clickhouse_key_id="test-key-id",
        clickhouse_key_secret="test-key-secret",
        clickhouse_url="https://queries.clickhouse.cloud/service/test/run"
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
        clickhouse_key_id="test-key-id",
        clickhouse_key_secret="test-key-secret",
        clickhouse_url="https://queries.clickhouse.cloud/service/test/run"
    )

    with patch.object(service, '_call_clickhouse', new_callable=AsyncMock) as mock_ch:
        mock_ch.return_value = {
            "data": [
                {"order_id": "1", "total_amount": 100.0},
                {"order_id": "2", "total_amount": 200.0}
            ]
        }

        sql = "SELECT order_id, total_amount FROM orders LIMIT 2"
        results = await service.execute_query(sql)

        assert len(results["data"]) == 2
        assert results["data"][0]["order_id"] == "1"
        mock_ch.assert_called_once_with(sql)
