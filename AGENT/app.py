from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

from AGENT.rag import DEFAULT_CONFIG, DatabaseRAGSystem

APP_NAME = "industrial-chain-rag"
rag_system = DatabaseRAGSystem(DEFAULT_CONFIG)
app = FastAPI(title=APP_NAME)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    sessionId: str | None = None
    userId: int


class SessionUpdateRequest(BaseModel):
    title: str | None = None
    isPinned: bool | None = None


def _stream_event(payload: dict):
    return json.dumps(payload, ensure_ascii=False) + "\n"


@app.get("/health")
def health():
    return {
        "success": True,
        "service": APP_NAME,
        **rag_system.get_health(),
    }


@app.post("/admin/rebuild-index")
def rebuild_index():
    return {"success": True, "data": rag_system.rebuild_index()}


@app.post("/chat")
def chat(request: ChatRequest):
    user_messages = [message for message in request.messages if message.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="至少需要一条 user 消息")

    session_id = request.sessionId or str(uuid4())
    question = user_messages[-1].content.strip()
    chat_history = [
        {"role": message.role, "content": message.content}
        for message in request.messages[:-1]
        if message.role in {"user", "assistant", "system"}
    ]

    result = rag_system.ask(question, chat_history)
    rag_system.save_chat_turn(
        user_id=request.userId,
        session_id=session_id,
        user_content=question,
        assistant_content=result["answer"],
        retrieval_metadata=result["retrieval_metadata"],
    )
    return {
        "success": True,
        "data": result["answer"],
        "sessionId": session_id,
        "retrieval": result["retrieval_metadata"],
    }


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    user_messages = [message for message in request.messages if message.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="至少需要一条 user 消息")

    session_id = request.sessionId or str(uuid4())
    question = user_messages[-1].content.strip()
    chat_history = [
        {"role": message.role, "content": message.content}
        for message in request.messages[:-1]
        if message.role in {"user", "assistant", "system"}
    ]

    def event_stream():
        answer_parts: list[str] = []
        try:
            yield _stream_event({"type": "status", "stage": "understand", "content": "正在理解问题"})
            rag_system.initialize()
            state = {
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
            state = rag_system._rewrite_query_node(state)
            state = rag_system._route_task_node(state)
            yield _stream_event(
                {
                    "type": "status",
                    "stage": "rewrite",
                    "content": "已识别分析目标",
                }
            )
            yield _stream_event({"type": "status", "stage": "retrieve", "content": "正在整理相关信息"})
            state = rag_system._retrieve_context_node(state)
            yield _stream_event(
                {
                    "type": "status",
                    "stage": "retrieve_done",
                    "content": "已完成信息整理",
                }
            )
            yield _stream_event(
                {
                    "type": "meta",
                    "sessionId": session_id,
                }
            )
            yield _stream_event({"type": "status", "stage": "generate", "content": "正在组织回答"})
            stream = rag_system.generation_module.stream_answer(
                question=state["question"],
                rewritten_query=state["rewritten_query"],
                task_type=state["task_type"],
                task_label=state["task_label"],
                chat_history=state["chat_history"],
                retrieved_docs=state["retrieved_docs"],
                live_rows=state["live_rows"],
            )
            for chunk in stream:
                if chunk:
                    answer_parts.append(chunk)
                    yield _stream_event({"type": "delta", "content": chunk})

            answer = "".join(answer_parts).strip()
            if not answer:
                answer = "当前没有生成有效回答。"
            rag_system.save_chat_turn(
                user_id=request.userId,
                session_id=session_id,
                user_content=question,
                assistant_content=answer,
                retrieval_metadata=state["retrieval_metadata"],
            )
            yield _stream_event({"type": "done", "sessionId": session_id})
        except Exception as error:
            yield _stream_event({"type": "error", "message": str(error)})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.get("/history")
def history(userId: int):
    return {"success": True, "data": rag_system.list_sessions(userId)}


@app.get("/history/{session_id}")
def history_detail(session_id: str, userId: int):
    messages = rag_system.get_messages(session_id, userId)
    if not messages:
        raise HTTPException(status_code=404, detail="会话不存在")
    for item in messages:
        if item.get("role") == "assistant" and item.get("content"):
            item["content"] = rag_system.generation_module.sanitize_public_answer(
                str(item["content"]),
            )
    return {"success": True, "data": messages}


@app.delete("/history/{session_id}")
def history_delete(session_id: str, userId: int):
    deleted = rag_system.delete_session(session_id, userId)
    if not deleted:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "sessionId": session_id}


@app.patch("/history/{session_id}")
def history_update(session_id: str, request: SessionUpdateRequest, userId: int):
    updated = rag_system.update_session(
        session_id,
        userId,
        title=request.title.strip() if request.title is not None else None,
        is_pinned=request.isPinned,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="会话不存在或没有可更新字段")
    return {"success": True, "sessionId": session_id}


@app.delete("/history")
def history_clear(userId: int):
    deleted_count = rag_system.clear_sessions(userId)
    return {"success": True, "deletedCount": deleted_count}
