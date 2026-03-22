from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore

from ..config import RAGConfig
from ..embeddings import DashScopeEmbeddings


class IndexConstructionModule:
    def __init__(self, config: RAGConfig):
        self.config = config
        self.snapshot_path = Path(config.snapshot_path)
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.embeddings = None
        self.vectorstore = None
        self.embedding_error: str | None = None

    def _setup_embeddings(self):
        if self.embeddings is not None:
            return self.embeddings

        if not os.getenv("DASHSCOPE_API_KEY"):
            return None

        self.embeddings = DashScopeEmbeddings(
            model=self.config.embedding_model,
            base_url=self.config.embedding_base_url,
            dimensions=self.config.embedding_dimensions,
        )
        return self.embeddings

    def build_vector_index(self, documents: list[Document]):
        self.embedding_error = None
        embeddings = self._setup_embeddings()
        if embeddings is None:
            self.vectorstore = None
            return None

        try:
            vectorstore = InMemoryVectorStore(embeddings)
            vectorstore.add_documents(documents)
            self.vectorstore = vectorstore
        except Exception as error:
            self.embedding_error = str(error)
            self.vectorstore = None
        return self.vectorstore

    def save_snapshot(self, documents: list[Document]) -> None:
        payload = {
            "snapshot_version": self.config.snapshot_version,
            "documents": [
                {"page_content": doc.page_content, "metadata": doc.metadata}
                for doc in documents
            ],
        }
        self.snapshot_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_snapshot(self) -> list[Document]:
        if not self.snapshot_path.exists():
            return []
        payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return []
        if payload.get("snapshot_version") != self.config.snapshot_version:
            return []
        documents = payload.get("documents")
        if not isinstance(documents, list):
            return []
        return [
            Document(page_content=item["page_content"], metadata=item.get("metadata", {}))
            for item in documents
        ]

    def load_or_build(self, documents: list[Document] | None = None) -> tuple[list[Document], Any]:
        docs = documents if documents is not None else self.load_snapshot()
        if documents is not None:
            self.save_snapshot(documents)
        self.build_vector_index(docs)
        return docs, self.vectorstore
