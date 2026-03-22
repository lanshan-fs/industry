from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..config import RAGConfig
from ..remote_vllm import AutoDLTunnelManager


TASK_PROMPTS: dict[str, dict[str, str]] = {
    "industry_diagnosis": {
        "label": "区域产业现状分析与链条诊断",
        "instruction": (
            "你当前承担的是区域产业现状分析与链条诊断任务。"
            "要围绕区域产业基础、链条结构、重点环节、代表性企业、优势与短板形成判断。"
            "优先回答产业整体结论，再展开链条结构与关键证据。"
            "如果证据不足，明确指出缺口，不要把缺口包装成确定事实。"
        ),
        "structure": (
            "建议按“总体判断 / 链条结构 / 关键主体与资源 / 主要短板 / 后续关注点”组织回答。"
        ),
    },
    "risk_assessment": {
        "label": "风险研判与预警",
        "instruction": (
            "你当前承担的是风险研判与预警任务。"
            "需要区分事实证据与分析判断，识别经营、迁移、创新、配套、合规或供应链风险。"
            "重点说明风险触发信号、影响范围、优先级和依据，不要无依据地夸大风险。"
        ),
        "structure": (
            "建议按“风险结论 / 风险信号 / 影响对象或环节 / 优先级排序 / 建议动作”组织回答。"
        ),
    },
    "chain_upgrade": {
        "label": "补链、延链、强链建议",
        "instruction": (
            "你当前承担的是补链、延链、强链建议任务。"
            "需要根据当前区域产业基础识别缺失环节、薄弱环节与可放大优势，提出可执行的补链延链强链路径。"
            "建议要和现有企业、技术、空间载体或创新资源相衔接，不能空泛罗列政策口号。"
        ),
        "structure": (
            "建议按“关键短板 / 目标环节 / 建议路径 / 可落地主体或资源 / 实施优先级”组织回答。"
        ),
    },
    "investment_attraction": {
        "label": "招商引资与目标企业推荐",
        "instruction": (
            "你当前承担的是招商引资与目标企业推荐任务。"
            "需要结合区域产业定位、现有链条短板和已掌握的企业证据，提出招商方向、目标企业类型或候选企业。"
            "如果数据库证据不足以支持具体企业名单，就只给出招商画像、筛选条件和优先方向，不要编造企业。"
        ),
        "structure": (
            "建议按“招商目标 / 推荐赛道或环节 / 候选企业或企业画像 / 推荐理由 / 跟进建议”组织回答。"
        ),
    },
    "enterprise_profile": {
        "label": "重点企业识别与企业画像",
        "instruction": (
            "你当前承担的是重点企业识别与企业画像支撑能力任务。"
            "需要围绕具体企业或重点企业群体，整合基础信息、技术能力、产业链位置、风险信号和招商价值。"
            "这个任务的目标是为招商、风险研判和链条分析提供支撑，因此回答要兼顾事实性与决策相关性。"
        ),
        "structure": (
            "建议按“企业概况 / 技术与资质 / 产业链角色 / 风险与约束 / 业务价值判断”组织回答。"
        ),
    },
    "general_followup": {
        "label": "通用接话与上下文承接",
        "instruction": (
            "你当前承担的是通用接话与上下文承接任务。"
            "用户这次没有明显发起新的一级任务，可能是在追问、澄清、比较、让你展开、让你举例或让你把上一轮结论转成更好执行的表达。"
            "需要优先承接最近一轮结论，补足解释、比较、示例或下一步建议。"
        ),
        "structure": (
            "建议按“先回应用户追问 / 补充关键信息 / 如仍需信息则说明还缺什么”组织回答。"
        ),
    },
}

TASK_ROUTER_ORDER = (
    "industry_diagnosis",
    "risk_assessment",
    "chain_upgrade",
    "investment_attraction",
    "enterprise_profile",
    "general_followup",
)

