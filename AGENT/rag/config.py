from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RAGConfig:
    db_name: str = os.getenv("DB_NAME", "industrial_chain")
    data_dir: Path = Path(__file__).resolve().parents[1] / "data"
    snapshot_path: Path = Path(__file__).resolve().parents[1] / "data" / "rag_index" / "documents.json"
    snapshot_version: str = os.getenv("RAG_SNAPSHOT_VERSION", "2026-03-20-rag-v2")
    llm_model: str = os.getenv("QWEN_MODEL", "qwen-plus")
    llm_base_url: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    primary_llm_enabled: bool = os.getenv("PRIMARY_LLM_ENABLED", "true").lower() == "true"
    primary_llm_model: str = os.getenv("PRIMARY_LLM_MODEL", "Qwen3-14B_sft_merged")
    primary_llm_base_url: str = os.getenv("PRIMARY_LLM_BASE_URL", "http://127.0.0.1:6006/v1")
    primary_llm_api_key: str = os.getenv("PRIMARY_LLM_API_KEY", "EMPTY")
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    ssh_command: str = os.getenv("SSH", "").replace("\r", "").strip()
    ssh_password: str = os.getenv("PASSWORD", "").replace("\r", "").strip()
    autodl_tunnel_enabled: bool = os.getenv("AUTODL_TUNNEL_ENABLED", "true").lower() == "true"
    autodl_tunnel_local_host: str = os.getenv("AUTODL_TUNNEL_LOCAL_HOST", "127.0.0.1")
    autodl_tunnel_local_port: int = int(os.getenv("AUTODL_TUNNEL_LOCAL_PORT", "6006"))
    autodl_tunnel_remote_host: str = os.getenv("AUTODL_TUNNEL_REMOTE_HOST", "127.0.0.1")
    autodl_tunnel_remote_port: int = int(os.getenv("AUTODL_TUNNEL_REMOTE_PORT", "6006"))
    autodl_tunnel_startup_timeout_seconds: int = int(os.getenv("AUTODL_TUNNEL_STARTUP_TIMEOUT_SECONDS", "12"))
    embedding_model: str = os.getenv("QWEN_EMBEDDING_MODEL", "text-embedding-v3")
    embedding_base_url: str = os.getenv("QWEN_EMBEDDING_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    embedding_dimensions: int = int(os.getenv("QWEN_EMBEDDING_DIMENSIONS", "1024"))
    sample_rows_per_table: int = int(os.getenv("RAG_SAMPLE_ROWS_PER_TABLE", "8"))
    live_rows_per_table: int = int(os.getenv("RAG_LIVE_ROWS_PER_TABLE", "3"))
    top_k_docs: int = int(os.getenv("RAG_TOP_K_DOCS", "8"))
    max_candidate_tables: int = int(os.getenv("RAG_MAX_CANDIDATE_TABLES", "4"))
    max_context_docs: int = int(os.getenv("RAG_MAX_CONTEXT_DOCS", "10"))
    max_context_rows: int = int(os.getenv("RAG_MAX_CONTEXT_ROWS", "12"))
    exclude_tables: tuple[str, ...] = (
        "rag_chat_session",
        "rag_chat_message",
    )


DEFAULT_CONFIG = RAGConfig()
