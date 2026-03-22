from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from typing import Any

import pymysql


TEXTUAL_TYPES = {
    "char",
    "varchar",
    "text",
    "tinytext",
    "mediumtext",
    "longtext",
    "json",
    "date",
    "datetime",
    "timestamp",
}

COLUMN_PRIORITY_PATTERNS = (
    "name",
    "title",
    "scope",
    "industry",
    "subdistrict",
    "address",
    "status",
    "type",
    "category",
    "tag",
    "comment",
    "desc",
    "content",
)

NAME_COLUMN_PATTERNS = (
    "company",
    "enterprise",
    "corp",
    "firm",
    "org",
    "unit",
    "institution",
    "applicant",
    "assignee",
    "owner",
    "vendor",
    "customer",
    "supplier",
    "name",
    "full_name",
)

ENTERPRISE_SUFFIXES = (
    "有限责任公司",
    "股份有限公司",
    "集团有限公司",
    "科技有限公司",
    "有限公司",
    "股份公司",
    "集团公司",
    "集团",
    "公司",
)


class DatabaseClient:
    def __init__(self, database: str | None = None):
        self.database = database or os.getenv("DB_NAME", "industrial_chain")
        self._columns_cache: dict[str, list[dict[str, Any]]] = {}
        self._table_comment_cache: dict[str, str] = {}

    @contextmanager
    def connect(self):
        conn = pymysql.connect(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=self.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
        try:
            yield conn
        finally:
            conn.close()

    def query(self, sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or [])
                return cursor.fetchall()

    def query_one(self, sql: str, params: list[Any] | tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def list_tables(self, exclude_tables: tuple[str, ...] = ()) -> list[dict[str, Any]]:
        rows = self.query(
            """
            SELECT
                TABLE_NAME AS table_name,
                TABLE_COMMENT AS table_comment,
                COALESCE(TABLE_ROWS, 0) AS table_rows
            FROM information_schema.tables
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME
            """,
            [self.database],
        )
        for row in rows:
            self._table_comment_cache[row["table_name"]] = row["table_comment"] or ""
        excluded = set(exclude_tables)
        return [row for row in rows if row["table_name"] not in excluded]

    def get_table_display_name(self, table_name: str, table_comment: str | None = None) -> str:
        comment = (table_comment or self._table_comment_cache.get(table_name) or "").strip()
        if comment:
            return comment
        return "相关业务数据"

    def list_columns(self, table_name: str) -> list[dict[str, Any]]:
        if table_name in self._columns_cache:
            return self._columns_cache[table_name]

        rows = self.query(
            """
            SELECT
                COLUMN_NAME AS column_name,
                DATA_TYPE AS data_type,
                COLUMN_TYPE AS column_type,
                IS_NULLABLE AS is_nullable,
                COLUMN_KEY AS column_key,
                COLUMN_COMMENT AS column_comment
            FROM information_schema.columns
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            [self.database, table_name],
        )
        self._columns_cache[table_name] = rows
        return rows

    def list_foreign_keys(self, exclude_tables: tuple[str, ...] = ()) -> list[dict[str, Any]]:
        rows = self.query(
            """
            SELECT
                TABLE_NAME AS table_name,
                COLUMN_NAME AS column_name,
                REFERENCED_TABLE_NAME AS referenced_table_name,
                REFERENCED_COLUMN_NAME AS referenced_column_name
            FROM information_schema.key_column_usage
            WHERE TABLE_SCHEMA = %s
              AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME, COLUMN_NAME
            """,
            [self.database],
        )
        excluded = set(exclude_tables)
        return [
            row
            for row in rows
            if row["table_name"] not in excluded and row["referenced_table_name"] not in excluded
        ]

    def get_primary_key(self, table_name: str) -> str | None:
        for column in self.list_columns(table_name):
            if column["column_key"] == "PRI":
                return column["column_name"]
        return None

    def get_textual_columns(self, table_name: str) -> list[str]:
        columns = []
        for column in self.list_columns(table_name):
            if column["data_type"] in TEXTUAL_TYPES:
                columns.append(column["column_name"])
        return self._prioritize_columns(columns)

    def get_order_by_column(self, table_name: str) -> str | None:
        column_names = {column["column_name"] for column in self.list_columns(table_name)}
        for candidate in ("updated_at", "update_time", "created_at", "create_time", "id"):
            if candidate in column_names:
                return candidate
        primary_key = self.get_primary_key(table_name)
        return primary_key

    def get_name_like_columns(self, table_name: str) -> list[str]:
        columns = self.get_textual_columns(table_name)
        matched = [column for column in columns if self._is_name_like_column(column)]
        return matched or columns[:4]

    def _quote_identifier(self, identifier: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_]+", identifier):
            raise ValueError(f"非法标识符: {identifier}")
        return f"`{identifier}`"

    def fetch_sample_rows(self, table_name: str, limit: int) -> list[dict[str, Any]]:
        columns = self.get_textual_columns(table_name)
        primary_key = self.get_primary_key(table_name)
        if primary_key and primary_key not in columns:
            columns = [primary_key, *columns]
        if not columns:
            return []

        select_cols = ", ".join(self._quote_identifier(column) for column in columns[:16])
        order_by = self.get_order_by_column(table_name)
        sql = f"SELECT {select_cols} FROM {self._quote_identifier(table_name)}"
        if order_by:
            sql += f" ORDER BY {self._quote_identifier(order_by)} DESC"
        sql += " LIMIT %s"
        return self.query(sql, [limit])

    def search_rows(self, table_name: str, query_text: str, limit: int) -> list[dict[str, Any]]:
        scored_rows = self._search_rows_with_scores(table_name, query_text, limit)
        return [row for _, row in scored_rows[:limit]]

    def probe_relevant_tables(
        self,
        query_text: str,
        exclude_tables: tuple[str, ...] = (),
        limit_tables: int = 6,
    ) -> list[str]:
        ranked_tables: list[tuple[float, str]] = []
        entity_candidates = self.extract_entity_candidates(query_text)
        for table in self.list_tables(exclude_tables=exclude_tables):
            table_name = table["table_name"]
            try:
                rows = self._search_rows_with_scores(table_name, query_text, 1)
            except Exception:
                rows = []
            if not rows:
                continue

            top_score = rows[0][0]
            if entity_candidates and self.get_name_like_columns(table_name):
                top_score += 5
            ranked_tables.append((top_score, table_name))

        ranked_tables.sort(key=lambda item: item[0], reverse=True)
        return [table_name for _, table_name in ranked_tables[:limit_tables]]

    def extract_entity_candidates(self, text: str) -> list[str]:
        candidates: list[str] = []
        patterns = [
            r"[\u4e00-\u9fffA-Za-z0-9（）()·\-_]{3,40}(?:公司|集团|研究院|研究所|医院|银行|中心|大学|事务所|基金会)",
            r"[A-Za-z0-9\u4e00-\u9fff（）()·\-_]{4,40}",
        ]

        for pattern in patterns[:1]:
            for match in re.findall(pattern, text):
                cleaned = self._clean_entity_candidate(match)
                if len(cleaned) >= 3:
                    candidates.append(cleaned)

        if not candidates:
            for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9_]{4,40}", text):
                if any(suffix in token for suffix in ENTERPRISE_SUFFIXES):
                    candidates.append(self._clean_entity_candidate(token))

        seen: set[str] = set()
        result: list[str] = []
        for candidate in candidates:
            normalized = self._normalize_company_name(candidate)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(candidate)
        return result[:4]

    def _search_rows_with_scores(
        self,
        table_name: str,
        query_text: str,
        limit: int,
    ) -> list[tuple[float, dict[str, Any]]]:
        columns = self.get_textual_columns(table_name)
        primary_key = self.get_primary_key(table_name)
        if primary_key and primary_key not in columns:
            columns = [primary_key, *columns]
        if not columns:
            return []

        query_tokens = self._tokenize(query_text)
        entity_candidates = self.extract_entity_candidates(query_text)
        normalized_entities = [self._normalize_company_name(entity) for entity in entity_candidates]
        select_cols = ", ".join(self._quote_identifier(column) for column in columns[:14])
        sql = f"SELECT {select_cols} FROM {self._quote_identifier(table_name)}"
        params: list[Any] = []
        searchable_columns = columns[:20]
        name_like_columns = self.get_name_like_columns(table_name)[:8]
        where_clauses: list[str] = []

        if query_tokens:
            for token in query_tokens:
                like_value = f"%{token}%"
                field_clauses = [f"COALESCE({self._quote_identifier(column)}, '') LIKE %s" for column in searchable_columns]
                where_clauses.append("(" + " OR ".join(field_clauses) + ")")
                params.extend([like_value] * len(searchable_columns))

        for entity in entity_candidates:
            like_value = f"%{entity}%"
            field_clauses = [f"COALESCE({self._quote_identifier(column)}, '') LIKE %s" for column in name_like_columns]
            if field_clauses:
                where_clauses.append("(" + " OR ".join(field_clauses) + ")")
                params.extend([like_value] * len(field_clauses))

        if where_clauses:
            sql += " WHERE " + " OR ".join(where_clauses)

        order_by = self.get_order_by_column(table_name)
        if order_by:
            sql += f" ORDER BY {self._quote_identifier(order_by)} DESC"
        sql += " LIMIT %s"
        params.append(max(limit * 20, 40))
        rows = self.query(sql, params)

        if not query_tokens and not entity_candidates:
            return [(1.0, row) for row in rows[:limit]]

        scored_rows: list[tuple[int, dict[str, Any]]] = []
        for row in rows:
            row_text = " ".join(str(value) for value in row.values() if value not in (None, ""))
            normalized_row_text = self._normalize_text(row_text)
            score = 0
            for token in query_tokens:
                lowered = token.lower()
                score += row_text.lower().count(lowered)
                score += normalized_row_text.count(self._normalize_text(token)) * 2

            for column_name, value in row.items():
                if value in (None, ""):
                    continue
                value_text = str(value)
                normalized_value = self._normalize_text(value_text)
                normalized_company_value = self._normalize_company_name(value_text)
                if column_name in name_like_columns:
                    for entity in entity_candidates:
                        if entity in value_text:
                            score += 25
                    for normalized_entity in normalized_entities:
                        if not normalized_entity:
                            continue
                        if normalized_entity == normalized_company_value:
                            score += 80
                        elif normalized_entity and normalized_entity in normalized_company_value:
                            score += 40
                        elif normalized_company_value and normalized_company_value in normalized_entity:
                            score += 20
                else:
                    for normalized_entity in normalized_entities:
                        if normalized_entity and normalized_entity in normalized_value:
                            score += 8

            if query_text.strip() and query_text.strip().lower() in row_text.lower():
                score += 12
            if score > 0:
                scored_rows.append((score, row))

        scored_rows.sort(key=lambda item: item[0], reverse=True)
        return scored_rows[:limit]

    def ensure_chat_tables(self) -> None:
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS `rag_chat_session` (
                      `session_id` VARCHAR(64) NOT NULL COMMENT 'RAG 对话会话 ID',
                      `user_id` BIGINT NOT NULL COMMENT '所属用户 ID',
                      `title` VARCHAR(255) DEFAULT NULL COMMENT '会话标题',
                      `is_pinned` TINYINT NOT NULL DEFAULT 0 COMMENT '是否置顶（1:是，0:否）',
                      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                      `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                      PRIMARY KEY (`session_id`),
                      KEY `idx_rag_chat_session_updated_at` (`updated_at`),
                      KEY `idx_rag_chat_session_user_updated_at` (`user_id`, `updated_at`),
                      KEY `idx_rag_chat_session_pin_updated_at` (`is_pinned`, `updated_at`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RAG 对话会话表'
                    """
                )
                user_id_exists = cursor.execute(
                    """
                    SHOW COLUMNS FROM `rag_chat_session` LIKE 'user_id'
                    """
                )
                if not user_id_exists:
                    cursor.execute(
                        """
                        ALTER TABLE `rag_chat_session`
                        ADD COLUMN `user_id` BIGINT DEFAULT NULL COMMENT '所属用户 ID'
                        AFTER `session_id`
                        """
                    )
                user_id_column = self.query_one(
                    """
                    SELECT IS_NULLABLE AS is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                      AND table_name = 'rag_chat_session'
                      AND column_name = 'user_id'
                    """
                )
                has_null_user_id = self.query_one(
                    """
                    SELECT 1 AS has_null_user_id
                    FROM `rag_chat_session`
                    WHERE `user_id` IS NULL
                    LIMIT 1
                    """
                )
                if user_id_column and user_id_column["is_nullable"] == "YES" and not has_null_user_id:
                    cursor.execute(
                        """
                        ALTER TABLE `rag_chat_session`
                        MODIFY COLUMN `user_id` BIGINT NOT NULL COMMENT '所属用户 ID'
                        """
                    )
                column_exists = cursor.execute(
                    """
                    SHOW COLUMNS FROM `rag_chat_session` LIKE 'is_pinned'
                    """
                )
                if not column_exists:
                    cursor.execute(
                        """
                        ALTER TABLE `rag_chat_session`
                        ADD COLUMN `is_pinned` TINYINT NOT NULL DEFAULT 0 COMMENT '是否置顶（1:是，0:否）'
                        AFTER `title`
                        """
                    )
                index_exists = cursor.execute(
                    """
                    SHOW INDEX FROM `rag_chat_session`
                    WHERE Key_name = 'idx_rag_chat_session_pin_updated_at'
                    """
                )
                if not index_exists:
                    cursor.execute(
                        """
                        CREATE INDEX `idx_rag_chat_session_pin_updated_at`
                        ON `rag_chat_session` (`is_pinned`, `updated_at`)
                        """
                    )
                user_index_exists = cursor.execute(
                    """
                    SHOW INDEX FROM `rag_chat_session`
                    WHERE Key_name = 'idx_rag_chat_session_user_updated_at'
                    """
                )
                if not user_index_exists:
                    cursor.execute(
                        """
                        CREATE INDEX `idx_rag_chat_session_user_updated_at`
                        ON `rag_chat_session` (`user_id`, `updated_at`)
                        """
                    )
                fk_exists = cursor.execute(
                    """
                    SELECT 1
                    FROM information_schema.referential_constraints
                    WHERE constraint_schema = DATABASE()
                      AND table_name = 'rag_chat_session'
                      AND constraint_name = 'fk_rag_chat_session_user'
                    """
                )
                if not fk_exists:
                    try:
                        cursor.execute(
                            """
                            ALTER TABLE `rag_chat_session`
                            ADD CONSTRAINT `fk_rag_chat_session_user`
                            FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
                            ON DELETE CASCADE
                            """
                        )
                    except Exception:
                        pass
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS `rag_chat_message` (
                      `message_id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '消息主键',
                      `session_id` VARCHAR(64) NOT NULL COMMENT '所属会话 ID',
                      `role` VARCHAR(16) NOT NULL COMMENT '消息角色(user/assistant/system)',
                      `content` LONGTEXT NOT NULL COMMENT '消息正文',
                      `retrieval_metadata` JSON DEFAULT NULL COMMENT '检索元数据',
                      `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                      PRIMARY KEY (`message_id`),
                      KEY `idx_rag_chat_message_session_created_at` (`session_id`, `created_at`),
                      CONSTRAINT `fk_rag_chat_message_session`
                        FOREIGN KEY (`session_id`) REFERENCES `rag_chat_session` (`session_id`)
                        ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='RAG 对话消息表'
                    """
                )

    def save_chat_turn(
        self,
        user_id: int,
        session_id: str,
        user_content: str,
        assistant_content: str,
        retrieval_metadata: dict[str, Any],
    ) -> None:
        with self.connect() as conn:
            with conn.cursor() as cursor:
                existing_session = self.query_one(
                    """
                    SELECT user_id
                    FROM `rag_chat_session`
                    WHERE `session_id` = %s
                    """,
                    [session_id],
                )
                if existing_session and existing_session.get("user_id") not in {None, user_id}:
                    raise ValueError("会话不属于当前用户")
                cursor.execute(
                    """
                    INSERT INTO `rag_chat_session` (`session_id`, `user_id`, `title`)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      `user_id` = VALUES(`user_id`),
                      `updated_at` = CURRENT_TIMESTAMP
                    """,
                    [session_id, user_id, user_content[:255] or "新对话"],
                )
                cursor.execute(
                    """
                    INSERT INTO `rag_chat_message` (`session_id`, `role`, `content`)
                    VALUES (%s, 'user', %s)
                    """,
                    [session_id, user_content],
                )
                cursor.execute(
                    """
                    INSERT INTO `rag_chat_message` (`session_id`, `role`, `content`, `retrieval_metadata`)
                    VALUES (%s, 'assistant', %s, %s)
                    """,
                    [session_id, assistant_content, json.dumps(retrieval_metadata, ensure_ascii=False)],
                )

    def list_chat_sessions(self, user_id: int) -> list[dict[str, Any]]:
        return self.query(
            """
            SELECT session_id, title, is_pinned, created_at AS create_time, updated_at AS update_time
            FROM rag_chat_session
            WHERE user_id = %s
            ORDER BY is_pinned DESC, updated_at DESC
            """,
            [user_id],
        )

    def get_chat_messages(self, session_id: str, user_id: int) -> list[dict[str, Any]]:
        return self.query(
            """
            SELECT m.role, m.content, m.created_at AS create_time, m.retrieval_metadata
            FROM rag_chat_message m
            INNER JOIN rag_chat_session s ON s.session_id = m.session_id
            WHERE m.session_id = %s
              AND s.user_id = %s
            ORDER BY message_id ASC
            """,
            [session_id, user_id],
        )

    def delete_chat_session(self, session_id: str, user_id: int) -> int:
        with self.connect() as conn:
            with conn.cursor() as cursor:
                affected = cursor.execute(
                    """
                    DELETE FROM rag_chat_session
                    WHERE session_id = %s
                      AND user_id = %s
                    """,
                    [session_id, user_id],
                )
                return affected

    def clear_chat_sessions(self, user_id: int) -> int:
        with self.connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM rag_chat_session WHERE user_id = %s", [user_id])
                return cursor.rowcount

    def update_chat_session(
        self,
        session_id: str,
        user_id: int,
        title: str | None = None,
        is_pinned: bool | None = None,
    ) -> bool:
        updates: list[str] = []
        params: list[Any] = []
        if title is not None:
            updates.append("`title` = %s")
            params.append(title[:255] or "未命名对话")
        if is_pinned is not None:
            updates.append("`is_pinned` = %s")
            params.append(1 if is_pinned else 0)
        if not updates:
            return False

        updates.append("`updated_at` = CURRENT_TIMESTAMP")
        params.append(session_id)
        with self.connect() as conn:
            with conn.cursor() as cursor:
                affected = cursor.execute(
                    f"""
                    UPDATE `rag_chat_session`
                    SET {", ".join(updates)}
                    WHERE `session_id` = %s
                      AND `user_id` = %s
                    """,
                    [*params, user_id],
                )
                return affected > 0

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        raw_tokens = re.findall(r"[A-Za-z0-9_]{2,}|[\u4e00-\u9fff]+", text)
        seen: set[str] = set()
        result: list[str] = []
        for token in raw_tokens:
            if re.fullmatch(r"[\u4e00-\u9fff]+", token):
                grams: list[str] = [token]
                for size in (4, 3, 2):
                    if len(token) < size:
                        continue
                    for index in range(len(token) - size + 1):
                        grams.append(token[index:index + size])
                candidates = grams
            else:
                candidates = [token]

            for candidate in candidates:
                key = candidate.lower()
                if key in seen:
                    continue
                seen.add(key)
                result.append(candidate)
        return result[:12]

    @staticmethod
    def _prioritize_columns(columns: list[str]) -> list[str]:
        def score(column_name: str) -> tuple[int, str]:
            lowered = column_name.lower()
            priority = 100
            for index, pattern in enumerate(COLUMN_PRIORITY_PATTERNS):
                if pattern in lowered:
                    priority = index
                    break
            return priority, lowered

        return sorted(columns, key=score)

    @staticmethod
    def _is_name_like_column(column_name: str) -> bool:
        lowered = column_name.lower()
        return any(pattern in lowered for pattern in NAME_COLUMN_PATTERNS)

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = str(text).lower()
        return re.sub(r"[\s\W_]+", "", lowered, flags=re.UNICODE)

    @classmethod
    def _normalize_company_name(cls, text: str) -> str:
        normalized = cls._normalize_text(text)
        for suffix in ENTERPRISE_SUFFIXES:
            suffix_normalized = cls._normalize_text(suffix)
            if normalized.endswith(suffix_normalized) and len(normalized) > len(suffix_normalized) + 1:
                normalized = normalized[: -len(suffix_normalized)]
                break
        return normalized

    @staticmethod
    def _clean_entity_candidate(text: str) -> str:
        cleaned = text.strip("，。！？；：、（）()[]【】\"' ")
        cleaned = re.sub(
            r"^(请问|请帮我|请帮忙|请做一下|请做个|请分析一下|请分析|帮我|帮忙|做一下|做个|看一下|查一下|查查|介绍一下|想了解|了解一下)+",
            "",
            cleaned,
        )
        return cleaned.strip()
