#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from _import_utils import (
    clean_text,
    insert_rows,
    normalize_company_name,
    parse_bool_flag,
    parse_date,
    parse_env,
    query_json_rows,
    query_mysql,
    run_mysql_sql,
    split_multi_value,
    truncate_text,
)


RAW_TABLE_COLUMNS: Dict[str, List[str]] = {
    "raw_import_company_ai_model_filing": [
        "raw_id",
        "source_file",
        "source_sheet",
        "sheet_row_no",
        "period_raw",
        "filing_type",
        "source_order_raw",
        "territory",
        "model_name",
        "company_name",
        "filing_number",
        "filed_at_raw",
    ],
    "raw_import_company_high_quality_dataset": [
        "raw_id",
        "source_file",
        "source_sheet",
        "sheet_row_no",
        "source_order_raw",
        "dataset_name",
        "applicant_unit",
        "recommender_unit",
    ],
    "raw_import_company_innovation_notice": [
        "raw_id",
        "source_file",
        "source_sheet",
        "notice_type",
        "sheet_row_no",
        "source_order_raw",
        "notice_title",
        "notice_category",
        "company_name",
        "owner_name",
        "product_name",
        "reg_no",
        "acceptance_no",
        "public_date_raw",
        "public_end_date_raw",
        "rare_disease_flag_raw",
    ],
}


BUSINESS_TABLES = [
    "company_ai_model_filing",
    "company_high_quality_dataset",
    "company_innovation_notice",
]


SPLIT_PATTERN = r"[;\n；、,，]+"
EMPTY_NAME_SET = {"无", "暂无", "-", "--", "不涉及", "nan", "None"}


