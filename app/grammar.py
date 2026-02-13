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
         | STRING

    group_by_clause: "GROUP BY" column_name ("," column_name)*

    order_by_clause: "ORDER BY" column_name [sort_order] ("," column_name [sort_order])*

    sort_order: "ASC" | "DESC"

    limit_clause: "LIMIT" INT

    column_name: CNAME

    STRING: /'[^']*'/ | /"[^"]*"/

    %import common.CNAME
    %import common.INT
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
    """
