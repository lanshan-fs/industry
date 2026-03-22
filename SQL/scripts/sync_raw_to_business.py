#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Optional, Sequence, Tuple


SYNC_TABLES = [
    "company_patent_patent_type_map",
    "company_patent_company_map",
    "company_patent_type",
    "company_patent",
    "company_software_copyright",
    "company_ranking",
    "company_customer",
    "company_work_copyright",
    "company_recruit",
    "company_risk",
    "company_subdistrict",
    "company_basic_count",
    "company_listing_status",
    "company_financing",
    "company_qualification",
    "company_address",
    "company_employee_count",
    "company_shareholder",
    "company_recommended_phone",
    "company_contact_info",
    "company_contact_phone",
    "company_branch",
    "company_basic",
]

RAW_TABLE_COLUMNS: Dict[str, List[str]] = {
    "raw_import_company_basic": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "credit_code",
        "establish_info",
        "register_capital_raw",
        "paid_capital_raw",
        "company_type_raw",
        "org_type_raw",
        "investment_type_raw",
        "company_scale_raw",
        "branch_count_raw",
        "branch_names_raw",
        "address_info_raw",
        "financing_round_raw",
        "qualification_raw",
        "legal_representative",
        "register_number",
        "org_code",
        "industry_name_raw",
        "business_scope_raw",
        "email_business",
        "email_auth",
        "shareholder_raw",
        "contact_phone_1",
        "contact_phone_2",
        "contact_phone_3",
        "contact_phone_4",
        "contact_phone_5",
        "recommended_phone",
    ],
    "raw_import_company_operation": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "employee_count_raw",
        "insured_count_raw",
        "listing_status_raw",
        "national_industry_raw",
        "contact_info_raw",
        "same_phone_count_raw",
        "email_business",
        "is_micro_enterprise_raw",
        "changed_info_raw",
        "is_general_taxpayer_raw",
        "has_financing_info_raw",
        "has_bidding_raw",
        "bidding_count_raw",
        "has_recruitment_raw",
        "recruit_count_raw",
        "has_customer_info_raw",
        "customer_count_raw",
        "has_ranking_raw",
        "ranking_count_raw",
    ],
    "raw_import_company_ip_overview": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "has_work_copyright_raw",
        "work_copyright_count_raw",
        "has_software_copyright_raw",
        "software_copyright_count_raw",
        "is_high_tech_enterprise_raw",
        "is_srdi_sme_raw",
        "is_gazelle_company_raw",
        "is_tech_sme_raw",
        "is_egalet_company_raw",
        "is_srdi_little_giant_raw",
        "is_innovative_sme_raw",
        "has_patent_raw",
        "patent_count_raw",
    ],
    "raw_import_software_copyright": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "software_name",
        "register_number",
        "software_short_name",
        "register_date_raw",
        "status_raw",
        "obtain_method_raw",
    ],
    "raw_import_company_ranking": [
        "raw_id",
        "company_name",
        "ranking_name",
        "ranking_type",
        "ranking_source",
        "ranking_position_raw",
        "ranking_alias",
        "publish_year_raw",
    ],
    "raw_import_company_customer": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "customer_name",
        "sales_ratio_raw",
        "sales_amount_raw",
        "report_period_raw",
        "data_source",
    ],
    "raw_import_company_work_copyright": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "work_name",
        "register_number",
        "work_type_raw",
        "first_publish_date_raw",
        "register_date_raw",
        "status_raw",
        "author_raw",
    ],
    "raw_import_company_patent": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "patent_number",
        "patent_name",
        "patent_type_raw",
        "application_date_raw",
        "auth_publish_date_raw",
    ],
    "raw_import_company_risk": [
        "raw_id",
        "company_name",
        "source_row_no",
        "legal_doc_case_count_raw",
        "legal_doc_judgement_count_raw",
        "has_legal_document_raw",
        "legal_doc_total_count_raw",
        "has_dishonest_execution_raw",
        "dishonest_execution_count_raw",
        "has_chattel_mortgage_raw",
        "chattel_mortgage_count_raw",
        "has_business_abnormal_raw",
        "business_abnormal_count_raw",
        "has_admin_penalty_raw",
        "admin_penalty_count_raw",
        "has_bankruptcy_overlap_raw",
        "bankruptcy_overlap_count_raw",
        "has_liquidation_info_raw",
        "liquidation_info_count_raw",
        "has_env_penalty_raw",
        "env_penalty_count_raw",
        "has_equity_freeze_raw",
        "equity_freeze_count_raw",
        "has_executed_person_raw",
        "executed_person_count_raw",
        "has_consumption_restriction_raw",
        "consumption_restriction_count_raw",
    ],
    "raw_import_company_subdistrict": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "street_name",
        "region_name",
    ],
    "raw_import_company_recruit": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "position_name",
        "salary_raw",
        "work_year_raw",
        "work_place",
        "edu_req_raw",
        "recruit_time_raw",
    ],
}


def parse_env(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def mysql_command(env: Dict[str, str], with_database: bool = True) -> Tuple[List[str], Dict[str, str]]:
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
        "--default-character-set=utf8mb4",
    ]
    if with_database:
        cmd.extend(["-D", env.get("DB_NAME", "industrial_chain")])
    child_env = os.environ.copy()
    if env.get("DB_PASSWORD"):
        child_env["MYSQL_PWD"] = env["DB_PASSWORD"]
    return cmd, child_env


def run_mysql_sql(sql: str, env: Dict[str, str], with_database: bool = True) -> None:
    cmd, child_env = mysql_command(env, with_database=with_database)
    subprocess.run(cmd, input=sql, text=True, env=child_env, check=True)


def query_mysql(sql: str, env: Dict[str, str], with_database: bool = True) -> str:
    cmd, child_env = mysql_command(env, with_database=with_database)
    cmd.extend(["--batch", "--raw", "--skip-column-names", "-e", sql])
    result = subprocess.run(cmd, text=True, capture_output=True, env=child_env, check=True)
    return result.stdout


