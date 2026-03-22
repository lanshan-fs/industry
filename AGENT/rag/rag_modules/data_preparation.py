from __future__ import annotations

import json
from typing import Any

from langchain_core.documents import Document

from ..config import RAGConfig
from ..db import DatabaseClient


TASK_KNOWLEDGE_DOCS = (
    {
        "task_type": "industry_diagnosis",
        "title": "区域产业现状分析与链条诊断任务定义",
        "content": (
            "一级任务：区域产业现状分析与链条诊断。"
            "主要回答某一区域产业发展得怎么样、链条结构是否完整、重点环节分布是否合理。"
            "重点证据包括企业基础信息、产业分类、产业链环节标签、区域分布和代表性企业。"
            "典型输出应覆盖总体判断、链条结构、关键主体、主要短板和后续关注点。"
        ),
    },
    {
        "task_type": "risk_assessment",
        "title": "风险研判与预警任务定义",
        "content": (
            "一级任务：风险研判与预警。"
            "主要回答当前产业链中哪些企业或环节存在潜在风险、风险来源是什么、可能影响哪些链条节点。"
            "重点证据包括经营异常、行政处罚、法律文书、失信执行、清算信息等风险字段。"
            "典型输出应覆盖风险结论、触发信号、影响范围、优先级和建议动作。"
        ),
    },
    {
        "task_type": "chain_upgrade",
        "title": "补链延链强链建议任务定义",
        "content": (
            "一级任务：补链延链强链建议。"
            "主要回答当前区域产业链的薄弱环节在哪里、哪些关键节点需要补足、哪些方向适合延伸和强化。"
            "重点证据包括产业链关键环节、企业数量分布、能力短板和区域产业基础。"
            "典型输出应覆盖关键短板、目标环节、建议路径、可落地主体或资源以及实施优先级。"
        ),
    },
    {
        "task_type": "investment_attraction",
        "title": "招商引资与目标企业推荐任务定义",
        "content": (
            "一级任务：招商引资与目标企业推荐。"
            "主要回答围绕当前产业链结构应当引进哪些企业、优先布局哪些方向、招商对象应具备何种特征。"
            "重点证据包括链条缺口分析、企业画像、科技属性、经营能力和潜在匹配方向。"
            "典型输出应覆盖招商目标、推荐赛道或环节、候选企业或企业画像、推荐理由和跟进建议。"
        ),
    },
    {
        "task_type": "enterprise_profile",
        "title": "重点企业识别与企业画像支撑能力定义",
        "content": (
            "支撑能力：重点企业识别与企业画像。"
            "用于回答这家企业是谁、处于链条何处、具备何种技术与经营特征、存在何种风险、是否具备招商或培育价值。"
            "重点证据包括企业基本信息、经营信息、知识产权、风险信息和产业链标签。"
            "该能力服务于招商推荐、风险研判和链条诊断，不与四个一级任务并列。"
        ),
    },
)


