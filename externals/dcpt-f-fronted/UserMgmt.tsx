import React, { useEffect, useState } from "react";
import {
  Table, Tag, Button, Modal, Select, message, Space,
  Typography, Card, Tabs, Form, Input, Row, Col, Result, InputNumber, Popconfirm
} from "antd";
import {
  UserOutlined, EditOutlined, TeamOutlined, KeyOutlined,
  UserAddOutlined, PlusOutlined, SafetyCertificateOutlined,
  CopyOutlined, ReloadOutlined, MailOutlined, PhoneOutlined,
  BankOutlined, IdcardOutlined, LockOutlined, DeleteOutlined,
  SearchOutlined, CheckCircleOutlined, StopOutlined
} from "@ant-design/icons";

const { Title, Text } = Typography;
const { Option } = Select;

// --- 类型定义 ---
interface UserDataType {
  user_id: number;
  user_name: string;
  role_id: number;
  role_name: string;
  is_active: number; // 新增：用户状态字段 1-正常，0-已注销
}

interface InviteCodeType {
  code: string;
  created_at: string;
}

const UserMgmt: React.FC = () => {
  const [activeTab, setActiveTab] = useState("1");
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);

  // --- 状态控制 ---
  const [userLoading, setUserLoading] = useState(false);
  const [userData, setUserData] = useState<UserDataType[]>([]);
  const [searchText, setSearchText] = useState(""); // 新增：搜索框文本
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [currentUser, setCurrentUser] = useState<UserDataType | null>(null);
  const [newRoleId, setNewRoleId] = useState<number | null>(null);

  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteData, setInviteData] = useState<InviteCodeType[]>([]);
  const [batchCount, setBatchCount] = useState<number>(1);

  const [createForm] = Form.useForm();
  const [createLoading, setCreateLoading] = useState(false);

  // --- 常量定义 ---
  const roles = [
    { id: 1, name: "ADMIN", label: "系统管理员" },
    { id: 2, name: "senior_user", label: "高级用户" },
    { id: 3, name: "ordinary_user", label: "普通用户" },
  ];

  const domains = [
    "数字康养",
    "数字医疗"
  ];

  useEffect(() => {
    const userJson = localStorage.getItem("user");
    if (userJson) {
      try {
        const user = JSON.parse(userJson);
        if (user.role === 'ADMIN') {
          setIsAdmin(true);
          fetchUsers();
          fetchInviteCodes();
        } else {
          setIsAdmin(false);
        }
      } catch (e) { setIsAdmin(false); }
    } else { setIsAdmin(false); }
  }, []);

  const getToken = () => {
    const token = localStorage.getItem("token") || "";
    return token.trim().replace(/^["']+|["']+$/g, '');
  };

  // ===================== 功能函数 =====================
  const fetchUsers = async () => {
    const token = getToken();
    setUserLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/users/list", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const result = await res.json();
      if (result.success) setUserData(result.data);
    } catch (error) { message.error("获取用户列表失败"); }
    finally { setUserLoading(false); }
  };

  // --- 新增/修改：状态切换逻辑（包含注销和恢复） ---
  const handleToggleStatus = async (user_id: number, target_status: number) => {
    const token = getToken();
    try {
      const res = await fetch("http://localhost:8000/api/users/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ user_id, target_status }), // 传入目标状态
      });
      const result = await res.json();
      if (result.success) {
        message.success(result.message);
        fetchUsers();
      } else {
        message.error(result.message);
      }
    } catch (error) { message.error("操作请求失败"); }
  };

  const handleUpdateRole = async () => {
    const token = getToken();
    try {
      const res = await fetch("http://localhost:8000/api/users/update-role", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ user_id: currentUser?.user_id, role_id: newRoleId }),
      });
      const result = await res.json();
      if (result.success) {
        message.success("角色权限更新成功");
        setIsModalVisible(false);
        fetchUsers();
      }
    } catch (error) { message.error("操作失败"); }
  };

  const fetchInviteCodes = async () => {
    const token = getToken();
    setInviteLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/invite-codes/list", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const result = await res.json();
      if (result.success) setInviteData(result.data);
    } catch (error) { console.error(error); }
    finally { setInviteLoading(false); }
  };

  const generateCodes = async () => {
    const token = getToken();
    try {
      const res = await fetch("http://localhost:8000/api/invite-codes/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ count: batchCount }),
      });
      const result = await res.json();
      if (result.success) {
        message.success(`成功批量生成 ${batchCount} 个邀请码`);
        fetchInviteCodes();
      }
    } catch (error) { message.error("生成失败"); }
  };

  const handleCreateUser = async (values: any) => {
    const token = getToken();
    setCreateLoading(true);
    try {
      const res = await fetch("http://localhost:8000/api/users/admin-create", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(values),
      });
      const result = await res.json();
      if (result.success) {
        message.success("用户录入成功！");
        createForm.resetFields();
        fetchUsers();
        setActiveTab("1");
      } else { message.error(result.message); }
    } catch (error) { message.error("请求异常"); }
    finally { setCreateLoading(false); }
  };

  // --- 新增：过滤搜索后的数据 ---
  const filteredUsers = userData.filter(u =>
    u.user_name.toLowerCase().includes(searchText.toLowerCase()) ||
    u.user_id.toString().includes(searchText)
  );

  if (isAdmin === null) return null;
  if (isAdmin === false) return <Result status="403" title="无权访问" subTitle="该页面仅对系统管理员开放" />;

  return (
    <div style={{ padding: "24px", background: "#f0f2f5", minHeight: "100vh" }}>
      <Card bordered={false} style={{ borderRadius: "12px", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}>
        <Title level={3}><TeamOutlined style={{ marginRight: 12, color: '#1890ff' }} /> 用户管理中心</Title>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: "1",
              label: <span><TeamOutlined /> 用户权限列表</span>,
              children: (
                <div style={{ padding: '8px 0' }}>
                   <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    {/* 新增：左侧搜索框 */}
                    <Input
                      placeholder="输入用户名或ID进行搜索"
                      prefix={<SearchOutlined />}
                      value={searchText}
                      onChange={e => setSearchText(e.target.value)}
                      allowClear
                      style={{ width: 300 }}
                    />
                    {/* 右侧刷新按钮 */}
                    <Button icon={<ReloadOutlined />} onClick={fetchUsers}>同步最新数据</Button>
                  </div>
                  <Table
                    columns={[
                      { title: "ID", dataIndex: "user_id", width: 80 },
                      { title: "用户名", dataIndex: "user_name", render: (t) => <Text strong>{t}</Text> },
                      { title: "角色", dataIndex: "role_name", render: (r) => <Tag color={r === 'ADMIN' ? 'red' : 'blue'}>{r}</Tag> },
                      {
                        title: "状态", // 新增状态列
                        dataIndex: "is_active",
                        render: (status) => (
                          status === 1 || status === undefined
                            ? <Tag icon={<CheckCircleOutlined />} color="success">正常</Tag>
                            : <Tag icon={<StopOutlined />} color="default">已禁用/注销</Tag>
                        )
                      },
                      {
                        title: "操作",
                        align: "right",
                        render: (_, r) => (
                          <Space size="middle">
                            <Button
                              type="link"
                              icon={<EditOutlined />}
                              disabled={r.is_active === 0} // 禁用状态下不允许修改角色
                              onClick={() => {
                                setCurrentUser(r);
                                setNewRoleId(r.role_id);
                                setIsModalVisible(true);
                              }}
                            >
                              编辑角色
                            </Button>

                            {/* 新增：根据状态判断显示禁用还是恢复 */}
                            {r.is_active === 1 || r.is_active === undefined ? (
                              <Popconfirm
                                title="确定要禁用该账号吗？"
                                description="禁用后用户将被强制退出，但数据将保留。"
                                onConfirm={() => handleToggleStatus(r.user_id, 0)}
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
                                description="恢复后该用户可以正常登录系统。"
                                onConfirm={() => handleToggleStatus(r.user_id, 1)}
                                okText="确定恢复"
                                cancelText="取消"
                              >
                                <Button type="link" style={{ color: '#52c41a' }} icon={<ReloadOutlined />}>
                                  恢复账号
                                </Button>
                              </Popconfirm>
                            )}
                          </Space>
                        )
                      }
                    ]}
                    dataSource={filteredUsers} // 绑定过滤后的数据
                    rowKey="user_id"
                    loading={userLoading}
                    pagination={{ pageSize: 10 }}
                  />
                </div>
              )
            },
            {
              key: "2",
              label: <span><KeyOutlined /> 批量邀请码</span>,
              children: (
                <div style={{ padding: '8px 0' }}>
                  <div style={{ marginBottom: 20, padding: '16px', background: '#f9f9f9', borderRadius: '8px' }}>
                    <Space size="large">
                      <span>生成数量 (1-50): <InputNumber min={1} max={50} value={batchCount} onChange={(v) => setBatchCount(v || 1)} /></span>
                      <Button type="primary" icon={<PlusOutlined />} onClick={generateCodes}>开始批量生成</Button>
                    </Space>
                  </div>
                  <Table
                    columns={[
                      { title: "可用邀请码", dataIndex: "code", render: (c) => <Text copyable strong style={{color: '#1890ff'}}>{c}</Text> },
                      { title: "状态", render: () => <Tag color="green">未使用</Tag> },
                      { title: "创建时间", dataIndex: "created_at" }
                    ]}
                    dataSource={inviteData} rowKey="code" loading={inviteLoading}
                  />
                </div>
              )
            },
            {
              key: "3",
              label: <span><UserAddOutlined /> 手动录入用户</span>,
              children: (
                <div style={{ maxWidth: 800, margin: "24px auto", padding: "40px", background: "#fff", borderRadius: 12, border: "1px solid #f0f0f0" }}>
                  <div style={{ textAlign: "center", marginBottom: 32 }}>
                    <Title level={4}><SafetyCertificateOutlined style={{ color: '#52c41a' }} /> 录入新用户信息</Title>
                    <Text type="secondary">管理员录入模式：绕过邀请码直接同步至数据库</Text>
                  </div>

                  <Form form={createForm} layout="vertical" onFinish={handleCreateUser} size="large">
                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item
                          name="username"
                          label="登录用户名"
                          validateTrigger="onBlur"
                          rules={[
                            { required: true, message: '请输入用户名' },
                            {
                              validator: async (_, value) => {
                                if (!value) return Promise.resolve();
                                const res = await fetch(`http://localhost:8000/api/auth/check-username?username=${value}`);
                                const data = await res.json();
                                if (data.exists) {
                                  return Promise.reject(new Error('数据库中已存在该用户名'));
                                }
                                return Promise.resolve();
                              }
                            }
                          ]}
                        >
                          <Input prefix={<UserOutlined style={{ color: "rgba(0,0,0,.25)" }} />} placeholder="用户名" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="password" label="初始登录密码" rules={[{required: true, min: 6, message: '密码至少6位'}]}>
                          <Input.Password prefix={<LockOutlined style={{ color: "rgba(0,0,0,.25)" }} />} placeholder="初始密码" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item name="email" label="电子邮箱" rules={[{type: 'email', message: '邮箱格式不正确'}]}>
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
                        <Form.Item name="domain" label="所属业务领域" rules={[{required: true, message: '请选择领域'}]}>
                          <Select placeholder="请选择领域">
                            {domains.map(d => <Option key={d} value={d}>{d}</Option>)}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="role" label="分配系统角色" initialValue="ordinary_user">
                          <Select>
                            {roles.map(r => <Option key={r.name} value={r.name}>{r.label}</Option>)}
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
              )
            }
          ]}
        />
      </Card>

      <Modal title="修改角色权限" open={isModalVisible} onOk={handleUpdateRole} onCancel={() => setIsModalVisible(false)} okText="保存" cancelText="取消">
        <div style={{ padding: '10px 0' }}>
          <p>正在调整用户：<Text strong>{currentUser?.user_name}</Text></p>
          <Select style={{ width: "100%" }} value={newRoleId} onChange={setNewRoleId}>
            {roles.map(r => <Option key={r.id} value={r.id}>{r.label} ({r.name})</Option>)}
          </Select>
        </div>
      </Modal>
    </div>
  );
};

export default UserMgmt;