def query_json_rows(table: str, columns: Sequence[str], env: Dict[str, str]) -> List[Dict[str, object]]:
    json_args = ", ".join(f"'{column}', `{column}`" for column in columns)
    order_by = "`raw_id`" if "raw_id" in columns else "1"
    sql = f"SELECT JSON_OBJECT({json_args}) FROM `{table}` ORDER BY {order_by};"
    output = query_mysql(sql, env)
    rows: List[Dict[str, object]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def escape_sql(value: object) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    if text == "":
        return "NULL"
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "''")
    text = text.replace("\x00", "")
    return f"'{text}'"


def insert_rows(env: Dict[str, str], table: str, columns: Sequence[str], rows: Sequence[Sequence[object]], batch_size: int = 500) -> None:
    if not rows:
        return
    expected_len = len(columns)
    for index, row in enumerate(rows, start=1):
        if len(row) != expected_len:
            raise ValueError(f"{table} row {index} has {len(row)} values, expected {expected_len}")
    column_sql = ", ".join(f"`{column}`" for column in columns)
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        values_sql = []
        for row in batch:
            values_sql.append("(" + ", ".join(escape_sql(value) for value in row) + ")")
        sql = f"INSERT INTO `{table}` ({column_sql}) VALUES\n" + ",\n".join(values_sql) + ";\n"
        run_mysql_sql(sql, env)


def truncate_business_tables(env: Dict[str, str]) -> None:
    statements = ["SET FOREIGN_KEY_CHECKS = 0;"]
    for table in SYNC_TABLES:
        statements.append(f"TRUNCATE TABLE `{table}`;")
    statements.append("SET FOREIGN_KEY_CHECKS = 1;")
    run_mysql_sql("\n".join(statements) + "\n", env)


def drop_raw_tables(env: Dict[str, str]) -> None:
    statements = ["SET FOREIGN_KEY_CHECKS = 0;"]
    for table in RAW_TABLE_COLUMNS:
        statements.append(f"DROP TABLE IF EXISTS `{table}`;")
    statements.append("SET FOREIGN_KEY_CHECKS = 1;")
    run_mysql_sql("\n".join(statements) + "\n", env)


def refresh_actual_count_columns(env: Dict[str, str]) -> None:
    statements = [
        """
        UPDATE company_basic_count c
        LEFT JOIN (
            SELECT company_id, COUNT(*) AS cnt
            FROM company_branch
            GROUP BY company_id
        ) t ON c.company_id = t.company_id
        SET c.branch_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (
            SELECT company_id, COUNT(*) AS cnt
            FROM company_recruit
            GROUP BY company_id
        ) t ON c.company_id = t.company_id
        SET c.recruit_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (
            SELECT company_id, COUNT(*) AS cnt
            FROM company_software_copyright
            GROUP BY company_id
        ) t ON c.company_id = t.company_id
        SET c.software_copyright_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (
            SELECT company_id, COUNT(*) AS cnt
            FROM company_work_copyright
            GROUP BY company_id
        ) t ON c.company_id = t.company_id
        SET c.work_copyright_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (
            SELECT company_id, COUNT(*) AS cnt
            FROM company_customer
            GROUP BY company_id
        ) t ON c.company_id = t.company_id
        SET c.customer_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (
            SELECT company_id, COUNT(*) AS cnt
            FROM company_ranking
            GROUP BY company_id
        ) t ON c.company_id = t.company_id
        SET c.ranking_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (
            SELECT company_id, COUNT(DISTINCT company_patent_id) AS cnt
            FROM company_patent_company_map
            GROUP BY company_id
        ) t ON c.company_id = t.company_id
        SET c.patent_count = COALESCE(t.cnt, 0);
        """,
    ]
    run_mysql_sql("\n".join(statements) + "\n", env)


def clean_text(value: object) -> Optional[str]:
    if value is None:
        return None
    text = str(value).replace("\xa0", " ").strip()
    return text or None


def normalize_company_name(value: object) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    return re.sub(r"\s+", " ", text)


def truncate_text(value: Optional[str], length: int) -> Optional[str]:
    if value is None:
        return None
    return value[:length]


def split_multi_value(text: Optional[str], pattern: str) -> List[str]:
    if not text:
        return []
    items = []
    for token in re.split(pattern, text):
        token = clean_text(token)
        if not token:
            continue
        items.append(token)
    seen = set()
    ordered = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def parse_int(value: object) -> Optional[int]:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+", text.replace(",", ""))
    if not match:
        return None
    return int(match.group(0))


def parse_decimal(value: object) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    try:
        number = Decimal(match.group(0))
    except InvalidOperation:
        return None
    return format(number, "f")


def parse_date(value: object) -> Optional[str]:
    text = clean_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_employee_info(value: object) -> Tuple[Optional[int], Optional[int]]:
    text = clean_text(value)
    if not text:
        return None, None
    count = parse_int(text)
    year_match = re.search(r"\((\d{4})年\)", text)
    year = int(year_match.group(1)) if year_match else None
    return count, year


