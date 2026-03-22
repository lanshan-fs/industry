from __future__ import annotations

import os
from typing import Iterable

from langchain_core.embeddings import Embeddings
from openai import OpenAI


class DashScopeEmbeddings(Embeddings):
    def __init__(
        self,
        model: str = "text-embedding-v3",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        dimensions: int | None = 1024,
        batch_size: int = 10,
    ):
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("缺少 DASHSCOPE_API_KEY，无法初始化 embedding 客户端")

        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        normalized = [self._normalize_text(text) for text in texts]
        vectors: list[list[float]] = []
        for batch in self._chunk(normalized, self.batch_size):
            response = self._create_embedding(batch)
            vectors.extend(item.embedding for item in response.data)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        response = self._create_embedding(self._normalize_text(text))
        return response.data[0].embedding

    def _create_embedding(self, input_value: str | list[str]):
        payload = {
            "model": self.model,
            "input": input_value,
            "encoding_format": "float",
        }
        if self.dimensions:
            payload["dimensions"] = self.dimensions

        try:
            return self.client.embeddings.create(**payload)
        except Exception:
            if "dimensions" not in payload:
                raise
            payload.pop("dimensions", None)
            return self.client.embeddings.create(**payload)

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = (text or "").strip()[:8000]
        return normalized or "空白内容"

    @staticmethod
    def _chunk(items: list[str], size: int) -> Iterable[list[str]]:
        for index in range(0, len(items), size):
            yield items[index:index + size]
