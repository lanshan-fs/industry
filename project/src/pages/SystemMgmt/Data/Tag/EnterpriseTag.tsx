import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  Modal,
  Popover,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  CheckOutlined,
  CloseCircleFilled,
  EditOutlined,
  EyeOutlined,
  PlusOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import type { TableProps } from "antd";

const { Text } = Typography;

type VerificationAction = () => Promise<boolean>;

type DimensionKey = "basic" | "business" | "tech" | "risk" | "region" | "industry" | "scene";

interface TagOption {
  id: number;
  name: string;
}

interface TagDetail {
  id: number;
  name: string;
  dimensionId: number;
  dimensionName: string;
  subdimensionId: number;
  subdimensionName: string;
  taggedAt?: string;
}

interface EnterpriseDimensions {
  basic: string[];
  business: string[];
  tech: string[];
  risk: string[];
  region: string[];
  industry: string[];
  scene: string[];
}

interface EnterpriseRow {
  key: number;
  companyId: number;
  name: string;
  code: string;
  updateTime?: string;
  tagCount: number;
  dimensions: EnterpriseDimensions;
  tags: TagDetail[];
}

interface TagLibraryResponse {
  data?: {
    grouped?: Record<DimensionKey, TagOption[]>;
  };
}

const DIMENSION_META: Record<DimensionKey, { label: string; color: string }> = {
  basic: { label: "基本信息", color: "cyan" },
  business: { label: "经营状况", color: "blue" },
  tech: { label: "知识产权", color: "purple" },
  risk: { label: "风险信息", color: "red" },
  region: { label: "街道地区", color: "geekblue" },
  industry: { label: "行业标签", color: "orange" },
  scene: { label: "应用场景", color: "green" },
};

const EMPTY_LIBRARY: Record<DimensionKey, TagOption[]> = {
  basic: [],
  business: [],
  tech: [],
  risk: [],
  region: [],
  industry: [],
  scene: [],
};

