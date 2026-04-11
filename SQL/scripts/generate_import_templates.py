from __future__ import annotations

import csv
import os
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import django


ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend_django"
OUTPUT_DIR = ROOT / "externals" / "template"
ZIP_PATH = OUTPUT_DIR / "enterprise-import-templates.zip"


def _setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("PYTHONPATH", str(BACKEND_DIR))
    import sys

    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    django.setup()


def _write_csv(path: Path, headers: list[str], sample_row: list[str] | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        if sample_row:
            writer.writerow(sample_row)


def _render_table_guide(table: dict) -> str:
    required_columns = [column["import_label"] for column in table["columns"] if column["creatable"] and column["required"]]
    importable_columns = [column["import_label"] for column in table["columns"] if column["creatable"]]
    lines = [
        f"## {table['table_name']}",
        "",
        f"- 中文名称：{table['label']}",
        f"- 模板文件：`{table['table_name']}.csv`",
        f"- 必填字段：{', '.join(required_columns) if required_columns else '无'}",
        f"- 可导入字段数：{len(importable_columns)}",
        "",
        "| 导入列名 | 字段名 | 类型 | 必填 | 备注 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for column in table["columns"]:
        if not column["creatable"]:
            continue
        lines.append(
            "| {import_label} | `{name}` | `{column_type}` | {required} | {comment} |".format(
                import_label=column["import_label"],
                name=column["name"],
                column_type=column["column_type"],
                required="是" if column["required"] else "否",
                comment=column["comment"] or "-",
            )
        )
    lines.append("")
    return "\n".join(lines)


def main():
    _setup_django()
    from system_api.views import SYSTEM_COMPANY_TEMPLATE_HEADERS, _managed_table_map

    if OUTPUT_DIR.exists():
        for child in OUTPUT_DIR.iterdir():
            if child.is_file():
                child.unlink()
            else:
                shutil.rmtree(child)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _write_csv(
        OUTPUT_DIR / "company_basic.csv",
        SYSTEM_COMPANY_TEMPLATE_HEADERS,
        [
            "示例企业",
            "91110000123456789A",
            "张三",
            "2024-01-01",
            "生物制药",
            "1000",
            "500",
            "A轮",
            "有限责任公司",
            "企业法人",
            "民营",
            "100-499人",
            "010-12345678",
            "demo@example.com",
            "北京市朝阳区示例路1号",
            "示例股东",
            "高新技术企业",
            "110000000000001",
            "123456789",
            "技术开发；技术咨询；技术服务",
        ],
    )

    table_map = _managed_table_map()
    guides = [
        "# 企业数据管理导入模板说明",
        "",
        "说明：",
        "- `company_basic.csv` 对应企业主表导入模板。",
        "- 其余 `company_*.csv` 对应企业数据管理子表模板，字段名与 Django 企业数据管理导入口径保持一致。",
        "- CSV 文件均为 `UTF-8 with BOM` 编码，建议直接用 Excel/WPS 打开整理后再保存。",
        "- 只有模板中的列可以直接导入；系统主键、自增字段、审计字段未写入模板。",
        "",
    ]

    for table_name in sorted(table_map.keys()):
        table = table_map[table_name]
        importable_columns = [column["import_label"] for column in table["columns"] if column["creatable"]]
        _write_csv(OUTPUT_DIR / f"{table_name}.csv", importable_columns)
        guides.append(_render_table_guide(table))

    guide_path = OUTPUT_DIR / "README.md"
    guide_path.write_text("\n".join(guides), encoding="utf-8")

    with ZipFile(ZIP_PATH, "w", compression=ZIP_DEFLATED) as zip_file:
        for child in sorted(OUTPUT_DIR.iterdir()):
            if child == ZIP_PATH:
                continue
            zip_file.write(child, arcname=child.name)

    print(f"generated {len(table_map) + 2} files into {OUTPUT_DIR}")
    print(f"zip: {ZIP_PATH}")


if __name__ == "__main__":
    main()