TASK_FEW_SHOT_EXAMPLES: dict[str, list[str]] = {
    "industry_diagnosis": [
        "示例1：问题=分析朝阳区数字医疗产业现状；回答思路=先判断产业规模与集聚度，再看上中下游环节分布，最后指出优势环节和薄弱环节。",
        "示例2：问题=朝阳区数字医疗链条完整吗；回答思路=先判断链条是否成型，再说明缺失环节、代表企业和后续关注点。",
    ],
    "risk_assessment": [
        "示例1：问题=识别当前区域产业链的断链风险；回答思路=先给总体风险判断，再列出高风险企业或环节、风险信号和建议动作。",
        "示例2：问题=哪些企业存在明显合规风险；回答思路=先说明风险等级，再给出处罚、异常、诉讼等证据与影响范围。",
    ],
    "chain_upgrade": [
        "示例1：问题=给出朝阳区数字医疗的补链建议；回答思路=先定位短板环节，再提出补链、延链、强链的优先路径和依托资源。",
        "示例2：问题=哪些环节适合重点强化；回答思路=基于现有优势企业和创新资源，判断可放大环节与实施顺序。",
    ],
    "investment_attraction": [
        "示例1：问题=生成一份医疗器械产业链招商建议书；回答思路=先明确招商目标，再给招商方向、目标企业画像、推荐理由和跟进建议。",
        "示例2：问题=推荐可招引的目标企业；回答思路=若证据足够可列候选企业，否则输出企业画像、筛选条件与优先方向。",
    ],
    "enterprise_profile": [
        "示例1：问题=分析某企业是否值得重点培育；回答思路=整合企业概况、知识产权、链条角色、风险信号和发展价值。",
        "示例2：问题=给这家企业做画像；回答思路=回答它是谁、处于链条何处、具备哪些技术和经营特征、是否具备招商或培育价值。",
    ],
    "general_followup": [
        "示例1：问题=为什么这么判断；回答思路=承接上一轮结论，补充关键证据和判断依据，不重复铺陈无关内容。",
        "示例2：问题=再具体一点；回答思路=把上一轮抽象结论改写成更细的行动建议、比较结果或示例说明。",
    ],
}


