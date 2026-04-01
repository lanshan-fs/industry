#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pymysql


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_ROOT = PROJECT_ROOT / "SQL"
DEFAULT_JSON_PATH = SQL_ROOT / "data" / "chain_industry_seed.json"


def parse_env(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def mysql_connect(env: Dict[str, str]):
    host = env.get("DB_HOST", "127.0.0.1")
    if host == "localhost":
        host = "127.0.0.1"
    return pymysql.connect(
        host=host,
        port=int(env.get("DB_PORT", "3306")),
        user=env.get("DB_USER", "root"),
        password=env.get("DB_PASSWORD", ""),
        database=env.get("DB_NAME", "industrial_chain"),
        charset="utf8mb4",
        autocommit=False,
    )


def query_rows(sql: str, env: Dict[str, str]) -> List[List[str]]:
    connection = mysql_connect(env)
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return [list(row) for row in cursor.fetchall()]
    finally:
        connection.close()


def load_seed_rows(json_path: Path) -> List[Dict[str, object]]:
    rows = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{json_path} 缺少有效链路种子数据")
    return rows


def fetch_category_id_map(env: Dict[str, str]) -> Dict[str, int]:
    rows = query_rows(
        "SELECT category_level_code, category_id FROM category_industry WHERE category_level = 1 AND field_belong = 1;",
        env,
    )
    return {str(code): int(category_id) for code, category_id in rows}


def apply_seed(seed_rows: List[Dict[str, object]], category_id_map: Dict[str, int], env: Dict[str, str]) -> None:
    chain_rows = []
    map_rows = []

    for row in seed_rows:
        chain_id = int(row["chain_id"])
        category_level_code = str(row["category_level_code"])
        category_id = category_id_map.get(category_level_code)
        if not category_id:
            raise ValueError(f"未找到一级行业分类编码 {category_level_code} 对应的 category_id")
        chain_rows.append((chain_id, str(row["chain_name"]), str(row["chain_des"])))
        map_rows.append((chain_id, category_id))

    connection = mysql_connect(env)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM chain_industry_category_industry_map;")
            cursor.execute("DELETE FROM chain_industry;")
            cursor.executemany(
                "INSERT INTO chain_industry (chain_id, chain_name, chain_des) VALUES (%s, %s, %s);",
                chain_rows,
            )
            cursor.executemany(
                "INSERT INTO chain_industry_category_industry_map (chain_id, category_id) VALUES (%s, %s);",
                map_rows,
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import chain_industry seed data and level-1 mappings.")
    parser.add_argument("--json-file", default=str(DEFAULT_JSON_PATH), help="Path to chain_industry seed json")
    parser.add_argument("--env-file", default=str(PROJECT_ROOT / ".env"), help="Path to .env file")
    parser.add_argument("--apply", action="store_true", help="Import seed data into MySQL")
    args = parser.parse_args()

    json_path = Path(args.json_file)
    env_path = Path(args.env_file)
    seed_rows = load_seed_rows(json_path)

    print(f"[ok] loaded {len(seed_rows)} chain nodes from {json_path}")

    if not args.apply:
        return 0

    env = parse_env(env_path)
    category_id_map = fetch_category_id_map(env)
    apply_seed(seed_rows, category_id_map, env)
    print("[ok] imported chain_industry and chain_industry_category_industry_map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
