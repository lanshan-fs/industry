#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "SQL" / "sql"
DESIGN_DIR = ROOT / "SQL" / "mysql-design"

INIT_OUTPUT = SQL_DIR / "init-2026-04-10-credit-code.sql"
DESIGN_INPUT = DESIGN_DIR / "design-2026-4-8-V1.csv"
DESIGN_OUTPUT = DESIGN_DIR / "design-2026-4-10-V1.csv"
def read_current_init_sql() -> str:
    return (SQL_DIR / "init.sql").read_text(encoding="utf-8")

def transform_company_basic_block(sql: str) -> str:
    pattern = re.compile(
        r"(CREATE TABLE `company_basic` \(\n)(.*?)(\n\) ENGINE=InnoDB.*?COMMENT='企业基础信息表';)",
        re.S,
    )
    match = pattern.search(sql)
    if not match:
        return sql
    header, body, footer = match.groups()
    filtered_lines = []
    for line in body.splitlines():
        if re.fullmatch(r"\s*`company_id`\s+bigint\s+NOT NULL AUTO_INCREMENT COMMENT '企业唯一标识',", line):
            continue
        filtered_lines.append(line)
    body = "\n".join(filtered_lines)
    body = body.replace("PRIMARY KEY (`company_id`)", "PRIMARY KEY (`credit_code`)")
    return sql[: match.start()] + header + body + footer + sql[match.end() :]


def transform_sql(sql: str) -> str:
    sql = transform_company_basic_block(sql)
    sql = re.sub(r"DROP TABLE IF EXISTS `raw_import_[^`]+`;\nCREATE TABLE `raw_import_[^;]+?\) ENGINE=InnoDB.*?;\n\n", "", sql, flags=re.S)

    replacements = [
        ("customer_company_id", "customer_credit_code"),
        ("supplier_company_id", "supplier_credit_code"),
        ("enterprise_id", "enterprise_credit_code"),
        ("company_id", "credit_code"),
    ]
    for source, target in replacements:
        sql = re.sub(rf"\b{source}\b", target, sql)

    sql = re.sub(
        r"`(credit_code|customer_credit_code|supplier_credit_code|enterprise_credit_code)`\s+bigint",
        r"`\1` char(18) COLLATE utf8mb4_unicode_ci",
        sql,
    )

    comment_replacements = {
        "credit_code": "统一社会信用代码",
        "customer_credit_code": "客户统一社会信用代码",
        "supplier_credit_code": "供应商统一社会信用代码",
        "enterprise_credit_code": "统一社会信用代码",
    }
    for column_name, comment in comment_replacements.items():
        sql = re.sub(
            rf"(`{column_name}`\s+char\(18\) COLLATE utf8mb4_unicode_ci(?: NOT NULL| DEFAULT NULL)? COMMENT )'[^']+'",
            rf"\1'{comment}'",
            sql,
        )

    sql = sql.replace("REFERENCES `company_basic` (`credit_code`)", "REFERENCES `company_basic` (`credit_code`)")
    return sql

def transform_design() -> None:
    with DESIGN_INPUT.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))

    header = rows[0]
    output_rows = [header]
    for row in rows[1:]:
        if not row:
            continue
        table_name, field_name = row[0], row[1]
        if table_name.startswith("raw_import_"):
            continue
        if table_name == "company_basic" and field_name == "company_id":
            continue

        rename_map = {
            "company_id": "credit_code",
            "customer_company_id": "customer_credit_code",
            "supplier_company_id": "supplier_credit_code",
            "enterprise_id": "enterprise_credit_code",
        }
        row[1] = rename_map.get(field_name, field_name)

        if row[1] in {"credit_code", "customer_credit_code", "supplier_credit_code", "enterprise_credit_code"}:
            row[2] = "CHAR(18)"
            if row[1] == "credit_code":
                row[4] = "统一社会信用代码"
            elif row[1] == "customer_credit_code":
                row[4] = "客户统一社会信用代码"
            elif row[1] == "supplier_credit_code":
                row[4] = "供应商统一社会信用代码"
            else:
                row[4] = "统一社会信用代码"

        if table_name == "company_basic" and row[1] == "credit_code":
            row[5] = "1"
            row[7] = "1"

        for index in [9, 12]:
            if len(row) > index and row[index]:
                for source, target in rename_map.items():
                    row[index] = row[index].replace(source, target)

        output_rows.append(row)

    with DESIGN_OUTPUT.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(output_rows)


def main() -> None:
    latest_sql = transform_sql(read_current_init_sql())
    INIT_OUTPUT.write_text(latest_sql, encoding="utf-8")
    (SQL_DIR / "init.sql").write_text(latest_sql, encoding="utf-8")
    transform_design()
    print("Generated credit_code schema files.")


if __name__ == "__main__":
    main()
