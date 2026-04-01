import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Empty,
  Input,
  Progress,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import type { TableProps } from "antd";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

interface DimensionOption {
  id: number;
  key: string;
  name: string;
  color: string;
  description: string;
}

interface CompanyCandidate {
  key: number;
  companyId: number;
  name: string;
  code: string;
  establishDate?: string;
  updateTime?: string;
  tagCount: number;
}

interface TagDetail {
  id: number;
  name: string;
  dimensionName: string;
  subdimensionName: string;
}

interface BatchSummaryTag {
  company_tag_id: number;
  company_tag_name: string;
  company_tag_dimension_name: string;
  company_tag_subdimension_name: string;
  confidence?: number;
  evidence?: string;
}

interface BatchResult {
  company_id: number;
  tag_count: number;
  tags: BatchSummaryTag[];
}

interface BatchRecord {
  batchId: number;
  batchCode: string;
  batchName?: string;
  status: "pending" | "running" | "completed" | "failed";
  requestedByUserId?: number | null;
  dimensionIds: number[];
  dimensionNames: string[];
  requestedCompanyCount: number;
  successCompanyCount: number;
  failedCompanyCount: number;
  summary?: {
    company_count?: number;
    assignment_count?: number;
    conflicted_company_count?: number;
    results?: BatchResult[];
  } | null;
  errorMessage?: string;
  startedAt?: string;
  finishedAt?: string;
  createdAt?: string;
  updatedAt?: string;
}

interface BatchItemRow {
  batchItemId: number;
  key: number;
  companyId: number;
  name: string;
  code: string;
  updateTime?: string;
  tagCount: number;
  tags: TagDetail[];
  dimensions: Record<string, string[]>;
  status: "pending" | "success" | "failed";
  errorMessage?: string;
  result?: BatchResult | null;
}

interface LlmBatchRecord {
  batchId: number;
  batchCode: string;
  batchName?: string;
  status: "pending" | "running" | "completed" | "failed";
  provider: string;
  modelName?: string | null;
  dimensionId: number;
  requestedByUserId?: number | null;
  requestedCompanyCount: number;
  successCompanyCount: number;
  failedCompanyCount: number;
  summary?: {
    mapped_count?: number;
    unmapped_count?: number;
    results?: Array<{
      company_id: number;
      mapped_count: number;
      unmapped_count: number;
      summary?: string;
      error_message?: string;
    }>;
  } | null;
  errorMessage?: string;
  startedAt?: string;
  finishedAt?: string;
  createdAt?: string;
  updatedAt?: string;
}

interface LlmCandidateRow {
  candidateId: number;
  companyId: number;
  companyName: string;
  creditCode: string;
  companyTagId?: number | null;
  companyTagName?: string | null;
  candidateType: "mapped_tag" | "unmapped_term";
  candidateName: string;
  normalizedName?: string | null;
  status: "pending" | "unmapped" | "applied" | "rejected";
  confidence?: number | null;
  reasonText?: string;
  reviewedByUserId?: number | null;
  reviewedAt?: string;
  appliedAt?: string;
  createdAt?: string;
}

interface UploadResolveResponse {
  summary: {
    inputCount: number;
    matchedEntryCount: number;
    matchedCompanyCount: number;
    unmatchedCount: number;
    ambiguousCount: number;
  };
  matchedCompanies: CompanyCandidate[];
  unmatchedIdentifiers: string[];
  ambiguousIdentifiers: Array<{
    identifier: string;
    companyCount: number;
    companies: Array<{
      companyId: number;
      companyName: string;
      creditCode: string;
    }>;
  }>;
}

const DIMENSION_COLORS: Record<string, string> = {
  基本信息: "cyan",
  经营状况: "blue",
  知识产权: "purple",
  风险信息: "red",
  街道地区: "geekblue",
  行业标签: "orange",
  应用场景: "green",
};

const STATUS_META: Record<string, { color: string; label: string }> = {
  pending: { color: "default", label: "待执行" },
  running: { color: "processing", label: "执行中" },
  completed: { color: "success", label: "已完成" },
  failed: { color: "error", label: "失败" },
  success: { color: "success", label: "成功" },
  unmapped: { color: "orange", label: "未映射" },
  applied: { color: "success", label: "已采纳" },
  rejected: { color: "default", label: "已驳回" },
};

function parseIdentifierText(content: string) {
  return [...new Set(content.split(/[\n\r,，;；\t]+/).map((item) => item.trim()).filter(Boolean))];
}