class DataPreparationModule:
    def __init__(self, db: DatabaseClient, config: RAGConfig):
        self.db = db
        self.config = config

    def prepare_documents(self) -> list[Document]:
        tables = self.db.list_tables(exclude_tables=self.config.exclude_tables)
        foreign_keys = self.db.list_foreign_keys(exclude_tables=self.config.exclude_tables)
        docs: list[Document] = []
        display_name_map = {
            table["table_name"]: self.db.get_table_display_name(table["table_name"], table["table_comment"])
            for table in tables
        }

        for task_doc in TASK_KNOWLEDGE_DOCS:
            docs.append(
                Document(
                    page_content=task_doc["content"],
                    metadata={
                        "source_type": "task_definition",
                        "task_type": task_doc["task_type"],
                        "display_name": task_doc["title"],
                        "table_name": "__task__",
                    },
                )
            )

        overview_lines = [
            f"数据库名称: {self.config.db_name}",
            f"数据表总数: {len(tables)}",
            "数据表概览:",
        ]
        for table in tables:
            display_name = display_name_map[table["table_name"]]
            overview_lines.append(
                f"- {display_name} | 说明={table['table_comment'] or '无'} | 估计行数={int(table['table_rows'] or 0)}"
            )
        docs.append(
            Document(
                page_content="\n".join(overview_lines),
                metadata={
                    "source_type": "database_overview",
                    "table_name": "__database__",
                    "display_name": "数据库总览",
                },
            )
        )

        fk_lines_by_table: dict[str, list[str]] = {}
        for relation in foreign_keys:
            table_name = relation["table_name"]
            from_columns = self.db.list_columns(relation["table_name"])
            to_columns = self.db.list_columns(relation["referenced_table_name"])
            from_label_map = {
                column["column_name"]: self._column_label(column)
                for column in from_columns
            }
            to_label_map = {
                column["column_name"]: self._column_label(column)
                for column in to_columns
            }
            fk_lines_by_table.setdefault(table_name, []).append(
                f"{from_label_map.get(relation['column_name'], '关联字段')} -> "
                f"{display_name_map.get(relation['referenced_table_name'], '相关业务数据')}.{to_label_map.get(relation['referenced_column_name'], '关联字段')}"
            )
            docs.append(
                Document(
                    page_content=(
                        f"关系说明: {display_name_map.get(relation['table_name'], '相关业务数据')}.{from_label_map.get(relation['column_name'], '关联字段')} "
                        f"关联 {display_name_map.get(relation['referenced_table_name'], '相关业务数据')}.{to_label_map.get(relation['referenced_column_name'], '关联字段')}"
                    ),
                    metadata={
                        "source_type": "table_relation",
                        "table_name": relation["table_name"],
                        "referenced_table_name": relation["referenced_table_name"],
                        "display_name": "表关系说明",
                    },
                )
            )

        for table in tables:
            table_name = table["table_name"]
            display_name = display_name_map[table_name]
            columns = self.db.list_columns(table_name)
            column_label_map = {
                column["column_name"]: self._column_label(column)
                for column in columns
            }
            column_lines = []
            for column in columns:
                column_lines.append(
                    f"- {column_label_map[column['column_name']]} | 类型={column['column_type']} | 主键={column['column_key'] or '否'} | 注释={column['column_comment'] or '无'}"
                )

            relation_lines = fk_lines_by_table.get(table_name, [])
            table_doc_content = "\n".join(
                [
                    f"数据主题: {display_name}",
                    f"表说明: {table['table_comment'] or '无'}",
                    f"估计行数: {int(table['table_rows'] or 0)}",
                    "字段定义:",
                    *column_lines,
                    "表关系:",
                    *(relation_lines or ["- 无外键关系记录"]),
                ]
            )
            docs.append(
                Document(
                    page_content=table_doc_content,
                    metadata={
                        "source_type": "table_schema",
                        "table_name": table_name,
                        "display_name": display_name,
                        "table_comment": table["table_comment"] or "",
                    },
                )
            )
            docs.append(self._build_table_ddl_doc(table, columns, relation_lines))

            sample_rows = self.db.fetch_sample_rows(table_name, self.config.sample_rows_per_table)
            for index, row in enumerate(sample_rows):
                row_text = self._format_row(row, column_label_map)
                docs.append(
                    Document(
                        page_content=(
                            f"数据行样本 | 来源={display_name} | 序号={index + 1}\n"
                            f"{row_text}"
                        ),
                        metadata={
                            "source_type": "table_row",
                            "table_name": table_name,
                            "row_index": index,
                            "display_name": display_name,
                            "table_comment": table["table_comment"] or "",
                        },
                    )
                )

        return docs

    def _build_table_ddl_doc(
        self,
        table: dict[str, Any],
        columns: list[dict[str, Any]],
        relation_lines: list[str],
    ) -> Document:
        table_name = table["table_name"]
        display_name = self.db.get_table_display_name(table_name, table["table_comment"])
        ddl_lines = [f"CREATE TABLE `{table_name}` ("]
        for index, column in enumerate(columns):
            suffix = "," if index < len(columns) - 1 else ""
            comment_text = str(column["column_comment"] or "").replace("'", "’") or "无"
            ddl_lines.append(
                "  "
                f"`{column['column_name']}` {column['column_type']}"
                f"{' NOT NULL' if column['is_nullable'] == 'NO' else ''}"
                f"{' PRIMARY KEY' if column['column_key'] == 'PRI' else ''}"
                f"{' UNIQUE KEY' if column['column_key'] == 'UNI' else ''}"
                f" COMMENT '{comment_text}'{suffix}"
            )
        table_comment_text = str(table["table_comment"] or "").replace("'", "’") or "无"
        ddl_lines.append(f") COMMENT='{table_comment_text}';")
        if relation_lines:
            ddl_lines.append("关系提示:")
            ddl_lines.extend(f"- {line}" for line in relation_lines)
        return Document(
            page_content=(
                f"精确模式 | 业务主题={display_name}\n"
                + "\n".join(ddl_lines)
            ),
            metadata={
                "source_type": "table_ddl",
                "table_name": table_name,
                "display_name": display_name,
                "table_comment": table["table_comment"] or "",
            },
        )

    @staticmethod
    def _format_row(row: dict[str, Any], column_label_map: dict[str, str]) -> str:
        items = []
        for key, value in row.items():
            if value in (None, ""):
                continue
            if isinstance(value, (dict, list)):
                value_text = json.dumps(value, ensure_ascii=False)
            else:
                value_text = str(value)
            items.append(f"{column_label_map.get(key, '字段信息')}={value_text[:200]}")
        return "\n".join(items[:14]) or "空行"

    @staticmethod
    def _column_label(column: dict[str, Any]) -> str:
        comment = str(column.get("column_comment") or "").strip()
        if comment:
            return comment

        column_name = str(column.get("column_name") or "").lower()
        fallback_map = (
            ("name", "名称"),
            ("title", "标题"),
            ("scope", "经营范围"),
            ("industry", "行业"),
            ("address", "地址"),
            ("subdistrict", "街道"),
            ("district", "区域"),
            ("status", "状态"),
            ("type", "类型"),
            ("date", "日期"),
            ("time", "时间"),
            ("phone", "联系电话"),
            ("email", "邮箱"),
            ("patent", "专利信息"),
            ("company", "企业信息"),
            ("id", "标识"),
        )
        for pattern, label in fallback_map:
            if pattern in column_name:
                return label
        return "字段信息"
