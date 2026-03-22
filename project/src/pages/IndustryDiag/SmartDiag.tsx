import React, { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import {
  Input,
  Button,
  Typography,
  List,
  Avatar,
  Modal,
  message,
  Layout,
  theme,
  Tooltip,
  Empty,
} from "antd";
import {
  SendOutlined,
  SettingOutlined,
  UserOutlined,
  RobotOutlined,
  CopyOutlined,
  CheckOutlined,
  PlusOutlined,
  MessageOutlined,
  BulbOutlined,
  DeleteOutlined,
  EditOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  PushpinOutlined,
  PushpinFilled,
  HistoryOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
} from "@ant-design/icons";

const { Title, Text } = Typography;
const { TextArea } = Input;
const { Content } = Layout;

// --- 类型定义 ---
interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  time: string;
  trace?: string[];
}

interface HistorySession {
  session_id: string;
  title: string;
  create_time: string;
  update_time: string;
  is_pinned?: number;
}

// --- 模拟推荐提问 (Initial Prompts) ---
const INITIAL_PROMPTS = [
  { icon: <BulbOutlined />, text: "分析朝阳区数字医疗产业现状" },
  { icon: <BulbOutlined />, text: "生成一份医疗器械产业链招商建议书" },
  { icon: <BulbOutlined />, text: "识别当前区域产业链的断链风险" },
  { icon: <BulbOutlined />, text: "评估某企业的科技属性得分" },
];

interface StreamEvent {
  type: "meta" | "status" | "delta" | "done" | "error";
  stage?: string;
  sessionId?: string;
  content?: string;
  detail?: string;
  message?: string;
}

const LINK_PATTERN = /(https?:\/\/[^\s<]+|www\.[^\s<]+)/gi;

