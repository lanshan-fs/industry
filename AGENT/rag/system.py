from __future__ import annotations

import json
from threading import Lock
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .config import DEFAULT_CONFIG, RAGConfig
from .db import DatabaseClient
from .rag_modules.data_preparation import DataPreparationModule
from .rag_modules.generation_integration import GenerationIntegrationModule
from .rag_modules.index_construction import IndexConstructionModule
from .rag_modules.retrieval_optimization import RetrievalOptimizationModule


class GraphState(TypedDict):
    question: str
    chat_history: list[dict[str, str]]
    rewritten_query: str
    task_type: str
    task_label: str
    retrieved_docs: list[Any]
    candidate_tables: list[str]
    live_rows: dict[str, list[dict[str, Any]]]
    answer: str
    retrieval_metadata: dict[str, Any]


class DatabaseRAGSystem:
    def __init__(self, config: RAGConfig = DEFAULT_CONFIG):
        self.config = config
        self.db = DatabaseClient(config.db_name)
        self.data_module = DataPreparationModule(self.db, config)
        self.index_module = IndexConstructionModule(config)
        self.generation_module = GenerationIntegrationModule(config)
        self.retrieval_module: RetrievalOptimizationModule | None = None
        self.documents = []
        self._lock = Lock()
        self._initialized = False
        self.graph = self._build_graph()

    def initialize(self, force_rebuild: bool = False) -> None:
        with self._lock:
            self.db.ensure_chat_tables()
            if self._initialized and not force_rebuild:
                return

            if force_rebuild:
                self.documents = self.data_module.prepare_documents()
                self.documents, vectorstore = self.index_module.load_or_build(self.documents)
            else:
                snapshot_docs = self.index_module.load_snapshot()
                if snapshot_docs:
                    self.documents, vectorstore = self.index_module.load_or_build(snapshot_docs)
                else:
                    self.documents = self.data_module.prepare_documents()
                    self.documents, vectorstore = self.index_module.load_or_build(self.documents)

            self.retrieval_module = RetrievalOptimizationModule(self.documents, vectorstore)
            self._initialized = True

    def rebuild_index(self) -> dict[str, Any]:
        self.initialize(force_rebuild=True)
        return self.get_health()

    def get_health(self) -> dict[str, Any]:
        return {
            "initialized": self._initialized,
            "document_count": len(self.documents),
            "vector_enabled": self.index_module.vectorstore is not None,
            "embedding_error": self.index_module.embedding_error,
            "generation": self.generation_module.get_health(),
        }

    def ask(self, question: str, chat_history: list[dict[str, str]]) -> dict[str, Any]:
        self.initialize()
        return self.graph.invoke(
            {
                "question": question,
                "chat_history": chat_history,
                "rewritten_query": "",
                "task_type": "",
                "task_label": "",
                "retrieved_docs": [],
                "candidate_tables": [],
                "live_rows": {},
                "answer": "",
                "retrieval_metadata": {},
            }
        )

    def prepare_context(self, question: str, chat_history: list[dict[str, str]]) -> GraphState:
        self.initialize()
        state: GraphState = {
            "question": question,
            "chat_history": chat_history,
            "rewritten_query": "",
            "task_type": "",
            "task_label": "",
            "retrieved_docs": [],
            "candidate_tables": [],
            "live_rows": {},
            "answer": "",
            "retrieval_metadata": {},
        }
        state = self._rewrite_query_node(state)
        state = self._route_task_node(state)
        state = self._retrieve_context_node(state)
        return state

    def stream_answer(self, question: str, chat_history: list[dict[str, str]]):
        state = self.prepare_context(question, chat_history)
        stream = self.generation_module.stream_answer(
            question=state["question"],
            rewritten_query=state["rewritten_query"],
            task_type=state["task_type"],
            task_label=state["task_label"],
            chat_history=state["chat_history"],
            retrieved_docs=state["retrieved_docs"],
            live_rows=state["live_rows"],
        )
        return state, stream

    def save_chat_turn(
        self,
        user_id: int,
        session_id: str,
        user_content: str,
        assistant_content: str,
        retrieval_metadata: dict[str, Any],
    ) -> None:
        self.db.save_chat_turn(user_id, session_id, user_content, assistant_content, retrieval_metadata)

    def list_sessions(self, user_id: int) -> list[dict[str, Any]]:
        self.db.ensure_chat_tables()
        return self.db.list_chat_sessions(user_id)

    def get_messages(self, session_id: str, user_id: int) -> list[dict[str, Any]]:
        self.db.ensure_chat_tables()
        return self.db.get_chat_messages(session_id, user_id)

    def delete_session(self, session_id: str, user_id: int) -> bool:
        self.db.ensure_chat_tables()
        return self.db.delete_chat_session(session_id, user_id) > 0

    def clear_sessions(self, user_id: int) -> int:
        self.db.ensure_chat_tables()
        return self.db.clear_chat_sessions(user_id)

    def update_session(
        self,
        session_id: str,
        user_id: int,
        title: str | None = None,
        is_pinned: bool | None = None,
    ) -> bool:
        self.db.ensure_chat_tables()
        return self.db.update_chat_session(session_id, user_id, title=title, is_pinned=is_pinned)

    def _build_graph(self):
        graph = StateGraph(GraphState)
        graph.add_node("rewrite_query", self._rewrite_query_node)
        graph.add_node("route_task", self._route_task_node)
        graph.add_node("retrieve_context", self._retrieve_context_node)
        graph.add_node("generate_answer", self._generate_answer_node)
        graph.add_edge(START, "rewrite_query")
        graph.add_edge("rewrite_query", "route_task")
        graph.add_edge("route_task", "retrieve_context")
        graph.add_edge("retrieve_context", "generate_answer")
        graph.add_edge("generate_answer", END)
        return graph.compile()

    def _rewrite_query_node(self, state: GraphState) -> GraphState:
        rewritten_query = self.generation_module.rewrite_query(state["question"], state["chat_history"])
        return {
            **state,
            "rewritten_query": rewritten_query,
        }

    def _route_task_node(self, state: GraphState) -> GraphState:
        task = self.generation_module.classify_task(
            state["question"],
            state["rewritten_query"],
            state["chat_history"],
        )
        return {
            **state,
            "task_type": task["type"],
            "task_label": task["label"],
        }

    def _retrieve_context_node(self, state: GraphState) -> GraphState:
        assert self.retrieval_module is not None
        retrieved_docs = self.retrieval_module.hybrid_search(
            state["rewritten_query"] or state["question"],
            top_k=self.config.top_k_docs,
        )
        indexed_tables = self.retrieval_module.select_candidate_tables(
            retrieved_docs,
            max_tables=self.config.max_candidate_tables,
        )
        entity_candidates = self.db.extract_entity_candidates(state["question"])
        probed_tables = self.db.probe_relevant_tables(
            state["question"],
            exclude_tables=self.config.exclude_tables,
            limit_tables=self.config.max_candidate_tables,
        )
        entity_tables: list[str] = []
        for entity in entity_candidates:
            for table_name in self.db.probe_relevant_tables(
                entity,
                exclude_tables=self.config.exclude_tables,
                limit_tables=self.config.max_candidate_tables,
            ):
                if table_name not in entity_tables:
                    entity_tables.append(table_name)
        candidate_tables = []
        for table_name in [*indexed_tables, *entity_tables, *probed_tables]:
            if table_name not in candidate_tables:
                candidate_tables.append(table_name)
        candidate_tables = candidate_tables[: self.config.max_candidate_tables]
        live_rows: dict[str, list[dict[str, Any]]] = {}
        for table_name in candidate_tables:
            rows: list[dict[str, Any]] = []
            seen_rows: set[str] = set()
            for query_text in [*entity_candidates, state["question"], state["rewritten_query"]]:
                if not query_text:
                    continue
                for row in self.db.search_rows(table_name, query_text, self.config.live_rows_per_table):
                    key = json.dumps(row, ensure_ascii=False, sort_keys=True, default=str)
                    if key in seen_rows:
                        continue
                    seen_rows.add(key)
                    rows.append(row)
                    if len(rows) >= self.config.live_rows_per_table:
                        break
                if len(rows) >= self.config.live_rows_per_table:
                    break
            if rows:
                display_name = self.db.get_table_display_name(table_name)
                live_rows.setdefault(display_name, []).extend(rows)

        context_docs = self._augment_context_docs(
            retrieved_docs=retrieved_docs,
            candidate_tables=candidate_tables,
            task_type=state["task_type"],
        )

        retrieval_metadata = {
            "task_type": state["task_type"],
            "task_label": state["task_label"],
            "rewritten_query": state["rewritten_query"],
            "entity_candidates": entity_candidates,
            "indexed_sources": [self.db.get_table_display_name(table_name) for table_name in indexed_tables],
            "entity_sources": [self.db.get_table_display_name(table_name) for table_name in entity_tables],
            "probed_sources": [self.db.get_table_display_name(table_name) for table_name in probed_tables],
            "candidate_sources": [self.db.get_table_display_name(table_name) for table_name in candidate_tables],
            "retrieved_docs": [
                {
                    "source_name": doc.metadata.get("display_name") or doc.metadata.get("table_comment") or self.db.get_table_display_name(str(doc.metadata.get("table_name") or "")),
                    "source_type": doc.metadata.get("source_type"),
                    "preview": doc.page_content[:240],
                }
                for doc in context_docs[: self.config.max_context_docs]
            ],
            "live_rows_sources": {source_name: len(rows) for source_name, rows in live_rows.items()},
        }
        return {
            **state,
            "retrieved_docs": context_docs[: self.config.max_context_docs],
            "candidate_tables": candidate_tables,
            "live_rows": dict(list(live_rows.items())[: self.config.max_context_rows]),
            "retrieval_metadata": retrieval_metadata,
        }

    def _generate_answer_node(self, state: GraphState) -> GraphState:
        answer = self.generation_module.generate_answer(
            question=state["question"],
            rewritten_query=state["rewritten_query"],
            task_type=state["task_type"],
            task_label=state["task_label"],
            chat_history=state["chat_history"],
            retrieved_docs=state["retrieved_docs"],
            live_rows=state["live_rows"],
        )
        return {**state, "answer": answer}

    def _augment_context_docs(
        self,
        retrieved_docs: list[Any],
        candidate_tables: list[str],
        task_type: str,
    ) -> list[Any]:
        selected: list[Any] = []
        seen: set[tuple[str, str, str]] = set()

        def add(doc: Any) -> None:
            key = (
                str(doc.metadata.get("source_type") or ""),
                str(doc.metadata.get("table_name") or ""),
                doc.page_content[:200],
            )
            if key in seen:
                return
            seen.add(key)
            selected.append(doc)

        for doc in self.documents:
            source_type = str(doc.metadata.get("source_type") or "")
            table_name = str(doc.metadata.get("table_name") or "")
            if source_type == "task_definition" and str(doc.metadata.get("task_type") or "") == task_type:
                add(doc)
            elif source_type == "database_overview":
                add(doc)
            elif table_name in candidate_tables and source_type in {"table_ddl", "table_schema", "table_relation"}:
                add(doc)

        for doc in retrieved_docs:
            add(doc)

        return selected