def parse_bool_flag(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return 1 if value > 0 else 0
    text = clean_text(value)
    if not text:
        return 0
    if text in {"1", "是", "有", "true", "True", "Y", "已登记"}:
        return 1
    if text in {"0", "否", "无", "false", "False", "N"}:
        return 0
    number = parse_int(text)
    if number is not None:
        return 1 if number > 0 else 0
    return 1


def parse_listing_status_code(value: object) -> Optional[int]:
    text = clean_text(value)
    if not text:
        return None
    if any(keyword in text for keyword in ("终止", "退市", "摘牌")):
        return 2
    return 1


def temp_credit_code(seed: str) -> str:
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest().upper()
    return f"TMP{digest[:15]}"


def first_non_empty(*values: object) -> Optional[str]:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return None


def extract_position(value: object) -> Optional[int]:
    return parse_int(value)


def derive_region_fields(address: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not address:
        return None, None, None
    province = "北京市" if "北京市" in address else None
    city = "北京市" if province else None
    district_match = re.search(r"(北京市)?([^市]{1,12}区|[^市]{1,12}县)", address)
    district = district_match.group(2) if district_match else None
    return province, city, district


def query_company_id_map(env: Dict[str, str]) -> Dict[str, int]:
    sql = "SELECT company_name, company_id FROM company_basic WHERE company_name IS NOT NULL;"
    output = query_mysql(sql, env)
    result: Dict[str, int] = {}
    for line in output.splitlines():
        if not line:
            continue
        name, company_id = line.split("\t", 1)
        key = normalize_company_name(name)
        if key:
            result[key] = int(company_id)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync raw_import_* tables into structured business tables.")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--batch-size", type=int, default=500, help="INSERT batch size")
    parser.add_argument("--drop-raw-after-sync", action="store_true", help="Drop raw_import_* staging tables after sync succeeds")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    if not env_path.exists():
        raise FileNotFoundError(f".env 文件不存在: {env_path}")
    env = parse_env(env_path)

    raw_tables = {table: query_json_rows(table, columns, env) for table, columns in RAW_TABLE_COLUMNS.items()}

    basic_by_company: Dict[str, Dict[str, object]] = {}
    operation_by_company: Dict[str, Dict[str, object]] = {}
    ip_by_company: Dict[str, Dict[str, object]] = {}
    risk_by_company: Dict[str, Dict[str, object]] = {}
    subdistrict_by_company: DefaultDict[str, List[Dict[str, object]]] = defaultdict(list)
    software_by_company: DefaultDict[str, List[Dict[str, object]]] = defaultdict(list)
    ranking_by_company: DefaultDict[str, List[Dict[str, object]]] = defaultdict(list)
    customer_by_company: DefaultDict[str, List[Dict[str, object]]] = defaultdict(list)
    work_by_company: DefaultDict[str, List[Dict[str, object]]] = defaultdict(list)
    patent_by_company: DefaultDict[str, List[Dict[str, object]]] = defaultdict(list)
    recruit_by_company: DefaultDict[str, List[Dict[str, object]]] = defaultdict(list)

    company_names: set[str] = set()

    def add_single(mapping: Dict[str, Dict[str, object]], row: Dict[str, object]) -> None:
        name = normalize_company_name(row.get("company_name"))
        if not name:
            return
        mapping[name] = row
        company_names.add(name)

    def add_multi(mapping: DefaultDict[str, List[Dict[str, object]]], rows: Iterable[Dict[str, object]]) -> None:
        for row in rows:
            name = normalize_company_name(row.get("company_name"))
            if not name:
                continue
            mapping[name].append(row)
            company_names.add(name)

    for row in raw_tables["raw_import_company_basic"]:
        add_single(basic_by_company, row)
    for row in raw_tables["raw_import_company_operation"]:
        add_single(operation_by_company, row)
    for row in raw_tables["raw_import_company_ip_overview"]:
        add_single(ip_by_company, row)
    for row in raw_tables["raw_import_company_risk"]:
        add_single(risk_by_company, row)

    add_multi(subdistrict_by_company, raw_tables["raw_import_company_subdistrict"])
    add_multi(software_by_company, raw_tables["raw_import_software_copyright"])
    add_multi(ranking_by_company, raw_tables["raw_import_company_ranking"])
    add_multi(customer_by_company, raw_tables["raw_import_company_customer"])
    add_multi(work_by_company, raw_tables["raw_import_company_work_copyright"])
    add_multi(patent_by_company, raw_tables["raw_import_company_patent"])
    add_multi(recruit_by_company, raw_tables["raw_import_company_recruit"])

    truncate_business_tables(env)

    company_basic_rows: List[Tuple[object, ...]] = []
    company_basic_count_rows: List[Tuple[object, ...]] = []
    pending_company_meta: Dict[str, Dict[str, object]] = {}

    for company_name in sorted(company_names):
        basic = basic_by_company.get(company_name, {})
        operation = operation_by_company.get(company_name, {})
        ip = ip_by_company.get(company_name, {})
        risk = risk_by_company.get(company_name, {})
        subdistrict_rows = subdistrict_by_company.get(company_name, [])
        software_rows = software_by_company.get(company_name, [])
        ranking_rows = ranking_by_company.get(company_name, [])
        customer_rows = customer_by_company.get(company_name, [])
        work_rows = work_by_company.get(company_name, [])
        patent_rows = patent_by_company.get(company_name, [])
        recruit_rows = recruit_by_company.get(company_name, [])

        branch_names = split_multi_value(clean_text(basic.get("branch_names_raw")), r"[\n\r]+")
        shareholders = split_multi_value(clean_text(basic.get("shareholder_raw")), r"[;\n；]+")
        qualifications = split_multi_value(clean_text(basic.get("qualification_raw")), r"\|")
        address = first_non_empty(basic.get("address_info_raw"))
        street_names = []
        for row in subdistrict_rows:
            for candidate in (row.get("street_name"), row.get("region_name")):
                value = clean_text(candidate)
                if value:
                    street_names.append(value)
        street_names = list(dict.fromkeys(street_names))
        subdistrict = street_names[0] if street_names else None

        employee_count, employee_year = parse_employee_info(operation.get("employee_count_raw"))
        insured_count = parse_int(operation.get("insured_count_raw"))
        register_capital = parse_decimal(basic.get("register_capital_raw"))
        paid_capital = parse_decimal(basic.get("paid_capital_raw"))
        listing_status_code = parse_listing_status_code(operation.get("listing_status_raw"))
        financing_round = clean_text(basic.get("financing_round_raw"))
        if financing_round and "无明确投融资轮次信息" in financing_round:
            financing_round = None

        register_sheng, register_shi, register_xian = derive_region_fields(address)
        credit_code = clean_text(basic.get("credit_code"))
        if not credit_code:
            credit_code = temp_credit_code(company_name)

        has_changed_info = parse_bool_flag(operation.get("changed_info_raw"))
        has_bidding = parse_bool_flag(operation.get("has_bidding_raw"))
        has_recruitment = parse_bool_flag(operation.get("has_recruitment_raw")) or (1 if recruit_rows else 0)
        has_software_copyright = parse_bool_flag(ip.get("has_software_copyright_raw")) or (1 if software_rows else 0)
        has_work_copyright = parse_bool_flag(ip.get("has_work_copyright_raw")) or (1 if work_rows else 0)
        has_patent = parse_bool_flag(ip.get("has_patent_raw")) or (1 if patent_rows else 0)

        legal_doc_case_count = parse_int(risk.get("legal_doc_case_count_raw")) or 0
        legal_doc_judgement_count = parse_int(risk.get("legal_doc_judgement_count_raw")) or 0
        legal_doc_all_count = parse_int(risk.get("legal_doc_total_count_raw")) or 0
        dishonest_execution_count = parse_int(risk.get("dishonest_execution_count_raw")) or 0
        chattel_mortgage_count = parse_int(risk.get("chattel_mortgage_count_raw")) or 0
        business_abnormal_count = parse_int(risk.get("business_abnormal_count_raw")) or 0
        admin_penalty_count = parse_int(risk.get("admin_penalty_count_raw")) or 0
        bankruptcy_overlap_count = parse_int(risk.get("bankruptcy_overlap_count_raw")) or 0
        liquidation_info_count = parse_int(risk.get("liquidation_info_count_raw")) or 0
        env_penalty_count = parse_int(risk.get("env_penalty_count_raw")) or 0
        equity_freeze_count = parse_int(risk.get("equity_freeze_count_raw")) or 0
        executed_person_count = parse_int(risk.get("executed_person_count_raw")) or 0
        consumption_restriction_count = parse_int(risk.get("consumption_restriction_count_raw")) or 0

        same_phone_company_count = parse_int(operation.get("same_phone_count_raw")) or 0

        normalized_ranking_rows: List[Tuple[object, ...]] = []
        for row in ranking_rows:
            ranking_name = clean_text(row.get("ranking_name"))
            if not ranking_name:
                continue
            normalized_ranking_rows.append(
                (
                    truncate_text(ranking_name, 255),
                    truncate_text(clean_text(row.get("ranking_type")), 255),
                    truncate_text(clean_text(row.get("ranking_source")), 255),
                    extract_position(row.get("ranking_position_raw")),
                    truncate_text(clean_text(row.get("ranking_alias")), 255),
                    parse_int(row.get("publish_year_raw")),
                )
            )

        normalized_customer_rows: List[Tuple[object, ...]] = []
        for row in customer_rows:
            customer_name = clean_text(row.get("customer_name"))
            if not customer_name:
                continue
            normalized_customer_rows.append(
                (
                    truncate_text(customer_name, 255),
                    parse_decimal(row.get("sales_amount_raw")),
                    parse_decimal(row.get("sales_ratio_raw")),
                    parse_date(row.get("report_period_raw")),
                )
            )

        normalized_software_rows: List[Tuple[object, ...]] = []
        seen_company_software_register_numbers = set()
        for row in software_rows:
            register_number = clean_text(row.get("register_number"))
            software_name = clean_text(row.get("software_name"))
            if not register_number or not software_name:
                continue
            if register_number in seen_company_software_register_numbers:
                continue
            seen_company_software_register_numbers.add(register_number)
            normalized_software_rows.append(
                (
                    truncate_text(software_name, 255),
                    truncate_text(register_number, 255),
                    parse_date(row.get("register_date_raw")),
                    truncate_text(clean_text(row.get("software_short_name")), 255),
                    truncate_text(clean_text(row.get("status_raw")), 255),
                    truncate_text(clean_text(row.get("obtain_method_raw")), 255),
                )
            )

        normalized_work_rows: List[Tuple[object, ...]] = []
        seen_company_work_register_numbers = set()
        for row in work_rows:
            work_name = clean_text(row.get("work_name"))
            register_number = clean_text(row.get("register_number"))
            if not work_name or not register_number:
                continue
            if register_number in seen_company_work_register_numbers:
                continue
            seen_company_work_register_numbers.add(register_number)
            normalized_work_rows.append(
                (
                    truncate_text(work_name, 255),
                    truncate_text(register_number, 255),
                    truncate_text(clean_text(row.get("work_type_raw")), 255),
                    parse_date(row.get("first_publish_date_raw")),
                    parse_date(row.get("register_date_raw")),
                    truncate_text(clean_text(row.get("status_raw")), 255),
                )
            )

        normalized_patent_rows: List[Tuple[object, ...]] = []
        seen_company_patent_numbers = set()
        for row in patent_rows:
            patent_number = clean_text(row.get("patent_number"))
            patent_name = clean_text(row.get("patent_name"))
            if not patent_number or not patent_name:
                continue
            if patent_number in seen_company_patent_numbers:
                continue
            seen_company_patent_numbers.add(patent_number)
            normalized_patent_rows.append(
                (
                    truncate_text(patent_number, 255),
                    truncate_text(patent_name, 255),
                    parse_date(row.get("application_date_raw")),
                    parse_date(row.get("auth_publish_date_raw")),
                    truncate_text(clean_text(row.get("patent_type_raw")), 255),
                )
            )

        normalized_recruit_rows: List[Tuple[object, ...]] = []
        for row in recruit_rows:
            position_name = clean_text(row.get("position_name"))
            if not position_name:
                continue
            normalized_recruit_rows.append(
                (
                    truncate_text(position_name, 255),
                    truncate_text(clean_text(row.get("salary_raw")), 255),
                    truncate_text(clean_text(row.get("work_year_raw")), 255),
                    truncate_text(clean_text(row.get("work_place")), 255),
                    truncate_text(clean_text(row.get("edu_req_raw")), 255),
                    parse_date(row.get("recruit_time_raw")),
                )
            )

        branch_count_actual = len(branch_names)
        branch_count_raw = parse_int(basic.get("branch_count_raw")) or branch_count_actual
        recruit_count_actual = len(normalized_recruit_rows)
        recruit_count_raw = parse_int(operation.get("recruit_count_raw")) or recruit_count_actual
        software_count_actual = len(normalized_software_rows)
        software_count_raw = parse_int(ip.get("software_copyright_count_raw")) or software_count_actual
        work_count_actual = len(normalized_work_rows)
        work_count_raw = parse_int(ip.get("work_copyright_count_raw")) or work_count_actual
        patent_count_actual = len(normalized_patent_rows)
        patent_count_raw = parse_int(ip.get("patent_count_raw")) or patent_count_actual
        customer_count_actual = len(normalized_customer_rows)
        customer_count_raw = parse_int(operation.get("customer_count_raw")) or customer_count_actual
        ranking_count_actual = len(normalized_ranking_rows)
        ranking_count_raw = parse_int(operation.get("ranking_count_raw")) or ranking_count_actual
        bidding_count = parse_int(operation.get("bidding_count_raw")) or 0

        company_basic_rows.append(
            (
                company_name,
                credit_code,
                clean_text(basic.get("legal_representative")),
                clean_text(basic.get("register_number")),
                clean_text(basic.get("org_code")),
                parse_date(basic.get("establish_info")),
                truncate_text(clean_text(basic.get("business_scope_raw")), 65535),
                first_non_empty(basic.get("email_business"), operation.get("email_business")),
                clean_text(basic.get("email_auth")),
                first_non_empty(basic.get("contact_phone_1"), basic.get("contact_phone_2"), basic.get("contact_phone_3"), basic.get("contact_phone_4"), basic.get("contact_phone_5")),
                clean_text(operation.get("contact_info_raw")),
                clean_text(basic.get("recommended_phone")),
                truncate_text(shareholders[0] if shareholders else None, 255),
                register_sheng,
                register_shi,
                register_xian,
                truncate_text(subdistrict, 255),
                register_capital,
                paid_capital,
                clean_text(basic.get("company_type_raw")),
                clean_text(basic.get("org_type_raw")),
                clean_text(basic.get("investment_type_raw")),
                clean_text(basic.get("company_scale_raw")),
                employee_count,
                insured_count,
                first_non_empty(basic.get("industry_name_raw"), operation.get("national_industry_raw")),
                1 if branch_names else 0,
                truncate_text(branch_names[0] if branch_names else None, 255),
                truncate_text(address, 255),
                truncate_text(address, 255),
                truncate_text(qualifications[0] if qualifications else None, 255),
                parse_bool_flag(operation.get("is_general_taxpayer_raw")),
                financing_round,
                financing_round,
                listing_status_code,
                same_phone_company_count,
                parse_bool_flag(ip.get("is_high_tech_enterprise_raw")),
                parse_bool_flag(operation.get("is_micro_enterprise_raw")),
                has_changed_info,
                has_bidding,
                has_recruitment,
                has_software_copyright,
                has_work_copyright,
                parse_bool_flag(ip.get("is_srdi_sme_raw")),
                parse_bool_flag(ip.get("is_gazelle_company_raw")),
                parse_bool_flag(ip.get("is_tech_sme_raw")),
                parse_bool_flag(ip.get("is_egalet_company_raw")),
                parse_bool_flag(ip.get("is_srdi_little_giant_raw")),
                parse_bool_flag(ip.get("is_innovative_sme_raw")),
                has_patent,
                parse_bool_flag(risk.get("has_legal_document_raw")) or (1 if legal_doc_all_count > 0 else 0),
                parse_bool_flag(risk.get("has_dishonest_execution_raw")) or (1 if dishonest_execution_count > 0 else 0),
                parse_bool_flag(risk.get("has_chattel_mortgage_raw")) or (1 if chattel_mortgage_count > 0 else 0),
                parse_bool_flag(risk.get("has_business_abnormal_raw")) or (1 if business_abnormal_count > 0 else 0),
                parse_bool_flag(risk.get("has_admin_penalty_raw")) or (1 if admin_penalty_count > 0 else 0),
                parse_bool_flag(risk.get("has_bankruptcy_overlap_raw")) or (1 if bankruptcy_overlap_count > 0 else 0),
                parse_bool_flag(risk.get("has_liquidation_info_raw")) or (1 if liquidation_info_count > 0 else 0),
                parse_bool_flag(risk.get("has_env_penalty_raw")) or (1 if env_penalty_count > 0 else 0),
                parse_bool_flag(risk.get("has_equity_freeze_raw")) or (1 if equity_freeze_count > 0 else 0),
                parse_bool_flag(risk.get("has_executed_person_raw")) or (1 if executed_person_count > 0 else 0),
                parse_bool_flag(risk.get("has_consumption_restriction_raw")) or (1 if consumption_restriction_count > 0 else 0),
                consumption_restriction_count,
                1 if ((address and "朝阳" in address) or subdistrict) else 0,
            )
        )

        pending_company_meta[company_name] = {
            "branch_names": branch_names,
            "shareholders": shareholders,
            "qualifications": qualifications,
            "address": address,
            "employee_count": employee_count,
            "employee_year": employee_year,
            "financing_round": financing_round,
            "listing_status_code": listing_status_code,
            "listing_status_raw": clean_text(operation.get("listing_status_raw")),
            "street_names": street_names,
            "software_entries": normalized_software_rows,
            "ranking_entries": normalized_ranking_rows,
            "customer_entries": normalized_customer_rows,
            "work_entries": normalized_work_rows,
            "patent_entries": normalized_patent_rows,
            "recruit_entries": normalized_recruit_rows,
            "phones": [
                phone
                for phone in [
                    clean_text(basic.get("contact_phone_1")),
                    clean_text(basic.get("contact_phone_2")),
                    clean_text(basic.get("contact_phone_3")),
                    clean_text(basic.get("contact_phone_4")),
                    clean_text(basic.get("contact_phone_5")),
                ]
                if phone
            ],
            "contact_info": clean_text(operation.get("contact_info_raw")),
            "recommended_phone": clean_text(basic.get("recommended_phone")),
            "register_sheng": register_sheng,
            "register_shi": register_shi,
            "register_xian": register_xian,
        }

        company_basic_count_rows.append(
            (
                branch_count_actual,
                branch_count_raw,
                recruit_count_actual,
                recruit_count_raw,
                software_count_actual,
                software_count_raw,
                work_count_actual,
                work_count_raw,
                patent_count_actual,
                patent_count_raw,
                0,
                customer_count_actual,
                customer_count_raw,
                ranking_count_actual,
                ranking_count_raw,
                bidding_count,
                legal_doc_case_count,
                legal_doc_judgement_count,
                legal_doc_all_count,
                dishonest_execution_count,
                chattel_mortgage_count,
                business_abnormal_count,
                admin_penalty_count,
                bankruptcy_overlap_count,
                liquidation_info_count,
                env_penalty_count,
                equity_freeze_count,
                executed_person_count,
                company_name,
            )
        )

    insert_rows(
        env,
        "company_basic",
        [
            "company_name",
            "credit_code",
            "legal_representative",
            "register_number",
            "org_code",
            "establish_date",
            "business_scope",
            "email_business",
            "email_auth",
            "contact_phone",
            "contact_info",
            "recommended_phone",
            "latest_shareholder_name",
            "register_sheng",
            "register_shi",
            "register_xian",
            "subdistrict",
            "register_capital",
            "paid_capital",
            "company_type",
            "org_type",
            "investment_type",
            "company_scale",
            "employee_count",
            "insured_count",
            "industry_belong",
            "is_branch",
            "branch_name",
            "register_address",
            "register_address_detail",
            "qualification_label",
            "is_general_taxpayer",
            "financing_round",
            "financing_info",
            "listing_status",
            "same_phone_company_count",
            "is_high_tech_enterprise",
            "is_micro_enterprise",
            "has_changed_info",
            "has_bidding",
            "has_recruitment",
            "has_software_copyright",
            "has_work_copyright",
            "is_srdi_sme",
            "is_gazelle_company",
            "is_tech_sme",
            "is_egalet_company",
            "is_srdi_little_giant",
            "is_innovative_sme",
            "has_patent",
            "has_legal_document",
            "has_dishonest_execution",
            "has_chattel_mortgage",
            "has_business_abnormal",
            "has_admin_penalty",
            "has_bankruptcy_overlap",
            "has_liquidation_info",
            "has_env_penalty",
            "has_equity_freeze",
            "has_executed_person",
            "has_consumption_restriction",
            "consumption_restriction_count",
            "is_chaoyang_company",
        ],
        company_basic_rows,
        batch_size=args.batch_size,
    )

    company_id_map = query_company_id_map(env)

    branch_rows: List[Tuple[object, ...]] = []
    contact_phone_rows: List[Tuple[object, ...]] = []
    contact_info_rows: List[Tuple[object, ...]] = []
    recommended_phone_rows: List[Tuple[object, ...]] = []
    shareholder_rows: List[Tuple[object, ...]] = []
    employee_count_rows: List[Tuple[object, ...]] = []
    address_rows: List[Tuple[object, ...]] = []
    qualification_rows: List[Tuple[object, ...]] = []
    financing_rows: List[Tuple[object, ...]] = []
    listing_rows: List[Tuple[object, ...]] = []
    basic_count_rows: List[Tuple[object, ...]] = []
    subdistrict_rows_insert: List[Tuple[object, ...]] = []
    software_rows_insert: List[Tuple[object, ...]] = []
    ranking_rows_insert: List[Tuple[object, ...]] = []
    customer_rows_insert: List[Tuple[object, ...]] = []
    work_rows_insert: List[Tuple[object, ...]] = []
    patent_rows_insert: List[Tuple[object, ...]] = []
    recruit_rows_insert: List[Tuple[object, ...]] = []
    risk_rows_insert: List[Tuple[object, ...]] = []

    patent_types: Dict[str, None] = {}
    patent_type_pairs: List[Tuple[str, str]] = []
    patent_company_pairs: List[Tuple[str, int]] = []
    seen_software_register_numbers = set()
    seen_work_register_numbers = set()
    seen_patent_numbers = set()

    risk_categories = [
        ("法律文书", "legal_doc_all_count_raw"),
        ("失信被执行", "dishonest_execution_count_raw"),
        ("动产抵押", "chattel_mortgage_count_raw"),
        ("经营异常", "business_abnormal_count_raw"),
        ("行政处罚", "admin_penalty_count_raw"),
        ("破产重叠", "bankruptcy_overlap_count_raw"),
        ("清算信息", "liquidation_info_count_raw"),
        ("环保处罚", "env_penalty_count_raw"),
        ("股权冻结", "equity_freeze_count_raw"),
        ("被执行人", "executed_person_count_raw"),
        ("限制高消费", "consumption_restriction_count_raw"),
    ]

    for raw_count_row in company_basic_count_rows:
        company_name = raw_count_row[-1]
        company_id = company_id_map.get(company_name)
        if company_id is None:
            continue
        basic_count_rows.append((company_id,) + tuple(raw_count_row[:-1]))

    for company_name, meta in pending_company_meta.items():
        company_id = company_id_map.get(company_name)
        if company_id is None:
            continue

        for idx, branch_name in enumerate(meta["branch_names"]):  # type: ignore[index]
            branch_rows.append((company_id, truncate_text(branch_name, 255)))

        phones = list(dict.fromkeys(meta["phones"]))  # type: ignore[index]
        for idx, phone in enumerate(phones):
            contact_phone_rows.append((company_id, truncate_text(phone, 255), 1 if idx == 0 else 0))

        contact_info = meta["contact_info"]
        if contact_info:
            contact_info_rows.append((company_id, truncate_text(contact_info, 255), 1))

        recommended_phone = meta["recommended_phone"]
        if recommended_phone:
            recommended_phone_rows.append((company_id, truncate_text(recommended_phone, 255), 1))

        for idx, shareholder_name in enumerate(meta["shareholders"]):  # type: ignore[index]
            shareholder_rows.append((company_id, truncate_text(shareholder_name, 255), 1 if idx == 0 else 0))

        if meta["employee_count"] is not None and meta["employee_year"] is not None:
            employee_count_rows.append((company_id, meta["employee_year"], meta["employee_count"]))

        address = meta["address"]
        if address:
            address_rows.append(
                (
                    company_id,
                    "registered",
                    truncate_text(address, 255),
                    meta["register_sheng"],
                    meta["register_shi"],
                    meta["register_xian"],
                    1,
                )
            )

        for idx, qualification_name in enumerate(meta["qualifications"]):  # type: ignore[index]
            qualification_rows.append((company_id, truncate_text(qualification_name, 255), 1 if idx == 0 else 0))

        if meta["financing_round"]:
            financing_rows.append((company_id, truncate_text(meta["financing_round"], 255), 1))

        if meta["listing_status_code"] is not None:
            listing_rows.append(
                (
                    company_id,
                    meta["listing_status_code"],
                    None,
                    truncate_text(meta["listing_status_raw"], 255),
                    1,
                )
            )

        for subdistrict_name in meta["street_names"]:  # type: ignore[index]
            subdistrict_rows_insert.append((truncate_text(subdistrict_name, 255), company_id))

        for software_entry in meta["software_entries"]:  # type: ignore[index]
            software_name, register_number, register_date, software_short_name, status, obtain_method = software_entry
            if register_number in seen_software_register_numbers:
                continue
            seen_software_register_numbers.add(register_number)
            software_rows_insert.append(
                (
                    software_name,
                    company_id,
                    register_number,
                    register_date,
                    software_short_name,
                    status,
                    obtain_method,
                )
            )

        for ranking_entry in meta["ranking_entries"]:  # type: ignore[index]
            ranking_name, ranking_type, ranking_source, ranking_position, ranking_alias, publish_year = ranking_entry
            ranking_rows_insert.append(
                (
                    ranking_name,
                    company_id,
                    ranking_type,
                    ranking_source,
                    ranking_position,
                    ranking_alias,
                    publish_year,
                )
            )

        for customer_entry in meta["customer_entries"]:  # type: ignore[index]
            customer_name, sales_amount, sales_ratio, report_date = customer_entry
            customer_rows_insert.append(
                (
                    customer_name,
                    company_id,
                    sales_amount,
                    sales_ratio,
                    report_date,
                )
            )

        for work_entry in meta["work_entries"]:  # type: ignore[index]
            work_name, register_number, work_type, publish_date, register_date, status = work_entry
            if register_number in seen_work_register_numbers:
                continue
            seen_work_register_numbers.add(register_number)
            work_rows_insert.append(
                (
                    work_name,
                    company_id,
                    register_number,
                    work_type,
                    publish_date,
                    register_date,
                    status,
                )
            )

        for patent_entry in meta["patent_entries"]:  # type: ignore[index]
            patent_number, patent_name, application_date, auth_date, patent_type = patent_entry
            if patent_number in seen_patent_numbers:
                patent_company_pairs.append((patent_number, company_id))
                if patent_type:
                    patent_type_pairs.append((patent_number, patent_type))
                continue
            seen_patent_numbers.add(patent_number)
            patent_rows_insert.append((patent_number, patent_name, company_id, application_date, auth_date))
            patent_company_pairs.append((patent_number, company_id))
            if patent_type:
                patent_types[patent_type] = None
                patent_type_pairs.append((patent_number, patent_type))

        for recruit_entry in meta["recruit_entries"]:  # type: ignore[index]
            position_name, salary, work_year, work_place, edu_req, recruit_time = recruit_entry
            recruit_rows_insert.append(
                (
                    position_name,
                    company_id,
                    salary,
                    work_year,
                    work_place,
                    edu_req,
                    recruit_time,
                )
            )

        risk = risk_by_company.get(company_name, {})
        for risk_name, risk_column in risk_categories:
            count = parse_int(risk.get(risk_column)) or 0
            if count > 0:
                risk_rows_insert.append((company_id, risk_name, count))

    insert_rows(env, "company_branch", ["company_id", "company_branch_name"], branch_rows, batch_size=args.batch_size)
    insert_rows(env, "company_contact_phone", ["company_id", "contact_phone", "is_latest"], contact_phone_rows, batch_size=args.batch_size)
    insert_rows(env, "company_contact_info", ["company_id", "contact_info", "is_latest"], contact_info_rows, batch_size=args.batch_size)
    insert_rows(env, "company_recommended_phone", ["company_id", "recommended_phone", "is_latest"], recommended_phone_rows, batch_size=args.batch_size)
    insert_rows(env, "company_shareholder", ["company_id", "shareholder_name", "is_latest"], shareholder_rows, batch_size=args.batch_size)
    insert_rows(env, "company_employee_count", ["company_id", "stat_year", "employee_count"], employee_count_rows, batch_size=args.batch_size)
    insert_rows(env, "company_address", ["company_id", "address_type", "address_text", "province", "city", "district", "is_latest"], address_rows, batch_size=args.batch_size)
    insert_rows(env, "company_qualification", ["company_id", "qualification_name", "is_latest"], qualification_rows, batch_size=args.batch_size)
    insert_rows(env, "company_financing", ["company_id", "financing_round", "is_latest"], financing_rows, batch_size=args.batch_size)
    insert_rows(env, "company_listing_status", ["company_id", "listing_status", "stock_code", "market_name", "is_latest"], listing_rows, batch_size=args.batch_size)
    insert_rows(env, "company_basic_count", ["company_id", "branch_count", "branch_count_raw", "recruit_count", "recruit_count_raw", "software_copyright_count", "software_copyright_count_raw", "work_copyright_count", "work_copyright_count_raw", "patent_count", "patent_count_raw", "trademark_count", "customer_count", "customer_count_raw", "ranking_count", "ranking_count_raw", "bidding_count", "legal_doc_case_count", "legal_doc_judgement_count", "legal_doc_all_count", "dishonest_execution_count", "chattel_mortgage_count", "business_abnormal_count", "admin_penalty_count", "bankruptcy_overlap_count", "liquidation_info_count", "env_penalty_count", "equity_freeze_count", "executed_person_count"], basic_count_rows, batch_size=args.batch_size)
    insert_rows(env, "company_subdistrict", ["company_subdistrict_name", "company_id"], subdistrict_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_software_copyright", ["company_software_copyright_name", "company_id", "company_software_copyright_register_number", "company_software_copyright_register_date", "company_software_copyright_for_short", "company_software_copyright_status", "company_software_copyright_obtain"], software_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_ranking", ["company_ranking_name", "company_id", "company_ranking_type", "company_ranking_source", "company_ranking_position", "company_ranking_alias", "company_ranking_publish_year"], ranking_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_customer", ["company_customer_name", "company_id", "company_customer_sales_amount", "company_customer_sales_ratio", "company_customer_report_date"], customer_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_work_copyright", ["company_work_copyright_name", "company_id", "company_work_copyright_register_number", "company_work_copyright_type", "company_work_copyright_publish_date", "company_work_copyright_register_date", "company_work_copyright_status"], work_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_patent", ["company_patent_number", "company_patent_name", "company_id", "application_date", "auth_date"], patent_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_recruit", ["company_recruit_position", "company_id", "company_recruit_salary", "company_recruit_work_year_req", "company_recruit_work_place", "company_recruit_edu_req", "company_recruit_time"], recruit_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_risk", ["company_id", "company_risk_category_name", "company_risk_category_count"], risk_rows_insert, batch_size=args.batch_size)

    patent_type_rows = [(patent_type,) for patent_type in sorted(patent_types.keys())]
    insert_rows(env, "company_patent_type", ["company_patent_type_name"], patent_type_rows, batch_size=args.batch_size)

    patent_id_output = query_mysql("SELECT company_patent_id, company_patent_number FROM company_patent;", env)
    patent_id_by_number: Dict[str, int] = {}
    for line in patent_id_output.splitlines():
        if not line:
            continue
        patent_id, patent_number = line.split("\t", 1)
        patent_id_by_number[patent_number] = int(patent_id)

    patent_type_output = query_mysql("SELECT company_patent_type_id, company_patent_type_name FROM company_patent_type;", env)
    patent_type_id_by_name: Dict[str, int] = {}
    for line in patent_type_output.splitlines():
        if not line:
            continue
        type_id, type_name = line.split("\t", 1)
        patent_type_id_by_name[type_name] = int(type_id)

    patent_map_rows: List[Tuple[object, ...]] = []
    seen_patent_map = set()
    for patent_number, patent_type_name in patent_type_pairs:
        patent_id = patent_id_by_number.get(patent_number)
        patent_type_id = patent_type_id_by_name.get(patent_type_name)
        if patent_id is None or patent_type_id is None:
            continue
        key = (patent_id, patent_type_id)
        if key in seen_patent_map:
            continue
        seen_patent_map.add(key)
        patent_map_rows.append((patent_id, patent_type_id))

    insert_rows(env, "company_patent_patent_type_map", ["company_patent_id", "company_patent_type_id"], patent_map_rows, batch_size=args.batch_size)

    patent_company_map_rows: List[Tuple[object, ...]] = []
    seen_patent_company_map = set()
    for patent_number, company_id in patent_company_pairs:
        patent_id = patent_id_by_number.get(patent_number)
        if patent_id is None:
            continue
        key = (patent_id, company_id)
        if key in seen_patent_company_map:
            continue
        seen_patent_company_map.add(key)
        patent_company_map_rows.append((patent_id, company_id))

    insert_rows(env, "company_patent_company_map", ["company_patent_id", "company_id"], patent_company_map_rows, batch_size=args.batch_size)
    refresh_actual_count_columns(env)

    print(f"[sync] company_basic: {len(company_basic_rows)}")
    print(f"[sync] company_branch: {len(branch_rows)}")
    print(f"[sync] company_contact_phone: {len(contact_phone_rows)}")
    print(f"[sync] company_shareholder: {len(shareholder_rows)}")
    print(f"[sync] company_qualification: {len(qualification_rows)}")
    print(f"[sync] company_financing: {len(financing_rows)}")
    print(f"[sync] company_basic_count: {len(basic_count_rows)}")
    print(f"[sync] company_software_copyright: {len(software_rows_insert)}")
    print(f"[sync] company_ranking: {len(ranking_rows_insert)}")
    print(f"[sync] company_customer: {len(customer_rows_insert)}")
    print(f"[sync] company_work_copyright: {len(work_rows_insert)}")
    print(f"[sync] company_patent: {len(patent_rows_insert)}")
    print(f"[sync] company_patent_company_map: {len(patent_company_map_rows)}")
    print(f"[sync] company_recruit: {len(recruit_rows_insert)}")
    print(f"[sync] company_risk: {len(risk_rows_insert)}")
    if args.drop_raw_after_sync:
        drop_raw_tables(env)
        print("[sync] raw_import_* tables dropped")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("[error] mysql command failed", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
