from __future__ import annotations

import re
from collections import defaultdict

from langchain_core.documents import Document


class RetrievalOptimizationModule:
    def __init__(self, documents: list[Document], vectorstore):
        self.documents = documents
        self.vectorstore = vectorstore

    def hybrid_search(self, query: str, top_k: int = 8) -> list[Document]:
        lexical_docs = self.lexical_search(query, top_k=top_k * 2)
        vector_docs = self.vector_search(query, top_k=top_k * 2)
        return self._rrf_merge(lexical_docs, vector_docs, top_k=top_k)

    def lexical_search(self, query: str, top_k: int = 8) -> list[Document]:
        tokens = self._tokenize(query)
        normalized_query = query.lower()
        normalized_compact_query = self._normalize_text(query)
        if not tokens:
            return self.documents[:top_k]

        scored_docs: list[tuple[float, Document]] = []
        for doc in self.documents:
            content = doc.page_content.lower()
            table_name = str(doc.metadata.get("table_name", "")).lower()
            display_name = str(doc.metadata.get("display_name", "")).lower()
            table_comment = str(doc.metadata.get("table_comment", "")).lower()
            source_type = str(doc.metadata.get("source_type", "")).lower()
            normalized_content = self._normalize_text(doc.page_content)
            normalized_display_name = self._normalize_text(display_name)
            score = 0.0
            for token in tokens:
                token_lower = token.lower()
                score += content.count(token_lower)
                score += display_name.count(token_lower) * 3
                score += table_comment.count(token_lower) * 2
                normalized_token = self._normalize_text(token)
                if normalized_token:
                    score += normalized_content.count(normalized_token) * 1.5
                    score += normalized_display_name.count(normalized_token) * 4
                if token_lower in table_name:
                    score += 3
                if token_lower in source_type:
                    score += 1
            if table_name and table_name in normalized_query:
                score += 25
            if normalized_compact_query and normalized_compact_query in normalized_content:
                score += 18
            if score > 0:
                scored_docs.append((score, doc))

        scored_docs.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored_docs[:top_k]]

    def vector_search(self, query: str, top_k: int = 8) -> list[Document]:
        if self.vectorstore is None:
            return []
        return self.vectorstore.similarity_search(query, k=top_k)

    def select_candidate_tables(self, documents: list[Document], max_tables: int = 4) -> list[str]:
        table_scores: dict[str, float] = defaultdict(float)
        for rank, doc in enumerate(documents):
            table_name = doc.metadata.get("table_name")
            if not table_name or table_name == "__database__":
                continue
            table_scores[table_name] += 1 / (rank + 1)
        ranked = sorted(table_scores.items(), key=lambda item: item[1], reverse=True)
        return [table_name for table_name, _ in ranked[:max_tables]]

    def _rrf_merge(self, lexical_docs: list[Document], vector_docs: list[Document], top_k: int) -> list[Document]:
        if not vector_docs:
            return lexical_docs[:top_k]

        scores: dict[int, float] = defaultdict(float)
        docs_by_id: dict[int, Document] = {}
        for source_docs in (lexical_docs, vector_docs):
            for rank, doc in enumerate(source_docs):
                doc_id = hash((doc.page_content, tuple(sorted(doc.metadata.items()))))
                docs_by_id[doc_id] = doc
                scores[doc_id] += 1 / (60 + rank + 1)
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [docs_by_id[doc_id] for doc_id, _ in ranked[:top_k]]

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
    def _normalize_text(text: str) -> str:
        return re.sub(r"[\s\W_]+", "", str(text).lower(), flags=re.UNICODE)