const EnterpriseTag: React.FC = () => {
  const [data, setData] = useState<EnterpriseRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [searchText, setSearchText] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [tagLibrary, setTagLibrary] = useState<Record<DimensionKey, TagOption[]>>(EMPTY_LIBRARY);
  const [popoverOpenState, setPopoverOpenState] = useState<Record<string, boolean>>({});
  const [editingKeys, setEditingKeys] = useState<Set<number>>(new Set());
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [currentRecord, setCurrentRecord] = useState<EnterpriseRow | null>(null);
  const [verificationOpen, setVerificationOpen] = useState(false);
  const [verificationTitle, setVerificationTitle] = useState("");
  const [verificationDescription, setVerificationDescription] = useState("");
  const [verificationText, setVerificationText] = useState("");
  const [verificationSubmitting, setVerificationSubmitting] = useState(false);
  const verificationActionRef = useRef<VerificationAction | null>(null);

  const allDimensionKeys = useMemo(() => Object.keys(DIMENSION_META) as DimensionKey[], []);

  const fetchData = async (page = 1, size = 10, keyword = "") => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/tags/companies?page=${page}&pageSize=${size}&keyword=${encodeURIComponent(keyword)}`,
      );
      const result = await response.json();
      if (result.success) {
        setData(result.data.list || []);
        setTotal(result.data.total || 0);
        setCurrentPage(page);
      } else {
        message.error(result.message || "加载企业标签失败");
      }
    } catch (error) {
      console.error(error);
      message.error("加载企业标签失败");
    } finally {
      setLoading(false);
    }
  };

  const fetchTagLibrary = async () => {
    try {
      const response = await fetch("/api/tags/library/options");
      const result: TagLibraryResponse & { success?: boolean; message?: string } = await response.json();
      if (result.success) {
        setTagLibrary({
          ...EMPTY_LIBRARY,
          ...(result.data?.grouped || {}),
        });
      } else {
        message.error(result.message || "加载标签库失败");
      }
    } catch (error) {
      console.error(error);
      message.error("加载标签库失败");
    }
  };

  useEffect(() => {
    fetchData(1, pageSize);
    fetchTagLibrary();
  }, [pageSize]);

  const handleSearch = (value: string) => {
    setSearchText(value);
    fetchData(1, pageSize, value);
  };

  const toggleEditMode = (key: number) => {
    const next = new Set(editingKeys);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    setEditingKeys(next);
  };

  const openVerification = (title: string, description: string, action: VerificationAction) => {
    verificationActionRef.current = action;
    setVerificationTitle(title);
    setVerificationDescription(description);
    setVerificationText("");
    setVerificationOpen(true);
  };

  const closeVerification = () => {
    if (verificationSubmitting) {
      return;
    }
    verificationActionRef.current = null;
    setVerificationOpen(false);
    setVerificationText("");
    setVerificationTitle("");
    setVerificationDescription("");
  };

  const handleVerificationConfirm = async () => {
    if (verificationText.trim() !== "确认") {
      message.warning('请输入“确认”后再继续');
      return;
    }
    const action = verificationActionRef.current;
    if (!action) {
      closeVerification();
      return;
    }
    setVerificationSubmitting(true);
    try {
      const success = await action();
      if (success) {
        verificationActionRef.current = null;
        setVerificationOpen(false);
        setVerificationText("");
        setVerificationTitle("");
        setVerificationDescription("");
      }
    } finally {
      setVerificationSubmitting(false);
    }
  };

  const executeAddTag = async (record: EnterpriseRow, dimension: DimensionKey, optionId: number) => {
    const popoverKey = `${record.key}_${dimension}`;
    setPopoverOpenState((prev) => ({ ...prev, [popoverKey]: false }));

    const option = (tagLibrary[dimension] || []).find((item) => item.id === optionId);
    if (!option) {
      return false;
    }
    if (record.dimensions[dimension].includes(option.name)) {
      message.warning("该标签已存在");
      return false;
    }

    try {
      const response = await fetch("/api/tags/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ companyId: record.companyId, tagId: option.id }),
      });
      const result = await response.json();
      if (result.success) {
        message.success("打标成功");
        fetchData(currentPage, pageSize, searchText);
        return true;
      } else {
        message.error(result.message || "打标失败");
      }
    } catch (error) {
      console.error(error);
      message.error("打标失败");
    }
    return false;
  };

  const requestAddTag = (record: EnterpriseRow, dimension: DimensionKey, optionId: number) => {
    const option = (tagLibrary[dimension] || []).find((item) => item.id === optionId);
    if (!option) {
      return;
    }
    openVerification(
      `确认添加标签“${option.name}”吗？`,
      `请输入“确认”后为企业“${record.name}”添加该标签。`,
      () => executeAddTag(record, dimension, optionId),
    );
  };

  const executeDeleteTag = async (record: EnterpriseRow, tagName: string) => {
    try {
      const response = await fetch("/api/tags/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ companyId: record.companyId, tagName }),
      });
      const result = await response.json();
      if (result.success) {
        message.success("标签已删除");
        fetchData(currentPage, pageSize, searchText);
        return true;
      } else {
        message.error(result.message || "删除失败");
      }
    } catch (error) {
      console.error(error);
      message.error("删除失败");
    }
    return false;
  };

  const handleDeleteTagConfirm = (record: EnterpriseRow, tagName: string) => {
    openVerification(
      `确认删除标签“${tagName}”吗？`,
      `请输入“确认”后从企业“${record.name}”中移除该标签。此操作会直接影响当前正式标签结果。`,
      () => executeDeleteTag(record, tagName),
    );
  };

  const renderDimensionCell = (
    tags: string[] = [],
    record: EnterpriseRow,
    dimension: DimensionKey,
  ) => {
    const editing = editingKeys.has(record.key);
    const popoverKey = `${record.key}_${dimension}`;
    const options = (tagLibrary[dimension] || []).map((option) => ({
      label: option.name,
      value: option.id,
    }));

    return (
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4, minHeight: 32 }}>
        {tags.map((tagName) => (
          <div key={tagName} style={{ position: "relative" }}>
            <Tag color={DIMENSION_META[dimension].color} style={{ margin: 0 }}>
              {tagName}
            </Tag>
            {editing ? (
              <CloseCircleFilled
                style={{
                  position: "absolute",
                  top: -5,
                  right: -5,
                  color: "#f5222d",
                  cursor: "pointer",
                  fontSize: 12,
                  background: "#fff",
                  borderRadius: "50%",
                }}
                onClick={() => handleDeleteTagConfirm(record, tagName)}
              />
            ) : null}
          </div>
        ))}
        {editing ? (
          <Popover
            trigger="click"
            open={popoverOpenState[popoverKey] || false}
            onOpenChange={(visible) => setPopoverOpenState((prev) => ({ ...prev, [popoverKey]: visible }))}
            content={(
              <Select
                showSearch
                style={{ width: 220 }}
                placeholder="选择标签"
                options={options}
                onChange={(value) => requestAddTag(record, dimension, value)}
              />
            )}
          >
            <Button type="dashed" size="small" icon={<PlusOutlined />} />
          </Popover>
        ) : null}
      </div>
    );
  };

  const columns: TableProps<EnterpriseRow>["columns"] = [
    {
      title: "企业基本信息",
      key: "info",
      width: 260,
      fixed: "left",
      render: (_, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{record.name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.code}
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            共 {record.tagCount} 个标签
          </Text>
        </Space>
      ),
    },
    ...allDimensionKeys.map((dimension) => ({
      title: DIMENSION_META[dimension].label,
      dataIndex: ["dimensions", dimension],
      key: dimension,
      width: 220,
      render: (value: string[], record: EnterpriseRow) => renderDimensionCell(value, record, dimension),
    })),
    {
      title: "操作",
      key: "action",
      width: 120,
      fixed: "right",
      align: "center",
      render: (_, record) => {
        const editing = editingKeys.has(record.key);
        return (
          <Space>
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => {
                setCurrentRecord(record);
                setViewModalOpen(true);
              }}
            />
            <Button
              type={editing ? "primary" : "link"}
              size="small"
              icon={editing ? <CheckOutlined /> : <EditOutlined />}
              onClick={() => toggleEditMode(record.key)}
            >
              {editing ? "完成" : "编辑"}
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card bordered={false} style={{ marginBottom: 16 }}>
        <Space size="large">
          <Input.Search
            placeholder="搜索企业名称或统一社会信用代码"
            onSearch={handleSearch}
            style={{ width: 360 }}
            enterButton
          />
          <Button
            type="primary"
            onClick={() => fetchData(currentPage, pageSize, searchText)}
            icon={<ReloadOutlined />}
          >
            刷新
          </Button>
        </Space>
      </Card>

      <Card bordered={false}>
        <Table
          rowKey="key"
          columns={columns}
          dataSource={data}
          loading={loading}
          scroll={{ x: 1800 }}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (nextPage, nextPageSize) => {
              setPageSize(nextPageSize);
              fetchData(nextPage, nextPageSize, searchText);
            },
          }}
        />
      </Card>

      <Modal
        title={`标签全景 - ${currentRecord?.name || ""}`}
        open={viewModalOpen}
        onCancel={() => setViewModalOpen(false)}
        footer={null}
        width={760}
      >
        {currentRecord ? (
          <Descriptions column={1} bordered size="small">
            {allDimensionKeys.map((dimension) => (
              <Descriptions.Item key={dimension} label={DIMENSION_META[dimension].label}>
                <Space size={[0, 6]} wrap>
                  {currentRecord.dimensions[dimension].length > 0 ? (
                    currentRecord.dimensions[dimension].map((tagName) => (
                      <Tag color={DIMENSION_META[dimension].color} key={`${dimension}_${tagName}`}>
                        {tagName}
                      </Tag>
                    ))
                  ) : (
                    <Text type="secondary">暂无标签</Text>
                  )}
                </Space>
              </Descriptions.Item>
            ))}
          </Descriptions>
        ) : null}
      </Modal>

      <Modal
        title={verificationTitle || "安全验证"}
        open={verificationOpen}
        onCancel={closeVerification}
        onOk={() => void handleVerificationConfirm()}
        confirmLoading={verificationSubmitting}
        okText="确认执行"
        cancelText="取消"
        destroyOnClose
      >
        <Space direction="vertical" size={12} style={{ width: "100%", marginTop: 12 }}>
          <Alert
            type="warning"
            showIcon
            message="标签操作二次确认"
            description={verificationDescription || "请输入“确认”后继续执行当前操作。"}
          />
          <Form layout="vertical">
            <Form.Item label='请输入“确认”'>
              <Input
                value={verificationText}
                onChange={(event) => setVerificationText(event.target.value)}
                placeholder='请输入“确认”'
                onPressEnter={() => void handleVerificationConfirm()}
              />
            </Form.Item>
          </Form>
        </Space>
      </Modal>
    </div>
  );
};

export default EnterpriseTag;
