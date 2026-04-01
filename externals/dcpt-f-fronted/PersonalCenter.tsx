import React, { useEffect, useState, useMemo } from "react";
import {
  Card, Row, Col, Typography, Tag, Avatar, Button, Modal,
  Form, Input, message, Skeleton, Space, Menu, Divider, Progress
} from "antd";
import {
  UserOutlined, MailOutlined, PhoneOutlined, IdcardOutlined,
  SafetyCertificateOutlined, EditOutlined, KeyOutlined,
  ExclamationCircleOutlined, BankOutlined, LogoutOutlined,
  GlobalOutlined, CalendarOutlined, LockOutlined, ShieldOutlined
} from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;
const { confirm } = Modal;

const PersonalCenter: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [userInfo, setUserInfo] = useState<any>(null);
  const [activeTab, setActiveTab] = useState("basic");
  const [submitLoading, setSubmitLoading] = useState(false);

  const [isEditModalVisible, setIsEditModalVisible] = useState(false);
  const [isPwdModalVisible, setIsPwdModalVisible] = useState(false);
  const [editForm] = Form.useForm();
  const [pwdForm] = Form.useForm();

  const fetchProfile = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/api/users/profile", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (data.success) setUserInfo(data.data);
    } catch (err) {
      message.error("获取信息失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProfile(); }, []);

  const completeness = useMemo(() => {
    if (!userInfo) return 0;
    const fields = ['user_name', 'email', 'phone', 'organization', 'position'];
    const filled = fields.filter(f => userInfo[f] && userInfo[f] !== '');
    return Math.round((filled.length / fields.length) * 100);
  }, [userInfo]);

  // --- 核心逻辑：注销用户 ---
  const handleDeleteAccount = () => {
    confirm({
      title: '您确定要永久注销账号吗？',
      icon: <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />,
      content: '注销后，您的所有个人数据、项目记录将从数据库中永久物理删除，不可恢复！',
      okText: '确认注销',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const token = localStorage.getItem("token");
          const res = await fetch("http://localhost:8000/api/users/profile/delete", {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` },
          });
          const data = await res.json();
          if (data.success) {
            message.success("账号已注销，感谢您的使用");
            localStorage.clear(); // 清除登录状态
            window.location.href = "/login"; // 跳转回登录页
          } else {
            message.error(data.message || "注销失败");
          }
        } catch (err) {
          message.error("服务器响应异常，请稍后再试");
        }
      },
    });
  };

  // --- 资料更新逻辑 ---
  const handleEditSubmit = async (values: any) => {
    setSubmitLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/api/users/profile/update", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      if (data.success) {
        message.success("资料更新成功");
        setIsEditModalVisible(false);
        fetchProfile();
      }
    } finally {
      setSubmitLoading(false);
    }
  };

  // --- 修改密码逻辑 ---
  const handlePwdSubmit = async (values: any) => {
    setSubmitLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/api/users/profile/security", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ action: 'change_password', ...values }),
      });
      const data = await res.json();
      if (data.success) {
        message.success("密码修改成功，请重新登录");
        localStorage.clear();
        window.location.href = "/login";
      } else {
        message.error(data.message || "修改失败");
      }
    } finally {
      setSubmitLoading(false);
    }
  };

  if (loading) return <Skeleton active avatar paragraph={{ rows: 12 }} />;

  return (
    <div style={{ backgroundColor: "#eaedf2", minHeight: "100vh", padding: "40px" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <Row gutter={24}>
          {/* 左侧卡片 */}
          <Col xs={24} lg={8}>
            <Card
              bordered={false}
              style={{
                borderRadius: 24,
                boxShadow: '0 12px 40px rgba(0,0,0,0.12)',
                background: 'linear-gradient(135deg, #001529 0%, #003a8c 100%)',
                color: '#fff',
                textAlign: 'center',
                overflow: 'hidden'
              }}
            >
              <div style={{ padding: '30px 0' }}>
                <Avatar size={90} icon={<UserOutlined />} style={{ border: '4px solid rgba(255,255,255,0.15)', background: 'transparent' }} />
                <Title level={3} style={{ color: '#fff', marginTop: 16, marginBottom: 0 }}>{userInfo?.user_name}</Title>
                <Tag color="blue" style={{ marginTop: 8, borderRadius: 4 }}>{userInfo?.role_name}</Tag>
              </div>

              <div style={{ background: 'rgba(255,255,255,0.05)', padding: '24px', textAlign: 'left' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12 }}>资料完整度</Text>
                  <Text style={{ color: '#52c41a', fontWeight: 'bold' }}>{completeness}%</Text>
                </div>
                <Progress percent={completeness} showInfo={false} strokeColor="#52c41a" trailColor="rgba(255,255,255,0.1)" strokeWidth={6} />

                <Menu
                  mode="inline"
                  selectedKeys={[activeTab]}
                  onClick={({ key }) => setActiveTab(key)}
                  theme="dark"
                  style={{ background: 'transparent', border: 'none', marginTop: 24 }}
                  items={[
                    { key: 'basic', icon: <UserOutlined />, label: '基本信息详情' },
                    { key: 'security', icon: <SafetyCertificateOutlined />, label: '安全与注销' },
                  ]}
                />
              </div>
            </Card>
          </Col>

          {/* 右侧内容 */}
          <Col xs={24} lg={16}>
            <Card
              bordered={false}
              style={{ borderRadius: 24, boxShadow: '0 8px 30px rgba(0,0,0,0.05)', minHeight: 520 }}
              title={<Title level={4} style={{ margin: 0 }}>{activeTab === 'basic' ? '资料卡片' : '安全管理'}</Title>}
              extra={activeTab === 'basic' && (
                <Button type="primary" shape="round" icon={<EditOutlined />} onClick={() => {
                  editForm.setFieldsValue(userInfo);
                  setIsEditModalVisible(true);
                }}>编辑资料</Button>
              )}
            >
              {activeTab === 'basic' ? (
                <Row gutter={[16, 16]}>
                  {[
                    { label: '所属机构', value: userInfo?.organization, icon: <BankOutlined />, color: '#1677ff' },
                    { label: '业务领域', value: userInfo?.domain_name, icon: <GlobalOutlined />, color: '#722ed1' },
                    { label: '电子邮箱', value: userInfo?.email, icon: <MailOutlined />, color: '#52c41a' },
                    { label: '联系电话', value: userInfo?.phone, icon: <PhoneOutlined />, color: '#faad14' },
                    { label: '当前职位', value: userInfo?.position, icon: <IdcardOutlined />, color: '#eb2f96' },
                    { label: '加入时间', value: userInfo?.registered_at, icon: <CalendarOutlined />, color: '#13c2c2' },
                  ].map((item, i) => (
                    <Col span={12} key={i}>
                      <div style={{ padding: 16, background: '#f8fafc', borderRadius: 16, border: '1px solid #edf2f7', height: '100%' }}>
                        <Space style={{ marginBottom: 4 }}>
                          <span style={{ color: item.color }}>{item.icon}</span>
                          <Text type="secondary" style={{ fontSize: 12 }}>{item.label}</Text>
                        </Space>
                        <div style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a' }}>{item.value || '未设置'}</div>
                      </div>
                    </Col>
                  ))}
                </Row>
              ) : (
                <Space direction="vertical" size={20} style={{ width: '100%' }}>
                  <div style={{ padding: 24, background: '#f0f7ff', borderRadius: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Space size={16}>
                      <div style={{ width: 48, height: 48, borderRadius: 12, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#1890ff', fontSize: 24 }}>
                        <LockOutlined />
                      </div>
                      <div>
                        <Text strong style={{ fontSize: 16 }}>账户密码</Text>
                        <Text type="secondary" block>定期修改密码，保障数据安全</Text>
                      </div>
                    </Space>
                    <Button type="primary" ghost onClick={() => setIsPwdModalVisible(true)}>修改密码</Button>
                  </div>

                  <div style={{ padding: 24, background: '#fff1f0', borderRadius: 20, border: '1px solid #ffccc7' }}>
                    <Title level={5} danger><ExclamationCircleOutlined /> 危险区域</Title>
                    <Paragraph type="secondary">账户注销后无法找回，请谨慎操作。</Paragraph>
                    <Button danger type="primary" onClick={handleDeleteAccount} icon={<LogoutOutlined />}>注销此账户</Button>
                  </div>
                </Space>
              )}
            </Card>
          </Col>
        </Row>
      </div>

      {/* 弹窗部分 */}
      <Modal title="编辑资料" open={isEditModalVisible} onCancel={() => setIsEditModalVisible(false)} onOk={() => editForm.submit()} confirmLoading={submitLoading} centered>
        <Form form={editForm} layout="vertical" onFinish={handleEditSubmit} style={{ marginTop: 20 }}>
          <Form.Item name="user_name" label="用户名" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="email" label="邮箱"><Input /></Form.Item>
          <Form.Item name="phone" label="手机号"><Input /></Form.Item>
          <Form.Item name="organization" label="机构名称"><Input /></Form.Item>
          <Form.Item name="position" label="职位"><Input /></Form.Item>
        </Form>
      </Modal>

      <Modal title="修改密码" open={isPwdModalVisible} onCancel={() => setIsPwdModalVisible(false)} onOk={() => pwdForm.submit()} confirmLoading={submitLoading} centered>
        <Form form={pwdForm} layout="vertical" onFinish={handlePwdSubmit} style={{ marginTop: 20 }}>
          <Form.Item name="old_password" label="原密码" rules={[{ required: true }]}><Input.Password /></Form.Item>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6 }]}><Input.Password /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default PersonalCenter;