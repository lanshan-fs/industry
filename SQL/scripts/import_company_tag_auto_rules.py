#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from _import_utils import parse_env, run_mysql_sql
from company_tag_rule_engine import RULES_JSON_PATH, load_rules


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def escape_sql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def build_insert_sql(rules: List[Dict[str, object]]) -> str:
    values_sql: List[str] = []
    for row in rules:
        values_sql.append(
            "("
            f"{int(row['company_tag_id'])}, "
            f"'{escape_sql_string(str(row['company_tag_auto_rule_type']))}', "
            f"'{escape_sql_string(json.dumps(row['rule_definition'], ensure_ascii=False, separators=(',', ':')))}', "
            f"{int(row.get('is_enabled', 1))}"
            ")"
        )
    return (
        "START TRANSACTION;\n"
        "DELETE FROM company_tag_auto_rule;\n"
        "INSERT INTO company_tag_auto_rule (company_tag_id, company_tag_auto_rule_type, rule_definition, is_enabled)\n"
        "VALUES\n  "
        + ",\n  ".join(values_sql)
        + ";\n"
        "COMMIT;\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Import company tag auto rules from SQL/data/company_tag_auto_rule.json.")
    parser.add_argument("--env-file", default=str(PROJECT_ROOT / ".env"), help="Path to .env file")
    parser.add_argument("--apply", action="store_true", help="Import rules into company_tag_auto_rule")
    args = parser.parse_args()

    rules = load_rules()
    print(f"[ok] loaded {RULES_JSON_PATH}")
    print(f"[ok] rules={len(rules)}")

    if not args.apply:
        return 0

    env = parse_env(Path(args.env_file))
    run_mysql_sql(build_insert_sql(rules), env)
    print("[ok] imported rules into company_tag_auto_rule")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

