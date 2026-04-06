#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_env(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'").strip()
    return env


def mysql_command(env: Dict[str, str], *, with_database: bool = True, batch: bool = False) -> Tuple[List[str], Dict[str, str]]:
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
    if batch:
        cmd.extend(["--batch", "--raw", "--skip-column-names"])
    child_env = os.environ.copy()
    password = env.get("DB_PASSWORD")
    if password:
        child_env["MYSQL_PWD"] = password
    return cmd, child_env


def run_mysql_sql(sql: str, env: Dict[str, str], *, with_database: bool = True) -> None:
    cmd, child_env = mysql_command(env, with_database=with_database)
    subprocess.run(cmd, input=sql, text=True, env=child_env, check=True)


def query_mysql(sql: str, env: Dict[str, str], *, with_database: bool = True) -> str:
    cmd, child_env = mysql_command(env, with_database=with_database, batch=True)
    cmd.extend(["-e", sql])
    result = subprocess.run(cmd, text=True, capture_output=True, env=child_env, check=True)
    return result.stdout


def query_rows(sql: str, env: Dict[str, str], *, with_database: bool = True) -> List[List[str]]:
    rows: List[List[str]] = []
    for line in query_mysql(sql, env, with_database=with_database).splitlines():
        if line.strip():
            rows.append(line.split("\t"))
    return rows


def query_json_rows(table: str, columns: Sequence[str], env: Dict[str, str]) -> List[Dict[str, Any]]:
    json_args = ", ".join(f"'{column}', `{column}`" for column in columns)
    sql = f"SELECT JSON_OBJECT({json_args}) FROM `{table}` ORDER BY `raw_id`;"
    rows: List[Dict[str, Any]] = []
    for line in query_mysql(sql, env).splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).replace("\xa0", " ").strip()
    return text or None


def normalize_company_name(value: Any) -> Optional[str]:
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
    items: List[str] = []
    for token in re.split(pattern, text):
        normalized = clean_text(token)
        if normalized:
            items.append(normalized)
    return list(dict.fromkeys(items))


def parse_int(value: Any) -> Optional[int]:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"-?\d+", text.replace(",", ""))
    if not match:
        return None
    return int(match.group(0))


def parse_decimal(value: Any) -> Optional[str]:
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


def parse_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = clean_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_year(value: Any) -> Optional[int]:
    text = clean_text(value)
    if not text:
        return None
    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None
    return int(match.group(0))


def parse_employee_info(value: Any) -> Tuple[Optional[int], Optional[int]]:
    text = clean_text(value)
    if not text:
        return None, None
    count = parse_int(text)
    year = parse_year(text)
    return count, year


def parse_bool_flag(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return 1 if value > 0 else 0
    text = clean_text(value)
    if not text:
        return 0
    if text in {"1", "是", "有", "true", "True", "Y", "已登记", "存续", "正常"}:
        return 1
    if text in {"0", "否", "无", "false", "False", "N", "未上市"}:
        return 0
    number = parse_int(text)
    if number is not None:
        return 1 if number > 0 else 0
    return 1


def parse_listing_status_code(value: Any) -> Optional[int]:
    text = clean_text(value)
    if not text:
        return None
    if any(keyword in text for keyword in ("未上市", "非上市", "否")):
        return 0
    if any(keyword in text for keyword in ("终止", "退市", "摘牌")):
        return 2
    return 1


def parse_validity_period(value: Any) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    text = clean_text(value)
    if not text:
        return None, None, None
    dates = re.findall(r"(19|20)\d{2}[./-]\d{1,2}[./-]\d{1,2}", text)
    if len(dates) >= 2:
        start = parse_date(dates[0])
        end = parse_date(dates[1])
        return start, end, text
    if len(dates) == 1:
        only = parse_date(dates[0])
        return only, only, text
    return None, None, text


def derive_region_fields(address: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not address:
        return None, None, None
    province = "北京市" if "北京市" in address else None
    city = "北京市" if province else None
    district_match = re.search(r"(北京市)?([^市]{1,12}区|[^市]{1,12}县)", address)
    district = district_match.group(2) if district_match else None
    return province, city, district


def temp_credit_code(seed: str) -> str:
    import hashlib

    digest = hashlib.md5(seed.encode("utf-8")).hexdigest().upper()
    return f"TMP{digest[:15]}"


def first_non_empty(*values: Any) -> Optional[str]:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return None


def chunked(items: Sequence[Tuple[Any, ...]], size: int) -> Iterable[Sequence[Tuple[Any, ...]]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def escape_sql(value: Any) -> str:
    if value is None:
        return "NULL"
    text = str(value)
    if text == "":
        return "NULL"
    text = text.replace("\\", "\\\\").replace("'", "''").replace("\x00", "")
    return f"'{text}'"


def insert_rows(env: Dict[str, str], table: str, columns: Sequence[str], rows: Sequence[Sequence[Any]], *, batch_size: int = 500) -> None:
    if not rows:
        return
    column_sql = ", ".join(f"`{column}`" for column in columns)
    for batch in chunked(list(rows), batch_size):
        values_sql = []
        for row in batch:
            values_sql.append("(" + ", ".join(escape_sql(value) for value in row) + ")")
        sql = f"INSERT INTO `{table}` ({column_sql}) VALUES\n" + ",\n".join(values_sql) + ";\n"
        run_mysql_sql(sql, env)

