#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pymysql


ROOT = Path(__file__).resolve().parents[2]
INIT_SQL_PATH = ROOT / "SQL" / "sql" / "init.sql"
ENV_PATH = ROOT / ".env"


def load_env(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().replace("\r", "")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def mysql_env(password: str) -> dict[str, str]:
    env = os.environ.copy()
    env["MYSQL_PWD"] = password
    return env


def mysql_cmd(host: str, user: str, database: str | None = None) -> list[str]:
    cmd = ["mysql", "-h", host, "-u", user]
    if database:
        cmd.extend(["-D", database])
    return cmd


def mysql_connect(host: str, user: str, password: str, database: str):
    return pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
        autocommit=True,
    )


def run_mysql(sql: str, host: str, user: str, password: str, database: str | None = None) -> None:
    subprocess.run(
        mysql_cmd(host, user, database=database),
        input=sql,
        text=True,
        env=mysql_env(password),
        check=True,
    )


def fetch_table_counts(host: str, user: str, password: str, database: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    with mysql_connect(host, user, password, database) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                counts[table] = int(cursor.fetchone()[0])
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify SQL/sql/init.sql can fully rebuild the live MySQL database.")
    parser.add_argument("--keep-temp-db", action="store_true", help="Keep the temporary regression database after verification.")
    args = parser.parse_args()

    env = load_env(ENV_PATH)
    db_host = (env.get("DB_HOST") or "127.0.0.1").replace("\r", "").strip() or "127.0.0.1"
    db_user = (env.get("DB_USER") or "root").replace("\r", "").strip()
    db_password = (env.get("DB_PASSWORD") or "").replace("\r", "").strip()
    db_name = (env.get("DB_NAME") or "industrial_chain").replace("\r", "").strip()
    temp_db = f"{db_name}_regression_{datetime.now():%Y%m%d_%H%M%S}"

    init_sql = INIT_SQL_PATH.read_text(encoding="utf-8")
    temp_sql = init_sql.replace(f"`{db_name}`", f"`{temp_db}`")

    run_mysql(f"DROP DATABASE IF EXISTS `{temp_db}`;\n", db_host, db_user, db_password)
    run_mysql(temp_sql, db_host, db_user, db_password)

    source_counts = fetch_table_counts(db_host, db_user, db_password, db_name)
    target_counts = fetch_table_counts(db_host, db_user, db_password, temp_db)

    source_tables = sorted(source_counts)
    target_tables = sorted(target_counts)
    if source_tables != target_tables:
        missing_in_target = sorted(set(source_tables) - set(target_tables))
        extra_in_target = sorted(set(target_tables) - set(source_tables))
        raise SystemExit(
            "table set mismatch: "
            f"missing_in_target={missing_in_target or '[]'} "
            f"extra_in_target={extra_in_target or '[]'}"
        )

    mismatches = [
        {"table": table, "source": source_counts[table], "target": target_counts[table]}
        for table in source_tables
        if source_counts[table] != target_counts[table]
    ]

    if not args.keep_temp_db:
        run_mysql(f"DROP DATABASE IF EXISTS `{temp_db}`;\n", db_host, db_user, db_password)

    if mismatches:
        print(f"TEMP_DB={temp_db}")
        print(f"TABLES={len(source_tables)}")
        print(f"MISMATCHES={len(mismatches)}")
        for item in mismatches[:20]:
            print(f"{item['table']}\t{item['source']}\t{item['target']}")
        raise SystemExit(1)

    print(f"TEMP_DB={temp_db}")
    print(f"TABLES={len(source_tables)}")
    print("MISMATCHES=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