def query_company_id_map(env: Dict[str, str]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    output = query_mysql("SELECT company_name, company_id FROM company_basic WHERE company_name IS NOT NULL;", env)
    for line in output.splitlines():
        if not line:
            continue
        company_name, company_id = line.split("\t", 1)
        normalized = normalize_company_name(company_name)
        if normalized:
            result[normalized] = int(company_id)
    return result


def resolve_company_matches(company_id_map: Dict[str, int], *values: Any) -> List[Tuple[int, str]]:
    results: List[Tuple[int, str]] = []
    seen: set[int] = set()
    for value in values:
        text = clean_text(value)
        if not text:
            continue
        candidates = [text, *split_multi_value(text, SPLIT_PATTERN)]
        for candidate in candidates:
            normalized = normalize_company_name(candidate)
            if not normalized or normalized in EMPTY_NAME_SET:
                continue
            company_id = company_id_map.get(normalized)
            if company_id is None or company_id in seen:
                continue
            seen.add(company_id)
            results.append((company_id, normalized))
    return results


def ensure_company_basic_count_rows(env: Dict[str, str]) -> None:
    run_mysql_sql(
        """
        INSERT INTO company_basic_count (company_id)
        SELECT company_id
        FROM company_basic
        ON DUPLICATE KEY UPDATE company_id = VALUES(company_id);
        """,
        env,
    )


def truncate_business_tables(env: Dict[str, str]) -> None:
    statements = ["SET FOREIGN_KEY_CHECKS = 0;"]
    for table in BUSINESS_TABLES:
        statements.append(f"TRUNCATE TABLE `{table}`;")
    statements.append("SET FOREIGN_KEY_CHECKS = 1;")
    run_mysql_sql("\n".join(statements) + "\n", env)


def refresh_count_columns(env: Dict[str, str]) -> None:
    run_mysql_sql(
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_ai_model_filing GROUP BY company_id) t
          ON c.company_id = t.company_id
        SET c.ai_model_filing_count = COALESCE(t.cnt, 0);

        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_high_quality_dataset GROUP BY company_id) t
          ON c.company_id = t.company_id
        SET c.high_quality_dataset_count = COALESCE(t.cnt, 0);

        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_innovation_notice GROUP BY company_id) t
          ON c.company_id = t.company_id
        SET c.innovation_notice_count = COALESCE(t.cnt, 0);
        """,
        env,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync auxiliary raw_import_* tables into business tables.")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--batch-size", type=int, default=500, help="INSERT batch size")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    if not env_path.exists():
        raise FileNotFoundError(f".env 文件不存在: {env_path}")
    env = parse_env(env_path)

    raw_tables = {table: query_json_rows(table, columns, env) for table, columns in RAW_TABLE_COLUMNS.items()}
    company_id_map = query_company_id_map(env)

    ensure_company_basic_count_rows(env)
    truncate_business_tables(env)

    ai_rows: List[Sequence[Any]] = []
    dataset_rows: List[Sequence[Any]] = []
    innovation_rows: List[Sequence[Any]] = []
    ai_seen: set[Tuple[int, str, str]] = set()
    dataset_seen: set[Tuple[int, str]] = set()
    innovation_seen: set[Tuple[int, str, str, str, str, str]] = set()
    unmatched_stats = {"ai_model": 0, "dataset": 0, "innovation": 0}

    for row in raw_tables["raw_import_company_ai_model_filing"]:
        matches = resolve_company_matches(company_id_map, row.get("company_name"))
        if not matches:
            unmatched_stats["ai_model"] += 1
            continue
        model_name = clean_text(row.get("model_name"))
        filing_no = clean_text(row.get("filing_number"))
        if not model_name:
            continue
        for company_id, company_name_raw in matches:
            dedupe_key = (company_id, filing_no or "", model_name)
            if dedupe_key in ai_seen:
                continue
            ai_seen.add(dedupe_key)
            ai_rows.append(
                (
                    company_id,
                    truncate_text(company_name_raw, 255),
                    truncate_text(model_name, 255),
                    truncate_text(filing_no, 255),
                    truncate_text(clean_text(row.get("filing_type")), 64),
                    truncate_text(clean_text(row.get("territory")), 255),
                    parse_date(row.get("filed_at_raw")),
                    truncate_text(clean_text(row.get("period_raw")), 64),
                    truncate_text(clean_text(row.get("source_file")), 255),
                    truncate_text(clean_text(row.get("source_sheet")), 128),
                )
            )

    for row in raw_tables["raw_import_company_high_quality_dataset"]:
        matches = resolve_company_matches(company_id_map, row.get("applicant_unit"))
        if not matches:
            unmatched_stats["dataset"] += 1
            continue
        dataset_name = clean_text(row.get("dataset_name"))
        if not dataset_name:
            continue
        applicant_unit = clean_text(row.get("applicant_unit"))
        for company_id, company_name_raw in matches:
            dedupe_key = (company_id, dataset_name)
            if dedupe_key in dataset_seen:
                continue
            dataset_seen.add(dedupe_key)
            dataset_rows.append(
                (
                    company_id,
                    truncate_text(company_name_raw, 255),
                    truncate_text(dataset_name, 255),
                    truncate_text(applicant_unit, 65535),
                    truncate_text(clean_text(row.get("recommender_unit")), 255),
                    None,
                    truncate_text(clean_text(row.get("source_file")), 255),
                    truncate_text(clean_text(row.get("source_sheet")), 128),
                )
            )

    for row in raw_tables["raw_import_company_innovation_notice"]:
        matches = resolve_company_matches(company_id_map, row.get("company_name"), row.get("owner_name"))
        if not matches:
            unmatched_stats["innovation"] += 1
            continue
        notice_type = clean_text(row.get("notice_type"))
        if not notice_type:
            continue
        notice_title = clean_text(row.get("notice_title"))
        notice_category = clean_text(row.get("notice_category"))
        product_name = clean_text(row.get("product_name"))
        reg_no = clean_text(row.get("reg_no"))
        acceptance_no = clean_text(row.get("acceptance_no"))
        owner_name = clean_text(row.get("owner_name"))
        for company_id, company_name_raw in matches:
            dedupe_key = (
                company_id,
                notice_type,
                reg_no or "",
                acceptance_no or "",
                product_name or "",
                owner_name or "",
            )
            if dedupe_key in innovation_seen:
                continue
            innovation_seen.add(dedupe_key)
            innovation_rows.append(
                (
                    company_id,
                    truncate_text(company_name_raw, 255),
                    truncate_text(notice_type, 64),
                    truncate_text(notice_title, 255),
                    truncate_text(notice_category, 255),
                    truncate_text(product_name, 255),
                    truncate_text(reg_no, 255),
                    truncate_text(acceptance_no, 255),
                    truncate_text(owner_name, 255),
                    parse_date(row.get("public_date_raw")),
                    parse_date(row.get("public_end_date_raw")),
                    parse_bool_flag(row.get("rare_disease_flag_raw")),
                    truncate_text(clean_text(row.get("source_file")), 255),
                    truncate_text(clean_text(row.get("source_sheet")), 128),
                )
            )

    insert_rows(
        env,
        "company_ai_model_filing",
        [
            "company_id",
            "company_name_raw",
            "model_name",
            "filing_no",
            "filing_type",
            "territory",
            "filed_at",
            "source_period_raw",
            "source_file",
            "source_sheet",
        ],
        ai_rows,
        batch_size=args.batch_size,
    )
    insert_rows(
        env,
        "company_high_quality_dataset",
        [
            "company_id",
            "company_name_raw",
            "dataset_name",
            "applicant_unit_raw",
            "recommender_unit",
            "announced_at",
            "source_file",
            "source_sheet",
        ],
        dataset_rows,
        batch_size=args.batch_size,
    )
    insert_rows(
        env,
        "company_innovation_notice",
        [
            "company_id",
            "company_name_raw",
            "notice_type",
            "notice_title",
            "notice_category",
            "product_name",
            "reg_no",
            "acceptance_no",
            "owner_name",
            "public_date",
            "public_end_date",
            "rare_disease_flag",
            "source_file",
            "source_sheet",
        ],
        innovation_rows,
        batch_size=args.batch_size,
    )

    refresh_count_columns(env)

    print(f"[sync-aux] company_ai_model_filing: {len(ai_rows)}")
    print(f"[sync-aux] company_high_quality_dataset: {len(dataset_rows)}")
    print(f"[sync-aux] company_innovation_notice: {len(innovation_rows)}")
    print(
        "[sync-aux] unmatched raw rows: "
        f"ai_model={unmatched_stats['ai_model']}, "
        f"dataset={unmatched_stats['dataset']}, "
        f"innovation={unmatched_stats['innovation']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("[error] mysql command failed", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
