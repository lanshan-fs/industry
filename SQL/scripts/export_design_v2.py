#!/usr/bin/env python3
from __future__ import annotations

import csv
import argparse
import re
from pathlib import Path
from typing import Dict, List


HEADER = ["数据表", "字段名", "数据类型", "是否有获取", "说明", "PK", "NOT NULL", "UNIQUE", "DEFAULT", "FK", "CHECK", "备注", "父记录"]


def parse_init_sql(init_sql_path: Path) -> List[Dict[str, str]]:
    text = init_sql_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    rows: List[Dict[str, str]] = []
    table_name = None
    table_comment = ""
    table_rows: List[Dict[str, str]] = []
    row_by_name: Dict[str, Dict[str, str]] = {}

    for line in lines:
        create_match = re.match(r"CREATE TABLE `([^`]+)` \(", line, flags=re.IGNORECASE)
        if create_match:
            table_name = create_match.group(1)
            table_comment = ""
            table_rows = []
            row_by_name = {}
            continue

        if table_name is None:
            continue

        column_match = re.match(
            r"\s*`([^`]+)`\s+([A-Z]+(?:\([^)]+\))?(?:\s+UNSIGNED)?|JSON|TEXT|LONGTEXT)\s*(.*)",
            line,
            flags=re.IGNORECASE,
        )
        if column_match:
            column_name = column_match.group(1)
            data_type = column_match.group(2).upper()
            rest = column_match.group(3)
            comment_match = re.search(r"COMMENT '([^']*)'", rest)
            default_match = re.search(r"DEFAULT ([^ ]+(?:\([^)]+\))?)", rest)
            row = {
                "数据表": table_name,
                "字段名": column_name,
                "数据类型": data_type,
                "是否有获取": "",
                "说明": comment_match.group(1) if comment_match else "",
                "PK": "",
                "NOT NULL": "1" if "NOT NULL" in rest.upper() else "",
                "UNIQUE": "",
                "DEFAULT": default_match.group(1) if default_match else "",
                "FK": "",
                "CHECK": "",
                "备注": "AUTO_INCREMENT" if "AUTO_INCREMENT" in rest.upper() else "",
                "父记录": "",
            }
            table_rows.append(row)
            row_by_name[column_name] = row
            continue

        primary_match = re.match(r"\s*PRIMARY KEY \((.+)\),?$", line, flags=re.IGNORECASE)
        if primary_match:
            cols = re.findall(r"`([^`]+)`", primary_match.group(1))
            for col in cols:
                if col in row_by_name:
                    row_by_name[col]["PK"] = "1"
            continue

        unique_match = re.match(r"\s*UNIQUE KEY `[^`]+` \((.+)\),?$", line, flags=re.IGNORECASE)
        if unique_match:
            cols = re.findall(r"`([^`]+)`", unique_match.group(1))
            for col in cols:
                if col in row_by_name:
                    row_by_name[col]["UNIQUE"] = "1"
            continue

        fk_match = re.match(
            r"\s*CONSTRAINT `[^`]+`\s+FOREIGN KEY \(`([^`]+)`\) REFERENCES `([^`]+)` \(`([^`]+)`\),?$",
            line,
            flags=re.IGNORECASE,
        )
        if fk_match:
            col, fk_table, fk_col = fk_match.groups()
            if col in row_by_name:
                row_by_name[col]["FK"] = f"{fk_table}.{fk_col}"
            continue

        check_match = re.match(r"\s*CONSTRAINT `[^`]+`\s+CHECK \((.+)\)\)?[, ]*$", line, flags=re.IGNORECASE)
        if check_match:
            expr = check_match.group(1)
            matched_columns = re.findall(r"`([^`]+)`", expr)
            if not matched_columns:
                continue
            if len(matched_columns) == 1:
                col = matched_columns[0]
                if col in row_by_name:
                    row_by_name[col]["CHECK"] = expr
            else:
                for col in matched_columns:
                    if col in row_by_name and not row_by_name[col]["CHECK"]:
                        row_by_name[col]["CHECK"] = expr
            continue

        end_match = re.match(r"\)\s*ENGINE=.*COMMENT='([^']*)';", line, flags=re.IGNORECASE)
        if end_match:
            table_comment = end_match.group(1)
            for row in table_rows:
                row["父记录"] = table_comment
            rows.extend(table_rows)
            table_name = None
            table_rows = []
            row_by_name = {}

    return rows


def write_csv(rows: List[Dict[str, str]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in HEADER})


def main() -> int:
    parser = argparse.ArgumentParser(description="Export executable SQL design to CSV.")
    parser.add_argument(
        "--output",
        default="SQL/mysql-design/design-2026-3-20-V2.csv",
        help="CSV output path",
    )
    args = parser.parse_args()
    init_sql_path = Path("SQL/sql/init.sql")
    output_path = Path(args.output)
    rows = parse_init_sql(init_sql_path)
    write_csv(rows, output_path)
    print(f"exported {len(rows)} rows -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
