import React, { useEffect, useMemo, useState } from "react";
import {
  Avatar,
  Button,
  Card,
  Col,
  Form,
  Input,
  Menu,
  Modal,
  Progress,
  Result,
  Row,
  Skeleton,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import {
  BankOutlined,
  CalendarOutlined,
  ExclamationCircleOutlined,
  GlobalOutlined,
  IdcardOutlined,
  LockOutlined,
  LogoutOutlined,
  MailOutlined,
  PhoneOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;
const { confirm } = Modal;

type UserProfile = {
  user_id: number;
  user_name: string;
  email: string | null;
  phone: string | null;
  organization: string | null;
  position: string | null;
  domain_name: string | null;
  role_name: string | null;
  registered_at: string | null;
};

const PersonalCenter: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [userInfo, setUserInfo] = useState<UserProfile | null>(null);
  const [activeTab, setActiveTab] = useState("basic");
  const [submitLoading, setSubmitLoading] = useState(false);
  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [isPwdModalVisible, setIsPwdModalVisible] = useState(false);
  const [editForm] = Form.useForm();
  const [pwdForm] = Form.useForm();

  const getToken = () => {
    const token = localStorage.getItem("token") || "";
    return token.trim().replace(/^["']+|["']+$/g, "");
  };

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/auth/users/profile", {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const data = await res.json();
      if (data.success) {
        setUserInfo(data.data);
      } else {
        message.error(data.message || "获取个人信息失败");
      }
    } catch {
      message.error("获取个人信息失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchProfile();
  }, []);

  const completeness = useMemo(() => {
    if (!userInfo) {
      return 0;
    }
    const fields = ["user_name", "email", "phone", "organization", "position"] as const;
    const filled = fields.filter((field) => userInfo[field]);
    return Math.round((filled.length / fields.length) * 100);
  }, [userInfo]);

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.setItem("user", "{}");
    window.location.href = "/login";
  };

  const handleDeleteAccount = () => {
    confirm({
      title: "您确定要注销账号吗？",
      icon: <ExclamationCircleOutlined style={{ color: "#ff4d4f" }} />,
      content: "注销后账号会被禁用，您将无法继续登录。",
      okText: "确认注销",
      okType: "danger",
      cancelText: "取消",
      onOk: async () => {
        try {
          const res = await fetch("/api/auth/users/profile/delete", {
            method: "DELETE",
            headers: { Authorization: `Bearer ${getToken()}` },
          });
          const data = await res.json();
          if (data.success) {
            message.success("账号已注销");
            logout();
          } else {
            message.error(data.message || "注销失败");
          }
        } catch {
          message.error("服务器响应异常，请稍后再试");
        }
      },
    });
  };

  const handleEditSubmit = async (values: Record<string, string>) => {
    setSubmitLoading(true);
    try {
      const res = await fetch("/api/auth/users/profile/update", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (data.success) {
        message.success("资料更新成功");
        setIsEditModalVisible(false);
        const currentUser = JSON.parse(localStorage.getItem("user") || "{}");
        localStorage.setItem(
          "user",
          JSON.stringify({
            ...currentUser,
            username: values.user_name || currentUser.username,
            organization: values.organization || currentUser.organization,
          }),
        );
        void fetchProfile();
      } else {
        message.error(data.message || "资料更新失败");
      }
    } catch {
      message.error("资料更新失败");
    } finally {
      setSubmitLoading(false);
    }
  };

  const handlePwdSubmit = async (values: Record<string, string>) => {
    setSubmitLoading(true);
    try {
      const res = await fetch("/api/auth/users/profile/security", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getToken()}`,
        },
        body: JSON.stringify({ action: "change_password", ...values }),
      });
      const data = await res.json();
      if (data.success) {
        message.success("密码修改成功，请重新登录");
        logout();
      } else {
        message.error(data.message || "修改失败");
      }
    } catch {
      message.error("修改失败");
    } finally {
      setSubmitLoading(false);
    }
  };

  if (loading) {
    return <Skeleton active avatar paragraph={{ rows: 12 }} style={{ padding: 24 }} />;
  }

  if (!userInfo) {
    return <Result status="error" title="加载失败" subTitle="未能获取个人信息" />;
  }

  return (
    <div style={{ backgroundColor: "#eaedf2", minHeight: "100vh", padding: 40 }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <Row gutter={24}>
          <Col xs={24} lg={8}>
            <Card
              bordered={false}
              style={{
                borderRadius: 24,
                boxShadow: "0 12px 40px rgba(0,0,0,0.12)",
                background: "linear-gradient(135deg, #001529 0%, #003a8c 100%)",
                color: "#fff",
                textAlign: "center",
                overflow: "hidden",
              }}
            >
              <div style={{ padding: "30px 0" }}>
                <Avatar
                  size={90}
                  icon={<UserOutlined />}
                  style={{ border: "4px solid rgba(255,255,255,0.15)", background: "transparent" }}
                />
                <Title level={3} style={{ color: "#fff", marginTop: 16, marginBottom: 0 }}>
                  {userInfo.user_name}
                </Title>
                <Tag color="blue" style={{ marginTop: 8, borderRadius: 4 }}>
                  {userInfo.role_name || "未分配角色"}
                </Tag>
              </div>

              <div style={{ background: "rgba(255,255,255,0.05)", padding: 24, textAlign: "left" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <Text style={{ color: "rgba(255,255,255,0.7)", fontSize: 12 }}>资料完整度</Text>
                  <Text style={{ color: "#52c41a", fontWeight: "bold" }}>{completeness}%</Text>
                </div>
                <Progress percent={completeness} showInfo={false} strokeColor="#52c41a" trailColor="rgba(255,255,255,0.1)" strokeWidth={6} />

                <Menu
                  mode="inline"
                  selectedKeys={[activeTab]}
                  onClick={({ key }) => setActiveTab(key)}
                  theme="dark"
                  style={{ background: "transparent", border: "none", marginTop: 24 }}
                  items={[
                    { key: "basic", icon: <UserOutlined />, label: "基本信息详情" },
                    { key: "security", icon: <SafetyCertificateOutlined />, label: "安全与注销" },
                  ]}
                />
              </div>
            </Card>
          </Col>

          <Col xs={24} lg={16}>
            <Card
              bordered={false}
              style={{ borderRadius: 24, boxShadow: "0 8px 30px rgba(0,0,0,0.05)", minHeight: 520 }}
              title={<Title level={4} style={{ margin: 0 }}>{activeTab === "basic" ? "资料卡片" : "安全管理"}</Title>}
              extra={
                activeTab === "basic" ? (
                  <Button
                    type="primary"
                    shape="round"
                    onClick={() => {
                      editForm.setFieldsValue(userInfo);
                      setIsEditModalVisible(true);
                    }}
                  >
                    编辑资料
                  </Button>
                ) : null
              }
            >
              {activeTab === "basic" ? (
                <Row gutter={[16, 16]}>
                  {[
                    { label: "所属机构", value: userInfo.organization, icon: <BankOutlined />, color: "#1677ff" },
                    { label: "业务领域", value: userInfo.domain_name, icon: <GlobalOutlined />, color: "#722ed1" },
                    { label: "电子邮箱", value: userInfo.email, icon: <MailOutlined />, color: "#52c41a" },
                    { label: "联系电话", value: userInfo.phone, icon: <PhoneOutlined />, color: "#faad14" },
                    { label: "当前职位", value: userInfo.position, icon: <IdcardOutlined />, color: "#eb2f96" },
                    { label: "加入时间", value: userInfo.registered_at, icon: <CalendarOutlined />, color: "#13c2c2" },
                  ].map((item) => (
                    <Col span={12} key={item.label}>
                      <div style={{ padding: 16, background: "#f8fafc", borderRadius: 16, border: "1px solid #edf2f7", height: "100%" }}>
                        <Space style={{ marginBottom: 4 }}>
                          <span style={{ color: item.color }}>{item.icon}</span>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {item.label}
                          </Text>
                        </Space>
                        <div style={{ fontSize: 15, fontWeight: 600, color: "#1a1a1a" }}>{item.value || "未设置"}</div>
                      </div>
                    </Col>
                  ))}
                </Row>
              ) : (
                <Space direction="vertical" size={20} style={{ width: "100%" }}>
                  <div
                    style={{
                      padding: 24,
                      background: "#f0f7ff",
                      borderRadius: 20,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <Space size={16}>
                      <div
                        style={{
                          width: 48,
                          height: 48,
                          borderRadius: 12,
                          background: "#fff",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "#1890ff",
                          fontSize: 24,
                        }}
                      >
                        <LockOutlined />
                      </div>
                      <div>
                        <Text strong style={{ fontSize: 16 }}>
                          账户密码
                        </Text>
                        <div>
                          <Text type="secondary">
                          定期修改密码，保障账户安全
                          </Text>
                        </div>
                      </div>
                    </Space>
                    <Button type="primary" ghost onClick={() => setIsPwdModalVisible(true)}>
                      修改密码
                    </Button>
                  </div>

                  <div style={{ padding: 24, background: "#fff1f0", borderRadius: 20, border: "1px solid #ffccc7" }}>
                    <Title level={5} style={{ color: "#ff4d4f" }}>
                      <ExclamationCircleOutlined /> 危险区域
                    </Title>
                    <Paragraph type="secondary">账户注销后会被禁用，后续需由管理员恢复。</Paragraph>
                    <Button danger type="primary" onClick={handleDeleteAccount} icon={<LogoutOutlined />}>
                      注销此账户
                    </Button>
                  </div>
                </Space>
              )}
            </Card>
          </Col>
        </Row>
      </div>

      <Modal
        title="编辑资料"
        open={isEditModalVisible}
        onCancel={() => setIsEditModalVisible(false)}
        onOk={() => editForm.submit()}
        confirmLoading={submitLoading}
        centered
      >
        <Form form={editForm} layout="vertical" onFinish={handleEditSubmit} style={{ marginTop: 20 }}>
          <Form.Item name="user_name" label="用户名" rules={[{ required: true, message: "请输入用户名" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ type: "email", message: "邮箱格式不正确" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="手机号">
            <Input />
          </Form.Item>
          <Form.Item name="organization" label="机构名称">
            <Input />
          </Form.Item>
          <Form.Item name="position" label="职位">
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="修改密码"
        open={isPwdModalVisible}
        onCancel={() => setIsPwdModalVisible(false)}
        onOk={() => pwdForm.submit()}
        confirmLoading={submitLoading}
        centered
      >
        <Form form={pwdForm} layout="vertical" onFinish={handlePwdSubmit} style={{ marginTop: 20 }}>
          <Form.Item name="old_password" label="原密码" rules={[{ required: true, message: "请输入原密码" }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item
            name="new_password"
            label="新密码"
            rules={[{ required: true, min: 6, message: "新密码至少 6 位" }]}
          >
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PersonalCenter;
