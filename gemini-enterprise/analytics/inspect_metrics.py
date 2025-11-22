#!/usr/bin/env python3
"""Inspect Gemini Enterprise analytics metrics imported into BigQuery."""

from __future__ import annotations

import argparse
from typing import Iterable, Optional, Sequence

from google.cloud import bigquery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect BigQuery tables that store Gemini Enterprise analytics."
    )
    parser.add_argument("--project-id", required=True, help="Source data project ID.")
    parser.add_argument("--dataset-id", required=True, help="BigQuery dataset ID.")
    parser.add_argument("--table-id", required=True, help="BigQuery table ID.")
    parser.add_argument(
        "--billing-project",
        help="Optional alternate project to bill the inspection queries to.",
    )
    parser.add_argument(
        "--date-field",
        help="Override the DATE/TIMESTAMP column used for range summaries.",
    )
    parser.add_argument(
        "--value-field",
        help="Override the numeric field used for aggregate totals.",
    )
    parser.add_argument(
        "--group-field",
        help="Optional dimension (STRING) for grouped counts and totals.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of sample rows to print from the table.",
    )
    return parser.parse_args()


def infer_field(
    schema: Sequence[bigquery.SchemaField], field_types: Iterable[str]
) -> Optional[str]:
    type_set = {ft.upper() for ft in field_types}
    for field in schema:
        if field.field_type.upper() in type_set:
            return field.name
    return None


def fully_qualified(project_id: str, dataset_id: str, table_id: str) -> str:
    return f"{project_id}.{dataset_id}.{table_id}"


def print_schema(schema: Sequence[bigquery.SchemaField]) -> None:
    print("Schema:")
    for field in schema:
        mode = f" ({field.mode})" if field.mode != "NULLABLE" else ""
        print(f"  - {field.name}: {field.field_type}{mode}")


def scalar_query(client: bigquery.Client, query: str) -> Optional[bigquery.Row]:
    job = client.query(query)
    results = list(job.result())
    return results[0] if results else None


def sample_rows(
    client: bigquery.Client, table: str, order_field: Optional[str], limit: int
) -> None:
    order_clause = f"ORDER BY `{order_field}` DESC" if order_field else ""
    query = f"SELECT * FROM `{table}` {order_clause} LIMIT {limit}"
    job = client.query(query)
    print(f"\nSample rows (limit {limit}):")
    for row in job.result():
        print(dict(row))


def summarize_groups(
    client: bigquery.Client,
    table: str,
    group_field: Optional[str],
    value_field: Optional[str],
) -> None:
    if not group_field:
        return
    select_expr = f"`{group_field}` AS group_value, COUNT(*) AS row_count"
    if value_field:
        select_expr += f", SUM(`{value_field}`) AS total_value"
    query = (
        f"SELECT {select_expr} "
        f"FROM `{table}` "
        f"GROUP BY group_value "
        f"ORDER BY row_count DESC "
        f"LIMIT 20"
    )
    job = client.query(query)
    print("\nTop group breakdown:")
    for row in job.result():
        print(dict(row))


def main() -> int:
    args = parse_args()
    billing_project = args.billing_project or args.project_id
    table_ref = fully_qualified(args.project_id, args.dataset_id, args.table_id)
    client = bigquery.Client(project=billing_project)
    table = client.get_table(table_ref)

    print(f"Table: {table_ref}")
    print(f"Rows (metadata cache): {table.num_rows}")
    print_schema(table.schema)

    schema = table.schema
    date_field = args.date_field or infer_field(schema, ["DATE", "TIMESTAMP"])

    numeric_types = {"INT64", "FLOAT64", "NUMERIC", "BIGNUMERIC", "DOUBLE"}
    value_field = args.value_field or infer_field(schema, numeric_types)

    string_types = {"STRING"}
    group_field = args.group_field or infer_field(schema, string_types)

    count_row = scalar_query(
        client, f"SELECT COUNT(*) AS total_rows FROM `{table_ref}`"
    )
    if count_row:
        print(f"\nAccurate row count: {count_row['total_rows']}")

    if date_field:
        range_row = scalar_query(
            client,
            f"SELECT MIN(`{date_field}`) AS min_value, "
            f"MAX(`{date_field}`) AS max_value "
            f"FROM `{table_ref}`",
        )
        if range_row:
            print(
                f"Date range ({date_field}): "
                f"{range_row['min_value']} -> {range_row['max_value']}"
            )

    if value_field:
        totals_row = scalar_query(
            client,
            f"SELECT SUM(`{value_field}`) AS total_value "
            f"FROM `{table_ref}`",
        )
        if totals_row:
            print(
                f"Aggregate {value_field} sum: {totals_row['total_value']}"
            )

    sample_rows(client, table_ref, date_field, args.limit)
    summarize_groups(client, table_ref, group_field, value_field)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

