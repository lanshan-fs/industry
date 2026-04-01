#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from company_tag_rule_engine import RULES_JSON_PATH, dump_rules_json


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_env(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def mysql_command(env: Dict[str, str]) -> Tuple[List[str], Dict[str, str]]:
    host = env.get("DB_HOST", "127.0.0.1")
    if host == "localhost":
        host = "127.0.0.1"
    cmd = [
        "mysql",
        "-h",
        host,
        "-P",
        env.get("DB_PORT", "3306"),
        "-u",
        env.get("DB_USER", "root"),
        "-D",
        env.get("DB_NAME", "industrial_chain"),
        "--default-character-set=utf8mb4",
        "--batch",
        "--raw",
        "--skip-column-names",
    ]
    child_env = os.environ.copy()
    if env.get("DB_PASSWORD"):
        child_env["MYSQL_PWD"] = env["DB_PASSWORD"]
    return cmd, child_env


def run_mysql_sql(sql: str, env: Dict[str, str]) -> None:
    cmd, child_env = mysql_command(env)
    result = subprocess.run(cmd, text=True, input=sql, capture_output=True, env=child_env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "mysql command failed")


def escape_sql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def build_insert_sql(rules: List[Dict[str, object]]) -> str:
    values_sql: List[str] = []
    for row in rules:
        values_sql.append(
            "("
            f"{row['company_tag_id']}, "
            f"'{escape_sql_string(str(row['company_tag_auto_rule_type']))}', "
            f"'{escape_sql_string(__import__('json').dumps(row['rule_definition'], ensure_ascii=False, separators=(',', ':')))}', "
            f"{row['is_enabled']}"
            ")"
        )
    return (
        "START TRANSACTION;\n"
        "DELETE FROM company_tag_auto_rule;\n"
        "INSERT INTO company_tag_auto_rule "
        "(company_tag_id, company_tag_auto_rule_type, rule_definition, is_enabled)\n"
        "VALUES\n  "
        + ",\n  ".join(values_sql)
        + ";\n"
        "COMMIT;\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and import first-wave company tag auto rules.")
    parser.add_argument("--env-file", default=str(PROJECT_ROOT / ".env"), help="Path to .env file")
    parser.add_argument("--apply", action="store_true", help="Import generated rules into company_tag_auto_rule")
    args = parser.parse_args()

    rules = dump_rules_json(RULES_JSON_PATH)
    print(f"[ok] generated {RULES_JSON_PATH}")
    print(f"[ok] rules={len(rules)}")

    if not args.apply:
        return 0

    env = parse_env(Path(args.env_file))
    run_mysql_sql(build_insert_sql(rules), env)
    print("[ok] imported rules into company_tag_auto_rule")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise
