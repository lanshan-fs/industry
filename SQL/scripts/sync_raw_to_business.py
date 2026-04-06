#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Sequence, Tuple

from _import_utils import (
    clean_text,
    derive_region_fields,
    first_non_empty,
    insert_rows,
    normalize_company_name,
    parse_bool_flag,
    parse_date,
    parse_decimal,
    parse_employee_info,
    parse_env,
    parse_int,
    parse_listing_status_code,
    parse_validity_period,
    query_json_rows,
    query_mysql,
    run_mysql_sql,
    split_multi_value,
    temp_credit_code,
    truncate_text,
)


SYNC_TABLES = [
    "company_patent_patent_type_map",
    "company_patent_company_map",
    "company_patent_type",
    "company_patent",
    "company_software_copyright",
    "company_supplier",
    "company_customer",
    "company_work_copyright",
    "company_ranking",
    "company_recruit",
    "company_risk",
    "company_subdistrict",
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
    "company_basic_count",
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
        "company_scale_raw",
        "has_branch_raw",
        "branch_count_raw",
        "address_info_raw",
        "financing_round_raw",
        "legal_representative",
        "insured_count_raw",
        "register_number",
        "org_code",
        "industry_name_raw",
        "business_scope_raw",
        "email_business",
        "shareholder_raw",
        "contact_phone_0",
        "contact_phone_1",
        "contact_phone_2",
        "contact_phone_3",
        "contact_phone_4",
        "contact_phone_5",
    ],
    "raw_import_company_branch": [
        "raw_id",
        "company_name",
        "branch_company_name",
        "branch_leader",
        "branch_region",
        "branch_establish_date_raw",
        "branch_status_raw",
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
        "has_supplier_raw",
        "supplier_count_raw",
        "has_recruitment_raw",
        "recruit_count_raw",
        "has_customer_info_raw",
        "customer_count_raw",
        "has_ranking_raw",
        "ranking_count_raw",
        "has_license_raw",
        "license_count_raw",
        "has_qualification_raw",
        "qualification_count_raw",
        "taxpayer_credit_rating_raw",
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
    "raw_import_company_recruit": [
        "raw_id",
        "company_name",
        "position_name",
        "salary_raw",
        "work_place",
        "work_year_raw",
        "edu_req_raw",
        "recruit_time_raw",
    ],
    "raw_import_company_license": [
        "raw_id",
        "company_name",
        "license_number",
        "license_name",
        "license_status",
        "data_source",
        "validity_period_raw",
        "issuing_authority",
    ],
    "raw_import_company_qualification": [
        "raw_id",
        "company_name",
        "qualification_name",
        "qualification_number",
        "qualification_type",
        "qualification_status",
        "issued_at_raw",
        "expires_at_raw",
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
        "software_name",
        "register_number",
        "software_short_name",
        "register_date_raw",
        "status_raw",
        "obtain_method_raw",
        "company_name",
    ],
    "raw_import_company_work_copyright": [
        "raw_id",
        "sheet_row_no",
        "work_name",
        "register_number",
        "work_type_raw",
        "first_publish_date_raw",
        "register_date_raw",
        "status_raw",
        "company_name",
    ],
    "raw_import_company_patent": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "patent_number",
        "patent_name",
        "patent_type_raw",
        "application_date_raw",
        "publication_date_raw",
    ],
    "raw_import_company_risk": [
        "raw_id",
        "company_name",
        "serious_illegal_count_raw",
        "judicial_case_count_raw",
        "cooperation_risk_count_raw",
        "dishonest_execution_count_raw",
        "bankruptcy_case_count_raw",
        "executed_person_count_raw",
        "consumption_restriction_count_raw",
        "business_abnormal_count_raw",
        "cluster_registration_count_raw",
    ],
    "raw_import_company_subdistrict": [
        "raw_id",
        "sheet_row_no",
        "company_name",
        "address_raw",
        "street_name",
        "region_name",
    ],
}

TECH_LABEL_SPECS = [
    ("高新技术企业", "is_high_tech_enterprise_raw"),
    ("专精特新中小企业", "is_srdi_sme_raw"),
    ("瞪羚企业", "is_gazelle_company_raw"),
    ("科技型中小企业", "is_tech_sme_raw"),
    ("雏鹰企业", "is_egalet_company_raw"),
    ("专精特新小巨人", "is_srdi_little_giant_raw"),
    ("创新型中小企业", "is_innovative_sme_raw"),
]


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
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_branch GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.branch_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_recruit GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.recruit_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_software_copyright GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.software_copyright_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_work_copyright GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.work_copyright_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_customer GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.customer_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_supplier GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.supplier_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_ranking GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.ranking_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_qualification WHERE record_kind = 'qualification' GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.qualification_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(*) AS cnt FROM company_qualification WHERE record_kind = 'license' GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.license_count = COALESCE(t.cnt, 0);
        """,
        """
        UPDATE company_basic_count c
        LEFT JOIN (SELECT company_id, COUNT(DISTINCT company_patent_id) AS cnt FROM company_patent_company_map GROUP BY company_id) t ON c.company_id = t.company_id
        SET c.patent_count = COALESCE(t.cnt, 0);
        """,
    ]
    run_mysql_sql("\n".join(statements) + "\n", env)


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


def qualification_label_from(names: List[str], tech_labels: List[str]) -> str | None:
    items = list(dict.fromkeys(tech_labels + names))
    if not items:
        return None
    return truncate_text("、".join(items), 255)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync raw_import_* tables into V2 business tables.")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    parser.add_argument("--batch-size", type=int, default=500, help="INSERT batch size")
    parser.add_argument("--drop-raw-after-sync", action="store_true", help="Drop raw_import_* tables after sync succeeds")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    if not env_path.exists():
        raise FileNotFoundError(f".env 文件不存在: {env_path}")
    env = parse_env(env_path)

    raw_tables = {table: query_json_rows(table, columns, env) for table, columns in RAW_TABLE_COLUMNS.items()}

    basic_by_company: Dict[str, Dict[str, Any]] = {}
    operation_by_company: Dict[str, Dict[str, Any]] = {}
    ip_by_company: Dict[str, Dict[str, Any]] = {}
    risk_by_company: Dict[str, Dict[str, Any]] = {}
    branch_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    subdistrict_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    software_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    ranking_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    customer_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    work_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    patent_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    recruit_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    license_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    qualification_by_company: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    company_names: set[str] = set()

    def add_single(target: Dict[str, Dict[str, Any]], row: Dict[str, Any]) -> None:
        company_name = normalize_company_name(row.get("company_name"))
        if not company_name:
            return
        target[company_name] = row
        company_names.add(company_name)

    def add_multi(target: DefaultDict[str, List[Dict[str, Any]]], rows: Iterable[Dict[str, Any]]) -> None:
        for row in rows:
            company_name = normalize_company_name(row.get("company_name"))
            if not company_name:
                continue
            target[company_name].append(row)
            company_names.add(company_name)

    for row in raw_tables["raw_import_company_basic"]:
        add_single(basic_by_company, row)
    for row in raw_tables["raw_import_company_operation"]:
        add_single(operation_by_company, row)
    for row in raw_tables["raw_import_company_ip_overview"]:
        add_single(ip_by_company, row)
    for row in raw_tables["raw_import_company_risk"]:
        add_single(risk_by_company, row)

    add_multi(branch_by_company, raw_tables["raw_import_company_branch"])
    add_multi(subdistrict_by_company, raw_tables["raw_import_company_subdistrict"])
    add_multi(software_by_company, raw_tables["raw_import_software_copyright"])
    add_multi(ranking_by_company, raw_tables["raw_import_company_ranking"])
    add_multi(customer_by_company, raw_tables["raw_import_company_customer"])
    add_multi(work_by_company, raw_tables["raw_import_company_work_copyright"])
    add_multi(patent_by_company, raw_tables["raw_import_company_patent"])
    add_multi(recruit_by_company, raw_tables["raw_import_company_recruit"])
    add_multi(license_by_company, raw_tables["raw_import_company_license"])
    add_multi(qualification_by_company, raw_tables["raw_import_company_qualification"])

    truncate_business_tables(env)

    company_basic_rows: List[Tuple[Any, ...]] = []
    company_basic_count_rows: List[Tuple[Any, ...]] = []
    pending_company_meta: Dict[str, Dict[str, Any]] = {}

    for company_name in sorted(company_names):
        basic = basic_by_company.get(company_name, {})
        operation = operation_by_company.get(company_name, {})
        ip = ip_by_company.get(company_name, {})
        risk = risk_by_company.get(company_name, {})
        branch_rows_raw = branch_by_company.get(company_name, [])
        subdistrict_rows = subdistrict_by_company.get(company_name, [])
        software_rows = software_by_company.get(company_name, [])
        ranking_rows = ranking_by_company.get(company_name, [])
        customer_rows = customer_by_company.get(company_name, [])
        work_rows = work_by_company.get(company_name, [])
        patent_rows = patent_by_company.get(company_name, [])
        recruit_rows = recruit_by_company.get(company_name, [])
        license_rows_raw = license_by_company.get(company_name, [])
        qualification_rows_raw = qualification_by_company.get(company_name, [])

        shareholders = split_multi_value(clean_text(basic.get("shareholder_raw")), r"[;\n；、]+")
        address = first_non_empty(basic.get("address_info_raw"))
        if not address:
            address = first_non_empty(*(row.get("address_raw") for row in subdistrict_rows))

        street_candidates: List[str] = []
        for row in subdistrict_rows:
            for candidate in (row.get("street_name"), row.get("region_name")):
                text = clean_text(candidate)
                if text:
                    street_candidates.append(text)
        street_candidates = list(dict.fromkeys(street_candidates))
        subdistrict = street_candidates[0] if street_candidates else None

        branch_entries: List[Tuple[Any, ...]] = []
        branch_names: List[str] = []
        seen_branch_names: set[str] = set()
        for row in branch_rows_raw:
            branch_name = clean_text(row.get("branch_company_name"))
            if not branch_name or branch_name in seen_branch_names:
                continue
            seen_branch_names.add(branch_name)
            branch_names.append(branch_name)
            branch_entries.append(
                (
                    truncate_text(branch_name, 255),
                    truncate_text(clean_text(row.get("branch_region")), 255),
                    truncate_text(clean_text(row.get("branch_status_raw")), 64),
                    parse_date(row.get("branch_establish_date_raw")),
                    truncate_text(clean_text(row.get("branch_leader")), 255),
                )
            )

        employee_count, employee_year = parse_employee_info(operation.get("employee_count_raw"))
        insured_count = parse_int(first_non_empty(operation.get("insured_count_raw"), basic.get("insured_count_raw")))
        register_capital = parse_decimal(basic.get("register_capital_raw"))
        paid_capital = parse_decimal(basic.get("paid_capital_raw"))
        listing_status_code = parse_listing_status_code(operation.get("listing_status_raw"))
        financing_round = clean_text(basic.get("financing_round_raw"))
        if financing_round and financing_round in {"无", "无明确投融资轮次信息", "暂无融资", "-", "--"}:
            financing_round = None

        register_sheng, register_shi, register_xian = derive_region_fields(address)
        credit_code = clean_text(basic.get("credit_code")) or temp_credit_code(company_name)
        tech_labels = [label for label, field in TECH_LABEL_SPECS if parse_bool_flag(ip.get(field)) == 1]

        qualification_names: List[str] = []
        normalized_qualification_rows: List[Tuple[Any, ...]] = []
        seen_qualification_keys: set[Tuple[str, str, str]] = set()
        for index, row in enumerate(qualification_rows_raw):
            qualification_name = clean_text(row.get("qualification_name"))
            if not qualification_name:
                continue
            qualification_names.append(qualification_name)
            key = (
                qualification_name,
                clean_text(row.get("qualification_number")) or "",
                clean_text(row.get("qualification_type")) or "",
            )
            if key in seen_qualification_keys:
                continue
            seen_qualification_keys.add(key)
            normalized_qualification_rows.append(
                (
                    "qualification",
                    truncate_text(qualification_name, 255),
                    truncate_text(clean_text(row.get("qualification_number")), 255),
                    truncate_text(clean_text(row.get("qualification_status")), 64),
                    truncate_text(clean_text(row.get("qualification_type")), 255),
                    None,
                    parse_date(row.get("issued_at_raw")),
                    None,
                    parse_date(row.get("expires_at_raw")),
                    None,
                    None,
                    1 if index == 0 else 0,
                )
            )

        license_names: List[str] = []
        normalized_license_rows: List[Tuple[Any, ...]] = []
        seen_license_keys: set[Tuple[str, str]] = set()
        for index, row in enumerate(license_rows_raw):
            license_name = clean_text(row.get("license_name"))
            if not license_name:
                continue
            license_names.append(license_name)
            key = (license_name, clean_text(row.get("license_number")) or "")
            if key in seen_license_keys:
                continue
            seen_license_keys.add(key)
            valid_from, expires_at, validity_text = parse_validity_period(row.get("validity_period_raw"))
            normalized_license_rows.append(
                (
                    "license",
                    truncate_text(license_name, 255),
                    truncate_text(clean_text(row.get("license_number")), 255),
                    truncate_text(clean_text(row.get("license_status")), 64),
                    None,
                    truncate_text(clean_text(row.get("data_source")), 255),
                    None,
                    valid_from,
                    expires_at,
                    truncate_text(validity_text, 255),
                    truncate_text(clean_text(row.get("issuing_authority")), 255),
                    1 if index == 0 else 0,
                )
            )

        qualification_label = qualification_label_from(qualification_names + license_names, tech_labels)

        normalized_ranking_rows: List[Tuple[Any, ...]] = []
        for row in ranking_rows:
            ranking_name = clean_text(row.get("ranking_name"))
            if not ranking_name:
                continue
            normalized_ranking_rows.append(
                (
                    truncate_text(ranking_name, 255),
                    truncate_text(clean_text(row.get("ranking_type")), 255),
                    truncate_text(clean_text(row.get("ranking_source")), 255),
                    parse_int(row.get("ranking_position_raw")),
                    truncate_text(clean_text(row.get("ranking_alias")), 255),
                    parse_int(row.get("publish_year_raw")),
                )
            )

        normalized_customer_rows: List[Tuple[Any, ...]] = []
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
                    truncate_text(clean_text(row.get("data_source")), 255),
                )
            )

        normalized_software_rows: List[Tuple[Any, ...]] = []
        seen_company_software_numbers: set[str] = set()
        for row in software_rows:
            software_name = clean_text(row.get("software_name"))
            register_number = clean_text(row.get("register_number"))
            if not software_name or not register_number or register_number in seen_company_software_numbers:
                continue
            seen_company_software_numbers.add(register_number)
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

        normalized_work_rows: List[Tuple[Any, ...]] = []
        seen_company_work_numbers: set[str] = set()
        for row in work_rows:
            work_name = clean_text(row.get("work_name"))
            register_number = clean_text(row.get("register_number"))
            if not work_name or not register_number or register_number in seen_company_work_numbers:
                continue
            seen_company_work_numbers.add(register_number)
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

        normalized_patent_rows: List[Tuple[Any, ...]] = []
        seen_company_patent_numbers: set[str] = set()
        for row in patent_rows:
            patent_number = clean_text(row.get("patent_number"))
            patent_name = clean_text(row.get("patent_name"))
            if not patent_number or not patent_name or patent_number in seen_company_patent_numbers:
                continue
            seen_company_patent_numbers.add(patent_number)
            normalized_patent_rows.append(
                (
                    truncate_text(patent_number, 255),
                    truncate_text(patent_name, 255),
                    parse_date(row.get("application_date_raw")),
                    parse_date(row.get("publication_date_raw")),
                    truncate_text(clean_text(row.get("patent_type_raw")), 255),
                )
            )

        normalized_recruit_rows: List[Tuple[Any, ...]] = []
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

        serious_illegal_count = parse_int(risk.get("serious_illegal_count_raw")) or 0
        judicial_case_count = parse_int(risk.get("judicial_case_count_raw")) or 0
        cooperation_risk_count = parse_int(risk.get("cooperation_risk_count_raw")) or 0
        dishonest_execution_count = parse_int(risk.get("dishonest_execution_count_raw")) or 0
        bankruptcy_case_count = parse_int(risk.get("bankruptcy_case_count_raw")) or 0
        executed_person_count = parse_int(risk.get("executed_person_count_raw")) or 0
        consumption_restriction_count = parse_int(risk.get("consumption_restriction_count_raw")) or 0
        business_abnormal_count = parse_int(risk.get("business_abnormal_count_raw")) or 0
        cluster_registration_count = parse_int(risk.get("cluster_registration_count_raw")) or 0

        branch_count_actual = len(branch_entries)
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
        qualification_count_actual = len(normalized_qualification_rows)
        qualification_count_raw = parse_int(operation.get("qualification_count_raw")) or qualification_count_actual
        license_count_actual = len(normalized_license_rows)
        license_count_raw = parse_int(operation.get("license_count_raw")) or license_count_actual
        supplier_count_raw = parse_int(operation.get("supplier_count_raw")) or 0
        bidding_count = parse_int(operation.get("bidding_count_raw")) or 0
        same_phone_company_count = parse_int(operation.get("same_phone_count_raw")) or 0

        phones = [
            clean_text(basic.get("contact_phone_0")),
            clean_text(basic.get("contact_phone_1")),
            clean_text(basic.get("contact_phone_2")),
            clean_text(basic.get("contact_phone_3")),
            clean_text(basic.get("contact_phone_4")),
            clean_text(basic.get("contact_phone_5")),
        ]
        phones = [phone for phone in phones if phone]

        has_branch = parse_bool_flag(basic.get("has_branch_raw")) or (1 if branch_entries else 0)
        has_recruitment = parse_bool_flag(operation.get("has_recruitment_raw")) or (1 if normalized_recruit_rows else 0)
        has_software_copyright = parse_bool_flag(ip.get("has_software_copyright_raw")) or (1 if normalized_software_rows else 0)
        has_work_copyright = parse_bool_flag(ip.get("has_work_copyright_raw")) or (1 if normalized_work_rows else 0)
        has_patent = parse_bool_flag(ip.get("has_patent_raw")) or (1 if normalized_patent_rows else 0)

        company_basic_rows.append(
            (
                company_name,
                credit_code,
                truncate_text(clean_text(basic.get("legal_representative")), 255),
                truncate_text(clean_text(basic.get("register_number")), 15),
                truncate_text(clean_text(basic.get("org_code")), 9),
                parse_date(basic.get("establish_info")),
                truncate_text(clean_text(basic.get("business_scope_raw")), 65535),
                first_non_empty(basic.get("email_business"), operation.get("email_business")),
                None,
                truncate_text(phones[0] if phones else None, 255),
                truncate_text(clean_text(operation.get("contact_info_raw")), 255),
                None,
                truncate_text(shareholders[0] if shareholders else None, 255),
                register_sheng,
                register_shi,
                register_xian,
                truncate_text(subdistrict, 255),
                register_capital,
                paid_capital,
                truncate_text(clean_text(basic.get("company_type_raw")), 255),
                truncate_text(clean_text(basic.get("org_type_raw")), 255),
                None,
                truncate_text(clean_text(basic.get("company_scale_raw")), 255),
                employee_count,
                insured_count,
                truncate_text(first_non_empty(operation.get("national_industry_raw"), basic.get("industry_name_raw")), 255),
                has_branch,
                truncate_text(branch_names[0] if branch_names else None, 255),
                truncate_text(address, 255),
                truncate_text(address, 255),
                qualification_label,
                parse_bool_flag(operation.get("is_general_taxpayer_raw")),
                "一般纳税人" if parse_bool_flag(operation.get("is_general_taxpayer_raw")) == 1 else None,
                truncate_text(clean_text(operation.get("taxpayer_credit_rating_raw")), 16),
                truncate_text(financing_round, 255),
                truncate_text(financing_round, 255),
                None,
                1,
                parse_bool_flag(ip.get("is_high_tech_enterprise_raw")),
                parse_bool_flag(operation.get("is_micro_enterprise_raw")),
                parse_bool_flag(operation.get("changed_info_raw")),
                parse_bool_flag(operation.get("has_bidding_raw")),
                has_recruitment,
                has_software_copyright,
                has_work_copyright,
                listing_status_code,
                same_phone_company_count,
                parse_bool_flag(ip.get("is_srdi_sme_raw")),
                parse_bool_flag(ip.get("is_gazelle_company_raw")),
                parse_bool_flag(ip.get("is_tech_sme_raw")),
                parse_bool_flag(ip.get("is_egalet_company_raw")),
                parse_bool_flag(ip.get("is_srdi_little_giant_raw")),
                parse_bool_flag(ip.get("is_innovative_sme_raw")),
                has_patent,
                1 if judicial_case_count > 0 else 0,
                1 if dishonest_execution_count > 0 else 0,
                0,
                1 if business_abnormal_count > 0 else 0,
                0,
                1 if bankruptcy_case_count > 0 else 0,
                0,
                0,
                0,
                1 if executed_person_count > 0 else 0,
                1 if consumption_restriction_count > 0 else 0,
                consumption_restriction_count,
                1 if any("朝阳" in item for item in [address or "", subdistrict or "", " ".join(street_candidates)]) else 0,
            )
        )

        pending_company_meta[company_name] = {
            "branch_entries": branch_entries,
            "phones": phones,
            "contact_info": clean_text(operation.get("contact_info_raw")),
            "shareholders": shareholders,
            "employee_count": employee_count,
            "employee_year": employee_year,
            "address": address,
            "register_sheng": register_sheng,
            "register_shi": register_shi,
            "register_xian": register_xian,
            "financing_round": financing_round,
            "listing_status_code": listing_status_code,
            "listing_status_raw": clean_text(operation.get("listing_status_raw")),
            "street_names": street_candidates,
            "software_entries": normalized_software_rows,
            "ranking_entries": normalized_ranking_rows,
            "customer_entries": normalized_customer_rows,
            "work_entries": normalized_work_rows,
            "patent_entries": normalized_patent_rows,
            "recruit_entries": normalized_recruit_rows,
            "qualification_entries": normalized_qualification_rows,
            "license_entries": normalized_license_rows,
            "risk_map": {
                "严重违法": serious_illegal_count,
                "司法案件": judicial_case_count,
                "合作风险": cooperation_risk_count,
                "失信被执行人": dishonest_execution_count,
                "破产案件": bankruptcy_case_count,
                "被执行人": executed_person_count,
                "限制高消费": consumption_restriction_count,
                "经营异常": business_abnormal_count,
                "集群注册": cluster_registration_count,
            },
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
                0,
                supplier_count_raw,
                qualification_count_actual,
                qualification_count_raw,
                license_count_actual,
                license_count_raw,
                bidding_count,
                judicial_case_count,
                0,
                judicial_case_count,
                dishonest_execution_count,
                0,
                business_abnormal_count,
                0,
                bankruptcy_case_count,
                0,
                0,
                0,
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
            "taxpayer_qualifications",
            "taxpayer_credit_rating",
            "financing_round",
            "financing_info",
            "stock_code",
            "field_belong",
            "is_high_tech_enterprise",
            "is_micro_enterprise",
            "has_changed_info",
            "has_bidding",
            "has_recruitment",
            "has_software_copyright",
            "has_work_copyright",
            "listing_status",
            "same_phone_company_count",
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

    branch_rows: List[Tuple[Any, ...]] = []
    contact_phone_rows: List[Tuple[Any, ...]] = []
    contact_info_rows: List[Tuple[Any, ...]] = []
    shareholder_rows: List[Tuple[Any, ...]] = []
    employee_count_rows: List[Tuple[Any, ...]] = []
    address_rows: List[Tuple[Any, ...]] = []
    qualification_rows: List[Tuple[Any, ...]] = []
    financing_rows: List[Tuple[Any, ...]] = []
    listing_rows: List[Tuple[Any, ...]] = []
    basic_count_rows: List[Tuple[Any, ...]] = []
    subdistrict_rows_insert: List[Tuple[Any, ...]] = []
    software_rows_insert: List[Tuple[Any, ...]] = []
    ranking_rows_insert: List[Tuple[Any, ...]] = []
    customer_rows_insert: List[Tuple[Any, ...]] = []
    work_rows_insert: List[Tuple[Any, ...]] = []
    patent_rows_insert: List[Tuple[Any, ...]] = []
    recruit_rows_insert: List[Tuple[Any, ...]] = []
    risk_rows_insert: List[Tuple[Any, ...]] = []

    patent_types: Dict[str, None] = {}
    patent_type_pairs: List[Tuple[str, str]] = []
    patent_company_pairs: List[Tuple[str, int]] = []
    seen_software_register_numbers: set[str] = set()
    seen_work_register_numbers: set[str] = set()
    seen_patent_numbers: set[str] = set()

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

        for branch_name, branch_region, branch_status, branch_establish_date, branch_leader in meta["branch_entries"]:
            branch_rows.append((company_id, branch_name, branch_region, branch_status, branch_establish_date, branch_leader))

        for index, phone in enumerate(list(dict.fromkeys(meta["phones"]))):
            contact_phone_rows.append((company_id, truncate_text(phone, 255), 1 if index == 0 else 0))

        contact_info = meta["contact_info"]
        if contact_info:
            contact_info_rows.append((company_id, truncate_text(contact_info, 255), 1))

        for index, shareholder_name in enumerate(meta["shareholders"]):
            shareholder_rows.append((company_id, truncate_text(shareholder_name, 255), 1 if index == 0 else 0))

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

        qualification_index = 0
        for entry in meta["qualification_entries"] + meta["license_entries"]:
            qualification_rows.append((company_id,) + entry[:-1] + (1 if qualification_index == 0 else entry[-1],))
            qualification_index += 1

        if meta["financing_round"]:
            financing_rows.append((company_id, truncate_text(meta["financing_round"], 255), 1))

        if meta["listing_status_code"] is not None:
            listing_rows.append((company_id, meta["listing_status_code"], None, truncate_text(meta["listing_status_raw"], 255), 1))

        for subdistrict_name in meta["street_names"]:
            subdistrict_rows_insert.append((truncate_text(subdistrict_name, 255), company_id))

        for software_entry in meta["software_entries"]:
            software_name, register_number, register_date, software_short_name, status, obtain_method = software_entry
            if register_number in seen_software_register_numbers:
                continue
            seen_software_register_numbers.add(register_number)
            software_rows_insert.append((software_name, company_id, register_number, register_date, software_short_name, status, obtain_method))

        for ranking_entry in meta["ranking_entries"]:
            ranking_name, ranking_type, ranking_source, ranking_position, ranking_alias, publish_year = ranking_entry
            ranking_rows_insert.append((ranking_name, company_id, ranking_type, ranking_source, ranking_position, ranking_alias, publish_year))

        for customer_entry in meta["customer_entries"]:
            customer_name, sales_amount, sales_ratio, report_date, data_source = customer_entry
            customer_company_id = company_id_map.get(normalize_company_name(customer_name) or "")
            customer_rows_insert.append((customer_name, company_id, customer_company_id, sales_amount, sales_ratio, report_date, data_source))

        for work_entry in meta["work_entries"]:
            work_name, register_number, work_type, publish_date, register_date, status = work_entry
            if register_number in seen_work_register_numbers:
                continue
            seen_work_register_numbers.add(register_number)
            work_rows_insert.append((work_name, company_id, register_number, work_type, publish_date, register_date, status))

        for patent_entry in meta["patent_entries"]:
            patent_number, patent_name, application_date, publication_date, patent_type = patent_entry
            if patent_number in seen_patent_numbers:
                patent_company_pairs.append((patent_number, company_id))
                if patent_type:
                    patent_type_pairs.append((patent_number, patent_type))
                continue
            seen_patent_numbers.add(patent_number)
            patent_rows_insert.append((patent_number, patent_name, company_id, application_date, None, publication_date))
            patent_company_pairs.append((patent_number, company_id))
            if patent_type:
                patent_types[patent_type] = None
                patent_type_pairs.append((patent_number, patent_type))

        for recruit_entry in meta["recruit_entries"]:
            position_name, salary, work_year, work_place, edu_req, recruit_time = recruit_entry
            recruit_rows_insert.append((position_name, company_id, salary, work_year, work_place, edu_req, recruit_time))

        for risk_name, risk_count in meta["risk_map"].items():
            if risk_count > 0:
                risk_rows_insert.append((company_id, risk_name, risk_count))

    insert_rows(env, "company_branch", ["company_id", "company_branch_name", "company_branch_region", "company_branch_status", "company_branch_establish_date", "company_branch_legal_representative"], branch_rows, batch_size=args.batch_size)
    insert_rows(env, "company_contact_phone", ["company_id", "contact_phone", "is_latest"], contact_phone_rows, batch_size=args.batch_size)
    insert_rows(env, "company_contact_info", ["company_id", "contact_info", "is_latest"], contact_info_rows, batch_size=args.batch_size)
    insert_rows(env, "company_shareholder", ["company_id", "shareholder_name", "is_latest"], shareholder_rows, batch_size=args.batch_size)
    insert_rows(env, "company_employee_count", ["company_id", "stat_year", "employee_count"], employee_count_rows, batch_size=args.batch_size)
    insert_rows(env, "company_address", ["company_id", "address_type", "address_text", "province", "city", "district", "is_latest"], address_rows, batch_size=args.batch_size)
    insert_rows(env, "company_qualification", ["company_id", "record_kind", "qualification_name", "qualification_number", "qualification_status", "qualification_type", "data_source", "issued_at", "valid_from", "expires_at", "validity_period_text", "issuing_authority", "is_latest"], qualification_rows, batch_size=args.batch_size)
    insert_rows(env, "company_financing", ["company_id", "financing_round", "is_latest"], financing_rows, batch_size=args.batch_size)
    insert_rows(env, "company_listing_status", ["company_id", "listing_status", "stock_code", "market_name", "is_latest"], listing_rows, batch_size=args.batch_size)
    insert_rows(env, "company_basic_count", ["company_id", "branch_count", "branch_count_raw", "recruit_count", "recruit_count_raw", "software_copyright_count", "software_copyright_count_raw", "work_copyright_count", "work_copyright_count_raw", "patent_count", "patent_count_raw", "trademark_count", "customer_count", "customer_count_raw", "ranking_count", "ranking_count_raw", "supplier_count", "supplier_count_raw", "qualification_count", "qualification_count_raw", "license_count", "license_count_raw", "bidding_count", "legal_doc_case_count", "legal_doc_judgement_count", "legal_doc_all_count", "dishonest_execution_count", "chattel_mortgage_count", "business_abnormal_count", "admin_penalty_count", "bankruptcy_overlap_count", "liquidation_info_count", "env_penalty_count", "equity_freeze_count", "executed_person_count"], basic_count_rows, batch_size=args.batch_size)
    insert_rows(env, "company_subdistrict", ["company_subdistrict_name", "company_id"], subdistrict_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_software_copyright", ["company_software_copyright_name", "company_id", "company_software_copyright_register_number", "company_software_copyright_register_date", "company_software_copyright_for_short", "company_software_copyright_status", "company_software_copyright_obtain"], software_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_ranking", ["company_ranking_name", "company_id", "company_ranking_type", "company_ranking_source", "company_ranking_position", "company_ranking_alias", "company_ranking_publish_year"], ranking_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_customer", ["company_customer_name", "company_id", "customer_company_id", "company_customer_sales_amount", "company_customer_sales_ratio", "company_customer_report_date", "data_source"], customer_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_work_copyright", ["company_work_copyright_name", "company_id", "company_work_copyright_register_number", "company_work_copyright_type", "company_work_copyright_publish_date", "company_work_copyright_register_date", "company_work_copyright_status"], work_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_patent", ["company_patent_number", "company_patent_name", "company_id", "application_date", "auth_date", "publication_date"], patent_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_recruit", ["company_recruit_position", "company_id", "company_recruit_salary", "company_recruit_work_year_req", "company_recruit_work_place", "company_recruit_edu_req", "company_recruit_time"], recruit_rows_insert, batch_size=args.batch_size)
    insert_rows(env, "company_risk", ["company_id", "company_risk_category_name", "company_risk_category_count"], risk_rows_insert, batch_size=args.batch_size)

    patent_type_rows = [(patent_type,) for patent_type in sorted(patent_types.keys())]
    insert_rows(env, "company_patent_type", ["company_patent_type_name"], patent_type_rows, batch_size=args.batch_size)

    patent_id_by_number: Dict[str, int] = {}
    for line in query_mysql("SELECT company_patent_id, company_patent_number FROM company_patent;", env).splitlines():
        if not line:
            continue
        patent_id, patent_number = line.split("\t", 1)
        patent_id_by_number[patent_number] = int(patent_id)

    patent_type_id_by_name: Dict[str, int] = {}
    for line in query_mysql("SELECT company_patent_type_id, company_patent_type_name FROM company_patent_type;", env).splitlines():
        if not line:
            continue
        type_id, type_name = line.split("\t", 1)
        patent_type_id_by_name[type_name] = int(type_id)

    patent_type_map_rows: List[Tuple[Any, ...]] = []
    seen_patent_type_map: set[Tuple[int, int]] = set()
    for patent_number, patent_type_name in patent_type_pairs:
        patent_id = patent_id_by_number.get(patent_number)
        patent_type_id = patent_type_id_by_name.get(patent_type_name)
        if patent_id is None or patent_type_id is None:
            continue
        key = (patent_id, patent_type_id)
        if key in seen_patent_type_map:
            continue
        seen_patent_type_map.add(key)
        patent_type_map_rows.append((patent_id, patent_type_id))
    insert_rows(env, "company_patent_patent_type_map", ["company_patent_id", "company_patent_type_id"], patent_type_map_rows, batch_size=args.batch_size)

    patent_company_map_rows: List[Tuple[Any, ...]] = []
    seen_patent_company_map: set[Tuple[int, int]] = set()
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
    print(f"[sync] company_qualification: {len(qualification_rows)}")
    print(f"[sync] company_customer: {len(customer_rows_insert)}")
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