class GenerationIntegrationModule:
    def __init__(self, config: RAGConfig):
        self.config = config
        self.tunnel_manager = AutoDLTunnelManager(config)
        self.primary_client = self._setup_primary_client()
        self.fallback_llm = self._setup_fallback_llm()
        self.last_provider = "none"
        self.last_error: str | None = None

    def _setup_primary_client(self) -> object | None:
        if not self.config.primary_llm_enabled:
            return None
        return object()

    def _setup_fallback_llm(self) -> ChatOpenAI | None:
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            return None
        return ChatOpenAI(
            model=self.config.llm_model,
            api_key=api_key,
            base_url=self.config.llm_base_url,
            temperature=self.config.llm_temperature,
            timeout=self.config.llm_timeout_seconds,
            max_retries=0,
        )

    def rewrite_query(self, question: str, chat_history: list[dict[str, str]]) -> str:
        history_text = "\n".join(f"{item['role']}: {item['content']}" for item in chat_history[-6:]) or "无"
        prompt = (
            "你是产业链智能助手的检索查询改写助手。"
            "请把用户问题改写成更利于后续资料检索和数据定位的中文短查询。"
            "要求保留核心实体、业务概念、时间范围和上一轮追问关系，不要发明不存在的业务对象。"
            "只输出改写后的查询。"
        )
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"最近对话:\n{history_text}\n\n原始问题:\n{question}"),
        ]
        content = self._invoke_with_fallback(messages)
        if content is None:
            return question
        return content.strip() if isinstance(content, str) else question

    def classify_task(
        self,
        question: str,
        rewritten_query: str = "",
        chat_history: list[dict[str, str]] | None = None,
    ) -> dict[str, str]:
        routed_task = self._route_task_with_llm(question, rewritten_query, chat_history or [])
        if routed_task is not None:
            return routed_task
        return self._classify_task_by_rules(question, rewritten_query, chat_history or [])

    def generate_answer(
        self,
        question: str,
        rewritten_query: str,
        task_type: str,
        task_label: str,
        chat_history: list[dict[str, str]],
        retrieved_docs: list[Document],
        live_rows: dict[str, list[dict[str, Any]]],
    ) -> str:
        system_prompt, user_prompt = self._build_prompts(
            question=question,
            rewritten_query=rewritten_query,
            task_type=task_type,
            task_label=task_label,
            chat_history=chat_history,
            retrieved_docs=retrieved_docs,
            live_rows=live_rows,
        )
        answer = self._invoke_with_fallback(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        if answer is None:
            return self._fallback_answer(retrieved_docs, live_rows)
        return self._sanitize_answer(answer, self._build_source_aliases(retrieved_docs))

    def stream_answer(
        self,
        question: str,
        rewritten_query: str,
        task_type: str,
        task_label: str,
        chat_history: list[dict[str, str]],
        retrieved_docs: list[Document],
        live_rows: dict[str, list[dict[str, Any]]],
    ):
        system_prompt, user_prompt = self._build_prompts(
            question=question,
            rewritten_query=rewritten_query,
            task_type=task_type,
            task_label=task_label,
            chat_history=chat_history,
            retrieved_docs=retrieved_docs,
            live_rows=live_rows,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        aliases = self._build_source_aliases(retrieved_docs)

        yielded = False
        for provider_name, client_kind, client in self._iter_llm_clients():
            try:
                if client_kind == "primary":
                    chunks = self._stream_primary(messages)
                else:
                    chunks = (
                        self._extract_chunk_text(chunk.content)
                        for chunk in client.stream(messages)
                    )
                for chunk in self._stream_sanitize(chunks, aliases):
                    if not chunk:
                        continue
                    yielded = True
                    yield chunk
                self.last_provider = provider_name
                self.last_error = None
                return
            except Exception as error:
                self.last_error = f"{provider_name}: {error}"
                if yielded:
                    return
                continue

        yield self._fallback_answer(retrieved_docs, live_rows)

    def get_health(self) -> dict[str, Any]:
        return {
            "primary_enabled": self.primary_client is not None,
            "primary_model": self.config.primary_llm_model if self.primary_client is not None else None,
            "primary_base_url": self.config.primary_llm_base_url if self.primary_client is not None else None,
            "fallback_enabled": self.fallback_llm is not None,
            "fallback_model": self.config.llm_model if self.fallback_llm is not None else None,
            "last_provider": self.last_provider,
            "last_error": self.last_error,
            "autodl_tunnel_enabled": self.config.autodl_tunnel_enabled,
            "autodl_tunnel_error": self.tunnel_manager.last_error,
        }

    def _iter_llm_clients(self):
        if self.primary_client is not None:
            if self.tunnel_manager.should_manage_tunnel(self.config.primary_llm_base_url):
                if not self.tunnel_manager.ensure_tunnel():
                    self.last_error = self.tunnel_manager.last_error or "未能建立 AutoDL 隧道。"
                else:
                    yield "finetuned-vllm", "primary", self.primary_client
                    if self.fallback_llm is not None:
                        yield "qwen-api", "fallback", self.fallback_llm
                    return
            else:
                yield "finetuned-vllm", "primary", self.primary_client
                if self.fallback_llm is not None:
                    yield "qwen-api", "fallback", self.fallback_llm
                return
        if self.fallback_llm is not None:
            yield "qwen-api", "fallback", self.fallback_llm

    def _invoke_with_fallback(self, messages: list[Any]) -> str | None:
        for provider_name, client_kind, client in self._iter_llm_clients():
            try:
                if client_kind == "primary":
                    response = self._invoke_primary(messages)
                else:
                    response = client.invoke(messages)
                    response = response.content if isinstance(response.content, str) else None
                if not response:
                    continue
                self.last_provider = provider_name
                self.last_error = None
                return response
            except Exception as error:
                self.last_error = f"{provider_name}: {error}"
                continue
        return None

    def _invoke_primary(self, messages: list[Any]) -> str | None:
        if self.primary_client is None:
            return None
        payload = {
            "model": self.config.primary_llm_model,
            "messages": self._to_openai_messages(messages),
            "temperature": self.config.llm_temperature,
        }
        response = self._run_primary_curl(payload)
        choices = response.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        return self._extract_chunk_text(message.get("content")) or None

    def _stream_primary(self, messages: list[Any]):
        content = self._invoke_primary(messages)
        if not content:
            return
        yield content

    @staticmethod
    def _to_openai_messages(messages: list[Any]) -> list[dict[str, str]]:
        formatted = []
        for message in messages:
            role = getattr(message, "type", None) or getattr(message, "role", None) or "user"
            if role == "human":
                role = "user"
            formatted.append(
                {
                    "role": str(role),
                    "content": str(getattr(message, "content", "") or ""),
                }
            )
        return formatted

    def _run_primary_curl(self, payload: dict[str, Any]) -> dict[str, Any]:
        command = [
            "curl",
            "-sS",
            "--noproxy",
            "*",
            "--max-time",
            str(self.config.llm_timeout_seconds),
            self.config.primary_llm_base_url.rstrip("/") + "/chat/completions",
            "-H",
            "Content-Type: application/json",
            "-d",
            json.dumps(payload, ensure_ascii=False),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or "curl 请求失败。"
            raise RuntimeError(stderr)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"主模型响应不是合法 JSON: {error}") from error
        if data.get("error"):
            raise RuntimeError(str(data["error"]))
        return data

    def _route_task_with_llm(
        self,
        question: str,
        rewritten_query: str,
        chat_history: list[dict[str, str]],
    ) -> dict[str, str] | None:
        history_text = "\n".join(f"{item['role']}: {item['content']}" for item in chat_history[-6:]) or "无"
        router_prompt = (
            "你是区域产业链智能助手的任务路由器。"
            "必须严格把用户问题归入以下 6 类之一："
            "1. industry_diagnosis=区域产业现状分析与链条诊断；"
            "2. risk_assessment=风险研判与预警；"
            "3. chain_upgrade=补链、延链、强链建议；"
            "4. investment_attraction=招商引资与目标企业推荐；"
            "5. enterprise_profile=重点企业识别与企业画像；"
            "6. general_followup=通用接话与上下文承接。"
            "边界要求：企业画像是支撑能力，不与前四类一级任务混淆；"
            "当用户只是在追问上一轮内容、要求展开、比较、解释、举例或换种表达时，优先判为 general_followup。"
            "只返回 JSON，不要解释。格式："
            '{"task_type":"...","task_label":"..."}'
        )
        example_lines = [
            '{"question":"分析朝阳区数字医疗产业现状","task_type":"industry_diagnosis","task_label":"区域产业现状分析与链条诊断"}',
            '{"question":"识别当前区域产业链的断链风险","task_type":"risk_assessment","task_label":"风险研判与预警"}',
            '{"question":"给出朝阳区数字医疗的补链建议","task_type":"chain_upgrade","task_label":"补链、延链、强链建议"}',
            '{"question":"生成一份医疗器械产业链招商建议书","task_type":"investment_attraction","task_label":"招商引资与目标企业推荐"}',
            '{"question":"给京东方健康做企业画像","task_type":"enterprise_profile","task_label":"重点企业识别与企业画像"}',
            '{"question":"为什么这么判断","task_type":"general_followup","task_label":"通用接话与上下文承接"}',
        ]
        messages = [
            SystemMessage(content=router_prompt),
            HumanMessage(
                content=(
                    "示例:\n"
                    + "\n".join(example_lines)
                    + f"\n\n最近对话:\n{history_text}\n\n"
                    + f"原始问题:\n{question}\n\n"
                    + f"检索改写:\n{rewritten_query or question}"
                )
            ),
        ]
        response = self._invoke_with_fallback(messages)
        if not response:
            return None

        parsed = self._parse_json_object(response)
        if not parsed:
            return None
        task_type = str(parsed.get("task_type") or "").strip()
        if task_type not in TASK_PROMPTS:
            return None
        return {"type": task_type, "label": TASK_PROMPTS[task_type]["label"]}

    def _classify_task_by_rules(
        self,
        question: str,
        rewritten_query: str,
        chat_history: list[dict[str, str]],
    ) -> dict[str, str]:
        text = f"{question}\n{rewritten_query}".lower()

        if self._looks_like_followup(question, chat_history):
            task_type = "general_followup"
        elif self._matches_any(
            text,
            ("企业画像", "企业档案", "企业情况", "企业概况", "企业信息", "公司怎么样", "公司情况", "重点企业"),
        ) or self._looks_like_enterprise_question(question):
            task_type = "enterprise_profile"
        elif self._matches_any(
            text,
            ("风险", "预警", "断链", "卡点", "堵点", "脆弱", "迁出", "外迁", "预判", "研判"),
        ):
            task_type = "risk_assessment"
        elif self._matches_any(
            text,
            ("补链", "延链", "强链", "短板", "薄弱环节", "缺失环节", "完善链条", "链条提升"),
        ):
            task_type = "chain_upgrade"
        elif self._matches_any(
            text,
            ("招商", "招引", "引资", "引育", "落地", "目标企业", "推荐企业", "招商建议", "招商方向"),
        ):
            task_type = "investment_attraction"
        else:
            task_type = "industry_diagnosis"

        return {"type": task_type, "label": TASK_PROMPTS[task_type]["label"]}

    def _build_source_aliases(self, retrieved_docs: list[Document]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for doc in retrieved_docs:
            table_name = str(doc.metadata.get("table_name") or "").strip()
            display_name = str(doc.metadata.get("display_name") or doc.metadata.get("table_comment") or "").strip()
            if not table_name or not display_name or table_name == display_name:
                continue
            aliases[table_name] = display_name
        return aliases

    @classmethod
    def _stream_sanitize(cls, chunks, aliases: dict[str, str]):
        if not aliases:
            for chunk in chunks:
                if chunk:
                    yield chunk
            return

        max_alias_len = max(len(name) for name in aliases)
        buffer = ""
        for chunk in chunks:
            if not chunk:
                continue
            buffer += chunk
            safe_length = max(0, len(buffer) - max_alias_len + 1)
            if safe_length == 0:
                continue
            safe_text = buffer[:safe_length]
            yield cls._sanitize_answer(safe_text, aliases)
            buffer = buffer[safe_length:]

        if buffer:
            yield cls._sanitize_answer(buffer, aliases)

    @staticmethod
    def _sanitize_answer(answer: str, aliases: dict[str, str]) -> str:
        return GenerationIntegrationModule.sanitize_public_answer(answer, aliases)

    @staticmethod
    def sanitize_public_answer(answer: str, aliases: dict[str, str] | None = None) -> str:
        original_answer = answer
        sanitized = answer
        without_reasoning = re.sub(r"<think>.*?</think>\s*", "", sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = without_reasoning if without_reasoning.strip() else sanitized
        for raw_name, display_name in (aliases or {}).items():
            sanitized = sanitized.replace(raw_name, display_name)
        sanitized = re.sub(r"`[^`]+`", "", sanitized)
        sanitized = re.sub(r"（\s*[A-Za-z0-9_]+\s*）", "", sanitized)
        sanitized = re.sub(r"\((?:[A-Za-z0-9_]+)\)", "", sanitized)
        sanitized = re.sub(r"资料\d+(?:、资料\d+)*", "", sanitized)
        sanitized = re.sub(r"(实时(?:证据)?样本|实时样本)", "动态资料", sanitized)
        sanitized = re.sub(r"估计行数", "资料完备度", sanitized)
        sanitized = re.sub(r"行数均为\s*\**\d+\**", "相关资料尚未补齐", sanitized)
        sanitized = re.sub(r"\b\d+\s*条记录\b", "相关记录", sanitized)
        sanitized = re.sub(r"\b\d+\s*条实时样本\b", "相关动态资料", sanitized)
        sanitized = re.sub(r"([一-龥A-Za-z0-9_]+)映射表", r"\1对应关系", sanitized)
        sanitized = re.sub(r"([一-龥A-Za-z0-9_]+)关联表", r"\1对应关系", sanitized)
        sanitized = re.sub(r"([一-龥A-Za-z0-9_]+)表", r"\1", sanitized)
        sanitized = sanitized.replace("字段", "信息项")
        sanitized = sanitized.replace("表结构", "资料结构")
        sanitized = sanitized.replace("企业ID → 产业链节点ID", "企业与产业链节点的对应关系")
        hidden_terms = {
            "LangGraph": "分析流程",
            "RAG": "资料分析",
            "rag": "资料分析",
            "prompt": "分析要求",
            "Prompt": "分析要求",
            "schema": "资料结构",
            "Schema": "资料结构",
            "embedding": "资料索引",
            "Embedding": "资料索引",
            "向量库": "资料库",
            "数据库设计": "资料结构设计",
        }
        for raw_text, replacement in hidden_terms.items():
            sanitized = sanitized.replace(raw_text, replacement)
        internal_markers = (
            r"`[^`]+`",
            r"资料\d+",
            r"实时(?:证据)?样本",
            r"字段",
            r"映射表",
            r"关联表",
            r"估计行数|行数均为",
            r"[A-Za-z0-9_]+_[A-Za-z0-9_]+",
            r"数据库中",
        )
        marker_hits = sum(
            1
            for pattern in internal_markers
            if re.search(pattern, original_answer, flags=re.IGNORECASE)
        )
        if marker_hits >= 3 and re.search(r"无法|不足|缺失|不具备|未建立|未加载|为空", original_answer):
            return (
                "当前可用资料还不足以支撑可靠结论。"
                "现阶段主要缺口在于产业链关键环节定义、企业与链条环节的对应关系，以及动态风险信号仍不完整。"
                "因此，暂不宜直接给出确定性的研判结论。"
                "建议先补齐链条基础台账、企业环节归属和关键风险指标，再继续分析。"
            )
        return sanitized.strip()

    def _build_prompts(
        self,
        question: str,
        rewritten_query: str,
        task_type: str,
        task_label: str,
        chat_history: list[dict[str, str]],
        retrieved_docs: list[Document],
        live_rows: dict[str, list[dict[str, Any]]],
    ) -> tuple[str, str]:
        history_text = "\n".join(f"{item['role']}: {item['content']}" for item in chat_history[-6:]) or "无"
        schema_text = self._format_schema_docs(retrieved_docs)
        docs_text = self._format_docs(retrieved_docs)
        live_rows_text = self._format_live_rows(live_rows)
        task_prompt = TASK_PROMPTS.get(task_type, TASK_PROMPTS["industry_diagnosis"])
        task_examples_text = self._format_task_examples(task_type)

        system_prompt = (
            "你是朝阳区产业链洞察平台智能助手。"
            "你的定位不是通用数据库问答，而是服务区域产业治理与服务场景。"
            "一级任务只有四类：区域产业现状分析与链条诊断、风险研判与预警、补链延链强链建议、招商引资与目标企业推荐。"
            "同时提供重点企业识别与企业画像能力作为支撑模块，并具备承接追问和澄清的接话能力。"
            "回答必须只基于提供的业务资料、精确模式、关系说明、示例和实时证据样本。"
            "如果证据不足，要明确说明，不要把缺口包装成确定事实。"
            "优先给出结论，再列支撑点。"
            "不要输出原始物理表名、字段名、SQL、模型名、RAG、向量库、提示词或数据库设计细节。"
            "当证据不足时，只能用业务层语言说明原因，例如链条定义不完整、企业与关键环节的对应关系不足、动态风险信号不充分。"
            "不要用某张表为空、某字段缺失、某映射未建立、多少条样本、多少条记录、资料编号等内部实现细节来解释。"
            "统一改用业务自然语言，例如企业基础信息、企业专利信息、企业地址信息等。"
            "对推断性表述要使用“根据现有证据可判断”“倾向于认为”等审慎措辞。"
            f"{task_prompt['instruction']}"
            f"{task_prompt['structure']}"
        )
        user_prompt = (
            f"任务类型: {task_label}\n"
            f"用户问题: {question}\n"
            f"检索改写: {rewritten_query}\n\n"
            f"最近对话:\n{history_text}\n\n"
            f"精确模式与关系资料:\n{schema_text}\n\n"
            f"高质量任务示例:\n{task_examples_text}\n\n"
            f"检索到的补充业务资料:\n{docs_text}\n\n"
            f"实时证据样本:\n{live_rows_text}"
        )
        return system_prompt, user_prompt

    @staticmethod
    def _matches_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _looks_like_enterprise_question(question: str) -> bool:
        company_pattern = (
            r"[\u4e00-\u9fffA-Za-z0-9（）()·\-_]{3,40}"
            r"(?:公司|集团|研究院|研究所|医院|银行|中心|大学|事务所|基金会)"
        )
        return re.search(company_pattern, question) is not None

    @staticmethod
    def _format_docs(documents: list[Document]) -> str:
        lines = []
        skipped_types = {"database_overview", "table_schema", "table_ddl", "table_relation"}
        for index, doc in enumerate(documents, start=1):
            if str(doc.metadata.get("source_type") or "") in skipped_types:
                continue
            display_name = doc.metadata.get("display_name") or doc.metadata.get("table_comment") or doc.metadata.get("table_name")
            lines.append(
                f"[资料 {index}] 来源={display_name} "
                f"类型={doc.metadata.get('source_type')} "
                f"content={doc.page_content[:700]}"
            )
        return "\n\n".join(lines) or "无"

    @staticmethod
    def _format_schema_docs(documents: list[Document]) -> str:
        lines = []
        kept_types = {"database_overview", "table_schema", "table_ddl", "table_relation", "task_definition"}
        for index, doc in enumerate(documents, start=1):
            source_type = str(doc.metadata.get("source_type") or "")
            if source_type not in kept_types:
                continue
            display_name = doc.metadata.get("display_name") or doc.metadata.get("table_comment") or doc.metadata.get("table_name")
            lines.append(f"[资料 {index}] 来源={display_name} 类型={source_type}\n{doc.page_content[:1200]}")
        return "\n\n".join(lines) or "无"

    @staticmethod
    def _format_live_rows(live_rows: dict[str, list[dict[str, Any]]]) -> str:
        blocks = []
        for source_name, rows in live_rows.items():
            if not rows:
                continue
            blocks.append(f"[实时样本 {source_name}]")
            for row in rows:
                blocks.append(json.dumps(row, ensure_ascii=False, default=str))
        return "\n".join(blocks) or "无"

    @staticmethod
    def _fallback_answer(retrieved_docs: list[Document], live_rows: dict[str, list[dict[str, Any]]]) -> str:
        if not retrieved_docs and not any(live_rows.values()):
            return "现有资料不足以支持可靠结论。你可以补充区域、企业名称、产业环节或时间范围，我再继续分析。"

        lines = [
            "现有资料可以支持初步判断，但还不足以形成完整结论。",
            "当前更适合先给出方向性分析，不适合给出过于确定的细节判断。",
            "如果你补充更明确的对象、时间范围或分析目标，我可以继续细化。",
        ]
        return "\n".join(lines)

    @staticmethod
    def _extract_chunk_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("text"):
                    parts.append(str(item["text"]))
                elif getattr(item, "text", None):
                    parts.append(str(item.text))
            return "".join(parts)
        return ""

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any] | None:
        cleaned = str(text).strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                return None
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _format_task_examples(task_type: str) -> str:
        examples = TASK_FEW_SHOT_EXAMPLES.get(task_type) or TASK_FEW_SHOT_EXAMPLES["general_followup"]
        return "\n".join(f"- {example}" for example in examples)

    @staticmethod
    def _looks_like_followup(question: str, chat_history: list[dict[str, str]]) -> bool:
        normalized = re.sub(r"\s+", "", question.lower())
        if not chat_history:
            return False
        if len(normalized) <= 16 and normalized in {"继续", "展开说说", "再具体一点", "详细一点", "还有呢", "然后呢"}:
            return True
        followup_patterns = (
            "为什么",
            "依据是什么",
            "展开",
            "详细",
            "具体",
            "再说说",
            "还有吗",
            "怎么理解",
            "什么意思",
            "举个例子",
            "换个说法",
            "怎么做",
            "优先级怎么排",
        )
        if any(pattern in normalized for pattern in followup_patterns):
            return True
        return False
