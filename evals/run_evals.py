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
