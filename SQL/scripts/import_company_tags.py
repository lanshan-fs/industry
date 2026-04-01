#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_ROOT = PROJECT_ROOT / "SQL"
DEFAULT_MM_PATH = SQL_ROOT / "data" / "企业标签.mm"
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"

DIMENSION_JSON_PATH = SQL_ROOT / "data" / "company_tag_dimension.json"
SUBDIMENSION_JSON_PATH = SQL_ROOT / "data" / "company_tag_subdimension.json"
LIBRARY_JSON_PATH = SQL_ROOT / "data" / "company_tag_library.json"

PLACEHOLDER_TAGS = {"暂无", "不限", "自定义"}


def parse_env(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def mysql_command(env: Dict[str, str]) -> Tuple[List[str], Dict[str, str]]:
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
    cmd, child_env = mysql_command(env)
    cmd.extend(["-e", sql])
    result = subprocess.run(cmd, text=True, capture_output=True, env=child_env, check=True)
    rows: List[List[str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        rows.append(line.split("\t"))
    return rows


def run_mysql_sql(sql: str, env: Dict[str, str]) -> None:
    cmd, child_env = mysql_command(env)
    result = subprocess.run(cmd, text=True, input=sql, capture_output=True, env=child_env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "mysql command failed")


def normalize_text(text: Optional[str]) -> str:
    return " ".join((text or "").split())


def child_nodes(node: ET.Element) -> List[ET.Element]:
    return [child for child in node.findall("node")]


def escape_sql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def parse_mm(
    mm_path: Path,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], List[Dict[str, object]]]:
    tree = ET.parse(mm_path)
    root = tree.getroot().find("./node")
    if root is None:
        raise ValueError(f"{mm_path} 缺少根 node")
    if normalize_text(root.attrib.get("TEXT")) != "企业标签":
        raise ValueError(f"{mm_path} 根节点 TEXT 不是 '企业标签'")

    dimensions: List[Dict[str, object]] = []
    subdimensions: List[Dict[str, object]] = []
    tags: List[Dict[str, object]] = []

    next_dimension_id = 1
    next_subdimension_id = 1
    next_tag_id = 1

    for dim_index, dimension_node in enumerate(child_nodes(root), start=1):
        dimension_name = normalize_text(dimension_node.attrib.get("TEXT"))
        if not dimension_name:
            continue
        dimension_id = next_dimension_id
        next_dimension_id += 1
        dimensions.append(
            {
                "company_tag_dimension_id": dimension_id,
                "company_tag_dimension_name": dimension_name,
                "company_tag_dimension_color": None,
                "company_tag_dimension_icon": None,
                "company_tag_dimension_des": None,
                "sort_order": dim_index * 10,
            }
        )

        second_level_nodes = child_nodes(dimension_node)
        if not second_level_nodes:
            continue

        if all(not child_nodes(node) for node in second_level_nodes):
            implicit_subdimension_id = next_subdimension_id
            next_subdimension_id += 1
            subdimensions.append(
                {
                    "company_tag_subdimension_id": implicit_subdimension_id,
                    "company_tag_subdimension_name": dimension_name,
                    "company_tag_dimension_id": dimension_id,
                    "sort_order": 10,
                }
            )
            for tag_index, tag_node in enumerate(second_level_nodes, start=1):
                tag_name = normalize_text(tag_node.attrib.get("TEXT"))
                if not tag_name or tag_name in PLACEHOLDER_TAGS:
                    continue
                tags.append(
                    {
                        "company_tag_id": next_tag_id,
                        "company_tag_name": tag_name,
                        "company_tag_subdimension_id": implicit_subdimension_id,
                        "company_tag_level": None,
                        "sort_order": tag_index * 10,
                    }
                )
                next_tag_id += 1
            continue

        for sub_index, subdimension_node in enumerate(second_level_nodes, start=1):
            subdimension_name = normalize_text(subdimension_node.attrib.get("TEXT"))
            if not subdimension_name:
                continue
            subdimension_id = next_subdimension_id
            next_subdimension_id += 1
            subdimensions.append(
                {
                    "company_tag_subdimension_id": subdimension_id,
                    "company_tag_subdimension_name": subdimension_name,
                    "company_tag_dimension_id": dimension_id,
                    "sort_order": sub_index * 10,
                }
            )

            sub_children = child_nodes(subdimension_node)
            tag_nodes: List[ET.Element] = []
            if any(normalize_text(node.attrib.get("TEXT")) == "配套标签" for node in sub_children):
                tag_container = next(
                    node for node in sub_children if normalize_text(node.attrib.get("TEXT")) == "配套标签"
                )
                tag_nodes = child_nodes(tag_container)
            elif all(not child_nodes(node) for node in sub_children):
                tag_nodes = sub_children

            for tag_index, tag_node in enumerate(tag_nodes, start=1):
                tag_name = normalize_text(tag_node.attrib.get("TEXT"))
                if not tag_name or tag_name in PLACEHOLDER_TAGS:
                    continue
                tags.append(
                    {
                        "company_tag_id": next_tag_id,
                        "company_tag_name": tag_name,
                        "company_tag_subdimension_id": subdimension_id,
                        "company_tag_level": None,
                        "sort_order": tag_index * 10,
                    }
                )
                next_tag_id += 1

    ensure_unique_names(dimensions, "company_tag_dimension_name")
    ensure_unique_names_within_parent(subdimensions)
    uniquify_tag_names(dimensions, subdimensions, tags)
    ensure_unique_names(tags, "company_tag_name")
    return dimensions, subdimensions, tags


def ensure_unique_names(rows: Sequence[Dict[str, object]], key: str) -> None:
    seen: Dict[str, int] = {}
    for index, row in enumerate(rows, start=1):
        value = str(row[key])
        if value in seen:
            raise ValueError(f"{key} 存在重复值 {value!r}，位置 {seen[value]} 和 {index}")
        seen[value] = index


def ensure_unique_names_within_parent(rows: Sequence[Dict[str, object]]) -> None:
    seen: Dict[Tuple[int, str], int] = {}
    for index, row in enumerate(rows, start=1):
        key = (int(row["company_tag_dimension_id"]), str(row["company_tag_subdimension_name"]))
        if key in seen:
            raise ValueError(
                "company_tag_subdimension_name 在同一维度下重复，"
                f"维度ID={key[0]} 名称={key[1]!r}，位置 {seen[key]} 和 {index}"
            )
        seen[key] = index


def uniquify_tag_names(
    dimensions: Sequence[Dict[str, object]],
    subdimensions: Sequence[Dict[str, object]],
    tags: Sequence[Dict[str, object]],
) -> None:
    original_counts = Counter(str(tag["company_tag_name"]) for tag in tags)
    subdimension_lookup = {
        int(row["company_tag_subdimension_id"]): {
            "name": str(row["company_tag_subdimension_name"]),
            "dimension_id": int(row["company_tag_dimension_id"]),
        }
        for row in subdimensions
    }
    dimension_lookup = {
        int(row["company_tag_dimension_id"]): str(row["company_tag_dimension_name"]) for row in dimensions
    }
    used_names: set[str] = set()

    for tag in tags:
        original_name = str(tag["company_tag_name"])
        if original_counts[original_name] == 1 and original_name not in used_names:
            used_names.add(original_name)
            continue

        subdimension = subdimension_lookup[int(tag["company_tag_subdimension_id"])]
        dimension_name = dimension_lookup[subdimension["dimension_id"]]
        candidates = [
            f"{subdimension['name']}:{original_name}",
            f"{dimension_name}/{subdimension['name']}:{original_name}",
        ]
        chosen_name: Optional[str] = None
        for candidate in candidates:
            if candidate not in used_names:
                chosen_name = candidate
                break
        if chosen_name is None:
            suffix = 2
            while True:
                candidate = f"{dimension_name}/{subdimension['name']}:{original_name}#{suffix}"
                if candidate not in used_names:
                    chosen_name = candidate
                    break
                suffix += 1

        tag["company_tag_name"] = chosen_name
        used_names.add(chosen_name)


def write_json(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(rows), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sql_value(value: Optional[object]) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, str):
        return f"'{escape_sql_string(value)}'"
    return str(value)


def build_insert_sql(
    dimensions: Sequence[Dict[str, object]],
    subdimensions: Sequence[Dict[str, object]],
    tags: Sequence[Dict[str, object]],
) -> str:
    dim_values = ",\n  ".join(
        "("
        f"{row['company_tag_dimension_id']}, "
        f"{sql_value(row['company_tag_dimension_name'])}, "
        f"{sql_value(row['company_tag_dimension_color'])}, "
        f"{sql_value(row['company_tag_dimension_icon'])}, "
        f"{sql_value(row['company_tag_dimension_des'])}, "
        f"{row['sort_order']}"
        ")"
        for row in dimensions
    )
    subdim_values = ",\n  ".join(
        "("
        f"{row['company_tag_subdimension_id']}, "
        f"{sql_value(row['company_tag_subdimension_name'])}, "
        f"{row['company_tag_dimension_id']}, "
        f"{row['sort_order']}"
        ")"
        for row in subdimensions
    )
    tag_values = ",\n  ".join(
        "("
        f"{row['company_tag_id']}, "
        f"{sql_value(row['company_tag_name'])}, "
        f"{row['company_tag_subdimension_id']}, "
        f"{sql_value(row['company_tag_level'])}, "
        f"{row['sort_order']}"
        ")"
        for row in tags
    )

    return (
        "START TRANSACTION;\n"
        "DELETE FROM company_tag_library;\n"
        "DELETE FROM company_tag_subdimension;\n"
        "DELETE FROM company_tag_dimension;\n"
        "INSERT INTO company_tag_dimension "
        "(company_tag_dimension_id, company_tag_dimension_name, company_tag_dimension_color, company_tag_dimension_icon, company_tag_dimension_des, sort_order)\n"
        "VALUES\n  "
        + dim_values
        + ";\n"
        "INSERT INTO company_tag_subdimension "
        "(company_tag_subdimension_id, company_tag_subdimension_name, company_tag_dimension_id, sort_order)\n"
        "VALUES\n  "
        + subdim_values
        + ";\n"
        "INSERT INTO company_tag_library "
        "(company_tag_id, company_tag_name, company_tag_subdimension_id, company_tag_level, sort_order)\n"
        "VALUES\n  "
        + tag_values
        + ";\n"
        "COMMIT;\n"
    )


def ensure_dependent_tables_empty(env: Dict[str, str]) -> Dict[str, int]:
    rows = query_rows(
        """
        SELECT 'company_tag_map', COUNT(*) FROM company_tag_map
        UNION ALL
        SELECT 'company_tag_auto_rule', COUNT(*) FROM company_tag_auto_rule
        UNION ALL
        SELECT 'company_tag_dimension_library_map', COUNT(*) FROM company_tag_dimension_library_map;
        """,
        env,
    )
    counts = {name: int(count) for name, count in rows}
    blocking = [name for name, count in counts.items() if count > 0]
    if blocking:
        detail = ", ".join(f"{name}={counts[name]}" for name in blocking)
        raise RuntimeError(
            "导入已中止：标签依赖映射表非空，不能直接重建 company_tag_* 基础表。"
            f" ({detail})"
        )
    return counts


def print_summary(
    dimensions: Sequence[Dict[str, object]],
    subdimensions: Sequence[Dict[str, object]],
    tags: Sequence[Dict[str, object]],
) -> None:
    print(f"[ok] dimensions={len(dimensions)}")
    print(f"[ok] subdimensions={len(subdimensions)}")
    print(f"[ok] tags={len(tags)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert 企业标签.mm into tag JSON files and optionally import them.")
    parser.add_argument("--mm-file", default=str(DEFAULT_MM_PATH), help="Path to 企业标签.mm")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH), help="Path to .env file")
    parser.add_argument("--apply", action="store_true", help="Import generated JSON data into company tag tables")
    args = parser.parse_args()

    dimensions, subdimensions, tags = parse_mm(Path(args.mm_file))
    write_json(DIMENSION_JSON_PATH, dimensions)
    write_json(SUBDIMENSION_JSON_PATH, subdimensions)
    write_json(LIBRARY_JSON_PATH, tags)
    print(f"[ok] generated {DIMENSION_JSON_PATH}")
    print(f"[ok] generated {SUBDIMENSION_JSON_PATH}")
    print(f"[ok] generated {LIBRARY_JSON_PATH}")
    print_summary(dimensions, subdimensions, tags)

    if not args.apply:
        return 0

    env = parse_env(Path(args.env_file))
    ensure_dependent_tables_empty(env)
    run_mysql_sql(build_insert_sql(dimensions, subdimensions, tags), env)
    print("[ok] imported company tag dimensions, subdimensions and tag library")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise
