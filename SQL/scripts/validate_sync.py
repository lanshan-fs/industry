#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from _import_utils import parse_env, query_rows


def query_single_map(sql: str, env: Dict[str, str]) -> Dict[str, str]:
    return {row[0]: row[1] for row in query_rows(sql, env) if len(row) >= 2}


def render_table(headers: List[str], rows: List[List[str]]) -> str:
    if not rows:
        return "_无数据_\n"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        padded = row + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(padded[: len(headers)]) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate raw_import_* to business-table sync results.")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--output", default="SQL/validation-sync-report.md", help="Markdown report output path")
    args = parser.parse_args()

    env = parse_env(Path(args.env_file))

    summary = query_single_map(
        """
        SELECT 'company_basic', COUNT(*) FROM company_basic
        UNION ALL SELECT 'company_branch', COUNT(*) FROM company_branch
        UNION ALL SELECT 'company_qualification', COUNT(*) FROM company_qualification
        UNION ALL SELECT 'company_customer', COUNT(*) FROM company_customer
        UNION ALL SELECT 'company_ranking', COUNT(*) FROM company_ranking
        UNION ALL SELECT 'company_recruit', COUNT(*) FROM company_recruit
        UNION ALL SELECT 'company_software_copyright', COUNT(*) FROM company_software_copyright
        UNION ALL SELECT 'company_work_copyright', COUNT(*) FROM company_work_copyright
        UNION ALL SELECT 'company_patent', COUNT(*) FROM company_patent
        UNION ALL SELECT 'company_patent_company_map', COUNT(*) FROM company_patent_company_map
        UNION ALL SELECT 'company_risk', COUNT(*) FROM company_risk
        UNION ALL SELECT 'company_tag_map', COUNT(*) FROM company_tag_map
        UNION ALL SELECT 'category_industry_company_map', COUNT(*) FROM category_industry_company_map;
        """,
        env,
    )

    checks = query_single_map(
        """
        SELECT 'company_basic_null_credit_code', COUNT(*) FROM company_basic WHERE credit_code IS NULL OR TRIM(credit_code) = ''
        UNION ALL SELECT 'company_basic_duplicate_credit_code', COUNT(*) FROM (SELECT credit_code FROM company_basic GROUP BY credit_code HAVING COUNT(*) > 1) t
        UNION ALL SELECT 'count_mismatch_branch', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_branch GROUP BY company_id) b ON c.company_id = b.company_id WHERE c.branch_count <> COALESCE(b.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_recruit', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_recruit GROUP BY company_id) r ON c.company_id = r.company_id WHERE c.recruit_count <> COALESCE(r.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_software', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_software_copyright GROUP BY company_id) s ON c.company_id = s.company_id WHERE c.software_copyright_count <> COALESCE(s.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_work', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_work_copyright GROUP BY company_id) w ON c.company_id = w.company_id WHERE c.work_copyright_count <> COALESCE(w.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_patent', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(DISTINCT company_patent_id) AS cnt FROM company_patent_company_map GROUP BY company_id) p ON c.company_id = p.company_id WHERE c.patent_count <> COALESCE(p.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_customer', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_customer GROUP BY company_id) p ON c.company_id = p.company_id WHERE c.customer_count <> COALESCE(p.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_ranking', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_ranking GROUP BY company_id) p ON c.company_id = p.company_id WHERE c.ranking_count <> COALESCE(p.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_qualification', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_qualification WHERE record_kind = 'qualification' GROUP BY company_id) q ON c.company_id = q.company_id WHERE c.qualification_count <> COALESCE(q.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_license', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_qualification WHERE record_kind = 'license' GROUP BY company_id) q ON c.company_id = q.company_id WHERE c.license_count <> COALESCE(q.cnt, 0)) x;
        """,
        env,
    )

    output_path = Path(args.output)
    lines = [
        "# 同步校验报告",
        "",
        "## 总览",
        "",
        *(f"- `{key}`: {value}" for key, value in summary.items()),
        "",
        "## 关键检查",
        "",
        render_table(["检查项", "结果"], [[key, value] for key, value in checks.items()]).rstrip(),
        "",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"validation report written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
