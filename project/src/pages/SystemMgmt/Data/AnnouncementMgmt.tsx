import React, { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Result,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  NotificationOutlined,
  PlusOutlined,
  ReloadOutlined,
} from "@ant-design/icons";

const { Text, Title } = Typography;
const { TextArea } = Input;

interface NoticeRow {
  id: number;
  title: string;
  type: string;
  date: string;
  content: string;
  sortOrder: number;
  isPublished: boolean;
  createdAt?: string;
  updatedAt?: string;
}

const NOTICE_TYPES = ["通知", "动态", "系统", "报告", "活动"];

const AnnouncementMgmt: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [data, setData] = useState<NoticeRow[]>([]);
  const [editing, setEditing] = useState<NoticeRow | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  const getToken = () => {
    const token = localStorage.getItem("token") || "";
    return token.trim().replace(/^["']+|["']+$/g, "");
  };

  const fetchNotices = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/dashboard/admin/notices", {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const json = await res.json();
      if (json.success) {
        setData(json.data || []);
      } else {
        message.error(json.message || "获取公告列表失败");
      }
    } catch {
      message.error("获取公告列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    try {
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      const role = String(user.role || "").toUpperCase();
      if (role === "ADMIN") {
        setIsAdmin(true);
        void fetchNotices();
      } else {
        setIsAdmin(false);
      }
    } catch {
      setIsAdmin(false);
    }
  }, []);

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({
      title: "",
      type: "通知",
      date: "",
      content: "",
      sortOrder: 0,
      isPublished: true,
    });
    setModalOpen(true);
  };

  const openEdit = (record: NoticeRow) => {
    setEditing(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const res = await fetch("/api/dashboard/admin/notices/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          id: editing?.id,
          ...values,
        }),
      });
      const json = await res.json();
      if (json.success) {
        message.success(json.message || "保存成功");
        setModalOpen(false);
        form.resetFields();
        void fetchNotices();
      } else {
        message.error(json.message || "保存失败");
      }
    } catch {
      message.error("保存失败");
    } finally {
      setSaving(false);
    }
  };

  const handlePublishChange = async (record: NoticeRow, checked: boolean) => {
    try {
      const res = await fetch("/api/dashboard/admin/notices/publish", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ id: record.id, isPublished: checked }),
      });
      const json = await res.json();
      if (json.success) {
        message.success("公告状态已更新");
        void fetchNotices();
      } else {
        message.error(json.message || "状态更新失败");
      }
    } catch {
      message.error("状态更新失败");
    }
  };

  const handleDelete = async (record: NoticeRow) => {
    try {
      const res = await fetch("/api/dashboard/admin/notices/delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ id: record.id }),
      });
      const json = await res.json();
      if (json.success) {
        message.success("公告已删除");
        void fetchNotices();
      } else {
        message.error(json.message || "删除失败");
      }
    } catch {
      message.error("删除失败");
    }
  };

  if (isAdmin === false) {
    return (
      <Result
        status="403"
        title="无权访问"
        subTitle="仅系统管理员可维护首页公告。"
      />
    );
  }

  const columns = [
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
      render: (text: string) => <Text strong>{text}</Text>,
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 100,
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: "发布日期",
      dataIndex: "date",
      key: "date",
      width: 120,
      render: (text: string) => text || "-",
    },
    {
      title: "排序",
      dataIndex: "sortOrder",
      key: "sortOrder",
      width: 90,
    },
    {
      title: "状态",
      dataIndex: "isPublished",
      key: "isPublished",
      width: 110,
      render: (_: boolean, record: NoticeRow) => (
        <Switch
          checked={record.isPublished}
          checkedChildren="发布"
          unCheckedChildren="草稿"
          onChange={(checked) => handlePublishChange(record, checked)}
        />
      ),
    },
    {
      title: "更新时间",
      dataIndex: "updatedAt",
      key: "updatedAt",
      width: 180,
      render: (text: string) => text || "-",
    },
    {
      title: "操作",
      key: "action",
      width: 160,
      render: (_: unknown, record: NoticeRow) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除这条公告？"
            onConfirm={() => handleDelete(record)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card bordered={false}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 20,
          }}
        >
          <div>
            <Space align="center">
              <NotificationOutlined style={{ color: "#1677ff" }} />
              <Title level={4} style={{ margin: 0 }}>
                平台公告管理
              </Title>
              <Badge count={data.length} color="#1677ff" />
            </Space>
            <Text type="secondary">
              这里维护首页公告轮播和公告中心内容，发布后首页会直接同步。
            </Text>
          </div>

          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void fetchNotices()}>
              刷新
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新建公告
            </Button>
          </Space>
        </div>

        <Table
          rowKey="id"
          loading={loading}
          columns={columns}
          dataSource={data}
          pagination={{ pageSize: 10, showSizeChanger: false }}
        />
      </Card>

      <Modal
        title={editing ? "编辑公告" : "新建公告"}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => void handleSave()}
        confirmLoading={saving}
        width={720}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="title"
            label="公告标题"
            rules={[{ required: true, message: "请输入公告标题" }]}
          >
            <Input maxLength={120} placeholder="请输入公告标题" />
          </Form.Item>

          <Space style={{ display: "flex" }} align="start">
            <Form.Item name="type" label="公告类型" style={{ minWidth: 160 }}>
              <Select options={NOTICE_TYPES.map((item) => ({ label: item, value: item }))} />
            </Form.Item>
            <Form.Item
              name="date"
              label="发布日期"
              tooltip="格式为 YYYY-MM-DD，留空时发布动作会自动补今天日期。"
              style={{ minWidth: 180 }}
            >
              <Input placeholder="2026-04-01" />
            </Form.Item>
            <Form.Item name="sortOrder" label="排序值" style={{ minWidth: 120 }}>
              <InputNumber style={{ width: "100%" }} />
            </Form.Item>
            <Form.Item name="isPublished" label="发布状态" valuePropName="checked">
              <Switch checkedChildren="发布" unCheckedChildren="草稿" />
            </Form.Item>
          </Space>

          <Form.Item
            name="content"
            label="公告内容"
            rules={[{ required: true, message: "请输入公告内容" }]}
          >
            <TextArea rows={8} maxLength={2000} placeholder="请输入首页公告详情内容" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AnnouncementMgmt;
