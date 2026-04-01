#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pymysql


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_ROOT = PROJECT_ROOT / "SQL"
TMP_ROOT = SQL_ROOT / "tmp"
RULES_JSON_PATH = SQL_ROOT / "data" / "category_industry_company_rules.json"
CHAIN_JSON_PATH = SQL_ROOT / "data" / "chain_industry_seed.json"

TEXT_COLUMNS = [
    "company_name",
    "industry_belong",
    "business_scope",
    "qualification_label",
]

STAGE_NUMBERS = {"upstream": 1, "midstream": 2, "downstream": 3}


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


def normalize_text(value: str) -> str:
    return re.sub(r"[\s\-/+()（）【】\[\]{}|,:：;；、，。.\"'·]+", "", (value or "").lower())


def load_rules() -> List[Dict[str, object]]:
    rules = json.loads(RULES_JSON_PATH.read_text(encoding="utf-8"))
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"{RULES_JSON_PATH} 缺少有效规则")
    for rule in rules:
        rule["include_any"] = [normalize_text(str(item)) for item in rule.get("include_any", []) if str(item).strip()]
        rule["exclude_any"] = [normalize_text(str(item)) for item in rule.get("exclude_any", []) if str(item).strip()]
    return rules


def load_stage_map() -> Dict[str, int]:
    seeds = json.loads(CHAIN_JSON_PATH.read_text(encoding="utf-8"))
    return {
        str(item["category_level_code"]): STAGE_NUMBERS[str(item["stage_key"])]
        for item in seeds
    }


def fetch_category_maps(env: Dict[str, str]) -> Tuple[Dict[str, int], Dict[str, str]]:
    rows = query_rows(
        "SELECT category_level_code, category_id, category_name FROM category_industry WHERE category_level = 1 AND field_belong = 1;",
        env,
    )
    code_to_id: Dict[str, int] = {}
    code_to_name: Dict[str, str] = {}
    for code, category_id, name in rows:
        code_to_id[str(code)] = int(category_id)
        code_to_name[str(code)] = str(name)
    return code_to_id, code_to_name


def fetch_company_rows(env: Dict[str, str]) -> List[Dict[str, object]]:
    rows = query_rows(
        """
        SELECT
          company_id,
          COALESCE(company_name, ''),
          COALESCE(industry_belong, ''),
          COALESCE(business_scope, ''),
          COALESCE(qualification_label, '')
        FROM company_basic
        ORDER BY company_id;
        """,
        env,
    )
    companies: List[Dict[str, object]] = []
    for company_id, company_name, industry_belong, business_scope, qualification_label in rows:
        companies.append(
            {
                "company_id": int(company_id),
                "company_name": company_name,
                "industry_belong": industry_belong,
                "business_scope": business_scope,
                "qualification_label": qualification_label,
            }
        )
    return companies


def company_text(company: Dict[str, object]) -> str:
    joined = " ".join(str(company[column]) for column in TEXT_COLUMNS)
    return normalize_text(joined)


def matches_rule(normalized_company_text: str, rule: Dict[str, object]) -> bool:
    include_any = rule.get("include_any", [])
    if not include_any:
        return False
    if not any(keyword in normalized_company_text for keyword in include_any):
        return False
    exclude_any = rule.get("exclude_any", [])
    return not any(keyword in normalized_company_text for keyword in exclude_any)


