#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pymysql
from pymysql.constants import CLIENT


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "SQL" / "data"
SQL_DIR = ROOT / "SQL" / "sql"
INIT_SQL = SQL_DIR / "init-2026-04-10-credit-code.sql"

BUSINESS_TABLES = [
    "company_basic",
    "company_basic_count",
    "company_address",
    "company_contact_info",
    "company_contact_phone",
    "company_shareholder",
    "company_financing",
    "company_branch",
    "company_customer",
    "company_ranking",
    "company_recruit",
    "company_supplier",
    "company_qualification",
    "company_software_copyright",
    "company_work_copyright",
    "company_patent_type",
    "company_patent",
    "company_patent_company_map",
    "company_patent_patent_type_map",
    "company_risk",
    "company_subdistrict",
    "company_bidding",
    "company_ai_model_filing",
    "company_high_quality_dataset",
    "company_innovation_notice",
]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def connect_mysql(database: str | None = None) -> pymysql.connections.Connection:
    env = load_env(ROOT / ".env")
    return pymysql.connect(
        host=env.get("DB_HOST", "127.0.0.1"),
        user=env.get("DB_USER", "root"),
        password=env.get("DB_PASSWORD", ""),
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        client_flag=CLIENT.MULTI_STATEMENTS,
        autocommit=False,
    )


def load_json(table_name: str) -> list[dict[str, Any]]:
    with (DATA_DIR / f"{table_name}.json").open("r", encoding="utf-8") as file:
        return json.load(file)


def load_business_rows() -> dict[str, list[dict[str, Any]]]:
    rows_by_table: dict[str, list[dict[str, Any]]] = {}
    for table_name in BUSINESS_TABLES:
        rows = load_json(table_name)
        for row in rows:
            invalid_columns = {
                key
                for key in row
                if key in {"company_id", "customer_company_id", "supplier_company_id", "enterprise_id"}
            }
            if invalid_columns:
                raise ValueError(
                    f"{table_name}.json still contains legacy columns: {sorted(invalid_columns)}"
                )
        rows_by_table[table_name] = rows
    return rows_by_table


def execute_sql_file(connection: pymysql.connections.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        cursor.execute(sql)
        while cursor.nextset():
            pass
    connection.commit()


def insert_rows(cursor: pymysql.cursors.Cursor, table_name: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(f"`{column}`" for column in columns)
    sql = f"INSERT INTO `{table_name}` ({column_sql}) VALUES ({placeholders})"
    batch = [tuple(row.get(column) for column in columns) for row in rows]
    cursor.executemany(sql, batch)


def rebuild_database(rows_by_table: dict[str, list[dict[str, Any]]]) -> None:
    with connect_mysql(None) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP DATABASE IF EXISTS `industrial_chain`")
            cursor.execute("CREATE DATABASE `industrial_chain` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        connection.commit()

    with connect_mysql("industrial_chain") as connection:
        execute_sql_file(connection, INIT_SQL)
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table_name in BUSINESS_TABLES:
                insert_rows(cursor, table_name, rows_by_table[table_name])
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        connection.commit()


def main() -> None:
    rows_by_table = load_business_rows()
    rebuild_database(rows_by_table)
    print("Rebuilt industrial_chain with credit_code-based enterprise imports.")


if __name__ == "__main__":
    main()
