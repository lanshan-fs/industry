import React, { useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from "antd";
import {
  BankOutlined,
  CheckCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  IdcardOutlined,
  KeyOutlined,
  LockOutlined,
  MailOutlined,
  PhoneOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SearchOutlined,
  StopOutlined,
  TeamOutlined,
  UserAddOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { getAuthToken } from "../../../utils/auth";

const { Title, Text } = Typography;
const { Option } = Select;

interface UserDataType {
  user_id: number;
  user_name: string;
  role_id: number | null;
  role_name: string;
  is_active: number;
}

interface InviteCodeType {
  code: string;
  created_at: string | null;
}

interface RoleOption {
  id: number;
  name: string;
  label: string;
}

const DOMAIN_OPTIONS = [
  { value: "digital_wellness", label: "数字康养" },
  { value: "digital_medical", label: "数字医疗" },
];

const UserMgmt: React.FC = () => {
  const [activeTab, setActiveTab] = useState("1");
  const [userLoading, setUserLoading] = useState(false);
  const [userData, setUserData] = useState<UserDataType[]>([]);
  const [searchText, setSearchText] = useState("");
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [currentUser, setCurrentUser] = useState<UserDataType | null>(null);
  const [newRoleId, setNewRoleId] = useState<number | null>(null);
  const [roles, setRoles] = useState<RoleOption[]>([]);

  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteData, setInviteData] = useState<InviteCodeType[]>([]);
  const [batchCount, setBatchCount] = useState<number>(1);

  const [createForm] = Form.useForm();
  const [createLoading, setCreateLoading] = useState(false);

  useEffect(() => {
    void fetchRoles();
    void fetchUsers();
    void fetchInviteCodes();
  }, []);

  const getToken = () => getAuthToken();

  const fetchRoles = async () => {
    const token = getToken();
    try {
      const res = await fetch("/api/auth/users/roles", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const result = await res.json();
      if (result.success) {
        setRoles(result.data);
      } else {
        message.error(result.message || "获取角色列表失败");
      }
    } catch {
      message.error("获取角色列表失败");
    }
  };

  const fetchUsers = async () => {
    const token = getToken();
    setUserLoading(true);
    try {
      const res = await fetch("/api/auth/users/list", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const result = await res.json();
      if (result.success) {
        setUserData(result.data);
      } else {
        message.error(result.message || "获取用户列表失败");
      }
    } catch {
      message.error("获取用户列表失败");
    } finally {
      setUserLoading(false);
    }
  };

  const handleToggleStatus = async (userId: number, targetStatus: number) => {
    const token = getToken();
    try {
      const res = await fetch("/api/auth/users/delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ user_id: userId, target_status: targetStatus }),
      });
      const result = await res.json();
      if (result.success) {
        message.success(result.message);
        void fetchUsers();
      } else {
        message.error(result.message || "操作失败");
      }
    } catch {
      message.error("操作请求失败");
    }
  };

  const handleUpdateRole = async () => {
    const token = getToken();
    try {
      const res = await fetch("/api/auth/users/update-role", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ user_id: currentUser?.user_id, role_id: newRoleId }),
      });
      const result = await res.json();
      if (result.success) {
        message.success("角色权限更新成功");
        setIsModalVisible(false);
        void fetchUsers();
      } else {
        message.error(result.message || "操作失败");
      }
    } catch {
      message.error("操作失败");
    }
  };

  const fetchInviteCodes = async () => {
    const token = getToken();
    setInviteLoading(true);
    try {
      const res = await fetch("/api/auth/invite-codes/list", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const result = await res.json();
      if (result.success) {
        setInviteData(result.data);
      } else {
        message.error(result.message || "获取邀请码失败");
      }
    } catch {
      message.error("获取邀请码失败");
    } finally {
      setInviteLoading(false);
    }
  };

  const generateCodes = async () => {
    const token = getToken();
    try {
      const res = await fetch("/api/auth/invite-codes/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ count: batchCount }),
      });
      const result = await res.json();
      if (result.success) {
        message.success(`成功批量生成 ${batchCount} 个邀请码`);
        void fetchInviteCodes();
      } else {
        message.error(result.message || "生成失败");
      }
    } catch {
      message.error("生成失败");
    }
  };

  const handleCreateUser = async (values: Record<string, unknown>) => {
    const token = getToken();
    setCreateLoading(true);
    try {
      const res = await fetch("/api/auth/users/admin-create", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(values),
      });
      const result = await res.json();
      if (result.success) {
        message.success("用户录入成功");
        createForm.resetFields();
        void fetchUsers();
        setActiveTab("1");
      } else {
        message.error(result.message || "录入失败");
      }
    } catch {
      message.error("请求异常");
    } finally {
      setCreateLoading(false);
    }
  };

  const filteredUsers = userData.filter(
    (user) =>
      user.user_name.toLowerCase().includes(searchText.toLowerCase()) ||
      user.user_id.toString().includes(searchText),
  );

  return (
    <div style={{ padding: 24, background: "#f0f2f5", minHeight: "100vh" }}>
      <Card bordered={false} style={{ borderRadius: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}>
        <Title level={3}>
          <TeamOutlined style={{ marginRight: 12, color: "#1890ff" }} />
          用户管理中心
        </Title>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: "1",
              label: (
                <span>
                  <TeamOutlined /> 用户权限列表
                </span>
              ),
              children: (
                <div style={{ padding: "8px 0" }}>
                  <div
                    style={{
                      marginBottom: 16,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <Input
                      placeholder="输入用户名或 ID 搜索"
                      prefix={<SearchOutlined />}
                      value={searchText}
                      onChange={(event) => setSearchText(event.target.value)}
                      allowClear
                      style={{ width: 320 }}
                    />
                    <Button icon={<ReloadOutlined />} onClick={() => void fetchUsers()}>
                      同步最新数据
                    </Button>
                  </div>
                  <Table
                    rowKey="user_id"
                    loading={userLoading}
                    dataSource={filteredUsers}
                    pagination={{ pageSize: 10 }}
                    columns={[
                      { title: "ID", dataIndex: "user_id", width: 80 },
                      {
                        title: "用户名",
                        dataIndex: "user_name",
                        render: (value: string) => <Text strong>{value}</Text>,
                      },
                      {
                        title: "角色",
                        dataIndex: "role_name",
                        render: (value: string) => (
                          <Tag color={String(value).toUpperCase() === "ADMIN" ? "red" : "blue"}>
                            {value}
                          </Tag>
                        ),
                      },
                      {
                        title: "状态",
                        dataIndex: "is_active",
                        render: (value: number) =>
                          value === 1 ? (
                            <Tag icon={<CheckCircleOutlined />} color="success">
                              正常
                            </Tag>
                          ) : (
                            <Tag icon={<StopOutlined />} color="default">
                              已禁用
                            </Tag>
                          ),
                      },
                      {
                        title: "操作",
                        align: "right",
                        render: (_value, record: UserDataType) => (
                          <Space size="middle">
                            <Button
                              type="link"
                              icon={<EditOutlined />}
                              disabled={record.is_active === 0}
                              onClick={() => {
                                setCurrentUser(record);
                                setNewRoleId(record.role_id);
                                setIsModalVisible(true);
                              }}
                            >
                              编辑角色
                            </Button>
                            {record.is_active === 1 ? (
                              <Popconfirm
                                title="确定要禁用该账号吗？"
                                description="禁用后用户将无法登录，但数据会保留。"
                                onConfirm={() => void handleToggleStatus(record.user_id, 0)}
                                okText="确定禁用"
                                cancelText="取消"
                                okButtonProps={{ danger: true }}
                              >
                                <Button type="link" danger icon={<DeleteOutlined />}>
                                  禁用账号
                                </Button>
                              </Popconfirm>
                            ) : (
                              <Popconfirm
                                title="确定要恢复该账号吗？"
                                description="恢复后用户可以重新登录系统。"
                                onConfirm={() => void handleToggleStatus(record.user_id, 1)}
                                okText="确定恢复"
                                cancelText="取消"
                              >
                                <Button type="link" style={{ color: "#52c41a" }} icon={<ReloadOutlined />}>
                                  恢复账号
                                </Button>
                              </Popconfirm>
                            )}
                          </Space>
                        ),
                      },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: "2",
              label: (
                <span>
                  <KeyOutlined /> 批量邀请码
                </span>
              ),
              children: (
                <div style={{ padding: "8px 0" }}>
                  <div style={{ marginBottom: 20, padding: 16, background: "#f9f9f9", borderRadius: 8 }}>
                    <Space size="large">
                      <span>
                        生成数量 (1-50):{" "}
                        <InputNumber min={1} max={50} value={batchCount} onChange={(value) => setBatchCount(value || 1)} />
                      </span>
                      <Button type="primary" icon={<PlusOutlined />} onClick={() => void generateCodes()}>
                        开始批量生成
                      </Button>
                    </Space>
                  </div>
                  <Table
                    rowKey="code"
                    loading={inviteLoading}
                    dataSource={inviteData}
                    columns={[
                      {
                        title: "可用邀请码",
                        dataIndex: "code",
                        render: (value: string) => (
                          <Text copyable strong style={{ color: "#1890ff" }}>
                            {value}
                          </Text>
                        ),
                      },
                      { title: "状态", render: () => <Tag color="green">未使用</Tag> },
                      { title: "创建时间", dataIndex: "created_at" },
                    ]}
                  />
                </div>
              ),
            },
            {
              key: "3",
              label: (
                <span>
                  <UserAddOutlined /> 手动录入用户
                </span>
              ),
              children: (
                <div
                  style={{
                    maxWidth: 800,
                    margin: "24px auto",
                    padding: 40,
                    background: "#fff",
                    borderRadius: 12,
                    border: "1px solid #f0f0f0",
                  }}
                >
                  <div style={{ textAlign: "center", marginBottom: 32 }}>
                    <Title level={4}>
                      <SafetyCertificateOutlined style={{ color: "#52c41a" }} /> 录入新用户信息
                    </Title>
                    <Text type="secondary">管理员录入模式：绕过邀请码直接创建账号</Text>
                  </div>

                  <Form form={createForm} layout="vertical" onFinish={handleCreateUser} size="large" initialValues={{ role: "ordinary_user" }}>
                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item
                          name="username"
                          label="登录用户名"
                          validateTrigger="onBlur"
                          rules={[
                            { required: true, message: "请输入用户名" },
                            {
                              validator: async (_rule, value) => {
                                if (!value) {
                                  return Promise.resolve();
                                }
                                const res = await fetch(`/api/auth/check-username?username=${encodeURIComponent(value)}`);
                                const data = await res.json();
                                if (data.exists) {
                                  return Promise.reject(new Error("数据库中已存在该用户名"));
                                }
                                return Promise.resolve();
                              },
                            },
                          ]}
                        >
                          <Input prefix={<UserOutlined style={{ color: "rgba(0,0,0,.25)" }} />} placeholder="用户名" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name="password"
                          label="初始登录密码"
                          rules={[{ required: true, min: 6, message: "密码至少 6 位" }]}
                        >
                          <Input.Password prefix={<LockOutlined style={{ color: "rgba(0,0,0,.25)" }} />} placeholder="初始密码" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item name="email" label="电子邮箱" rules={[{ type: "email", message: "邮箱格式不正确" }]}>
                          <Input prefix={<MailOutlined style={{ color: "rgba(0,0,0,.25)" }} />} placeholder="邮箱地址" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="phone" label="联系电话">
                          <Input prefix={<PhoneOutlined style={{ color: "rgba(0,0,0,.25)" }} />} placeholder="手机号" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item name="company" label="所属机构/公司">
                          <Input prefix={<BankOutlined style={{ color: "rgba(0,0,0,.25)" }} />} placeholder="单位名称" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="job" label="担任职务">
                          <Input prefix={<IdcardOutlined style={{ color: "rgba(0,0,0,.25)" }} />} placeholder="职位名称" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item name="domain" label="所属业务领域" rules={[{ required: true, message: "请选择领域" }]}>
                          <Select placeholder="请选择领域">
                            {DOMAIN_OPTIONS.map((item) => (
                              <Option key={item.value} value={item.value}>
                                {item.label}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="role" label="分配系统角色">
                          <Select placeholder="请选择角色">
                            {roles.map((role) => (
                              <Option key={role.id} value={role.name}>
                                {role.label} ({role.name})
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                    </Row>

                    <Form.Item style={{ marginTop: 24, marginBottom: 0 }}>
                      <Button type="primary" htmlType="submit" block loading={createLoading} style={{ height: 48, fontSize: 16 }}>
                        确认录入用户
                      </Button>
                    </Form.Item>
                  </Form>
                </div>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        title="修改角色权限"
        open={isModalVisible}
        onOk={() => void handleUpdateRole()}
        onCancel={() => setIsModalVisible(false)}
        okText="保存"
        cancelText="取消"
      >
        <div style={{ padding: "10px 0" }}>
          <p>
            正在调整用户：<Text strong>{currentUser?.user_name}</Text>
          </p>
          <Select style={{ width: "100%" }} value={newRoleId ?? undefined} onChange={setNewRoleId}>
            {roles.map((role) => (
              <Option key={role.id} value={role.id}>
                {role.label} ({role.name})
              </Option>
            ))}
          </Select>
        </div>
      </Modal>
    </div>
  );
};

export default UserMgmt;
