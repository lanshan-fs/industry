import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Empty,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  Upload,
  message,
} from "antd";
import type { TableProps, UploadFile, UploadProps } from "antd";
import {
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FundViewOutlined,
  InboxOutlined,
  ImportOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { useNavigate } from "react-router-dom";
import { getAuthToken } from "../../../utils/auth";

const { Text, Paragraph } = Typography;
const { Dragger } = Upload;

interface ManagedTableItem {
  tableName: string;
  label: string;
  comment: string;
  primaryKey: string;
  columnCount: number;
}

interface ManagedColumn {
  name: string;
  label: string;
  comment: string;
  dataType: string;
  columnType: string;
  nullable: boolean;
  primaryKey: boolean;
  autoIncrement: boolean;
  uniqueKey: boolean;
  systemIdentifier: boolean;
  businessIdentifier: boolean;
  creatable: boolean;
  editable: boolean;
  searchable: boolean;
  listable: boolean;
  detailVisible: boolean;
  relationDisplay?: boolean;
  relation?: {
    targetTable: string;
    valueField: string;
    labelField: string;
    subtitleField?: string | null;
    displayColumn: string;
    displayLabel: string;
  } | null;
  required: boolean;
  formType: string;
  importLabel: string;
}

interface ManagedSchema {
  tableName: string;
  label: string;
  comment: string;
  primaryKey: string;
  columns: ManagedColumn[];
}

interface RowColumnMeta {
  name: string;
  label: string;
  comment: string;
  listable: boolean;
  detailVisible: boolean;
  relationDisplay?: boolean;
  formType: string;
  primaryKey: boolean;
}

interface RelationOption {
  value: string | number;
  label: string;
  description?: string | null;
}

interface RowResponse {
  table: {
    tableName: string;
    label: string;
    comment: string;
    primaryKey: string;
  };
  columns: RowColumnMeta[];
  rows: Record<string, unknown>[];
  total: number;
}

type VerificationAction = () => Promise<boolean>;

const safeText = (value: unknown) => {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
};

const toBusinessLabel = (label?: string | null) => {
  const text = String(label || "").trim();
  if (!text) {
    return "";
  }
  return text.endsWith("表") ? text.slice(0, -1) : text;
};

const buildTableOptionLabel = (item: ManagedTableItem) => {
  const primary = toBusinessLabel(item.label);
  const secondary = toBusinessLabel(item.comment);
  if (primary && secondary && primary !== secondary) {
    return `${primary}（${secondary}）`;
  }
  return primary || secondary || item.tableName;
};

const EnterpriseData: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [tables, setTables] = useState<ManagedTableItem[]>([]);
  const [activeTable, setActiveTable] = useState("");
  const [schema, setSchema] = useState<ManagedSchema | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadingSchema, setLoadingSchema] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [keyword, setKeyword] = useState("");
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailRow, setDetailRow] = useState<Record<string, unknown> | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingRow, setEditingRow] = useState<Record<string, unknown> | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [csvText, setCsvText] = useState("");
  const [relationOptions, setRelationOptions] = useState<Record<string, RelationOption[]>>({});
  const [loadingRelationField, setLoadingRelationField] = useState<string | null>(null);
  const [verificationOpen, setVerificationOpen] = useState(false);
  const [verificationTitle, setVerificationTitle] = useState("");
  const [verificationDescription, setVerificationDescription] = useState("");
  const [verificationText, setVerificationText] = useState("");
  const [verificationSubmitting, setVerificationSubmitting] = useState(false);
  const verificationActionRef = useRef<VerificationAction | null>(null);

  const getAuthHeaders = (headers: Record<string, string> = {}) => ({
    Authorization: `Bearer ${getAuthToken()}`,
    ...headers,
  });

  const fetchTables = async () => {
    setLoadingSchema(true);
    try {
      const response = await fetch("/api/system/data-tables", {
        headers: getAuthHeaders(),
      });
      const result = await response.json();
      if (!result.success) {
        message.error(result.message || "获取数据表失败");
        return;
      }
      const tableItems = (result.data || []) as ManagedTableItem[];
      setTables(tableItems);
      if (tableItems.length > 0) {
        const preferredTable =
          tableItems.find((item) => item.tableName === "company_basic")?.tableName || tableItems[0].tableName;
        setActiveTable((current) =>
          current && tableItems.some((item) => item.tableName === current) ? current : preferredTable,
        );
      }
    } catch (error) {
      console.error(error);
      message.error("获取数据表失败");
    } finally {
      setLoadingSchema(false);
    }
  };

  const fetchSchema = async (tableName: string) => {
    if (!tableName) {
      return;
    }
    setLoadingSchema(true);
    try {
      const response = await fetch(`/api/system/data-tables/${encodeURIComponent(tableName)}/schema`, {
        headers: getAuthHeaders(),
      });
      const result = await response.json();
      if (!result.success) {
        message.error(result.message || "获取表结构失败");
        return;
      }
      setSchema(result.data as ManagedSchema);
    } catch (error) {
      console.error(error);
      message.error("获取表结构失败");
    } finally {
      setLoadingSchema(false);
    }
  };

  const fetchRows = async (tableName: string, page = 1, size = pageSize, search = keyword.trim()) => {
    if (!tableName) {
      return;
    }
    setLoading(true);
    try {
      const query = new URLSearchParams({
        page: String(page),
        pageSize: String(size),
        keyword: search,
      });
      const response = await fetch(
        `/api/system/data-tables/${encodeURIComponent(tableName)}/rows?${query.toString()}`,
        { headers: getAuthHeaders() },
      );
      const result = await response.json();
      if (!result.success) {
        message.error(result.message || "获取表数据失败");
        return;
      }
      const payload = result.data as RowResponse;
      setRows(payload.rows || []);
      setTotal(payload.total || 0);
      setCurrentPage(page);
      setPageSize(size);
      setKeyword(search);
      setSelectedRowKeys([]);
    } catch (error) {
      console.error(error);
      message.error("获取表数据失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchTables();
  }, []);

  useEffect(() => {
    if (!activeTable) {
      return;
    }
    void fetchSchema(activeTable);
    void fetchRows(activeTable, 1, pageSize, "");
    setRelationOptions({});
    setDetailOpen(false);
    setFormOpen(false);
    setImportOpen(false);
  }, [activeTable]);

  const activeTableMeta = useMemo(
    () => tables.find((item) => item.tableName === activeTable) || null,
    [tables, activeTable],
  );

  const listableColumns = useMemo(
    () => schema?.columns.filter((column) => column.listable) || [],
    [schema],
  );

  const editableColumns = useMemo(
    () => schema?.columns.filter((column) => column.editable) || [],
    [schema],
  );

  const creatableColumns = useMemo(
    () => schema?.columns.filter((column) => column.creatable) || [],
    [schema],
  );

  const detailColumns = useMemo(
    () => schema?.columns.filter((column) => column.detailVisible) || [],
    [schema],
  );

  const formColumns = useMemo(
    () => (editingRow ? editableColumns : creatableColumns),
    [editingRow, editableColumns, creatableColumns],
  );

  const hiddenIdentifierColumns = useMemo(
    () => schema?.columns.filter((column) => column.systemIdentifier || column.businessIdentifier) || [],
    [schema],
  );

  const visibleNameColumns = useMemo(
    () =>
      schema?.columns.filter((column) => {
        const normalized = column.name.toLowerCase();
        return (
          !column.systemIdentifier &&
          !column.businessIdentifier &&
          (normalized === "name" ||
            normalized.endsWith("_name") ||
            normalized.includes("company_name") ||
            normalized.includes("title"))
        );
      }) || [],
    [schema],
  );

  const getRowKey = (row: Record<string, unknown>) => {
    if (!schema) {
      return JSON.stringify(row);
    }
    return String(row[schema.primaryKey] ?? JSON.stringify(row));
  };

  const getRowDisplayName = (row: Record<string, unknown>) => {
    for (const column of visibleNameColumns) {
      const value = row[column.name];
      if (value !== null && value !== undefined && String(value).trim()) {
        return String(value).trim();
      }
    }
    if (schema?.primaryKey && row[schema.primaryKey] !== undefined) {
      return `${toBusinessLabel(schema.label) || "记录"} #${row[schema.primaryKey]}`;
    }
    return "当前记录";
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

  const handleSearch = (value: string) => {
    if (!activeTable) {
      return;
    }
    void fetchRows(activeTable, 1, pageSize, value.trim());
  };

  const handleRefresh = () => {
    if (!activeTable) {
      return;
    }
    void fetchRows(activeTable, currentPage, pageSize, keyword.trim());
  };

  const handleViewDetail = async (rowKey: React.Key) => {
    if (!activeTable) {
      return;
    }
    try {
      const response = await fetch(
        `/api/system/data-tables/${encodeURIComponent(activeTable)}/rows/${encodeURIComponent(String(rowKey))}`,
        { headers: getAuthHeaders() },
      );
      const result = await response.json();
      if (!result.success) {
        message.error(result.message || "获取记录详情失败");
        return;
      }
      setDetailRow(result.data || null);
      setDetailOpen(true);
    } catch (error) {
      console.error(error);
      message.error("获取记录详情失败");
    }
  };

  const fetchRelationOptions = async (column: ManagedColumn, keyword = "") => {
    if (!activeTable || !column.relation) {
      return;
    }
    setLoadingRelationField(column.name);
    try {
      const query = new URLSearchParams({
        keyword: keyword.trim(),
        limit: "20",
      });
      const response = await fetch(
        `/api/system/data-tables/${encodeURIComponent(activeTable)}/relations/${encodeURIComponent(column.name)}/options?${query.toString()}`,
        { headers: getAuthHeaders() },
      );
      const result = await response.json();
      if (!result.success) {
        message.error(result.message || `获取${column.label}候选项失败`);
        return;
      }
      setRelationOptions((current) => ({
        ...current,
        [column.name]: (result.data || []) as RelationOption[],
      }));
    } catch (error) {
      console.error(error);
      message.error(`获取${column.label}候选项失败`);
    } finally {
      setLoadingRelationField((current) => (current === column.name ? null : current));
    }
  };

  const openCreateModal = () => {
    setEditingRow(null);
    form.resetFields();
    setRelationOptions({});
    setFormOpen(true);
    creatableColumns
      .filter((column) => Boolean(column.relation))
      .forEach((column) => {
        void fetchRelationOptions(column);
      });
  };

  const openEditModal = (row: Record<string, unknown>) => {
    setEditingRow(row);
    const formValues: Record<string, unknown> = {};
    editableColumns.forEach((column) => {
      const value = row[column.name];
      if ((column.formType === "date" || column.formType === "datetime") && value) {
        formValues[column.name] = dayjs(String(value));
      } else if (column.formType === "boolean" && value !== null && value !== undefined && value !== "") {
        formValues[column.name] = String(value);
      } else {
        formValues[column.name] = value ?? undefined;
      }
    });
    form.setFieldsValue(formValues);
    setFormOpen(true);
  };

  const executeSave = async () => {
    if (!activeTable || !schema) {
      return false;
    }
    try {
      const values = await form.validateFields();
      const payload: Record<string, unknown> = {};
      formColumns.forEach((column) => {
        const rawValue = values[column.name];
        if (!rawValue) {
          payload[column.name] = rawValue ?? "";
          return;
        }
        if (column.formType === "date") {
          payload[column.name] = dayjs(rawValue).format("YYYY-MM-DD");
        } else if (column.formType === "datetime") {
          payload[column.name] = dayjs(rawValue).format("YYYY-MM-DD HH:mm:ss");
        } else {
          payload[column.name] = rawValue;
        }
      });

      setSaving(true);
      const isEditing = Boolean(editingRow);
      const rowKey = isEditing ? editingRow?.[schema.primaryKey] : null;
      const response = await fetch(
        isEditing
          ? `/api/system/data-tables/${encodeURIComponent(activeTable)}/rows/${encodeURIComponent(String(rowKey))}`
          : `/api/system/data-tables/${encodeURIComponent(activeTable)}/rows/create`,
        {
          method: isEditing ? "PUT" : "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify(payload),
        },
      );
      const result = await response.json();
      if (!response.ok || !result.success) {
        message.error(result.message || "保存记录失败");
        return false;
      }
      message.success(isEditing ? "记录已更新" : "记录已新增");
      setFormOpen(false);
      setEditingRow(null);
      form.resetFields();
      void fetchRows(activeTable, isEditing ? currentPage : 1, pageSize, isEditing ? keyword.trim() : "");
      return true;
    } catch (error: any) {
      if (!error?.errorFields) {
        console.error(error);
        message.error("保存记录失败");
      }
      return false;
    } finally {
      setSaving(false);
    }
  };

  const requestSave = () => {
    const businessLabel = toBusinessLabel(schema?.label) || "记录";
    openVerification(
      editingRow ? `确认保存${businessLabel}修改吗？` : `确认新增${businessLabel}吗？`,
      editingRow ? "请输入“确认”后保存本次修改。" : "请输入“确认”后创建这条新记录。",
      executeSave,
    );
  };

  const executeDelete = async (rowKey: React.Key) => {
    if (!activeTable) {
      return false;
    }
    try {
      const response = await fetch(
        `/api/system/data-tables/${encodeURIComponent(activeTable)}/rows/${encodeURIComponent(String(rowKey))}`,
        {
          method: "DELETE",
          headers: getAuthHeaders(),
        },
      );
      const result = await response.json();
      if (!response.ok || !result.success) {
        message.error(result.message || "删除记录失败");
        return false;
      }
      message.success(result.message || "记录已删除");
      void fetchRows(activeTable, currentPage, pageSize, keyword.trim());
      return true;
    } catch (error) {
      console.error(error);
      message.error("删除记录失败");
      return false;
    }
  };

  const requestDelete = (row: Record<string, unknown>) => {
    const rowKey = getRowKey(row);
    openVerification(
      "确认删除这条记录吗？",
      `请输入“确认”后删除“${getRowDisplayName(row)}”。该操作不可撤销。`,
      () => executeDelete(rowKey),
    );
  };

  const executeBatchDelete = async () => {
    if (!activeTable) {
      return false;
    }
    try {
      const response = await fetch(
        `/api/system/data-tables/${encodeURIComponent(activeTable)}/rows/batch-delete`,
        {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ ids: selectedRowKeys }),
        },
      );
      const result = await response.json();
      if (!response.ok || !result.success) {
        message.error(result.message || "批量删除失败");
        return false;
      }
      message.success(result.message || "批量删除成功");
      void fetchRows(activeTable, currentPage, pageSize, keyword.trim());
      return true;
    } catch (error) {
      console.error(error);
      message.error("批量删除失败");
      return false;
    }
  };

  const requestBatchDelete = () => {
    if (selectedRowKeys.length === 0) {
      return;
    }
    openVerification(
      `确认批量删除 ${selectedRowKeys.length} 条记录吗？`,
      `请输入“确认”后删除当前选中的 ${selectedRowKeys.length} 条记录。该操作不可撤销。`,
      executeBatchDelete,
    );
  };

  const handleDownloadTemplate = async () => {
    if (!activeTable) {
      return;
    }
    setDownloadingTemplate(true);
    try {
      const response = await fetch(
        `/api/system/data-tables/${encodeURIComponent(activeTable)}/template/download`,
        { headers: getAuthHeaders() },
      );
      if (!response.ok) {
        throw new Error("模板下载失败");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${activeTable}-template.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      message.success("模板下载完成");
    } catch (error) {
      console.error(error);
      message.error("模板下载失败");
    } finally {
      setDownloadingTemplate(false);
    }
  };

  const uploadProps: UploadProps = {
    name: "file",
    multiple: false,
    maxCount: 1,
    fileList,
    showUploadList: false,
    beforeUpload: async (file) => {
      const lowerName = file.name.toLowerCase();
      if (!lowerName.endsWith(".csv")) {
        message.error("当前仅支持 CSV 文件");
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
        message.success(`已载入 ${file.name}`);
      } catch (error) {
        console.error(error);
        message.error("读取 CSV 文件失败");
      }
      return false;
    },
    onRemove: () => {
      setFileList([]);
      setCsvText("");
    },
  };

  const executeImport = async () => {
    if (!activeTable) {
      return false;
    }
    if (!csvText.trim()) {
      message.warning("请先上传 CSV 文件");
      return false;
    }
    setImporting(true);
    try {
      const response = await fetch(
        `/api/system/data-tables/${encodeURIComponent(activeTable)}/import`,
        {
          method: "POST",
          headers: getAuthHeaders({ "Content-Type": "application/json" }),
          body: JSON.stringify({ csvText }),
        },
      );
      const result = await response.json();
      if (!response.ok || !result.success) {
        message.error(result.message || "导入失败");
        return false;
      }
      message.success(result.message || "导入成功");
      setImportOpen(false);
      setFileList([]);
      setCsvText("");
      void fetchRows(activeTable, 1, pageSize, "");
      return true;
    } catch (error) {
      console.error(error);
      message.error("导入失败");
      return false;
    } finally {
      setImporting(false);
    }
  };

  const requestImport = () => {
    const businessLabel = toBusinessLabel(schema?.label) || "当前数据";
    openVerification(
      `确认导入${businessLabel}吗？`,
      "请输入“确认”后开始导入。导入过程会按当前数据库结构写入记录，请先确认模板和内容无误。",
      executeImport,
    );
  };

  const columns: TableProps<Record<string, unknown>>["columns"] = useMemo(() => {
    if (!schema) {
      return [];
    }

    const baseColumns = listableColumns.map((column) => ({
      title: column.label,
      dataIndex: column.name,
      key: column.name,
      width: column.formType === "textarea" ? 260 : 180,
      ellipsis: true,
      render: (value: unknown) => {
        const text = safeText(value);
        return (
          <Tooltip title={text}>
            <span>{text}</span>
          </Tooltip>
        );
      },
    }));

    return [
      ...baseColumns,
      {
        title: "操作",
        key: "action",
        fixed: "right" as const,
        width: activeTable === "company_basic" ? 210 : 170,
        render: (_value: unknown, row: Record<string, unknown>) => (
          <Space size={4}>
            <Tooltip title="查看详情">
              <Button type="text" icon={<EyeOutlined />} onClick={() => void handleViewDetail(getRowKey(row))} />
            </Tooltip>
            <Tooltip title="编辑记录">
              <Button type="text" icon={<EditOutlined />} onClick={() => openEditModal(row)} />
            </Tooltip>
            {activeTable === "company_basic" ? (
              <Tooltip title="查看企业画像">
                <Button
                  type="text"
                  icon={<FundViewOutlined />}
                  onClick={() =>
                    navigate(
                      `/industry-portrait/enterprise-profile?id=${encodeURIComponent(String(getRowKey(row)))}&from=enterprise-data`,
                    )
                  }
                />
              </Tooltip>
            ) : null}
            <Tooltip title="删除记录">
              <Button danger type="text" icon={<DeleteOutlined />} onClick={() => requestDelete(row)} />
            </Tooltip>
          </Space>
        ),
      },
    ];
  }, [activeTable, listableColumns, navigate, schema]);

  return (
    <div style={{ padding: 24 }}>
      <Card style={{ marginBottom: 16 }} styles={{ body: { padding: "16px 24px" } }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} md={10}>
            <Space direction="vertical" size={6} style={{ width: "100%" }}>
              <Text type="secondary">当前管理对象</Text>
              <Select
                value={activeTable || undefined}
                placeholder="请选择数据表"
                loading={loadingSchema}
                onChange={(value) => setActiveTable(value)}
                options={tables.map((item) => ({
                  value: item.tableName,
                  label: buildTableOptionLabel(item),
                }))}
                style={{ width: "100%" }}
              />
            </Space>
          </Col>
          <Col xs={24} md={14}>
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Statistic title="当前表记录数" value={total} suffix="条" />
              </Col>
              <Col xs={24} md={8}>
                <Statistic title="当前表字段数" value={schema?.columns.length || activeTableMeta?.columnCount || 0} suffix="个" />
              </Col>
              <Col xs={24} md={8}>
                <Statistic title="可维护字段数" value={(editingRow ? editableColumns : creatableColumns).length} suffix="个" />
              </Col>
            </Row>
          </Col>
        </Row>
        {schema ? (
          <Alert
            style={{ marginTop: 16 }}
            type="info"
            showIcon
            message={`${toBusinessLabel(schema.label)}：${schema.comment}`}
          />
        ) : null}
        {hiddenIdentifierColumns.length > 0 ? (
          <Alert
            style={{ marginTop: 12 }}
            type="warning"
            showIcon
            message="系统已隐藏内部/唯一标识字段"
            description={
              visibleNameColumns.length > 0
                ? "页面优先展示名称等业务字段；唯一标识仅用于系统关联，不作为常规维护字段开放。"
                : "当前表缺少可直接替代的名称字段，系统已隐藏相关标识；如需更友好的维护方式，建议为该表补充名称字段或关联显示字段。"
            }
          />
        ) : null}
      </Card>

      <Card style={{ marginBottom: 16 }} styles={{ body: { padding: "16px 24px" } }}>
        <Row justify="space-between" gutter={[16, 16]}>
          <Col flex="auto">
            <Space wrap>
              <Input.Search
                placeholder={schema ? `按${toBusinessLabel(schema.label)}中的关键信息搜索` : "按当前表内容搜索"}
                value={keyword}
                allowClear
                onChange={(event) => setKeyword(event.target.value)}
                onSearch={handleSearch}
                enterButton={<><SearchOutlined /> 搜索</>}
                style={{ width: 360 }}
                disabled={!activeTable}
              />
              {schema ? <Tag color="blue">{toBusinessLabel(schema.label)}</Tag> : null}
            </Space>
          </Col>
          <Col>
            <Space wrap>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal} disabled={!activeTable}>
                新增记录
              </Button>
              <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)} disabled={!activeTable}>
                导入 CSV
              </Button>
              <Button danger disabled={selectedRowKeys.length === 0} icon={<DeleteOutlined />} onClick={requestBatchDelete}>
                批量删除
              </Button>
              <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading} disabled={!activeTable}>
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card styles={{ body: { padding: 0 } }}>
        {!activeTable ? (
          <div style={{ padding: 48 }}>
            <Empty description="暂无可管理的数据表" />
          </div>
        ) : (
          <Table
            rowKey={getRowKey}
            columns={columns}
            dataSource={rows}
            loading={loading}
            rowSelection={{
              selectedRowKeys,
              onChange: (keys) => setSelectedRowKeys(keys),
              columnWidth: 40,
            }}
            scroll={{ x: 2200 }}
            pagination={{
              current: currentPage,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (value) => `共 ${value} 条记录`,
              onChange: (page, size) => {
                if (!activeTable) {
                  return;
                }
                void fetchRows(activeTable, page, size, keyword.trim());
              },
            }}
          />
        )}
      </Card>

      <Modal
        title={schema ? `${toBusinessLabel(schema.label)}记录详情` : "记录详情"}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={<Button onClick={() => setDetailOpen(false)}>关闭</Button>}
        width={960}
      >
        {detailRow && schema ? (
          <Descriptions bordered size="small" column={2}>
            {detailColumns.map((column) => (
              <Descriptions.Item key={column.name} label={column.label} span={column.formType === "textarea" ? 2 : 1}>
                {column.formType === "textarea" ? (
                  <Paragraph style={{ marginBottom: 0 }}>{safeText(detailRow[column.name])}</Paragraph>
                ) : (
                  safeText(detailRow[column.name])
                )}
              </Descriptions.Item>
            ))}
          </Descriptions>
        ) : null}
      </Modal>

      <Modal
        title={editingRow ? `编辑${toBusinessLabel(schema?.label) || "记录"}` : `新增${toBusinessLabel(schema?.label) || "记录"}`}
        open={formOpen}
        onCancel={() => {
          setFormOpen(false);
          setEditingRow(null);
          form.resetFields();
        }}
        onOk={requestSave}
        confirmLoading={saving}
        width={980}
        okText="保存"
        cancelText="取消"
      >
        <Space direction="vertical" size={12} style={{ width: "100%", marginTop: 20 }}>
          {editingRow && hiddenIdentifierColumns.length > 0 ? (
            <Alert
              type="info"
              showIcon
              message="唯一标识和系统关联字段已锁定"
              description="编辑模式下仅开放业务内容字段，唯一标识与系统关联字段不可修改。"
            />
          ) : null}
          {!editingRow && formColumns.some((column) => column.businessIdentifier) ? (
            <Alert
              type="warning"
              showIcon
              message="唯一标识仅在新增时录入"
              description="这类字段在记录创建后会自动锁定，后续编辑时不再开放修改。"
            />
          ) : null}
          {!editingRow && formColumns.some((column) => column.systemIdentifier) ? (
            <Alert
              type="warning"
              showIcon
              message="当前表包含关联标识字段"
              description="系统会优先提供名称搜索选择；只有确实缺少名称映射的字段，才保留原始标识录入。"
            />
          ) : null}
          <Form form={form} layout="vertical">
            <Row gutter={16}>
              {formColumns.map((column) => (
                <Col xs={24} md={column.formType === "textarea" ? 24 : 12} key={column.name}>
                  <Form.Item
                    name={column.name}
                    label={!editingRow && column.businessIdentifier ? `${column.label}（创建后锁定）` : column.label}
                    tooltip={column.comment}
                    rules={column.required ? [{ required: true, message: `请输入${column.label}` }] : undefined}
                  >
                    {column.relation ? (
                      <Select
                        showSearch
                        filterOption={false}
                        options={(relationOptions[column.name] || []).map((option) => ({
                          label: option.description ? `${option.label}（${option.description}）` : option.label,
                          value: option.value,
                        }))}
                        placeholder={`请选择${column.relation.displayLabel}`}
                        loading={loadingRelationField === column.name}
                        onSearch={(value) => void fetchRelationOptions(column, value)}
                        onFocus={() => {
                          if (!relationOptions[column.name]?.length) {
                            void fetchRelationOptions(column);
                          }
                        }}
                      />
                    ) : column.formType === "textarea" ? (
                      <Input.TextArea rows={4} placeholder={`请输入${column.label}`} />
                    ) : column.formType === "date" ? (
                      <DatePicker style={{ width: "100%" }} />
                    ) : column.formType === "datetime" ? (
                      <DatePicker showTime style={{ width: "100%" }} />
                    ) : column.formType === "boolean" ? (
                      <Select
                        options={[
                          { label: "是", value: "1" },
                          { label: "否", value: "0" },
                        ]}
                        placeholder={`请选择${column.label}`}
                      />
                    ) : (
                      <Input placeholder={`请输入${column.label}`} />
                    )}
                  </Form.Item>
                </Col>
              ))}
            </Row>
          </Form>
        </Space>
      </Modal>

      <Modal
        title={schema ? `导入${toBusinessLabel(schema.label)}` : "导入数据"}
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        footer={[
          <Button key="template" icon={<DownloadOutlined />} loading={downloadingTemplate} onClick={() => void handleDownloadTemplate()}>
            下载模板
          </Button>,
          <Button key="cancel" onClick={() => setImportOpen(false)}>
            关闭
          </Button>,
          <Button key="import" type="primary" icon={<ImportOutlined />} loading={importing} onClick={requestImport}>
            开始导入
          </Button>,
        ]}
        width={640}
      >
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <Alert
            showIcon
            type="info"
            message={schema ? `模板字段已按“${toBusinessLabel(schema.label)}”当前数据库结构生成，表头均为中文说明。` : "模板字段已按当前表结构生成。"}
          />

          <Dragger
            {...uploadProps}
            style={{
              borderRadius: 12,
              border: "2px dashed #d9d9d9",
              background: "#fafafa",
            }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ fontSize: 40, color: "#1677ff" }} />
            </p>
            <p className="ant-upload-text">点击或拖拽 CSV 文件到此区域</p>
            <p className="ant-upload-hint">系统将按当前所选数据表的中文模板表头导入记录</p>
          </Dragger>

          {fileList.length > 0 ? (
            <Card size="small" styles={{ body: { padding: "12px 16px" } }}>
              <Space direction="vertical" size={4}>
                <Text strong>{fileList[0].name}</Text>
                <Text type="secondary">文件大小：{Math.ceil((fileList[0].size || 0) / 1024)} KB</Text>
              </Space>
            </Card>
          ) : null}
        </Space>
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
            message="高风险操作二次确认"
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

export default EnterpriseData;