const normalizeAssistantMarkdown = (content: string) => {
  let normalized = content.replace(/\r\n/g, "\n");

  if (!normalized.includes("\n") && normalized.includes("\\n")) {
    normalized = normalized.replace(/\\n/g, "\n");
  }

  normalized = normalized
    .replace(/\u00a0/g, " ")
    .replace(/(^|\n)\s*(✅|⚠️|📌|📍)\s*\*\*([^*\n]+)\*\*\s*[:：]?\s*/g, "$1## $3\n")
    .replace(/(^|\n)\s*\*\*([^*\n]{2,20})\*\*\s*[:：]\s*(?=\S)/g, "$1## $2\n")
    .replace(/(^|\n)(理由如下|结论如下|建议动作|建议路径|下一步建议)\s*[:：]\s*/g, "$1## $2\n")
    .replace(/([：:])(?=-)/g, "$1\n")
    .replace(/([。！？；])(?=-)/g, "$1\n")
    .replace(/(^|\n)-(?=\S)/g, "$1- ")
    .replace(/(^|\n)-\s*\*\*(?=\S)/g, "$1- **")
    .replace(/(^|\n)(\d+\.)\s*/g, "$1$2 ")
    .replace(/([：:])(?=\d+\.)/g, "$1\n")
    .replace(/(?<!\n)\n(#{1,6}\s)/g, "\n\n$1")
    .replace(/([^\n])\n(- |\d+\. )/g, "$1\n\n$2")
    .replace(/\n{3,}/g, "\n\n");

  return normalized.trim();
};

const renderInlineRichText = (text: string, keyPrefix: string) => {
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(LINK_PATTERN)) {
    const rawUrl = match[0];
    const index = match.index ?? 0;
    if (index > lastIndex) {
      nodes.push(text.slice(lastIndex, index));
    }
    const href = rawUrl.startsWith("http") ? rawUrl : `https://${rawUrl}`;
    nodes.push(
      <a
        key={`${keyPrefix}-${index}`}
        href={href}
        target="_blank"
        rel="noreferrer"
        className="smart-diag-richtext__link"
      >
        {rawUrl}
      </a>,
    );
    lastIndex = index + rawUrl.length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes.length ? nodes : [text];
};

const RichTextContent: React.FC<{ content: string }> = ({ content }) => {
  const normalizedContent = content.trim();
  if (!normalizedContent) {
    return null;
  }

  const paragraphs = normalizedContent.split(/\n{2,}/).filter(Boolean);

  return (
    <div className="smart-diag-richtext">
      {paragraphs.map((paragraph, paragraphIndex) => {
        const lines = paragraph.split("\n");
        return (
          <p key={`paragraph-${paragraphIndex}`}>
            {lines.map((line, lineIndex) => (
              <React.Fragment key={`line-${paragraphIndex}-${lineIndex}`}>
                {lineIndex > 0 ? <br /> : null}
                {renderInlineRichText(line, `paragraph-${paragraphIndex}-line-${lineIndex}`)}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
};

const AssistantMarkdown: React.FC<{ content: string }> = ({ content }) => (
  <div className="smart-diag-markdown">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeSanitize]}
      components={{
        h1: ({ children }) => <h1>{children}</h1>,
        h2: ({ children }) => <h2>{children}</h2>,
        h3: ({ children }) => <h3>{children}</h3>,
        p: ({ children }) => <p>{children}</p>,
        ul: ({ children }) => <ul>{children}</ul>,
        ol: ({ children }) => <ol>{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
        blockquote: ({ children }) => <blockquote>{children}</blockquote>,
        table: ({ children }) => (
          <div className="smart-diag-markdown__table-wrap">
            <table>{children}</table>
          </div>
        ),
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="smart-diag-markdown__link"
          >
            {children}
          </a>
        ),
        code: ({ className, children, ...props }) => {
          const codeText = String(children).replace(/\n$/, "");
          const isInline = !className && !codeText.includes("\n");
          if (isInline) {
            return (
              <code className="smart-diag-markdown__code-inline" {...props}>
                {children}
              </code>
            );
          }
          return (
            <code
              className={[
                "smart-diag-markdown__code-block",
                className || "",
              ].join(" ").trim()}
              {...props}
            >
              {children}
            </code>
          );
        },
        pre: ({ children }) => (
          <pre className="smart-diag-markdown__pre">{children}</pre>
        ),
      }}
    >
      {normalizeAssistantMarkdown(content)}
    </ReactMarkdown>
  </div>
);

const formatTraceLabel = (line: string) => {
  const labelMap: Array<[string, string]> = [
    ["正在理解问题", "理解问题"],
    ["已识别分析目标", "识别目标"],
    ["正在整理相关信息", "整理信息"],
    ["已完成信息整理", "信息就绪"],
    ["正在组织回答", "生成回答"],
  ];
  const matched = labelMap.find(([prefix]) => line.startsWith(prefix));
  return matched ? matched[1] : line;
};

const SmartDiag: React.FC = () => {
  const { token } = theme.useToken();
  const navigate = useNavigate();

  // --- 状态管理 ---
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [historyList, setHistoryList] = useState<HistorySession[]>([]);
  const [historySortMode, setHistorySortMode] = useState<"recent" | "created">(
    "recent",
  );
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [renameModalOpen, setRenameModalOpen] = useState(false);
  const [renameSessionId, setRenameSessionId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false); // 侧边栏折叠状态

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // --- API 交互 ---

  // 1. 初始化加载历史记录
  const fetchWithAuth = useCallback(
    async (input: string, init: RequestInit = {}) => {
      const authToken = localStorage.getItem("token");
      if (!authToken) {
        message.error("请先登录");
        navigate("/login");
        throw new Error("unauthorized");
      }

      const response = await fetch(input, {
        ...init,
        headers: {
          ...(init.headers || {}),
          Authorization: `Bearer ${authToken}`,
        },
      });

      if (response.status === 401) {
        localStorage.removeItem("token");
        localStorage.setItem("user", "{}");
        message.error("登录状态已失效，请重新登录");
        navigate("/login");
        throw new Error("unauthorized");
      }

      return response;
    },
    [navigate],
  );

  // 2. 消息滚动
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, loading]);

  const fetchHistoryList = useCallback(async () => {
    try {
      const res = await fetchWithAuth("/api/chat/history");
      const data = await res.json();
      if (data.success) {
        setHistoryList(data.data);
      }
    } catch (error) {
      console.error("Fetch history failed", error);
    }
  }, [fetchWithAuth]);

  useEffect(() => {
    fetchHistoryList();
  }, [fetchHistoryList]);

  const loadSession = async (sessionId: string) => {
    if (sessionId === currentSessionId) return;
    setLoading(true);
    try {
      const res = await fetchWithAuth(`/api/chat/history/${sessionId}`);
      const data = await res.json();
      if (data.success) {
        type HistoryMessageItem = {
          role: "assistant" | "user";
          content: string;
          create_time: string;
        };
        const formattedMsgs: Message[] = data.data.map(
          (item: HistoryMessageItem, index: number) => ({
            id: `${sessionId}-${index}`,
            role: item.role === "assistant" ? "ai" : "user",
            content: item.content,
            time: new Date(item.create_time).toLocaleTimeString(),
          }),
        );
        setMessages(formattedMsgs);
        setCurrentSessionId(sessionId);
      }
    } catch {
      message.error("加载会话失败");
    } finally {
      setLoading(false);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setCurrentSessionId(null);
    setInputValue("");
  };

  const sortedHistoryList = [...historyList].sort((left, right) => {
    const pinDiff = Number(right.is_pinned || 0) - Number(left.is_pinned || 0);
    if (pinDiff !== 0) return pinDiff;
    const leftTime =
      historySortMode === "recent" ? left.update_time : left.create_time;
    const rightTime =
      historySortMode === "recent" ? right.update_time : right.create_time;
    return new Date(rightTime).getTime() - new Date(leftTime).getTime();
  });

  const pinnedCount = historyList.filter((item) => item.is_pinned === 1).length;

  const formatSessionTime = (value: string) =>
    new Date(value).toLocaleString("zh-CN", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  const updateSessionMeta = async (
    sessionId: string,
    payload: { title?: string; isPinned?: boolean },
  ) => {
    const res = await fetchWithAuth(`/api/chat/history/${sessionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!data.success) {
      throw new Error(data.message || "更新失败");
    }
  };

  const openRenameModal = (session: HistorySession) => {
    setRenameSessionId(session.session_id);
    setRenameValue(session.title || "");
    setRenameModalOpen(true);
  };

  const submitRename = async () => {
    if (!renameSessionId) return;
    const nextTitle = renameValue.trim();
    if (!nextTitle) {
      message.warning("请输入会话标题");
      return;
    }
    try {
      await updateSessionMeta(renameSessionId, { title: nextTitle });
      setHistoryList((prev) =>
        prev.map((item) =>
          item.session_id === renameSessionId
            ? { ...item, title: nextTitle }
            : item,
        ),
      );
      setRenameModalOpen(false);
      setRenameSessionId(null);
      setRenameValue("");
      message.success("会话标题已更新");
    } catch {
      message.error("重命名失败");
    }
  };

  const togglePinned = async (session: HistorySession) => {
    try {
      const nextPinned = !(session.is_pinned === 1);
      await updateSessionMeta(session.session_id, { isPinned: nextPinned });
      setHistoryList((prev) =>
        prev.map((item) =>
          item.session_id === session.session_id
            ? { ...item, is_pinned: nextPinned ? 1 : 0 }
            : item,
        ),
      );
      message.success(nextPinned ? "已置顶会话" : "已取消置顶");
    } catch {
      message.error("更新置顶状态失败");
    }
  };

  const deleteSession = (sessionId: string) => {
    Modal.confirm({
      title: "删除这条历史记录？",
      content: "删除后不可恢复。",
      okText: "删除",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          const res = await fetchWithAuth(`/api/chat/history/${sessionId}`, {
            method: "DELETE",
          });
          const data = await res.json();
          if (!data.success) {
            throw new Error(data.message || "删除失败");
          }
          if (currentSessionId === sessionId) {
            setMessages([]);
            setCurrentSessionId(null);
          }
          setHistoryList((prev) =>
            prev.filter((item) => item.session_id !== sessionId),
          );
          message.success("历史记录已删除");
        } catch {
          message.error("删除历史记录失败");
        }
      },
    });
  };

  const clearHistory = () => {
    if (!historyList.length) return;
    Modal.confirm({
      title: "清空全部历史记录？",
      content: "这会删除所有历史对话，且不可恢复。",
      okText: "全部清空",
      okButtonProps: { danger: true },
      cancelText: "取消",
      onOk: async () => {
        try {
          const res = await fetchWithAuth("/api/chat/history", {
            method: "DELETE",
          });
          const data = await res.json();
          if (!data.success) {
            throw new Error(data.message || "清空失败");
          }
          setMessages([]);
          setCurrentSessionId(null);
          setHistoryList([]);
          message.success("历史记录已清空");
        } catch {
          message.error("清空历史记录失败");
        }
      },
    });
  };

  const appendAssistantText = (messageId: string, text: string) => {
    if (!text) return;
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId ? { ...msg, content: msg.content + text } : msg,
      ),
    );
  };

  const setAssistantText = (messageId: string, text: string) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, content: text } : msg)),
    );
  };

  const appendAssistantTrace = (messageId: string, line: string) => {
    if (!line) return;
    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id !== messageId) return msg;
        const trace = msg.trace || [];
        if (trace[trace.length - 1] === line) return msg;
        return { ...msg, trace: [...trace, line] };
      }),
    );
  };

  const copyAssistantMessage = async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(normalizeAssistantMarkdown(content));
      setCopiedMessageId(messageId);
      message.success("已复制回答");
      window.setTimeout(() => {
        setCopiedMessageId((current) => (current === messageId ? null : current));
      }, 1600);
    } catch {
      message.error("复制失败");
    }
  };

  const handleSend = async (text: string = inputValue) => {
    const contentToSend = text.trim();
    if (!contentToSend || loading) return;

    const activeSessionId = currentSessionId;
    const newUserMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: contentToSend,
      time: new Date().toLocaleTimeString(),
    };
    const newAiMsg: Message = {
      id: `${Date.now()}-assistant`,
      role: "ai",
      content: "",
      time: new Date().toLocaleTimeString(),
      trace: [],
    };
    const apiMessages = [...messages, newUserMsg].map((msg) => ({
      role: msg.role === "ai" ? "assistant" : "user",
      content: msg.content,
    }));

    setMessages((prev) => [...prev, newUserMsg, newAiMsg]);
    setInputValue("");
    setLoading(true);

    try {
      const res = await fetchWithAuth("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: apiMessages,
          sessionId: activeSessionId,
        }),
      });

      if (!res.ok || !res.body) {
        const errorText = await res.text();
        throw new Error(errorText || "请求失败");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let receivedError = false;

      const handleEvent = (event: StreamEvent) => {
        if (event.type === "meta" && event.sessionId) {
          setCurrentSessionId(event.sessionId);
        }
        if (event.type === "status" && event.content) {
          appendAssistantTrace(newAiMsg.id, event.content);
        }
        if (event.type === "delta" && event.content) {
          appendAssistantText(newAiMsg.id, event.content);
        }
        if (event.type === "error") {
          receivedError = true;
          setAssistantText(
            newAiMsg.id,
            event.message || "当前无法生成回答，请稍后重试。",
          );
        }
        if (event.type === "done") {
          if (event.sessionId) {
            setCurrentSessionId(event.sessionId);
          }
          fetchHistoryList();
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          handleEvent(JSON.parse(trimmed));
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) {
        handleEvent(JSON.parse(buffer.trim()));
      }

      if (receivedError) {
        message.error("回答生成失败");
      }
      if (!activeSessionId) {
        fetchHistoryList();
      }
    } catch {
      setAssistantText(newAiMsg.id, "网络连接异常，请检查服务是否已启动。");
      message.error("网络连接异常");
    } finally {
      setLoading(false);
    }
  };

  // --- 子组件渲染 ---

  // 侧边栏：功能面板
  const renderSidebar = () => {
    const isEmpty = sortedHistoryList.length === 0;

    return (
      <aside
        className={`smart-diag-panel ${collapsed ? "is-collapsed" : ""}`}
        style={{
          width: collapsed ? 84 : 340,
        }}
      >
        <div className="smart-diag-panel__shell">
          <div className="smart-diag-panel__hero">
            <div className="smart-diag-panel__eyebrow">
              <ThunderboltOutlined />
              智能助手
            </div>
            {!collapsed && (
              <>
                <div className="smart-diag-panel__title-row">
                  <div>
                    <div className="smart-diag-panel__title">功能面板</div>
                    <div className="smart-diag-panel__desc">
                      管理会话、切换排序和模型配置
                    </div>
                  </div>
                  <div className="smart-diag-panel__actions">
                    <Tooltip title="收起面板">
                      <Button
                        type="text"
                        shape="circle"
                        icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                        onClick={() => setCollapsed(!collapsed)}
                      />
                    </Tooltip>
                  </div>
                </div>
                <div className="smart-diag-panel__stats">
                  <div className="smart-diag-panel__stat">
                    <span className="smart-diag-panel__stat-value">
                      {historyList.length}
                    </span>
                    <span className="smart-diag-panel__stat-label">会话</span>
                  </div>
                  <div className="smart-diag-panel__stat">
                    <span className="smart-diag-panel__stat-value">{pinnedCount}</span>
                    <span className="smart-diag-panel__stat-label">置顶</span>
                  </div>
                  <div className="smart-diag-panel__stat">
                    <span className="smart-diag-panel__stat-value">
                      {currentSessionId ? "1" : "0"}
                    </span>
                    <span className="smart-diag-panel__stat-label">进行中</span>
                  </div>
                </div>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={startNewChat}
                  className="smart-diag-panel__new-chat"
                >
                  新建对话
                </Button>
              </>
            )}
            {collapsed && (
              <Tooltip title="展开面板">
                <Button
                  type="text"
                  shape="circle"
                  icon={<MenuUnfoldOutlined />}
                  onClick={() => setCollapsed(!collapsed)}
                />
              </Tooltip>
            )}
          </div>

          {!collapsed && (
            <>
              <div className="smart-diag-panel__section">
                <div className="smart-diag-panel__section-head">
                  <div className="smart-diag-panel__section-title">
                    <HistoryOutlined />
                    历史记录
                  </div>
                  {historyList.length > 0 && (
                    <Button type="text" size="small" danger onClick={clearHistory}>
                      清空
                    </Button>
                  )}
                </div>
                <div className="smart-diag-sort-toggle" role="tablist" aria-label="历史排序">
                  <button
                    type="button"
                    className={`smart-diag-sort-option ${
                      historySortMode === "recent" ? "is-active" : ""
                    }`}
                    onClick={() => setHistorySortMode("recent")}
                    aria-pressed={historySortMode === "recent"}
                  >
                    <ClockCircleOutlined />
                    最近使用
                  </button>
                  <button
                    type="button"
                    className={`smart-diag-sort-option ${
                      historySortMode === "created" ? "is-active" : ""
                    }`}
                    onClick={() => setHistorySortMode("created")}
                    aria-pressed={historySortMode === "created"}
                  >
                    <CalendarOutlined />
                    创建时间
                  </button>
                </div>
              </div>

              <div className="smart-diag-panel__list">
                {isEmpty ? (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无历史会话"
                  />
                ) : (
                  <List
                    dataSource={sortedHistoryList}
                    renderItem={(item) => {
                      const isActive = currentSessionId === item.session_id;
                      return (
                        <div
                          onClick={() => loadSession(item.session_id)}
                          className={`smart-diag-history-item ${isActive ? "is-active" : ""}`}
                        >
                          <div className="smart-diag-history-item__icon">
                            <MessageOutlined />
                          </div>
                          <div className="smart-diag-history-item__body">
                            <div className="smart-diag-history-item__title-row">
                              <div className="smart-diag-history-item__title">
                                {item.title || "无标题对话"}
                              </div>
                              {item.is_pinned === 1 && (
                                <span className="smart-diag-history-item__badge">
                                  置顶
                                </span>
                              )}
                            </div>
                            <div className="smart-diag-history-item__meta">
                              {formatSessionTime(item.update_time)}
                            </div>
                          </div>
                          <div className="smart-diag-history-item__actions">
                            <Tooltip title={item.is_pinned === 1 ? "取消置顶" : "置顶"}>
                              <Button
                                type="text"
                                size="small"
                                icon={
                                  item.is_pinned === 1 ? (
                                    <PushpinFilled />
                                  ) : (
                                    <PushpinOutlined />
                                  )
                                }
                                onClick={(event) => {
                                  event.stopPropagation();
                                  togglePinned(item);
                                }}
                              />
                            </Tooltip>
                            <Tooltip title="重命名">
                              <Button
                                type="text"
                                size="small"
                                icon={<EditOutlined />}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  openRenameModal(item);
                                }}
                              />
                            </Tooltip>
                            <Tooltip title="删除会话">
                              <Button
                                type="text"
                                size="small"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  deleteSession(item.session_id);
                                }}
                              />
                            </Tooltip>
                          </div>
                        </div>
                      );
                    }}
                  />
                )}
              </div>

              <div className="smart-diag-panel__footer">
                <Button
                  block
                  icon={<SettingOutlined />}
                  onClick={() => setIsConfigModalOpen(true)}
                >
                  模型配置
                </Button>
              </div>
            </>
          )}
        </div>
      </aside>
    );
  };

  // 初次输入状态（居中）
  const renderInitialState = () => (
    <div
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "0 20px",
        maxWidth: 800,
        margin: "0 auto",
        width: "100%",
      }}
    >
      <div style={{ marginBottom: 40, textAlign: "center" }}>
        <Title level={2} style={{ marginBottom: 8 }}>
          有什么可以帮您？
        </Title>
        <Text type="secondary" style={{ fontSize: 16 }}>
          我是您的智能助手，您可以询问关于产业链、企业画像或招商建议的任何问题。
        </Text>
      </div>

      {/* 输入框 (Initial) */}
      <div style={{ width: "100%", marginBottom: 40 }}>
        <div
          style={{
            position: "relative",
            boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
            borderRadius: 16,
            background: "#fff",
            border: "1px solid #e0e0e0",
          }}
        >
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="输入您的问题..."
            autoSize={{ minRows: 3, maxRows: 6 }}
            style={{
              padding: "16px 60px 16px 20px",
              borderRadius: 16,
              border: "none",
              fontSize: 16,
              resize: "none",
              backgroundColor: "transparent",
            }}
          />
          <Button
            type={inputValue.trim() ? "primary" : "default"}
            shape="circle"
            icon={<SendOutlined />}
            onClick={() => handleSend()}
            disabled={!inputValue.trim()}
            style={{ position: "absolute", right: 16, bottom: 16 }}
          />
        </div>
      </div>

      {/* 推荐提问 Chips */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          justifyContent: "center",
        }}
      >
        {INITIAL_PROMPTS.map((prompt, idx) => (
          <div
            key={idx}
            onClick={() => handleSend(prompt.text)}
            style={{
              padding: "8px 16px",
              background: "#f5f5f5",
              borderRadius: 20,
              cursor: "pointer",
              fontSize: 14,
              color: "#555",
              border: "1px solid transparent",
              transition: "all 0.2s",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "#fff";
              e.currentTarget.style.borderColor = "#d9d9d9";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "#f5f5f5";
              e.currentTarget.style.borderColor = "transparent";
            }}
          >
            {prompt.icon}
            {prompt.text}
          </div>
        ))}
      </div>
    </div>
  );

  // 正常对话界面 (输入框在底部)
  const renderChatInterface = () => (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* 消息列表区 */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 0" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", padding: "0 20px" }}>
          {messages.map((msg, index) => (
            <div
              key={msg.id}
              style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                marginBottom: 32,
              }}
            >
              {msg.role === "ai" && (
                <Avatar
                  icon={<RobotOutlined />}
                  style={{
                    backgroundColor: token.colorPrimary,
                    marginRight: 16,
                    marginTop: 4,
                  }}
                />
              )}
              <div style={{ maxWidth: "80%" }}>
                {msg.role === "ai" && (
                  <div className="smart-diag-assistant-head">
                    <div className="smart-diag-assistant-head__title">
                      <span className="smart-diag-assistant-head__name">智能助手</span>
                      {msg.trace && msg.trace.length > 0 && (
                        <span className="smart-diag-assistant-head__trace-count">
                          {msg.trace.length} 个步骤
                        </span>
                      )}
                    </div>
                    {msg.content && (
                      <Tooltip title={copiedMessageId === msg.id ? "已复制" : "复制回答"}>
                        <Button
                          type="text"
                          size="small"
                          className="smart-diag-assistant-head__copy"
                          icon={
                            copiedMessageId === msg.id ? (
                              <CheckOutlined />
                            ) : (
                              <CopyOutlined />
                            )
                          }
                          onClick={() => copyAssistantMessage(msg.id, msg.content)}
                        />
                      </Tooltip>
                    )}
                  </div>
                )}
                {msg.role === "ai" && msg.trace && msg.trace.length > 0 && (
                  <div className="smart-diag-trace-card">
                    {msg.trace.map((line, traceIndex) => (
                      <div
                        key={`${msg.id}-trace-${traceIndex}`}
                        className={`smart-diag-trace-step ${
                          loading && index === messages.length - 1 && traceIndex === msg.trace!.length - 1
                            ? "is-active"
                            : ""
                        }`}
                      >
                        <span className="smart-diag-trace-step__dot" />
                        <span className="smart-diag-trace-step__label">
                          {formatTraceLabel(line)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {(msg.role === "user" ||
                  msg.content ||
                  (loading && msg.role === "ai" && index === messages.length - 1)) && (
                  <div
                    className={`smart-diag-message ${
                      msg.role === "user"
                        ? "smart-diag-message--user"
                        : "smart-diag-message--assistant"
                    }`}
                    style={{
                      padding: "12px 16px",
                      borderRadius:
                        msg.role === "user"
                          ? "16px 16px 4px 16px"
                          : "4px 16px 16px 16px",
                      backgroundColor:
                        msg.role === "user" ? "#e6f4ff" : "#f5f5f5",
                      color: "#333",
                      lineHeight: 1.6,
                      fontSize: 15,
                    }}
                  >
                    {msg.role === "user" ? (
                      <RichTextContent content={msg.content} />
                    ) : msg.content ? (
                      <AssistantMarkdown content={msg.content} />
                    ) : (
                      <span className="smart-diag-typing" aria-label="正在生成回答">
                        <span className="smart-diag-typing__dot" />
                        <span className="smart-diag-typing__dot" />
                        <span className="smart-diag-typing__dot" />
                      </span>
                    )}
                  </div>
                )}
              </div>
              {msg.role === "user" && (
                <Avatar
                  icon={<UserOutlined />}
                  style={{
                    backgroundColor: "#87d068",
                    marginLeft: 16,
                    marginTop: 4,
                  }}
                />
              )}
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 底部输入框区 */}
      <div style={{ padding: "20px", background: "#fff" }}>
        <div style={{ maxWidth: 800, margin: "0 auto", position: "relative" }}>
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="输入您的问题..."
            autoSize={{ minRows: 1, maxRows: 6 }}
            style={{
              padding: "12px 50px 12px 16px",
              borderRadius: 24,
              resize: "none",
              background: "#f8f9fa",
              border: "1px solid transparent",
            }}
            onFocus={(e) => (e.target.style.background = "#fff")}
            onBlur={(e) => (e.target.style.background = "#f8f9fa")}
          />
          <Button
            type="primary"
            shape="circle"
            // size="small"
            icon={<SendOutlined />}
            onClick={() => handleSend()}
            disabled={!inputValue.trim() || loading}
            style={{ position: "absolute", right: 12, bottom: 7 }}
          />
        </div>
        <div
          style={{
            textAlign: "center",
            marginTop: 8,
            fontSize: 12,
            color: "#999",
          }}
        >
          AI 生成内容可能不准确，请结合实际情况判断。
        </div>
      </div>
    </div>
  );

  return (
    <Layout style={{ height: "100%", background: "#fff" }}>
      <div className="smart-diag-layout-shell">
        {/* 右侧功能侧边栏 */}
        {renderSidebar()}

        <Content
          style={{ height: "100%", position: "relative", minWidth: 0, overflow: "hidden" }}
        >
          {messages.length === 0 ? renderInitialState() : renderChatInterface()}
        </Content>
      </div>

      {/* 3. 配置弹窗 */}
      <Modal
        open={isConfigModalOpen}
        onCancel={() => setIsConfigModalOpen(false)}
        title="模型配置"
        footer={null}
      >
        <div style={{ padding: 20, textAlign: "center", color: "#999" }}>
          暂无更多高级配置项，当前使用默认模型。
        </div>
      </Modal>
      <Modal
        open={renameModalOpen}
        onCancel={() => {
          setRenameModalOpen(false);
          setRenameSessionId(null);
          setRenameValue("");
        }}
        onOk={submitRename}
        title="重命名会话"
        okText="保存"
        cancelText="取消"
      >
        <Input
          value={renameValue}
          onChange={(event) => setRenameValue(event.target.value)}
          placeholder="输入新的会话标题"
          maxLength={255}
          onPressEnter={submitRename}
        />
      </Modal>
      <style>{`
        .smart-diag-layout-shell {
          display: flex;
          gap: 16px;
          width: 100%;
          height: 100%;
          min-height: 0;
          align-items: stretch;
        }

        .smart-diag-layout-shell > .ant-layout-content {
          flex: 1;
          min-width: 0;
          min-height: 0;
          border-radius: 20px;
          background:
            radial-gradient(circle at top left, rgba(24, 144, 255, 0.08), transparent 34%),
            linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
        }

        .smart-diag-panel {
          flex: 0 0 auto;
          min-height: 0;
          height: 100%;
        }

        .smart-diag-panel__shell {
          height: 100%;
          display: flex;
          flex-direction: column;
          gap: 14px;
          padding: 16px;
          border-right: 1px solid rgba(15, 23, 42, 0.08);
          background:
            linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.94));
          box-shadow: 8px 0 32px rgba(15, 23, 42, 0.04);
          backdrop-filter: blur(14px);
          overflow: hidden;
          transition: width 0.2s ease;
        }

        .smart-diag-panel__hero {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 14px;
          border-radius: 18px;
          background:
            linear-gradient(145deg, rgba(24, 144, 255, 0.12), rgba(15, 23, 42, 0.04));
          border: 1px solid rgba(24, 144, 255, 0.14);
        }

        .smart-diag-panel__eyebrow {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: #2b4c7e;
        }

        .smart-diag-panel__title-row {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
        }

        .smart-diag-panel__title {
          font-size: 22px;
          font-weight: 700;
          color: #0f172a;
          line-height: 1.15;
        }

        .smart-diag-panel__desc {
          margin-top: 4px;
          font-size: 13px;
          line-height: 1.5;
          color: rgba(15, 23, 42, 0.62);
        }

        .smart-diag-panel__actions {
          display: flex;
          align-items: center;
          justify-content: flex-end;
        }

        .smart-diag-panel__stats {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 8px;
        }

        .smart-diag-panel__stat {
          padding: 10px 12px;
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.72);
          border: 1px solid rgba(15, 23, 42, 0.06);
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .smart-diag-panel__stat-value {
          font-size: 18px;
          font-weight: 700;
          color: #0f172a;
        }

        .smart-diag-panel__stat-label {
          font-size: 12px;
          color: rgba(15, 23, 42, 0.58);
        }

        .smart-diag-panel__new-chat {
          height: 42px;
          border-radius: 12px;
          box-shadow: 0 10px 24px rgba(24, 144, 255, 0.18);
        }

        .smart-diag-panel__section {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .smart-diag-panel__section-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }

        .smart-diag-panel__section-title {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          font-weight: 600;
          color: #0f172a;
        }

        .smart-diag-sort-toggle {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
          padding: 6px;
          border-radius: 16px;
          background: rgba(15, 23, 42, 0.04);
          border: 1px solid rgba(15, 23, 42, 0.06);
        }

        .smart-diag-sort-option {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          height: 38px;
          padding: 0 12px;
          border: 0;
          border-radius: 12px;
          background: transparent;
          color: rgba(15, 23, 42, 0.62);
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition:
            transform 0.18s ease,
            background 0.18s ease,
            color 0.18s ease,
            box-shadow 0.18s ease;
        }

        .smart-diag-sort-option:hover {
          background: rgba(255, 255, 255, 0.72);
          color: #0f172a;
          transform: translateY(-1px);
        }

        .smart-diag-sort-option.is-active {
          background: linear-gradient(135deg, #ffffff, #eef5ff);
          color: #1677ff;
          box-shadow:
            0 8px 18px rgba(24, 144, 255, 0.14),
            inset 0 0 0 1px rgba(24, 144, 255, 0.12);
        }

        .smart-diag-sort-option .anticon {
          font-size: 14px;
        }

        .smart-diag-panel__list {
          flex: 1;
          min-height: 0;
          overflow: auto;
          padding-right: 4px;
        }

        .smart-diag-panel__list::-webkit-scrollbar {
          width: 8px;
        }

        .smart-diag-panel__list::-webkit-scrollbar-thumb {
          border-radius: 999px;
          background: rgba(15, 23, 42, 0.12);
        }

        .smart-diag-panel__footer {
          padding-top: 4px;
        }

        .smart-diag-history-item {
          display: grid;
          grid-template-columns: 36px minmax(0, 1fr) auto;
          gap: 12px;
          align-items: center;
          padding: 12px;
          margin-bottom: 10px;
          border-radius: 16px;
          background: rgba(255, 255, 255, 0.78);
          border: 1px solid rgba(15, 23, 42, 0.06);
          box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
          cursor: pointer;
          transition:
            transform 0.18s ease,
            box-shadow 0.18s ease,
            border-color 0.18s ease,
            background 0.18s ease;
        }

        .smart-diag-history-item:hover {
          transform: translateY(-1px);
          border-color: rgba(24, 144, 255, 0.22);
          box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
          background: rgba(255, 255, 255, 0.96);
        }

        .smart-diag-history-item.is-active {
          background: linear-gradient(135deg, rgba(24, 144, 255, 0.14), rgba(24, 144, 255, 0.05));
          border-color: rgba(24, 144, 255, 0.28);
          box-shadow: 0 14px 28px rgba(24, 144, 255, 0.12);
        }

        .smart-diag-history-item__icon {
          width: 36px;
          height: 36px;
          border-radius: 12px;
          background: linear-gradient(135deg, rgba(24, 144, 255, 0.16), rgba(24, 144, 255, 0.06));
          color: #1677ff;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .smart-diag-history-item__body {
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .smart-diag-history-item__title-row {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .smart-diag-history-item__title {
          min-width: 0;
          flex: 1;
          font-size: 14px;
          font-weight: 600;
          color: #0f172a;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .smart-diag-history-item__badge {
          flex-shrink: 0;
          padding: 2px 8px;
          border-radius: 999px;
          background: rgba(24, 144, 255, 0.12);
          color: #1677ff;
          font-size: 12px;
          line-height: 1.4;
        }

        .smart-diag-history-item__meta {
          font-size: 12px;
          color: rgba(15, 23, 42, 0.52);
        }

        .smart-diag-history-item__actions {
          display: flex;
          align-items: center;
          gap: 2px;
          opacity: 0;
          transform: translateX(4px);
          transition:
            opacity 0.18s ease,
            transform 0.18s ease;
        }

        .smart-diag-history-item:hover .smart-diag-history-item__actions,
        .smart-diag-history-item.is-active .smart-diag-history-item__actions {
          opacity: 1;
          transform: translateX(0);
        }

        .smart-diag-history-item__actions .ant-btn {
          color: rgba(15, 23, 42, 0.55);
        }

        .smart-diag-history-item__actions .ant-btn-dangerous {
          color: #ff4d4f;
        }

        .smart-diag-panel.is-collapsed .smart-diag-panel__shell {
          align-items: center;
          padding-inline: 10px;
        }

        .smart-diag-panel.is-collapsed .smart-diag-panel__hero {
          width: 100%;
          align-items: center;
          text-align: center;
        }

        .smart-diag-panel.is-collapsed .smart-diag-panel__eyebrow {
          writing-mode: vertical-rl;
          text-orientation: mixed;
          letter-spacing: 0.12em;
        }

        .smart-diag-panel.is-collapsed .smart-diag-panel__new-chat,
        .smart-diag-panel.is-collapsed .smart-diag-panel__section,
        .smart-diag-panel.is-collapsed .smart-diag-panel__list,
        .smart-diag-panel.is-collapsed .smart-diag-panel__footer {
          display: none;
        }

        .smart-diag-message {
          word-break: break-word;
          overflow-wrap: anywhere;
          user-select: text;
          -webkit-user-select: text;
          box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
        }

        .smart-diag-message--assistant {
          background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(248, 250, 252, 0.96)) !important;
          border: 1px solid rgba(15, 23, 42, 0.08);
        }

        .smart-diag-message--user {
          background:
            linear-gradient(180deg, rgba(230, 244, 255, 0.98), rgba(214, 237, 255, 0.98)) !important;
          border: 1px solid rgba(22, 119, 255, 0.12);
        }

        .smart-diag-assistant-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 8px;
        }

        .smart-diag-assistant-head__title {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          min-width: 0;
        }

        .smart-diag-assistant-head__name {
          font-size: 13px;
          font-weight: 700;
          color: #334155;
          letter-spacing: 0.02em;
        }

        .smart-diag-assistant-head__trace-count {
          padding: 2px 8px;
          border-radius: 999px;
          background: rgba(15, 23, 42, 0.05);
          color: rgba(51, 65, 85, 0.72);
          font-size: 11px;
          white-space: nowrap;
        }

        .smart-diag-assistant-head__copy.ant-btn {
          color: rgba(51, 65, 85, 0.72);
        }

        .smart-diag-trace-card {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 12px;
        }

        .smart-diag-trace-step {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          min-height: 32px;
          padding: 7px 11px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.82);
          border: 1px solid rgba(15, 23, 42, 0.08);
          color: #475569;
          font-size: 12px;
          line-height: 1;
        }

        .smart-diag-trace-step.is-active {
          border-color: rgba(22, 119, 255, 0.24);
          background: rgba(22, 119, 255, 0.08);
          color: #1677ff;
        }

        .smart-diag-trace-step__dot {
          width: 8px;
          height: 8px;
          border-radius: 999px;
          background: currentColor;
          opacity: 0.8;
          flex-shrink: 0;
        }

        .smart-diag-trace-step.is-active .smart-diag-trace-step__dot {
          box-shadow: 0 0 0 6px rgba(22, 119, 255, 0.12);
        }

        .smart-diag-richtext p {
          margin: 0;
        }

        .smart-diag-richtext p + p {
          margin-top: 12px;
        }

        .smart-diag-richtext__link,
        .smart-diag-markdown__link {
          color: #1677ff;
          text-decoration: none;
          font-weight: 500;
        }

        .smart-diag-richtext__link:hover,
        .smart-diag-markdown__link:hover {
          text-decoration: underline;
        }

        .smart-diag-markdown > :first-child {
          margin-top: 0;
        }

        .smart-diag-markdown > :last-child {
          margin-bottom: 0;
        }

        .smart-diag-markdown h1,
        .smart-diag-markdown h2,
        .smart-diag-markdown h3,
        .smart-diag-markdown h4 {
          margin: 28px 0 12px;
          color: #0f172a;
          line-height: 1.25;
          font-weight: 700;
          letter-spacing: -0.01em;
        }

        .smart-diag-markdown h1 {
          font-size: 28px;
        }

        .smart-diag-markdown h2 {
          font-size: 22px;
        }

        .smart-diag-markdown h3,
        .smart-diag-markdown h4 {
          font-size: 18px;
        }

        .smart-diag-markdown p,
        .smart-diag-markdown ul,
        .smart-diag-markdown ol,
        .smart-diag-markdown blockquote,
        .smart-diag-markdown pre,
        .smart-diag-markdown table {
          margin: 0 0 16px;
        }

        .smart-diag-markdown p {
          color: #1e293b;
          line-height: 1.82;
        }

        .smart-diag-markdown ul,
        .smart-diag-markdown ol {
          padding-left: 24px;
          color: #1e293b;
          line-height: 1.78;
        }

        .smart-diag-markdown li + li {
          margin-top: 8px;
        }

        .smart-diag-markdown blockquote {
          padding: 12px 16px;
          border-left: 3px solid rgba(22, 119, 255, 0.42);
          background: rgba(22, 119, 255, 0.05);
          border-radius: 12px;
          color: #3b4f68;
        }

        .smart-diag-markdown__code-inline {
          padding: 0.15em 0.45em;
          border-radius: 6px;
          background: rgba(15, 23, 42, 0.08);
          color: #d6336c;
          font-size: 0.92em;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        }

        .smart-diag-markdown__pre {
          overflow-x: auto;
          padding: 16px 18px;
          border-radius: 16px;
          background: linear-gradient(180deg, #0f172a, #111827);
          color: #e2e8f0;
          box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.14);
        }

        .smart-diag-markdown__code-block {
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          font-size: 13px;
          line-height: 1.7;
          white-space: pre;
        }

        .smart-diag-markdown__table-wrap {
          width: 100%;
          overflow-x: auto;
          border-radius: 16px;
          box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.08);
          background: rgba(255, 255, 255, 0.9);
        }

        .smart-diag-markdown table {
          width: 100%;
          min-width: 420px;
          border-collapse: collapse;
          font-size: 14px;
        }

        .smart-diag-markdown hr {
          margin: 20px 0;
          border: none;
          border-top: 1px solid rgba(15, 23, 42, 0.1);
        }

        .smart-diag-typing {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          min-height: 24px;
        }

        .smart-diag-typing__dot {
          width: 8px;
          height: 8px;
          border-radius: 999px;
          background: rgba(71, 85, 105, 0.78);
          animation: smart-diag-typing-bounce 1.1s ease-in-out infinite;
        }

        .smart-diag-typing__dot:nth-child(2) {
          animation-delay: 0.16s;
        }

        .smart-diag-typing__dot:nth-child(3) {
          animation-delay: 0.32s;
        }

        @keyframes smart-diag-typing-bounce {
          0%, 80%, 100% {
            transform: translateY(0);
            opacity: 0.35;
          }

          40% {
            transform: translateY(-3px);
            opacity: 1;
          }
        }

        .smart-diag-markdown th,
        .smart-diag-markdown td {
          padding: 10px 12px;
          border-bottom: 1px solid rgba(15, 23, 42, 0.08);
          text-align: left;
          vertical-align: top;
        }

        .smart-diag-markdown th {
          background: rgba(15, 23, 42, 0.04);
          font-weight: 600;
          color: #10243e;
        }

        .smart-diag-markdown tr:last-child td {
          border-bottom: none;
        }
      `}</style>
    </Layout>
  );
};

export default SmartDiag;