const AutoTag: React.FC = () => {
  const [dimensions, setDimensions] = useState<DimensionOption[]>([]);
  const [selectedDimensions, setSelectedDimensions] = useState<number[]>([]);
  const [companies, setCompanies] = useState<CompanyCandidate[]>([]);
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<number[]>([]);
  const [loadingCompanies, setLoadingCompanies] = useState(false);
  const [creatingBatch, setCreatingBatch] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);
  const [total, setTotal] = useState(0);
  const [batches, setBatches] = useState<BatchRecord[]>([]);
  const [loadingBatches, setLoadingBatches] = useState(false);
  const [currentBatch, setCurrentBatch] = useState<BatchRecord | null>(null);
  const [batchItems, setBatchItems] = useState<BatchItemRow[]>([]);
  const [loadingBatchItems, setLoadingBatchItems] = useState(false);
  const [uploadText, setUploadText] = useState("");
  const [resolvingUpload, setResolvingUpload] = useState(false);
  const [uploadResolved, setUploadResolved] = useState<UploadResolveResponse | null>(null);
  const [llmBatches, setLlmBatches] = useState<LlmBatchRecord[]>([]);
  const [loadingLlmBatches, setLoadingLlmBatches] = useState(false);
  const [generatingLlmBatch, setGeneratingLlmBatch] = useState(false);
  const [currentLlmBatch, setCurrentLlmBatch] = useState<LlmBatchRecord | null>(null);
  const [llmCandidates, setLlmCandidates] = useState<LlmCandidateRow[]>([]);
  const [loadingLlmCandidates, setLoadingLlmCandidates] = useState(false);
  const [reviewingCandidateId, setReviewingCandidateId] = useState<number | null>(null);

  const fetchDimensions = async () => {
    try {
      const response = await fetch("/api/auto-tag/dimensions");
      const result = await response.json();
      if (result.success) {
        const nextDimensions = result.data || [];
        setDimensions(nextDimensions);
        setSelectedDimensions((prev) =>
          prev.length > 0 ? prev : nextDimensions.slice(0, 2).map((item: DimensionOption) => item.id),
        );
      } else {
        message.error(result.message || "加载维度失败");
      }
    } catch (error) {
      console.error(error);
      message.error("加载维度失败");
    }
  };

  const fetchCompanies = async (page = 1, size = 12, keyword = "") => {
    setLoadingCompanies(true);
    try {
      const response = await fetch(
        `/api/auto-tag/companies?page=${page}&pageSize=${size}&keyword=${encodeURIComponent(keyword)}`,
      );
      const result = await response.json();
      if (result.success) {
        setCompanies(result.data.list || []);
        setTotal(result.data.total || 0);
        setCurrentPage(page);
      } else {
        message.error(result.message || "加载企业失败");
      }
    } catch (error) {
      console.error(error);
      message.error("加载企业失败");
    } finally {
      setLoadingCompanies(false);
    }
  };

  const fetchBatches = async () => {
    setLoadingBatches(true);
    try {
      const response = await fetch("/api/auto-tag/batches?page=1&pageSize=8");
      const result = await response.json();
      if (result.success) {
        const list = result.data.list || [];
        setBatches(list);
        setCurrentBatch((prev) => prev || list[0] || null);
      } else {
        message.error(result.message || "加载批次失败");
      }
    } catch (error) {
      console.error(error);
      message.error("加载批次失败");
    } finally {
      setLoadingBatches(false);
    }
  };

  const fetchBatchItems = async (batchId: number) => {
    setLoadingBatchItems(true);
    try {
      const response = await fetch(`/api/auto-tag/batches/${batchId}/items?page=1&pageSize=200`);
      const result = await response.json();
      if (result.success) {
        setCurrentBatch(result.data.batch || null);
        setBatchItems(result.data.list || []);
      } else {
        message.error(result.message || "加载批次详情失败");
      }
    } catch (error) {
      console.error(error);
      message.error("加载批次详情失败");
    } finally {
      setLoadingBatchItems(false);
    }
  };

  const fetchLlmBatches = async () => {
    setLoadingLlmBatches(true);
    try {
      const response = await fetch("/api/auto-tag/llm-batches?page=1&pageSize=8");
      const result = await response.json();
      if (result.success) {
        const list = result.data.list || [];
        setLlmBatches(list);
        setCurrentLlmBatch((prev) => prev || list[0] || null);
      } else {
        message.error(result.message || "加载 LLM 候选批次失败");
      }
    } catch (error) {
      console.error(error);
      message.error("加载 LLM 候选批次失败");
    } finally {
      setLoadingLlmBatches(false);
    }
  };

  const fetchLlmCandidates = async (batchId: number) => {
    setLoadingLlmCandidates(true);
    try {
      const response = await fetch(`/api/auto-tag/llm-batches/${batchId}/candidates?page=1&pageSize=200`);
      const result = await response.json();
      if (result.success) {
        setCurrentLlmBatch(result.data.batch || null);
        setLlmCandidates(result.data.list || []);
      } else {
        message.error(result.message || "加载 LLM 候选失败");
      }
    } catch (error) {
      console.error(error);
      message.error("加载 LLM 候选失败");
    } finally {
      setLoadingLlmCandidates(false);
    }
  };

  useEffect(() => {
    fetchDimensions();
    fetchCompanies(1, pageSize);
    fetchBatches();
    fetchLlmBatches();
  }, [pageSize]);

  useEffect(() => {
    if (currentBatch?.batchId) {
      fetchBatchItems(currentBatch.batchId);
    } else {
      setBatchItems([]);
    }
  }, [currentBatch?.batchId]);

  useEffect(() => {
    if (currentLlmBatch?.batchId) {
      fetchLlmCandidates(currentLlmBatch.batchId);
    } else {
      setLlmCandidates([]);
    }
  }, [currentLlmBatch?.batchId]);

  useEffect(() => {
    if (!currentBatch || !["pending", "running"].includes(currentBatch.status)) {
      return;
    }

    const timer = window.setInterval(() => {
      fetchBatchItems(currentBatch.batchId);
      fetchBatches();
    }, 3000);

    return () => window.clearInterval(timer);
  }, [currentBatch]);

  useEffect(() => {
    if (!currentLlmBatch || !["pending", "running"].includes(currentLlmBatch.status)) {
      return;
    }

    const timer = window.setInterval(() => {
      fetchLlmCandidates(currentLlmBatch.batchId);
      fetchLlmBatches();
    }, 3000);

    return () => window.clearInterval(timer);
  }, [currentLlmBatch]);

  const selectedDimensionNames = useMemo(
    () => dimensions.filter((item) => selectedDimensions.includes(item.id)).map((item) => item.name),
    [dimensions, selectedDimensions],
  );

  const currentBatchProgress = useMemo(() => {
    if (!currentBatch || currentBatch.requestedCompanyCount <= 0) {
      return 0;
    }
    return Math.round(
      ((currentBatch.successCompanyCount + currentBatch.failedCompanyCount) / currentBatch.requestedCompanyCount) * 100,
    );
  }, [currentBatch]);

  const createBatch = async (companyIds: number[], batchName?: string) => {
    if (companyIds.length === 0) {
      message.warning("请至少选择或解析至少一家企业");
      return;
    }
    if (selectedDimensions.length === 0) {
      message.warning("请至少选择一个标签维度");
      return;
    }

    setCreatingBatch(true);
    try {
      const response = await fetch("/api/auto-tag/batches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          companyIds,
          dimensionIds: selectedDimensions,
          batchName,
        }),
      });
      const result = await response.json();
      if (result.success) {
        setCurrentBatch(result.data || null);
        setBatchItems([]);
        message.success("批次已创建，后台开始执行");
        fetchBatches();
        fetchCompanies(currentPage, pageSize, searchText);
      } else {
        message.error(result.message || "创建批次失败");
      }
    } catch (error) {
      console.error(error);
      message.error("创建批次失败");
    } finally {
      setCreatingBatch(false);
    }
  };

  const handleCreateBatch = async () => createBatch(selectedCompanyIds);

  const handleCreateUploadBatch = async () =>
    createBatch(
      uploadResolved?.matchedCompanies.map((item) => item.companyId) || [],
      "上传名单自动打标批次",
    );

  const handleResolveUpload = async () => {
    const identifiers = parseIdentifierText(uploadText);
    if (identifiers.length === 0) {
      message.warning("请先上传或粘贴企业名单");
      return;
    }

    setResolvingUpload(true);
    try {
      const response = await fetch("/api/auto-tag/companies/resolve-identifiers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifiers }),
      });
      const result = await response.json();
      if (result.success) {
        const resolved = result.data as UploadResolveResponse;
        setUploadResolved(resolved);
        setSelectedCompanyIds(resolved.matchedCompanies.map((item) => item.companyId));
        message.success(`已匹配 ${resolved.summary.matchedCompanyCount} 家企业，并同步到当前已选企业`);
      } else {
        message.error(result.message || "解析上传名单失败");
      }
    } catch (error) {
      console.error(error);
      message.error("解析上传名单失败");
    } finally {
      setResolvingUpload(false);
    }
  };

  const handleUploadFile = async (file: File) => {
    try {
      const text = await file.text();
      setUploadText(text);
      message.success(`已加载文件：${file.name}`);
    } catch (error) {
      console.error(error);
      message.error("读取文件失败");
    }
    return false;
  };

  const handleExport = (batchId: number) => {
    window.open(`/api/auto-tag/batches/${batchId}/export`, "_blank");
  };

  const handleCreateLlmBatch = async () => {
    if (selectedCompanyIds.length === 0) {
      message.warning("请至少选择一家企业");
      return;
    }

    setGeneratingLlmBatch(true);
    try {
      const response = await fetch("/api/auto-tag/llm-batches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          companyIds: selectedCompanyIds,
          batchName: "LLM 场景候选批次",
        }),
      });
      const result = await response.json();
      if (result.success) {
        setCurrentLlmBatch(result.data || null);
        setLlmCandidates([]);
        message.success("LLM 候选批次已创建，后台开始生成");
        fetchLlmBatches();
      } else {
        message.error(result.message || "创建 LLM 候选批次失败");
      }
    } catch (error) {
      console.error(error);
      message.error("创建 LLM 候选批次失败");
    } finally {
      setGeneratingLlmBatch(false);
    }
  };

  const handleApplyLlmCandidate = async (candidateId: number) => {
    setReviewingCandidateId(candidateId);
    try {
      const response = await fetch(`/api/auto-tag/llm-candidates/${candidateId}/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const result = await response.json();
      if (result.success) {
        message.success("候选标签已采纳");
        if (currentLlmBatch?.batchId) {
          fetchLlmCandidates(currentLlmBatch.batchId);
        }
        fetchCompanies(currentPage, pageSize, searchText);
      } else {
        message.error(result.message || "采纳失败");
      }
    } catch (error) {
      console.error(error);
      message.error("采纳失败");
    } finally {
      setReviewingCandidateId(null);
    }
  };

  const handleRejectLlmCandidate = async (candidateId: number) => {
    setReviewingCandidateId(candidateId);
    try {
      const response = await fetch(`/api/auto-tag/llm-candidates/${candidateId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const result = await response.json();
      if (result.success) {
        message.success("候选标签已驳回");
        if (currentLlmBatch?.batchId) {
          fetchLlmCandidates(currentLlmBatch.batchId);
        }
      } else {
        message.error(result.message || "驳回失败");
      }
    } catch (error) {
      console.error(error);
      message.error("驳回失败");
    } finally {
      setReviewingCandidateId(null);
    }
  };

  const renderStatusTag = (status: string) => {
    const meta = STATUS_META[status] || { color: "default", label: status };
    return <Tag color={meta.color}>{meta.label}</Tag>;
  };

  const companyColumns: TableProps<CompanyCandidate>["columns"] = [
    {
      title: "企业名称",
      dataIndex: "name",
      key: "name",
      render: (value: string, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.code}
          </Text>
        </Space>
      ),
    },
    {
      title: "已打标签数",
      dataIndex: "tagCount",
      key: "tagCount",
      width: 120,
      render: (value: number) => <Tag color="blue">{value} 个</Tag>,
    },
    {
      title: "成立日期",
      dataIndex: "establishDate",
      key: "establishDate",
      width: 140,
      render: (value?: string) => value || "-",
    },
    {
      title: "更新时间",
      dataIndex: "updateTime",
      key: "updateTime",
      width: 180,
      render: (value?: string) => (value ? new Date(value).toLocaleString() : "-"),
    },
  ];

  const batchColumns: TableProps<BatchRecord>["columns"] = [
    {
      title: "批次",
      key: "batchCode",
      render: (_: unknown, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.batchName || record.batchCode}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.batchCode}
          </Text>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (value: string) => renderStatusTag(value),
    },
    {
      title: "进度",
      key: "progress",
      width: 160,
      render: (_: unknown, record) => (
        <Text>
          {record.successCompanyCount + record.failedCompanyCount}/{record.requestedCompanyCount}
        </Text>
      ),
    },
    {
      title: "时间",
      dataIndex: "createdAt",
      key: "createdAt",
      width: 180,
      render: (value?: string) => (value ? new Date(value).toLocaleString() : "-"),
    },
    {
      title: "操作",
      key: "actions",
      width: 150,
      render: (_: unknown, record) => (
        <Space>
          <Button size="small" onClick={() => setCurrentBatch(record)}>
            查看
          </Button>
          <Button size="small" icon={<DownloadOutlined />} onClick={() => handleExport(record.batchId)}>
            导出
          </Button>
        </Space>
      ),
    },
  ];

  const llmBatchColumns: TableProps<LlmBatchRecord>["columns"] = [
    {
      title: "候选批次",
      key: "batchCode",
      render: (_: unknown, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.batchName || record.batchCode}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.batchCode}
          </Text>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (value: string) => renderStatusTag(value),
    },
    {
      title: "企业数",
      key: "progress",
      width: 120,
      render: (_: unknown, record) => (
        <Text>
          {record.successCompanyCount + record.failedCompanyCount}/{record.requestedCompanyCount}
        </Text>
      ),
    },
    {
      title: "时间",
      dataIndex: "createdAt",
      key: "createdAt",
      width: 180,
      render: (value?: string) => (value ? new Date(value).toLocaleString() : "-"),
    },
    {
      title: "操作",
      key: "actions",
      width: 90,
      render: (_: unknown, record) => (
        <Button size="small" onClick={() => setCurrentLlmBatch(record)}>
          查看
        </Button>
      ),
    },
  ];

  const resultColumns: TableProps<BatchItemRow>["columns"] = [
    {
      title: "企业名称",
      dataIndex: "name",
      key: "name",
      width: 240,
      render: (value: string, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.code}
          </Text>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (value: string) => renderStatusTag(value),
    },
    {
      title: "标签总数",
      dataIndex: "tagCount",
      key: "tagCount",
      width: 100,
      render: (value: number) => <Tag color="success">{value}</Tag>,
    },
    {
      title: "标签结果",
      key: "tags",
      render: (_: unknown, record) => (
        <Space size={[0, 6]} wrap>
          {record.tags.length > 0 ? (
            record.tags.map((tag) => (
              <Tag key={`${record.companyId}_${tag.id}`} color={DIMENSION_COLORS[tag.dimensionName] || "default"}>
                {tag.dimensionName} / {tag.name}
              </Tag>
            ))
          ) : (
            <Text type="secondary">未命中标签</Text>
          )}
        </Space>
      ),
    },
    {
      title: "错误信息",
      dataIndex: "errorMessage",
      key: "errorMessage",
      width: 220,
      render: (value?: string) => value || "-",
    },
  ];

  const llmCandidateColumns: TableProps<LlmCandidateRow>["columns"] = [
    {
      title: "企业",
      key: "companyName",
      width: 220,
      render: (_: unknown, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.companyName}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.creditCode}
          </Text>
        </Space>
      ),
    },
    {
      title: "候选类型",
      dataIndex: "candidateType",
      key: "candidateType",
      width: 110,
      render: (value: string) => (
        <Tag color={value === "mapped_tag" ? "green" : "orange"}>
          {value === "mapped_tag" ? "正式候选" : "未映射短语"}
        </Tag>
      ),
    },
    {
      title: "候选结果",
      key: "candidateName",
      render: (_: unknown, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.candidateName}</Text>
          {record.companyTagName ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              映射正式标签：{record.companyTagName}
            </Text>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>
              当前未映射到正式标签库
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: "置信度",
      dataIndex: "confidence",
      key: "confidence",
      width: 90,
      render: (value?: number | null) => (value ? <Tag color="blue">{value.toFixed(2)}</Tag> : "-"),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (value: string) => renderStatusTag(value),
    },
    {
      title: "生成原因",
      dataIndex: "reasonText",
      key: "reasonText",
      width: 260,
      render: (value?: string) => value || "-",
    },
    {
      title: "操作",
      key: "actions",
      width: 170,
      render: (_: unknown, record) => (
        <Space>
          <Button
            size="small"
            type="primary"
            disabled={record.candidateType !== "mapped_tag" || record.status !== "pending"}
            loading={reviewingCandidateId === record.candidateId}
            onClick={() => handleApplyLlmCandidate(record.candidateId)}
          >
            采纳
          </Button>
          <Button
            size="small"
            disabled={!["pending", "unmapped"].includes(record.status)}
            loading={reviewingCandidateId === record.candidateId}
            onClick={() => handleRejectLlmCandidate(record.candidateId)}
          >
            驳回
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }} size="large">
      <Card bordered={false} title="自动打标签">
        <Row gutter={24}>
          <Col xs={24} xl={9}>
            <Space direction="vertical" style={{ width: "100%" }} size="large">
              <Alert
                showIcon
                type="info"
                message="当前版本已切换为批次化执行：创建批次后后台写入 company_tag_batch / company_tag_batch_item，可追踪历史、查看进度并导出结果。"
              />

              <Card size="small" title="1. 选择标签维度">
                <Checkbox.Group
                  value={selectedDimensions}
                  onChange={(values) => setSelectedDimensions(values as number[])}
                  style={{ display: "grid", gap: 12 }}
                >
                  {dimensions.map((item) => (
                    <Checkbox key={item.id} value={item.id}>
                      <Space direction="vertical" size={0}>
                        <Text strong>{item.name}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {item.description}
                        </Text>
                      </Space>
                    </Checkbox>
                  ))}
                </Checkbox.Group>
              </Card>

              <Card size="small" title="2. 上传企业名单">
                <Space direction="vertical" style={{ width: "100%" }} size="middle">
                  <Alert
                    showIcon
                    type="info"
                    message="支持 TXT / CSV 上传或直接粘贴名单。系统会按 company_id、统一社会信用代码、企业名称精确匹配当前本地企业库。"
                  />
                  <Upload
                    accept=".txt,.csv"
                    showUploadList={false}
                    beforeUpload={(file) => handleUploadFile(file as File)}
                  >
                    <Button icon={<UploadOutlined />}>上传 TXT / CSV 名单</Button>
                  </Upload>
                  <TextArea
                    rows={6}
                    placeholder="每行一个企业标识；也支持逗号、分号、Tab 分隔。可填写 company_id、统一社会信用代码或企业名称。"
                    value={uploadText}
                    onChange={(event) => setUploadText(event.target.value)}
                  />
                  <Space>
                    <Button loading={resolvingUpload} onClick={handleResolveUpload}>
                      {resolvingUpload ? "解析中..." : "解析上传名单"}
                    </Button>
                    <Button
                      onClick={() => {
                        setUploadText("");
                        setUploadResolved(null);
                      }}
                    >
                      清空
                    </Button>
                  </Space>
                  {uploadResolved ? (
                    <Space direction="vertical" style={{ width: "100%" }} size="small">
                      <Row gutter={12}>
                        <Col span={8}>
                          <Statistic title="输入标识" value={uploadResolved.summary.inputCount} />
                        </Col>
                        <Col span={8}>
                          <Statistic title="匹配企业" value={uploadResolved.summary.matchedCompanyCount} />
                        </Col>
                        <Col span={8}>
                          <Statistic title="未匹配" value={uploadResolved.summary.unmatchedCount} />
                        </Col>
                      </Row>
                      {uploadResolved.summary.ambiguousCount > 0 ? (
                        <Alert
                          type="warning"
                          showIcon
                          message={`有 ${uploadResolved.summary.ambiguousCount} 个企业名称匹配到多家企业，未自动纳入本次批次。`}
                        />
                      ) : null}
                      {uploadResolved.unmatchedIdentifiers.length > 0 ? (
                        <Alert
                          type="warning"
                          showIcon
                          message={`未匹配标识：${uploadResolved.unmatchedIdentifiers.slice(0, 10).join("、")}${
                            uploadResolved.unmatchedIdentifiers.length > 10 ? " ..." : ""
                          }`}
                        />
                      ) : null}
                    </Space>
                  ) : null}
                </Space>
              </Card>

              <Card size="small" title="3. 创建批次">
                <Space direction="vertical" style={{ width: "100%" }} size="middle">
                  <Statistic title="已选企业" value={selectedCompanyIds.length} suffix="家" />
                  <Statistic title="上传匹配企业" value={uploadResolved?.summary.matchedCompanyCount || 0} suffix="家" />
                  <Statistic title="已选维度" value={selectedDimensions.length} suffix="个" />
                  <div>
                    <Text type="secondary">本次执行：</Text>
                    <Paragraph style={{ marginBottom: 0, marginTop: 8 }}>
                      {selectedDimensionNames.length > 0 ? (
                        selectedDimensionNames.map((name) => <Tag key={name}>{name}</Tag>)
                      ) : (
                        <Text type="secondary">尚未选择维度</Text>
                      )}
                    </Paragraph>
                  </div>
                  <Button
                    type="primary"
                    block
                    icon={<ThunderboltOutlined />}
                    loading={creatingBatch}
                    onClick={handleCreateBatch}
                  >
                    {creatingBatch ? "批次创建中..." : "创建自动打标批次"}
                  </Button>
                  <Button
                    block
                    disabled={!uploadResolved || uploadResolved.summary.matchedCompanyCount === 0}
                    loading={creatingBatch}
                    onClick={handleCreateUploadBatch}
                  >
                    按上传名单创建批次
                  </Button>
                </Space>
              </Card>
            </Space>
          </Col>

          <Col xs={24} xl={15}>
            <Card
              size="small"
              title="4. 选择企业"
              extra={(
                <Space>
                  <Input.Search
                    placeholder="搜索企业名称或统一社会信用代码"
                    allowClear
                    onSearch={(value) => {
                      setSearchText(value);
                      fetchCompanies(1, pageSize, value);
                    }}
                    style={{ width: 300 }}
                  />
                  <Button icon={<ReloadOutlined />} onClick={() => fetchCompanies(currentPage, pageSize, searchText)} />
                </Space>
              )}
            >
              <Table
                rowKey="key"
                loading={loadingCompanies}
                columns={companyColumns}
                dataSource={companies}
                rowSelection={{
                  selectedRowKeys: selectedCompanyIds,
                  onChange: (keys) => setSelectedCompanyIds(keys as number[]),
                }}
                pagination={{
                  current: currentPage,
                  pageSize,
                  total,
                  showSizeChanger: true,
                  onChange: (pageValue, pageSizeValue) => {
                    setPageSize(pageSizeValue);
                    fetchCompanies(pageValue, pageSizeValue, searchText);
                  },
                }}
              />
            </Card>
          </Col>
        </Row>
      </Card>

      <Card
        bordered={false}
        title="当前批次"
        extra={
          currentBatch ? (
            <Space wrap>
              <Button icon={<ReloadOutlined />} onClick={() => fetchBatchItems(currentBatch.batchId)} />
              <Button icon={<DownloadOutlined />} onClick={() => handleExport(currentBatch.batchId)}>
                导出
              </Button>
            </Space>
          ) : null
        }
      >
        {currentBatch ? (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Space wrap>
              <Text strong>{currentBatch.batchName || currentBatch.batchCode}</Text>
              {renderStatusTag(currentBatch.status)}
              {currentBatch.status === "running" ? <ClockCircleOutlined /> : <CheckCircleOutlined />}
            </Space>
            <Progress percent={currentBatchProgress} status={currentBatch.status === "failed" ? "exception" : undefined} />
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={8}>
                <Statistic title="企业总数" value={currentBatch.requestedCompanyCount} />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic title="成功" value={currentBatch.successCompanyCount} />
              </Col>
              <Col xs={24} sm={8}>
                <Statistic title="失败" value={currentBatch.failedCompanyCount} />
              </Col>
            </Row>
            <div>
              <Text type="secondary">批次维度：</Text>
              <Paragraph style={{ marginBottom: 0, marginTop: 8 }}>
                {currentBatch.dimensionNames.map((name) => <Tag key={name}>{name}</Tag>)}
              </Paragraph>
            </div>
            {currentBatch.errorMessage ? <Alert type="error" showIcon message={currentBatch.errorMessage} /> : null}
          </Space>
        ) : (
          <Empty description="暂无批次记录" />
        )}
      </Card>

      <Card
        bordered={false}
        title={(
          <Space>
            <span>批次结果</span>
            {currentBatch ? <Tag color="blue">{batchItems.length} 家企业</Tag> : null}
          </Space>
        )}
      >
        {currentBatch ? (
          <Table
            rowKey="batchItemId"
            columns={resultColumns}
            dataSource={batchItems}
            loading={loadingBatchItems}
            pagination={false}
            scroll={{ x: 1080 }}
          />
        ) : (
          <Empty description="请选择一个批次查看结果" />
        )}
      </Card>

      <Card
        bordered={false}
        title="历史批次"
        extra={<Button icon={<ReloadOutlined />} onClick={() => fetchBatches()} loading={loadingBatches} />}
      >
        <Table
          rowKey="batchId"
          columns={batchColumns}
          dataSource={batches}
          loading={loadingBatches}
          pagination={false}
          scroll={{ x: 760 }}
        />
      </Card>

      <Card
        bordered={false}
        title={(
          <Space>
            <span>上传名单解析结果</span>
            {uploadResolved ? <Tag color="blue">{uploadResolved.summary.matchedCompanyCount} 家匹配企业</Tag> : null}
          </Space>
        )}
      >
        {uploadResolved ? (
          <Table
            rowKey="companyId"
            columns={companyColumns}
            dataSource={uploadResolved.matchedCompanies}
            pagination={false}
            scroll={{ x: 760 }}
          />
        ) : (
          <Empty description="上传并解析企业名单后，可在这里预览命中的本地企业" />
        )}
      </Card>

      <Card
        bordered={false}
        title="当前 LLM 候选批次"
        extra={
          currentLlmBatch ? (
            <Button icon={<ReloadOutlined />} onClick={() => fetchLlmCandidates(currentLlmBatch.batchId)} />
          ) : null
        }
      >
        {currentLlmBatch ? (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Space wrap>
              <Text strong>{currentLlmBatch.batchName || currentLlmBatch.batchCode}</Text>
              {renderStatusTag(currentLlmBatch.status)}
              {currentLlmBatch.status === "running" ? <ClockCircleOutlined /> : <CheckCircleOutlined />}
            </Space>
            <Progress
              percent={
                currentLlmBatch.requestedCompanyCount > 0
                  ? Math.round(
                      ((currentLlmBatch.successCompanyCount + currentLlmBatch.failedCompanyCount) /
                        currentLlmBatch.requestedCompanyCount) *
                        100,
                    )
                  : 0
              }
              status={currentLlmBatch.status === "failed" ? "exception" : undefined}
            />
            <Row gutter={[16, 16]}>
              <Col xs={12} md={6}>
                <Statistic title="企业总数" value={currentLlmBatch.requestedCompanyCount} />
              </Col>
              <Col xs={12} md={6}>
                <Statistic title="成功" value={currentLlmBatch.successCompanyCount} />
              </Col>
              <Col xs={12} md={6}>
                <Statistic title="失败" value={currentLlmBatch.failedCompanyCount} />
              </Col>
              <Col xs={12} md={6}>
                <Statistic title="正式候选" value={currentLlmBatch.summary?.mapped_count || 0} />
              </Col>
            </Row>
            <Statistic title="未映射短语" value={currentLlmBatch.summary?.unmapped_count || 0} />
            {currentLlmBatch.errorMessage ? <Alert type="error" showIcon message={currentLlmBatch.errorMessage} /> : null}
          </Space>
        ) : (
          <Empty description="暂无 LLM 候选批次" />
        )}
      </Card>

      <Card
        bordered={false}
        title={(
          <Space>
            <span>LLM 场景候选</span>
            {currentLlmBatch ? <Tag color="blue">{llmCandidates.length} 条候选</Tag> : null}
          </Space>
        )}
      >
        {currentLlmBatch ? (
          <Table
            rowKey="candidateId"
            columns={llmCandidateColumns}
            dataSource={llmCandidates}
            loading={loadingLlmCandidates}
            pagination={false}
            scroll={{ x: 1180 }}
          />
        ) : (
          <Empty description="请选择一个 LLM 候选批次查看结果" />
        )}
      </Card>

      <Card
        bordered={false}
        title="LLM 场景候选批次"
        extra={<Button icon={<ReloadOutlined />} onClick={() => fetchLlmBatches()} loading={loadingLlmBatches} />}
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Alert
            showIcon
            type="warning"
            message="LLM 仅生成应用场景候选，不会直接写入正式标签。需要人工采纳后，才会写入 company_tag_map。"
          />
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            loading={generatingLlmBatch}
            onClick={handleCreateLlmBatch}
          >
            {generatingLlmBatch ? "候选生成中..." : "为已选企业生成 LLM 场景候选"}
          </Button>
          <Table
            rowKey="batchId"
            columns={llmBatchColumns}
            dataSource={llmBatches}
            loading={loadingLlmBatches}
            pagination={false}
            scroll={{ x: 720 }}
          />
        </Space>
      </Card>
    </Space>
  );
};

export default AutoTag;
