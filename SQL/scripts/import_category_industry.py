#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_ROOT = PROJECT_ROOT / "SQL"
DEFAULT_MM_PATH = SQL_ROOT / "data" / "行业分类.mm"
DEFAULT_JSON_PATH = SQL_ROOT / "data" / "category_industry.json"


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


def query_rows(sql: str, env: Dict[str, str]) -> List[List[str]]:
    cmd, child_env = mysql_command(env)
    cmd.extend(["-e", sql])
    result = subprocess.run(cmd, text=True, capture_output=True, env=child_env, check=True)
    rows: List[List[str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def run_mysql_sql(sql: str, env: Dict[str, str]) -> None:
    cmd, child_env = mysql_command(env)
    result = subprocess.run(cmd, text=True, input=sql, capture_output=True, env=child_env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "mysql command failed")


def normalize_text(text: Optional[str]) -> str:
    return " ".join((text or "").split())


def parse_mm_to_rows(mm_path: Path) -> List[Dict[str, Optional[object]]]:
    tree = ET.parse(mm_path)
    root = tree.getroot()
    root_node = root.find("./node")
    if root_node is None:
        raise ValueError(f"{mm_path} 缺少根 node")

    root_name = normalize_text(root_node.attrib.get("TEXT"))
    if root_name != "行业分类":
        raise ValueError(f"{mm_path} 根节点 TEXT 不是 '行业分类'，实际为 {root_name!r}")

    rows: List[Dict[str, Optional[object]]] = []
    next_category_id = 1

    def visit(parent_node: ET.Element, level: int, parent_code: Optional[str], path: Sequence[str]) -> None:
        nonlocal next_category_id
        children = [child for child in parent_node.findall("node")]
        if not children:
            return
        if level > 3:
            raise ValueError(f"发现超过 4 级的分类路径: {' > '.join(path)}")

        for index, child in enumerate(children, start=1):
            category_name = normalize_text(child.attrib.get("TEXT"))
            if not category_name:
                raise ValueError(f"发现空分类名称，路径: {' > '.join(path) or 'ROOT'}")
            code = f"{parent_code or ''}{index:02d}"
            current_path = [*path, category_name]
            rows.append(
                {
                    "category_id": next_category_id,
                    "category_name": category_name,
                    "category_level": level,
                    "category_level_code": code,
                    "category_level_code_parent": parent_code,
                    "field_belong": 1,
                    "sort_order": index * 10,
                }
            )
            next_category_id += 1
            visit(child, level + 1, code, current_path)

    visit(root_node, 0, None, [])
    return rows


def build_insert_sql(rows: Sequence[Dict[str, Optional[object]]]) -> str:
    values_sql: List[str] = []
    for row in rows:
        parent_code = row["category_level_code_parent"]
        parent_sql = "NULL" if parent_code is None else f"'{escape_sql_string(str(parent_code))}'"
        values_sql.append(
            "("
            f"{row['category_id']}, "
            f"'{escape_sql_string(str(row['category_name']))}', "
            f"{row['category_level']}, "
            f"'{escape_sql_string(str(row['category_level_code']))}', "
            f"{parent_sql}, "
            f"{row['field_belong']}, "
            f"{row['sort_order']}"
            ")"
        )

    return (
        "START TRANSACTION;\n"
        "DELETE FROM category_industry;\n"
        "INSERT INTO category_industry "
        "(category_id, category_name, category_level, category_level_code, category_level_code_parent, field_belong, sort_order)\n"
        "VALUES\n  "
        + ",\n  ".join(values_sql)
        + ";\n"
        "COMMIT;\n"
    )


def escape_sql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def ensure_related_tables_empty(env: Dict[str, str]) -> Dict[str, int]:
    checks = query_rows(
        """
        SELECT 'category_industry_company_map', COUNT(*) FROM category_industry_company_map
        UNION ALL
        SELECT 'chain_industry_category_industry_map', COUNT(*) FROM chain_industry_category_industry_map
        UNION ALL
        SELECT 'score_industry_path', COUNT(*) FROM score_industry_path;
        """,
        env,
    )
    counts = {name: int(count) for name, count in checks}
    blocking_tables = [
        table_name
        for table_name in ("category_industry_company_map", "chain_industry_category_industry_map")
        if counts.get(table_name, 0) > 0
    ]
    if blocking_tables:
        details = ", ".join(f"{table}={counts[table]}" for table in blocking_tables)
        raise RuntimeError(
            "导入已中止：关联映射表非空，当前不能直接重建 category_industry。"
            f" 需要先明确重建规则或清空相关映射表。({details})"
        )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert 行业分类.mm to JSON and optionally import category_industry.")
    parser.add_argument("--mm-file", default=str(DEFAULT_MM_PATH), help="Path to 行业分类.mm")
    parser.add_argument("--json-file", default=str(DEFAULT_JSON_PATH), help="Output JSON path")
    parser.add_argument("--env-file", default=str(PROJECT_ROOT / ".env"), help="Path to .env file")
    parser.add_argument("--apply", action="store_true", help="Import generated JSON rows into category_industry")
    args = parser.parse_args()

    mm_path = Path(args.mm_file)
    json_path = Path(args.json_file)
    env_path = Path(args.env_file)

    rows = parse_mm_to_rows(mm_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    level_summary: Dict[int, int] = {}
    for row in rows:
        level = int(row["category_level"])
        level_summary[level] = level_summary.get(level, 0) + 1

    print(f"[ok] generated {json_path} ({len(rows)} rows)")
    print(
        "[ok] level summary: "
        + ", ".join(f"level_{level}={level_summary[level]}" for level in sorted(level_summary))
    )

    if not args.apply:
        return 0

    env = parse_env(env_path)
    related_counts = ensure_related_tables_empty(env)
    run_mysql_sql(build_insert_sql(rows), env)

    print("[ok] imported rows into category_industry")
    if related_counts.get("score_industry_path", 0) > 0:
        print(
            "[warn] score_industry_path 非空，行业路径统计可能需要后续按新分类口径重新校准。",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