def chunked(items: List[int], size: int = 500) -> List[List[int]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def apply_assignments(
    assignments: Dict[int, Set[int]],
    company_stage_map: Dict[int, int],
    env: Dict[str, str],
) -> None:
    insert_rows = [
        (category_id, company_id)
        for company_id in sorted(assignments)
        for category_id in sorted(assignments[company_id])
    ]

    stage_buckets: Dict[int, List[int]] = defaultdict(list)
    for company_id, stage in company_stage_map.items():
        stage_buckets[stage].append(company_id)

    connection = mysql_connect(env)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM category_industry_company_map;")
            cursor.execute("UPDATE company_basic SET industry_chain_link = NULL;")
            if insert_rows:
                cursor.executemany(
                    "INSERT INTO category_industry_company_map (category_id, company_id) VALUES (%s, %s);",
                    insert_rows,
                )
            for stage in sorted(stage_buckets):
                for company_ids in chunked(sorted(stage_buckets[stage])):
                    placeholders = ", ".join(["%s"] * len(company_ids))
                    cursor.execute(
                        f"UPDATE company_basic SET industry_chain_link = %s WHERE company_id IN ({placeholders});",
                        [stage, *company_ids],
                    )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def build_report(
    total_companies: int,
    matched_company_count: int,
    assignments: Dict[int, Set[int]],
    company_stage_map: Dict[int, int],
    code_to_id: Dict[str, int],
    code_to_name: Dict[str, str],
) -> Path:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    report_path = TMP_ROOT / f"category-industry-company-map-report-{date.today().isoformat()}.md"

    category_company_counts: Counter[int] = Counter()
    for category_ids in assignments.values():
        for category_id in category_ids:
            category_company_counts[category_id] += 1

    stage_counts = Counter(company_stage_map.values())
    stage_name_map = {1: "上游", 2: "中游", 3: "下游"}
    code_to_count: Dict[str, int] = {
        code: category_company_counts.get(category_id, 0)
        for code, category_id in code_to_id.items()
    }

    lines = [
        "# 行业分类企业映射重建报告",
        "",
        f"- 日期: {date.today().isoformat()}",
        f"- 企业总数: {total_companies}",
        f"- 命中至少一个行业分类的企业数: {matched_company_count}",
        f"- 生成映射总数: {sum(len(items) for items in assignments.values())}",
        "",
        "## 产业链环节回填",
        "",
        *(f"- {stage_name_map[stage]}: {stage_counts.get(stage, 0)}" for stage in (1, 2, 3)),
        "",
        "## 一级行业分类命中数",
        "",
    ]

    for code, name in sorted(code_to_name.items()):
        lines.append(f"- {code} {name}: {code_to_count[code]}")

    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- 当前为首页链路服务的第一版保守映射，只落一级行业分类。",
            "- 规则仅使用 `company_name`、`industry_belong`、`business_scope`、`qualification_label` 的明确关键词命中。",
            "- 若企业同时命中多个产业链阶段，不回填 `company_basic.industry_chain_link`，保持为空以避免误导。",
            "",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild category_industry_company_map with conservative keyword rules.")
    parser.add_argument("--env-file", default=str(PROJECT_ROOT / ".env"), help="Path to .env file")
    parser.add_argument("--apply", action="store_true", help="Apply rebuilt mappings to MySQL")
    args = parser.parse_args()

    env = parse_env(Path(args.env_file))
    rules = load_rules()
    stage_map = load_stage_map()
    code_to_id, code_to_name = fetch_category_maps(env)
    companies = fetch_company_rows(env)

    assignments: Dict[int, Set[int]] = defaultdict(set)
    company_stage_candidates: Dict[int, Set[int]] = defaultdict(set)

    for company in companies:
        normalized = company_text(company)
        if not normalized:
            continue
        company_id = int(company["company_id"])
        for rule in rules:
            code = str(rule["category_level_code"])
            category_id = code_to_id.get(code)
            if not category_id:
                continue
            if matches_rule(normalized, rule):
                assignments[company_id].add(category_id)
                company_stage_candidates[company_id].add(stage_map[code])

    company_stage_map = {
        company_id: next(iter(stages))
        for company_id, stages in company_stage_candidates.items()
        if len(stages) == 1
    }

    if args.apply:
        apply_assignments(assignments, company_stage_map, env)

    report_path = build_report(
        total_companies=len(companies),
        matched_company_count=len(assignments),
        assignments=assignments,
        company_stage_map=company_stage_map,
        code_to_id=code_to_id,
        code_to_name=code_to_name,
    )

    print(f"[ok] matched companies: {len(assignments)} / {len(companies)}")
    print(f"[ok] generated category/company mappings: {sum(len(items) for items in assignments.values())}")
    print(f"[ok] report: {report_path}")
    if args.apply:
        print("[ok] applied category_industry_company_map rebuild")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
