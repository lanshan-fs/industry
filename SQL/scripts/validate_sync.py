#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


def parse_env(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def mysql_base_cmd(env: Dict[str, str]) -> Tuple[List[str], Dict[str, str]]:
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
    cmd, child_env = mysql_base_cmd(env)
    cmd.extend(["-e", sql])
    result = subprocess.run(cmd, text=True, capture_output=True, env=child_env, check=True)
    rows: List[List[str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def query_single_map(sql: str, env: Dict[str, str]) -> Dict[str, str]:
    rows = query_rows(sql, env)
    return {row[0]: row[1] for row in rows if len(row) >= 2}


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
        UNION ALL SELECT 'tmp_credit_code', COUNT(*) FROM company_basic WHERE credit_code LIKE 'TMP%'
        UNION ALL SELECT 'chaoyang_company', COUNT(*) FROM company_basic WHERE is_chaoyang_company = 1
        UNION ALL SELECT 'company_branch', COUNT(*) FROM company_branch
        UNION ALL SELECT 'company_contact_phone', COUNT(*) FROM company_contact_phone
        UNION ALL SELECT 'company_software_copyright', COUNT(*) FROM company_software_copyright
        UNION ALL SELECT 'company_patent', COUNT(*) FROM company_patent
        UNION ALL SELECT 'company_patent_company_map', COUNT(*) FROM company_patent_company_map
        UNION ALL SELECT 'company_customer', COUNT(*) FROM company_customer
        UNION ALL SELECT 'company_ranking', COUNT(*) FROM company_ranking
        UNION ALL SELECT 'company_recruit', COUNT(*) FROM company_recruit
        UNION ALL SELECT 'company_risk', COUNT(*) FROM company_risk;
        """,
        env,
    )

    checks = query_single_map(
        """
        SELECT 'company_basic_null_credit_code', COUNT(*) FROM company_basic WHERE credit_code IS NULL OR TRIM(credit_code) = ''
        UNION ALL SELECT 'company_basic_duplicate_credit_code', COUNT(*) FROM (SELECT credit_code FROM company_basic GROUP BY credit_code HAVING COUNT(*) > 1) t
        UNION ALL SELECT 'company_basic_null_company_name', COUNT(*) FROM company_basic WHERE company_name IS NULL OR TRIM(company_name) = ''
        UNION ALL SELECT 'contact_phone_orphans', COUNT(*) FROM company_contact_phone p LEFT JOIN company_basic b ON p.company_id = b.company_id WHERE b.company_id IS NULL
        UNION ALL SELECT 'software_orphans', COUNT(*) FROM company_software_copyright s LEFT JOIN company_basic b ON s.company_id = b.company_id WHERE b.company_id IS NULL
        UNION ALL SELECT 'patent_type_map_orphans', COUNT(*) FROM company_patent_patent_type_map m LEFT JOIN company_patent p ON m.company_patent_id = p.company_patent_id LEFT JOIN company_patent_type t ON m.company_patent_type_id = t.company_patent_type_id WHERE p.company_patent_id IS NULL OR t.company_patent_type_id IS NULL
        UNION ALL SELECT 'patent_company_map_orphans', COUNT(*) FROM company_patent_company_map m LEFT JOIN company_patent p ON m.company_patent_id = p.company_patent_id LEFT JOIN company_basic b ON m.company_id = b.company_id WHERE p.company_patent_id IS NULL OR b.company_id IS NULL
        UNION ALL SELECT 'count_mismatch_branch', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_branch GROUP BY company_id) b ON c.company_id = b.company_id WHERE c.branch_count <> COALESCE(b.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_recruit', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_recruit GROUP BY company_id) r ON c.company_id = r.company_id WHERE c.recruit_count <> COALESCE(r.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_software', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_software_copyright GROUP BY company_id) s ON c.company_id = s.company_id WHERE c.software_copyright_count <> COALESCE(s.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_work', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_work_copyright GROUP BY company_id) w ON c.company_id = w.company_id WHERE c.work_copyright_count <> COALESCE(w.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_patent', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(DISTINCT company_patent_id) AS cnt FROM company_patent_company_map GROUP BY company_id) p ON c.company_id = p.company_id WHERE c.patent_count <> COALESCE(p.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_customer', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_customer GROUP BY company_id) p ON c.company_id = p.company_id WHERE c.customer_count <> COALESCE(p.cnt, 0)) x
        UNION ALL SELECT 'count_mismatch_ranking', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_ranking GROUP BY company_id) p ON c.company_id = p.company_id WHERE c.ranking_count <> COALESCE(p.cnt, 0)) x;
        """,
        env,
    )

    raw_deltas = query_single_map(
        """
        SELECT 'raw_delta_branch', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_branch GROUP BY company_id) b ON c.company_id = b.company_id WHERE c.branch_count_raw <> COALESCE(b.cnt, 0)) x
        UNION ALL SELECT 'raw_delta_recruit', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_recruit GROUP BY company_id) r ON c.company_id = r.company_id WHERE c.recruit_count_raw <> COALESCE(r.cnt, 0)) x
        UNION ALL SELECT 'raw_delta_software', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_software_copyright GROUP BY company_id) s ON c.company_id = s.company_id WHERE c.software_copyright_count_raw <> COALESCE(s.cnt, 0)) x
        UNION ALL SELECT 'raw_delta_work', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_work_copyright GROUP BY company_id) w ON c.company_id = w.company_id WHERE c.work_copyright_count_raw <> COALESCE(w.cnt, 0)) x
        UNION ALL SELECT 'raw_delta_patent', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(DISTINCT company_patent_id) AS cnt FROM company_patent_company_map GROUP BY company_id) p ON c.company_id = p.company_id WHERE c.patent_count_raw <> COALESCE(p.cnt, 0)) x
        UNION ALL SELECT 'raw_delta_customer', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_customer GROUP BY company_id) p ON c.company_id = p.company_id WHERE c.customer_count_raw <> COALESCE(p.cnt, 0)) x
        UNION ALL SELECT 'raw_delta_ranking', COUNT(*) FROM (SELECT c.company_id FROM company_basic_count c LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_ranking GROUP BY company_id) p ON c.company_id = p.company_id WHERE c.ranking_count_raw <> COALESCE(p.cnt, 0)) x;
        """,
        env,
    )

    software_samples = query_rows(
        """
        SELECT b.company_name, c.software_copyright_count_raw, COALESCE(s.cnt,0) AS actual_software_count
        FROM company_basic b
        JOIN company_basic_count c ON b.company_id = c.company_id
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_software_copyright GROUP BY company_id) s ON b.company_id = s.company_id
        WHERE c.software_copyright_count_raw <> COALESCE(s.cnt,0)
        ORDER BY ABS(c.software_copyright_count_raw - COALESCE(s.cnt,0)) DESC, b.company_name
        LIMIT 10;
        """,
        env,
    )
    work_samples = query_rows(
        """
        SELECT b.company_name, c.work_copyright_count_raw, COALESCE(w.cnt,0) AS actual_work_count
        FROM company_basic b
        JOIN company_basic_count c ON b.company_id = c.company_id
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_work_copyright GROUP BY company_id) w ON b.company_id = w.company_id
        WHERE c.work_copyright_count_raw <> COALESCE(w.cnt,0)
        ORDER BY ABS(c.work_copyright_count_raw - COALESCE(w.cnt,0)) DESC, b.company_name
        LIMIT 10;
        """,
        env,
    )
    patent_samples = query_rows(
        """
        SELECT b.company_name, c.patent_count_raw, COALESCE(p.cnt,0) AS actual_patent_count
        FROM company_basic b
        JOIN company_basic_count c ON b.company_id = c.company_id
        LEFT JOIN (SELECT company_id, COUNT(DISTINCT company_patent_id) AS cnt FROM company_patent_company_map GROUP BY company_id) p ON b.company_id = p.company_id
        WHERE c.patent_count_raw <> COALESCE(p.cnt,0)
        ORDER BY ABS(c.patent_count_raw - COALESCE(p.cnt,0)) DESC, b.company_name
        LIMIT 10;
        """,
        env,
    )

    report_lines = [
        "# 同步校验报告",
        "",
        "本报告用于校验 `raw_import_* -> 结构化业务表` 的同步结果。",
        "",
        "## 总览",
        "",
        f"- `company_basic`: {summary.get('company_basic', '0')}",
        f"- `TMP*` 临时信用代码企业数: {summary.get('tmp_credit_code', '0')}",
        f"- `is_chaoyang_company = 1` 企业数: {summary.get('chaoyang_company', '0')}",
        f"- `company_branch`: {summary.get('company_branch', '0')}",
        f"- `company_contact_phone`: {summary.get('company_contact_phone', '0')}",
        f"- `company_software_copyright`: {summary.get('company_software_copyright', '0')}",
        f"- `company_patent`: {summary.get('company_patent', '0')}",
        f"- `company_patent_company_map`: {summary.get('company_patent_company_map', '0')}",
        f"- `company_customer`: {summary.get('company_customer', '0')}",
        f"- `company_ranking`: {summary.get('company_ranking', '0')}",
        f"- `company_recruit`: {summary.get('company_recruit', '0')}",
        f"- `company_risk`: {summary.get('company_risk', '0')}",
        "",
        "## 关键检查",
        "",
        render_table(
            ["检查项", "结果"],
            [[key, value] for key, value in checks.items()],
        ).rstrip(),
        "",
        "## 原始聚合值与结构化明细差异",
        "",
        render_table(
            ["检查项", "结果"],
            [[key, value] for key, value in raw_deltas.items()],
        ).rstrip(),
        "",
        "## 差异样本",
        "",
        "### 软件著作权原始聚合值差异",
        "",
        render_table(["企业名称", "原始聚合计数", "实际明细数"], software_samples).rstrip(),
        "",
        "### 作品著作权原始聚合值差异",
        "",
        render_table(["企业名称", "原始聚合计数", "实际明细数"], work_samples).rstrip(),
        "",
        "### 专利原始聚合值差异",
        "",
        render_table(["企业名称", "原始聚合计数", "实际明细数"], patent_samples).rstrip(),
        "",
        "## 说明",
        "",
        "- `count_mismatch_*` 为 0 说明结构化计数字段已经和对应明细表完全对齐。",
        "- `raw_delta_*` 大于 0 说明 Excel 中的原始聚合值与可落到明细表的实际数量存在差异，这些原值已单独保留，不再覆盖结构化计数。",
        "- `TMP*` 信用代码表示原始 Excel 中缺少统一社会信用代码，当前同步阶段为了满足主表唯一约束生成了临时值。",
        "",
    ]

    output_path = Path(args.output)
    output_path.write_text("\n".join(report_lines).strip() + "\n", encoding="utf-8")
    print(f"validation report written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
