import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Steps,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import {
  CloudUploadOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FileTextOutlined,
  FundViewOutlined,
  InboxOutlined,
  PieChartOutlined,
  ReloadOutlined,
  SaveOutlined,
  TagsOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import type { TableProps, UploadFile, UploadProps } from "antd";

const { Text, Paragraph, Title } = Typography;
const { Dragger } = Upload;

type DimensionKey = "basic" | "business" | "tech" | "risk" | "region" | "industry" | "scene";
type ResultTabKey = "all" | "success" | "failed";

interface DimensionOption {
  id: number;
  key: string;
  name: string;
  color: string;
  description: string;
}

interface TagOption {
  id: number;
  name: string;
}

interface TagLibraryResponse {
  success?: boolean;
  message?: string;
  data?: {
    grouped?: Record<DimensionKey, TagOption[]>;
  };
}

interface ImportCandidate {
  rowIndex: number;
  companyName: string;
  creditCode: string;
  establishDate?: string;
  registerCapital?: string;
  paidCapital?: string;
  employeeCount?: string;
  insuredCount?: string;
  contactPhone?: string;
  emailBusiness?: string;
  registerAddress?: string;
  registerAddressDetail?: string;
  businessScope?: string;
  qualificationLabel?: string;
  industryBelong?: string;
  subdistrict?: string;
  reason?: string;
  matchedCompanyId?: number;
  matchedCompanyName?: string;
  matchedCreditCode?: string;
}

interface ImportPreviewResponse {
  headers: string[];
  summary: {
    inputCount: number;
    existingCount: number;
    duplicateCount: number;
    newCount: number;
    invalidCount: number;
  };
  newCompanies: ImportCandidate[];
  existingCompanies: ImportCandidate[];
  duplicateCompanies: ImportCandidate[];
  invalidRows: Array<{
    rowIndex: number;
    companyName?: string;
    creditCode?: string;
    reason: string;
  }>;
}

interface TagDetail {
  id: number;
  name: string;
  dimensionId: number;
  dimensionName: string;
  subdimensionId: number;
  subdimensionName: string;
  temporary?: boolean;
  localKey?: string;
}

interface TagBuckets {
  basic: string[];
  business: string[];
  tech: string[];
  risk: string[];
  region: string[];
  industry: string[];
  scene: string[];
}

interface TagResultItem {
  batchItemId: number;
  key: number;
  companyId: number;
  name: string;
  code: string;
  updateTime?: string | null;
  tagCount: number;
  tags: TagDetail[];
  dimensions: TagBuckets;
  status: "success" | "failed";
  errorMessage?: string;
}

interface ImportRunResponse {
  summary: {
    companyCount: number;
    successCompanyCount: number;
    failedCompanyCount: number;
    assignmentCount: number;
  };
  items: TagResultItem[];
}

const EMPTY_LIBRARY: Record<DimensionKey, TagOption[]> = {
  basic: [],
  business: [],
  tech: [],
  risk: [],
  region: [],
  industry: [],
  scene: [],
};

const DIMENSION_META_BY_KEY: Record<DimensionKey, { label: string; color: string; accent: string }> = {
  basic: { label: "基本信息", color: "#1890ff", accent: "#e6f4ff" },
  business: { label: "经营状况", color: "#1677ff", accent: "#edf6ff" },
  tech: { label: "知识产权", color: "#722ed1", accent: "#f9f0ff" },
  risk: { label: "风险信息", color: "#f5222d", accent: "#fff1f0" },
  region: { label: "街道地区", color: "#2f54eb", accent: "#f0f5ff" },
  industry: { label: "行业标签", color: "#fa8c16", accent: "#fff7e6" },
  scene: { label: "应用场景", color: "#52c41a", accent: "#f6ffed" },
};

const DIMENSION_NAME_TO_KEY: Record<string, DimensionKey> = {
  基本信息: "basic",
  经营状况: "business",
  知识产权: "tech",
  风险信息: "risk",
  街道地区: "region",
  行业标签: "industry",
  应用场景: "scene",
  基本信息维度: "basic",
  经营状况维度: "business",
  科技属性维度: "tech",
  风险管控维度: "risk",
  街道地区维度: "region",
  行业标签维度: "industry",
  应用场景维度: "scene",
};

function createEmptyTagBuckets(): TagBuckets {
  return {
    basic: [],
    business: [],
    tech: [],
    risk: [],
    region: [],
    industry: [],
    scene: [],
  };
}

function resolveDimensionKey(dimensionName: string): DimensionKey {
  return DIMENSION_NAME_TO_KEY[dimensionName] || "basic";
}

function rebuildBuckets(tags: TagDetail[]): TagBuckets {
  const buckets = createEmptyTagBuckets();
  for (const tag of tags) {
    const dimensionKey = resolveDimensionKey(tag.dimensionName);
    buckets[dimensionKey].push(tag.name);
  }
  return buckets;
}

function getTagIdentity(tag: TagDetail): string {
  return tag.localKey ? `${tag.id}:${tag.localKey}` : `${tag.id}:${tag.dimensionName}:${tag.name}`;
}

function buildExportCsv(items: TagResultItem[]): string {
  const lines = [
    ["company_name", "credit_code", "status", "tag_count", "tags"],
    ...items.map((item) => [
      item.name,
      item.code,
      item.status,
      String(item.tagCount),
      item.tags.map((tag) => `${tag.dimensionName}/${tag.name}`).join(" | "),
    ]),
  ];

  return lines
    .map((line) =>
      line
        .map((cell) => {
          const text = String(cell ?? "");
          if (/[",\n\r]/.test(text)) {
            return `"${text.replace(/"/g, '""')}"`;
          }
          return text;
        })
        .join(","),
    )
    .join("\n");
}

const AutoTag: React.FC = () => {
  const [dimensions, setDimensions] = useState<DimensionOption[]>([]);
  const [selectedDimensionIds, setSelectedDimensionIds] = useState<number[]>([]);
  const [tagLibrary, setTagLibrary] = useState<Record<DimensionKey, TagOption[]>>(EMPTY_LIBRARY);

  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [csvText, setCsvText] = useState("");
  const [previewData, setPreviewData] = useState<ImportPreviewResponse | null>(null);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [runningImportTagging, setRunningImportTagging] = useState(false);

  const [resultItems, setResultItems] = useState<TagResultItem[]>([]);
  const [savedResultItems, setSavedResultItems] = useState<TagResultItem[]>([]);
  const [runSummary, setRunSummary] = useState<ImportRunResponse["summary"] | null>(null);

  const [activeResultTab, setActiveResultTab] = useState<ResultTabKey>("all");
  const [selectedResultDimensionKeys, setSelectedResultDimensionKeys] = useState<DimensionKey[]>([]);
  const [detailCompanyId, setDetailCompanyId] = useState<number | null>(null);
  const [editingCompanyId, setEditingCompanyId] = useState<number | null>(null);
  const [selectedAddDimensionKey, setSelectedAddDimensionKey] = useState<DimensionKey | undefined>(undefined);
  const [selectedAddTagId, setSelectedAddTagId] = useState<number | undefined>(undefined);
  const [dirtyCompanyIds, setDirtyCompanyIds] = useState<Set<number>>(new Set());

  const currentStep = useMemo(() => {
    if (resultItems.length > 0) {
      return 3;
    }
    if (runningImportTagging) {
      return 2;
    }
    if (previewData || fileList.length > 0) {
      return 1;
    }
    return 0;
  }, [fileList.length, previewData, resultItems.length, runningImportTagging]);

  const filteredResults = useMemo(() => {
    let next = [...resultItems];
    if (activeResultTab !== "all") {
      next = next.filter((item) => item.status === activeResultTab);
    }
    if (selectedResultDimensionKeys.length > 0) {
      next = next.filter((item) =>
        selectedResultDimensionKeys.every((dimensionKey) =>
          item.tags.some((tag) => resolveDimensionKey(tag.dimensionName) === dimensionKey),
        ),
      );
    }
    return next;
  }, [activeResultTab, resultItems, selectedResultDimensionKeys]);

  const resultStats = useMemo(
    () => ({
      all: resultItems.length,
      success: resultItems.filter((item) => item.status === "success").length,
      failed: resultItems.filter((item) => item.status === "failed").length,
    }),
    [resultItems],
  );

  const averageTagCount = useMemo(() => {
    if (resultItems.length === 0) {
      return 0;
    }
    return Number((resultItems.reduce((sum, item) => sum + item.tagCount, 0) / resultItems.length).toFixed(1));
  }, [resultItems]);

  const currentDetailRecord = useMemo(
    () => resultItems.find((item) => item.companyId === detailCompanyId) || null,
    [detailCompanyId, resultItems],
  );

  const currentEditingRecord = useMemo(
    () => resultItems.find((item) => item.companyId === editingCompanyId) || null,
    [editingCompanyId, resultItems],
  );

  const addTagOptions = selectedAddDimensionKey
    ? tagLibrary[selectedAddDimensionKey].map((item) => ({
        label: item.name,
        value: item.id,
      }))
    : [];

  const fetchDimensions = async () => {
    try {
      const response = await fetch("/api/auto-tag/dimensions");
      const result = (await response.json()) as {
        success?: boolean;
        data?: DimensionOption[];
        message?: string;
      };
      if (!result.success) {
        message.error(result.message || "加载标签维度失败");
        return;
      }
      const nextDimensions = result.data || [];
      setDimensions(nextDimensions);
      setSelectedDimensionIds((prev) => (prev.length > 0 ? prev : nextDimensions.map((item) => item.id)));
    } catch (error) {
      console.error(error);
      message.error("加载标签维度失败");
    }
  };

  const fetchTagLibrary = async () => {
    try {
      const response = await fetch("/api/tags/library/options");
      const result = (await response.json()) as TagLibraryResponse;
      if (!result.success) {
        message.error(result.message || "加载标签库失败");
        return;
      }
      setTagLibrary({
        ...EMPTY_LIBRARY,
        ...(result.data?.grouped || {}),
      });
    } catch (error) {
      console.error(error);
      message.error("加载标签库失败");
    }
  };

  useEffect(() => {
    fetchDimensions();
    fetchTagLibrary();
  }, []);

  const uploadProps: UploadProps = {
    name: "file",
    multiple: false,
    maxCount: 1,
    fileList,
    showUploadList: false,
    beforeUpload: async (file) => {
      const lowerName = file.name.toLowerCase();
      if (!lowerName.endsWith(".csv")) {
        message.error("只支持 CSV 文件");
        return Upload.LIST_IGNORE;
      }
      try {
        const text = await file.text();
        setFileList([
          {
            uid: file.uid,
            name: file.name,
            size: file.size,
            type: file.type,
            status: "done",
            originFileObj: file,
          },
        ]);
        setCsvText(text);
        setPreviewData(null);
        setResultItems([]);
        setSavedResultItems([]);
        setRunSummary(null);
        setDirtyCompanyIds(new Set());
        message.success(`已载入 ${file.name}`);
      } catch (error) {
        console.error(error);
        message.error("读取 CSV 失败");
      }
      return false;
    },
    onRemove: () => {
      setFileList([]);
      setCsvText("");
      setPreviewData(null);
    },
  };

  const handlePreview = async () => {
    if (!csvText.trim()) {
      message.warning("请先上传待入库企业 CSV");
      return;
    }
    setLoadingPreview(true);
    try {
      const response = await fetch("/api/auto-tag/import/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ csvText }),
      });
      const result = (await response.json()) as {
        success?: boolean;
        data?: ImportPreviewResponse;
        message?: string;
      };
      if (!result.success || !result.data) {
        message.error(result.message || "CSV 预检失败");
        return;
      }
      setPreviewData(result.data);
      setResultItems([]);
      setSavedResultItems([]);
      setRunSummary(null);
      setDirtyCompanyIds(new Set());
      message.success(`预检完成，可新增企业 ${result.data.summary.newCount} 家`);
    } catch (error) {
      console.error(error);
      message.error("CSV 预检失败");
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleStartTagging = async () => {
    if (!previewData || previewData.newCompanies.length === 0) {
      message.warning("当前没有可新增企业可供自动打标签");
      return;
    }
    if (selectedDimensionIds.length === 0) {
      message.warning("请至少选择一个标签维度");
      return;
    }

    setRunningImportTagging(true);
    try {
      const response = await fetch("/api/auto-tag/import/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          records: previewData.newCompanies,
          dimensionIds: selectedDimensionIds,
        }),
      });
      const result = (await response.json()) as {
        success?: boolean;
        data?: ImportRunResponse;
        message?: string;
      };
      if (!result.success || !result.data) {
        message.error(result.message || "自动打标签失败");
        return;
      }
      setResultItems(result.data.items);
      setSavedResultItems(result.data.items);
      setRunSummary(result.data.summary);
      setDirtyCompanyIds(new Set());
      message.success("待入库企业自动打标签完成");
    } catch (error) {
      console.error(error);
      message.error("自动打标签失败");
    } finally {
      setRunningImportTagging(false);
    }
  };

  const handleExport = () => {
    if (resultItems.length === 0) {
      message.warning("当前没有可导出的打标签结果");
      return;
    }
    const csv = buildExportCsv(resultItems);
    const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `待入库企业自动打标签结果-${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleLocalSaveChanges = () => {
    const nextItems = resultItems.map((item) => ({
      ...item,
      tags: item.tags.map((tag) => ({
        ...tag,
        temporary: false,
        localKey: undefined,
      })),
    }));
    setResultItems(nextItems);
    setSavedResultItems(nextItems);
    setDirtyCompanyIds(new Set());
    message.success("当前会话内修改已保存");
  };

  const handleDiscardChanges = () => {
    setResultItems(savedResultItems);
    setDirtyCompanyIds(new Set());
    message.info("已恢复到最近一次保存结果");
  };

  const updateCompanyTags = (companyId: number, nextTags: TagDetail[]) => {
    setResultItems((prev) =>
      prev.map((item) =>
        item.companyId === companyId
          ? {
              ...item,
              tags: nextTags,
              tagCount: nextTags.length,
              dimensions: rebuildBuckets(nextTags),
            }
          : item,
      ),
    );
    setDirtyCompanyIds((prev) => {
      const next = new Set(prev);
      next.add(companyId);
      return next;
    });
  };

  const handleDeleteTag = (tag: TagDetail) => {
    if (!currentEditingRecord) {
      return;
    }
    updateCompanyTags(
      currentEditingRecord.companyId,
      currentEditingRecord.tags.filter((item) => getTagIdentity(item) !== getTagIdentity(tag)),
    );
  };

  const handleAddTag = () => {
    if (!currentEditingRecord || !selectedAddDimensionKey || !selectedAddTagId) {
      message.warning("请选择维度和标签");
      return;
    }
    const option = tagLibrary[selectedAddDimensionKey].find((item) => item.id === selectedAddTagId);
    if (!option) {
      return;
    }
    const duplicate = currentEditingRecord.tags.some((item) => item.id === option.id);
    if (duplicate) {
      message.warning("该标签已存在");
      return;
    }
    const nextTag: TagDetail = {
      id: option.id,
      name: option.name,
      dimensionId: 0,
      dimensionName: DIMENSION_META_BY_KEY[selectedAddDimensionKey].label,
      subdimensionId: 0,
      subdimensionName: "",
      temporary: true,
      localKey: `${currentEditingRecord.companyId}-${option.id}-${Date.now()}`,
    };
    updateCompanyTags(currentEditingRecord.companyId, [...currentEditingRecord.tags, nextTag]);
    setSelectedAddTagId(undefined);
    message.success("标签已加入当前会话结果");
  };

  const toggleResultDimension = (dimensionKey: DimensionKey) => {
    setSelectedResultDimensionKeys((prev) =>
      prev.includes(dimensionKey)
        ? prev.filter((item) => item !== dimensionKey)
        : [...prev, dimensionKey],
    );
  };

  const previewColumns: TableProps<ImportCandidate>["columns"] = [
    {
      title: "行号",
      dataIndex: "rowIndex",
      key: "rowIndex",
      width: 80,
    },
    {
      title: "企业名称",
      dataIndex: "companyName",
      key: "companyName",
    },
    {
      title: "统一社会信用代码",
      dataIndex: "creditCode",
      key: "creditCode",
      width: 220,
    },
    {
      title: "处理说明",
      dataIndex: "reason",
      key: "reason",
      width: 260,
      render: (value?: string) => value || "-",
    },
  ];

  const resultColumns: TableProps<TagResultItem>["columns"] = [
    {
      title: "企业",
      dataIndex: "name",
      key: "name",
      width: 260,
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
      width: 90,
      render: (value: string) => <Tag color={value === "success" ? "success" : "error"}>{value === "success" ? "成功" : "失败"}</Tag>,
    },
    {
      title: "标签数",
      dataIndex: "tagCount",
      key: "tagCount",
      width: 90,
      render: (value: number) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: "标签结果",
      key: "tags",
      render: (_: unknown, record) => (
        <Space size={[6, 8]} wrap>
          {record.tags.length > 0 ? (
            record.tags.map((tag) => {
              const meta = DIMENSION_META_BY_KEY[resolveDimensionKey(tag.dimensionName)];
              return (
                <Tag
                  key={getTagIdentity(tag)}
                  style={{
                    margin: 0,
                    borderRadius: 999,
                    paddingInline: 10,
                    border: tag.temporary ? `1px dashed ${meta.color}` : "1px solid transparent",
                    background: meta.accent,
                    color: meta.color,
                  }}
                >
                  {tag.dimensionName} / {tag.name}
                  {tag.temporary ? " (未保存)" : ""}
                </Tag>
              );
            })
          ) : (
            <Text type="secondary">未命中标签</Text>
          )}
        </Space>
      ),
    },
    {
      title: "操作",
      key: "action",
      width: 96,
      fixed: "right",
      render: (_: unknown, record) => (
        <Space size={2}>
          <Button type="text" size="small" icon={<EyeOutlined />} onClick={() => setDetailCompanyId(record.companyId)} />
          <Badge dot={dirtyCompanyIds.has(record.companyId)}>
            <Button type="text" size="small" icon={<EditOutlined />} onClick={() => setEditingCompanyId(record.companyId)} />
          </Badge>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }} size="large">
      <Card
        bordered={false}
        style={{
          borderRadius: 16,
          background: "#fafafa",
          boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)",
        }}
      >
        <Steps
          current={currentStep}
          items={[
            { title: "上传文件", icon: <CloudUploadOutlined />, description: "选择企业数据文件" },
            { title: "预览确认", icon: <FileTextOutlined />, description: "确认数据格式" },
            { title: "自动打标", icon: <ThunderboltOutlined />, description: "系统智能打标" },
            { title: "查看结果", icon: <FundViewOutlined />, description: "筛选和分析标签" },
          ]}
        />
      </Card>

      <Row gutter={[24, 24]}>
        <Col xs={24} xl={9}>
          <Card
            bordered={false}
            style={{ height: "100%", borderRadius: 16, boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)" }}
            title={(
              <Space>
                <Avatar style={{ background: "#1890ff" }} icon={<CloudUploadOutlined />} />
                <span>上传企业数据</span>
              </Space>
            )}
          >
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <Alert
                showIcon
                type="info"
                message={(
                  <Space wrap>
                    <span>支持 CSV 模板上传，上传后可直接预览并开始自动打标。</span>
                    <Button type="link" size="small" icon={<DownloadOutlined />} href="/api/auto-tag/import/template" target="_blank">
                      下载模板
                    </Button>
                  </Space>
                )}
                style={{ borderRadius: 8 }}
              />

              <Dragger
                {...uploadProps}
                style={{
                  borderRadius: 16,
                  border: "2px dashed #d9d9d9",
                  background: "#fafafa",
                }}
              >
                <p className="ant-upload-drag-icon">
                  <InboxOutlined style={{ fontSize: 48, color: "#1890ff" }} />
                </p>
                <p className="ant-upload-text" style={{ fontSize: 16 }}>
                  点击或拖拽文件到此区域
                </p>
                <p className="ant-upload-hint">系统将基于企业字段自动生成标签建议</p>
              </Dragger>

              {fileList.length > 0 ? (
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 12,
                    padding: "12px 16px",
                    borderRadius: 8,
                    border: "1px solid #b7eb8f",
                    background: "#f6ffed",
                  }}
                >
                  <Space>
                    <FileTextOutlined style={{ color: "#52c41a" }} />
                    <Text strong>{fileList[0]?.name}</Text>
                  </Space>
                  <Space size={4}>
                    <Button size="small" type="primary" icon={<EyeOutlined />} onClick={() => previewData && setPreviewModalOpen(true)} disabled={!previewData}>
                      预览详情
                    </Button>
                    <Button
                      type="link"
                      size="small"
                      onClick={() => {
                        setFileList([]);
                        setCsvText("");
                        setPreviewData(null);
                        setResultItems([]);
                        setSavedResultItems([]);
                        setRunSummary(null);
                        setDirtyCompanyIds(new Set());
                      }}
                    >
                      清除
                    </Button>
                  </Space>
                </div>
              ) : null}

              <div
                style={{
                  padding: 16,
                  borderRadius: 16,
                  background: "#fafafa",
                  border: "1px solid #f0f0f0",
                }}
              >
                <Space direction="vertical" style={{ width: "100%" }} size="small">
                  <Space style={{ justifyContent: "space-between", width: "100%" }}>
                    <Text strong>附加设置：打标维度</Text>
                    <Space size={4}>
                      <Button type="link" size="small" onClick={() => setSelectedDimensionIds(dimensions.map((item) => item.id))}>
                        全选
                      </Button>
                      <Button type="link" size="small" onClick={() => setSelectedDimensionIds([])}>
                        清空
                      </Button>
                    </Space>
                  </Space>
                  <Space size={[8, 8]} wrap>
                    {dimensions.map((dimension) => {
                      const active = selectedDimensionIds.includes(dimension.id);
                      const meta = DIMENSION_META_BY_KEY[resolveDimensionKey(dimension.name)];
                      return (
                        <Tag
                          key={dimension.id}
                          onClick={() =>
                            setSelectedDimensionIds((prev) =>
                              prev.includes(dimension.id)
                                ? prev.filter((item) => item !== dimension.id)
                                : [...prev, dimension.id],
                            )
                          }
                          style={{
                            margin: 0,
                            cursor: "pointer",
                            borderRadius: 999,
                            padding: "6px 12px",
                            border: active ? `1px solid ${meta.color}` : "1px solid #d9d9d9",
                            background: active ? meta.accent : "#fff",
                            color: active ? meta.color : "#595959",
                          }}
                        >
                          {dimension.name}
                        </Tag>
                      );
                    })}
                  </Space>
                </Space>
              </div>

              <Button type="primary" onClick={handlePreview} loading={loadingPreview} block>
                {loadingPreview ? "预览中..." : "开始预览确认"}
              </Button>
              <Text type="secondary" style={{ fontSize: 12 }}>
                补充规则：系统会先做库内查重，只对不在数据库内、拟入库的企业执行自动打标签。
              </Text>
            </Space>
          </Card>
        </Col>

        <Col xs={24} xl={7}>
          <Card
            bordered={false}
            style={{ height: "100%", borderRadius: 16, boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)" }}
            title={(
              <Space>
                <Avatar style={{ background: "#52c41a" }} icon={<FileTextOutlined />} />
                <span>预览确认</span>
                {previewData ? <Badge count={previewData.summary.inputCount} style={{ backgroundColor: "#52c41a" }} /> : null}
              </Space>
            )}
          >
            {previewData ? (
              <Space direction="vertical" style={{ width: "100%" }} size="middle">
                <Text type="secondary">
                  {previewData.newCompanies.length > 0
                    ? "已完成预览确认，以下为即将进入自动打标的企业预览。"
                    : "已完成预览确认，当前文件中没有可进入自动打标的企业。"}
                </Text>

                <div style={{ maxHeight: 360, overflowY: "auto", paddingRight: 4 }}>
                  <Space direction="vertical" style={{ width: "100%" }} size="small">
                    {(previewData.newCompanies.length > 0 ? previewData.newCompanies : previewData.existingCompanies).slice(0, 10).map((item, index) => (
                      <div
                        key={`${item.rowIndex}-${item.creditCode || item.companyName}`}
                        style={{
                          display: "flex",
                          gap: 12,
                          alignItems: "center",
                          padding: "12px 14px",
                          borderRadius: 14,
                          background: "#fafafa",
                          border: "1px solid #f0f0f0",
                        }}
                      >
                        <div
                          style={{
                            width: 28,
                            height: 28,
                            flexShrink: 0,
                            borderRadius: "50%",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background: "#1677ff",
                            color: "#fff",
                            fontSize: 12,
                            fontWeight: 600,
                          }}
                        >
                          {index + 1}
                        </div>
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <Text strong style={{ display: "block" }}>
                            {item.companyName}
                          </Text>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {item.creditCode || "未提供统一社会信用代码"}
                          </Text>
                        </div>
                        {previewData.newCompanies.length > 0 ? <Tag color="success">可新增</Tag> : <Tag>库内/重复</Tag>}
                      </div>
                    ))}
                  </Space>
                </div>

                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <Space size={[6, 6]} wrap>
                    <Tag color="processing">总计 {previewData.summary.inputCount} 家</Tag>
                    <Tag color="success">可新增 {previewData.summary.newCount} 家</Tag>
                    <Tag color="default">已在库 {previewData.summary.existingCount} 家</Tag>
                    <Tag color="warning">疑似重复 {previewData.summary.duplicateCount} 家</Tag>
                    {previewData.summary.invalidCount > 0 ? <Tag color="error">无效 {previewData.summary.invalidCount} 行</Tag> : null}
                  </Space>
                  <Button type="link" icon={<EyeOutlined />} onClick={() => setPreviewModalOpen(true)}>
                    查看完整预览
                  </Button>
                </Space>
              </Space>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="上传文件后，这里展示预览确认结果" style={{ paddingBlock: 48 }} />
            )}
          </Card>
        </Col>

        <Col xs={24} xl={8}>
          <Card
            bordered={false}
            style={{ height: "100%", borderRadius: 16, boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)" }}
            title={(
              <Space>
                <Avatar style={{ background: "#722ed1" }} icon={<PieChartOutlined />} />
                <span>打标进度与统计</span>
                {runSummary ? <Badge count={resultItems.length} style={{ backgroundColor: "#722ed1" }} /> : null}
              </Space>
            )}
          >
            {runSummary || runningImportTagging ? (
              <Space direction="vertical" style={{ width: "100%" }} size="middle">
                <div
                  style={{
                    padding: 18,
                    borderRadius: 16,
                    background: "linear-gradient(135deg, #6f61ff 0%, #8f5ce6 100%)",
                    color: "#fff",
                  }}
                >
                  <Space direction="vertical" size={2} style={{ width: "100%" }}>
                    <Text style={{ color: "rgba(255,255,255,0.82)" }}>当前任务</Text>
                    <Title level={5} style={{ color: "#fff", margin: 0 }}>
                      自动打标
                    </Title>
                  </Space>
                  <Progress
                    percent={runSummary ? 100 : 75}
                    status={runSummary ? "success" : "active"}
                    style={{ marginTop: 16 }}
                  />
                </div>

                <Row gutter={12}>
                  <Col span={12}>
                    <Card size="small" style={{ borderRadius: 16, background: "#f6ffed", border: "1px solid #b7eb8f" }}>
                      <Statistic title="成功" value={runSummary?.successCompanyCount || 0} valueStyle={{ color: "#52c41a" }} />
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card size="small" style={{ borderRadius: 16, background: "#fff2f0", border: "1px solid #ffccc7" }}>
                      <Statistic title="失败" value={runSummary?.failedCompanyCount || 0} valueStyle={{ color: "#f5222d" }} />
                    </Card>
                  </Col>
                </Row>

                <Card size="small" style={{ borderRadius: 16, background: "linear-gradient(135deg, #eef4ff 0%, #faf5ff 100%)", border: "1px solid #d6e4ff" }}>
                  <Statistic title="企业平均标签数" value={averageTagCount} suffix="个 / 家" />
                  <Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 8 }}>
                    总标签数：{runSummary?.assignmentCount || 0}，企业数：{runSummary?.companyCount || 0}
                  </Paragraph>
                </Card>

                {dirtyCompanyIds.size > 0 ? (
                  <Space direction="vertical" style={{ width: "100%" }} size="small">
                    <Button type="primary" icon={<SaveOutlined />} onClick={handleLocalSaveChanges} block>
                      保存本次修改（{dirtyCompanyIds.size} 家）
                    </Button>
                    <Button icon={<ReloadOutlined />} onClick={handleDiscardChanges} block>
                      放弃本次修改
                    </Button>
                  </Space>
                ) : null}

                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <Button icon={<DownloadOutlined />} onClick={handleExport}>
                    导出结果
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={handleStartTagging} loading={runningImportTagging}>
                    重新打标
                  </Button>
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  补充功能：支持按维度打标、结果编辑、会话内保存和导出 CSV。
                </Text>
              </Space>
            ) : (
              <Space direction="vertical" style={{ width: "100%" }} size="large">
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无打标结果" style={{ paddingBlock: 28 }} />
                <Button
                  type="primary"
                  icon={<ThunderboltOutlined />}
                  loading={runningImportTagging}
                  onClick={handleStartTagging}
                  disabled={!previewData || previewData.newCompanies.length === 0}
                  block
                >
                  {runningImportTagging ? "打标中..." : "开始自动打标"}
                </Button>
              </Space>
            )}
          </Card>
        </Col>
      </Row>

      <Card
            bordered={false}
        style={{ borderRadius: 16, boxShadow: "0 8px 24px rgba(15, 23, 42, 0.05)" }}
        title={(
          <Space>
            <Avatar style={{ background: "#fa8c16" }} icon={<TagsOutlined />} />
            <span>标签结果明细</span>
            {resultItems.length > 0 ? <Badge count={filteredResults.length} style={{ backgroundColor: "#fa8c16" }} /> : null}
            {dirtyCompanyIds.size > 0 ? <Tag color="warning">有未保存修改</Tag> : null}
          </Space>
        )}
        extra={resultItems.length > 0 ? (
          <Space size={8}>
            <Button icon={<DeleteOutlined />} size="small" onClick={() => {
              setResultItems([]);
              setSavedResultItems([]);
              setRunSummary(null);
              setDirtyCompanyIds(new Set());
              setSelectedResultDimensionKeys([]);
            }}>
              清空
            </Button>
            <Button icon={<DownloadOutlined />} size="small" onClick={handleExport}>导出</Button>
          </Space>
        ) : null}
      >
        {resultItems.length > 0 ? (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Space size={[8, 10]} wrap>
              {(Object.entries(DIMENSION_META_BY_KEY) as Array<[DimensionKey, (typeof DIMENSION_META_BY_KEY)[DimensionKey]]>).map(
                ([dimensionKey, meta]) => {
                  const active = selectedResultDimensionKeys.includes(dimensionKey);
                  return (
                    <Tag
                      key={dimensionKey}
                      onClick={() => toggleResultDimension(dimensionKey)}
                      style={{
                        margin: 0,
                        cursor: "pointer",
                        borderRadius: 999,
                        padding: "6px 12px",
                        border: active ? `1px solid ${meta.color}` : "1px solid #d9d9d9",
                        background: active ? meta.accent : "#fff",
                        color: active ? meta.color : "#595959",
                      }}
                    >
                      {meta.label}
                    </Tag>
                  );
                },
              )}
              {selectedResultDimensionKeys.length > 0 ? (
                <Button type="link" size="small" onClick={() => setSelectedResultDimensionKeys([])}>
                  清空筛选
                </Button>
              ) : null}
            </Space>

            <Tabs
              activeKey={activeResultTab}
              onChange={(value) => setActiveResultTab(value as ResultTabKey)}
              items={[
                { key: "all", label: `全部 (${resultStats.all})` },
                { key: "success", label: `成功 (${resultStats.success})` },
                { key: "failed", label: `失败 (${resultStats.failed})` },
              ]}
            />

            <Table
              rowKey="batchItemId"
              columns={resultColumns}
              dataSource={filteredResults}
              pagination={{ pageSize: 8, showSizeChanger: true, showQuickJumper: true, showTotal: (value) => `共 ${value} 条` }}
              scroll={{ x: 1180 }}
            />
            <Text type="secondary" style={{ fontSize: 12 }}>
              附加功能：支持筛选、查看详情、人工编辑标签，并将修改保存在当前会话中。
            </Text>
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请先上传文件并开始自动打标" style={{ paddingBlock: 48 }} />
        )}
      </Card>

      <Modal title="完整文件预览" open={previewModalOpen} onCancel={() => setPreviewModalOpen(false)} footer={null} width={980}>
        {previewData ? (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Alert showIcon type="success" message={`当前文件共 ${previewData.summary.inputCount} 家企业，其中可新增 ${previewData.summary.newCount} 家。`} />
            {previewData.existingCompanies.length > 0 ? (
              <>
                <Title level={5} style={{ marginBottom: 0 }}>
                  已在库企业
                </Title>
                <Table rowKey={(record) => `existing-${record.rowIndex}`} columns={previewColumns} dataSource={previewData.existingCompanies} pagination={false} />
              </>
            ) : null}
            {previewData.duplicateCompanies.length > 0 ? (
              <>
                <Title level={5} style={{ marginBottom: 0 }}>
                  疑似重复企业
                </Title>
                <Table rowKey={(record) => `duplicate-${record.rowIndex}`} columns={previewColumns} dataSource={previewData.duplicateCompanies} pagination={false} />
              </>
            ) : null}
            {previewData.newCompanies.length > 0 ? (
              <>
                <Title level={5} style={{ marginBottom: 0 }}>
                  可新增企业
                </Title>
                <Table rowKey={(record) => `new-${record.rowIndex}`} columns={previewColumns} dataSource={previewData.newCompanies} pagination={false} />
              </>
            ) : null}
          </Space>
        ) : null}
      </Modal>

      <Modal title="标签详情" open={Boolean(currentDetailRecord)} onCancel={() => setDetailCompanyId(null)} footer={null} width={720}>
        {currentDetailRecord ? (
          <Space direction="vertical" style={{ width: "100%" }} size="middle">
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="企业名称">{currentDetailRecord.name}</Descriptions.Item>
              <Descriptions.Item label="统一社会信用代码">{currentDetailRecord.code}</Descriptions.Item>
              <Descriptions.Item label="处理状态">
                <Tag color={currentDetailRecord.status === "success" ? "success" : "error"}>
                  {currentDetailRecord.status === "success" ? "成功" : "失败"}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="标签总数">{currentDetailRecord.tagCount}</Descriptions.Item>
            </Descriptions>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                padding: 16,
                borderRadius: 16,
                background: "#fafafa",
                border: "1px solid #f0f0f0",
              }}
            >
              {currentDetailRecord.tags.length > 0 ? (
                currentDetailRecord.tags.map((tag) => {
                  const meta = DIMENSION_META_BY_KEY[resolveDimensionKey(tag.dimensionName)];
                  return (
                    <Tag
                      key={getTagIdentity(tag)}
                      style={{
                        margin: 0,
                        borderRadius: 999,
                        paddingInline: 10,
                        border: tag.temporary ? `1px dashed ${meta.color}` : "1px solid transparent",
                        background: meta.accent,
                        color: meta.color,
                      }}
                    >
                      [{tag.dimensionName}] {tag.name}
                      {tag.temporary ? " (未保存)" : ""}
                    </Tag>
                  );
                })
              ) : (
                <Text type="secondary">暂无标签</Text>
              )}
            </div>
          </Space>
        ) : null}
      </Modal>

      <Modal
        title={currentEditingRecord ? `编辑标签：${currentEditingRecord.name}` : "编辑标签"}
        open={Boolean(currentEditingRecord)}
        onCancel={() => {
          setEditingCompanyId(null);
          setSelectedAddDimensionKey(undefined);
          setSelectedAddTagId(undefined);
        }}
        footer={null}
        width={820}
      >
        {currentEditingRecord ? (
          <Space direction="vertical" style={{ width: "100%" }} size="large">
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="统一社会信用代码">{currentEditingRecord.code}</Descriptions.Item>
              <Descriptions.Item label="当前标签数">{currentEditingRecord.tagCount}</Descriptions.Item>
            </Descriptions>

            <div style={{ padding: 16, borderRadius: 16, background: "#fafafa", border: "1px solid #f0f0f0" }}>
              <Space direction="vertical" style={{ width: "100%" }} size="middle">
                <Text strong>当前标签</Text>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {currentEditingRecord.tags.length > 0 ? (
                    currentEditingRecord.tags.map((tag) => {
                      const meta = DIMENSION_META_BY_KEY[resolveDimensionKey(tag.dimensionName)];
                      return (
                        <Tag
                          key={getTagIdentity(tag)}
                          closable
                          onClose={(event) => {
                            event.preventDefault();
                            handleDeleteTag(tag);
                          }}
                          style={{
                            margin: 0,
                            borderRadius: 999,
                            paddingInline: 10,
                            border: tag.temporary ? `1px dashed ${meta.color}` : "1px solid transparent",
                            background: meta.accent,
                            color: meta.color,
                          }}
                        >
                          {tag.dimensionName} / {tag.name}
                          {tag.temporary ? " (未保存)" : ""}
                        </Tag>
                      );
                    })
                  ) : (
                    <Text type="secondary">暂无标签</Text>
                  )}
                </div>
              </Space>
            </div>

            <div style={{ padding: 16, borderRadius: 16, background: "#fbfdff", border: "1px solid #d6e4ff" }}>
              <Space direction="vertical" style={{ width: "100%" }} size="middle">
                <Text strong>添加标签</Text>
                <Row gutter={12}>
                  <Col span={10}>
                    <Select<DimensionKey>
                      style={{ width: "100%" }}
                      placeholder="选择维度"
                      value={selectedAddDimensionKey}
                      onChange={(value) => {
                        setSelectedAddDimensionKey(value);
                        setSelectedAddTagId(undefined);
                      }}
                      options={(Object.entries(DIMENSION_META_BY_KEY) as Array<[DimensionKey, (typeof DIMENSION_META_BY_KEY)[DimensionKey]]>).map(
                        ([value, meta]) => ({
                          label: meta.label,
                          value,
                        }),
                      )}
                    />
                  </Col>
                  <Col span={10}>
                    <Select<number>
                      style={{ width: "100%" }}
                      placeholder="选择标签"
                      value={selectedAddTagId}
                      onChange={(value) => setSelectedAddTagId(value)}
                      options={addTagOptions}
                      showSearch
                      optionFilterProp="label"
                    />
                  </Col>
                  <Col span={4}>
                    <Button type="primary" onClick={handleAddTag} block>
                      添加
                    </Button>
                  </Col>
                </Row>
              </Space>
            </div>

            <Space style={{ width: "100%", justifyContent: "space-between" }}>
              <Text type="secondary">这里的修改只作用于当前待入库企业打标签结果，不会写入正式数据库。</Text>
              <Button type="primary" icon={<SaveOutlined />} onClick={handleLocalSaveChanges}>
                保存当前会话修改
              </Button>
            </Space>
          </Space>
        ) : null}
      </Modal>
    </Space>
  );
};

export default AutoTag;
