import React, { useEffect, useState } from "react";
import { 
  Table, Button, Card, Row, Col, Input, Space, Tag, 
  message, Typography, Tooltip, Popconfirm, Modal, Form, DatePicker, Select, Upload
} from "antd";
import type { TableProps } from "antd";
import { 
  PlusOutlined, ImportOutlined, ReloadOutlined, 
  DatabaseOutlined, EditOutlined, DeleteOutlined, InboxOutlined, DownloadOutlined
} from "@ant-design/icons";
import dayjs from "dayjs";
import { useNavigate } from "react-router-dom"; // 1. 新增导入

const { Text, Title } = Typography;
const { Dragger } = Upload;

interface EnterpriseDataType {
  company_id: number;
  company_name: string;
  credit_code: string;
  establish_date: string; 
  register_capital: string;
  paid_capital: string;
  company_type: string;
  organization_type: string;
  investment_type: string;
  company_scale: string;
  branch_count: number;
  branch_name: string;
  register_address: string;
  financing_round: string;
  company_qualification: string;
  legal_representative: string;
  register_number: string;
  org_code: string;
  industry_belong: string;
  business_scope: string;
  email_business: string;
  shareholders: string;
  contact_phone: string;
}

const EnterpriseData: React.FC = () => {
  const navigate = useNavigate(); // 2. 新增 hooks 声明
  const [data, setData] = useState<EnterpriseDataType[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(30); 
  
  // 专门用来记住当前的搜索词，防止刷新或翻页时搜索条件丢失
  const [searchText, setSearchText] = useState(""); 
  
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isImportVisible, setIsImportVisible] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null); 
  const [form] = Form.useForm();

  const API_BASE = "http://127.0.0.1:8000/api/companies";

  // 默认使用 searchText，保证翻页和刷新不丢条件
  const fetchData = async (page = 1, size = 30, keyword = searchText) => {
    setLoading(true);
    try {
      const url = `${API_BASE}/?page=${page}&pageSize=${size}&keyword=${encodeURIComponent(keyword)}`;
      const response = await fetch(url);
      const result = await response.json();
      if (result.code === 200) {
        setData(result.data || []);
        setTotal(result.total || 0);
        setCurrentPage(page);
        setSearchText(keyword); // 每次请求成功后，把关键词记下来
        setSelectedRowKeys([]); 
      }
    } catch (error) {
      message.error("后端连接异常，请确认 Django 已启动");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { 
    fetchData(1, pageSize); 
  }, []);

  // 专属的刷新函数
  const handleRefresh = () => {
    fetchData(currentPage, pageSize, searchText);
    message.success("表格数据已刷新");
  };

  const handleBatchDelete = async () => {
    try {
      const response = await fetch(`${API_BASE}/batch_delete/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: selectedRowKeys })
      });
      const res = await response.json();
      if (res.code === 200) {
        message.success(res.message);
        fetchData(currentPage, pageSize);
      }
    } catch (error) {
      message.error("操作失败，请检查网络");
    }
  };

  const showAddModal = () => {
    setEditingId(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const showEditModal = (record: EnterpriseDataType) => {
    setEditingId(record.company_id);
    const formData = {
      ...record,
      establish_date: record.establish_date ? dayjs(record.establish_date) : null
    };
    form.setFieldsValue(formData);
    setIsModalVisible(true);
  };

  const handleFormSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const payload = {
        ...values,
        establish_date: values.establish_date ? values.establish_date.format('YYYY-MM-DD') : null
      };
      
      const url = editingId ? `${API_BASE}/${editingId}/` : `${API_BASE}/`;
      const method = editingId ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const result = await response.json().catch(() => ({}));
      
      if (response.ok && (result.code === 200 || result.code === 201 || result.code === undefined)) {
        message.success("企业数据保存成功！");
        setIsModalVisible(false);
        fetchData(currentPage, pageSize, searchText); 
      } else {
        let errorMsg = result.message || "保存失败，请检查字段是否有遗漏或重复";
        if (result.data && typeof result.data === 'object' && !Array.isArray(result.data)) {
          errorMsg = Object.values(result.data).flat().join("；") || errorMsg;
        }
        message.error(`后端拒绝录入: ${errorMsg}`);
      }
    } catch (error: any) {
      if (!error.errorFields) {
        message.error("请求异常，请检查网络或后端状态");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      const response = await fetch(`${API_BASE}/${id}/`, { method: 'DELETE' });
      if (response.ok) {
        message.success('数据已彻底删除');
        fetchData(currentPage, pageSize, searchText);
      }
    } catch (error) {
      message.error('删除异常');
    }
  };

  const handleDownloadTemplate = () => {
    window.open(`${API_BASE}/template/download/`);
  };

  const uploadProps = {
    name: 'file',
    action: `${API_BASE}/import/`,
    accept: ".xlsx, .xls",
    showUploadList: false,
    onChange(info: any) {
      if (info.file.status === 'done') {
        const res = info.file.response;
        if (res && res.code === 200) {
          message.success(res.message || "导入成功");
          setIsImportVisible(false);
          setSearchText(""); 
          fetchData(1, pageSize, "");
        } else {
          message.error(res?.message || "导入失败，请检查模板字段");
        }
      } else if (info.file.status === 'error') {
        message.error("导入请求失败，请检查后端服务");
      }
    },
  };

  const columns: TableProps<EnterpriseDataType>["columns"] = [
    { 
      title: "企业名称", 
      dataIndex: "company_name", 
      fixed: 'left', 
      width: 160, 
      ellipsis: true,
      // 3. 核心修改：点击名字跳转
      render: (text, record) => (
        <Text 
          strong 
          style={{ color: '#1677ff', fontSize: '16px', cursor: 'pointer' }} 
          onClick={() => navigate(`/industry-portrait/enterprise-profile?id=${record.company_id}`)}
        >
          {text}
        </Text>
      )
    },
    { title: "法人", dataIndex: "legal_representative", width: 80, ellipsis: true },
    { title: "信用代码", dataIndex: "credit_code", width: 180 },
    { title: "注册资本", dataIndex: "register_capital", width: 130 },
    { 
      title: "融资轮次", 
      dataIndex: "financing_round", 
      width: 180, 
      render: (t) => {
        if (!t || t === '未融资') {
          return <Tag style={{ color: '#d48806', background: '#fffbe6', borderColor: '#ffe58f' }}>无明确投融资轮次信息</Tag>;
        }
        return <Tag color="gold">{t}</Tag>;
      }
    },
    { title: "行业", dataIndex: "industry_belong", width: 150, ellipsis: true },
    { title: "成立日期", dataIndex: "establish_date", width: 110 }, 
    { title: "联系电话", dataIndex: "contact_phone", width: 160, ellipsis: true },
    { title: "注册地址", dataIndex: "register_address", width: 300, ellipsis: true },
    { 
      title: "经营范围", 
      dataIndex: "business_scope", 
      width: 600, 
      ellipsis: true, 
      render:(s) => <Tooltip title={s}>{s}</Tooltip> 
    },
    { 
      title: "操作", 
      key: "action", 
      fixed: 'right', 
      width: 50,
      align: 'center',
      render: (_, record) => (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '6px' }}>
            <EditOutlined 
              style={{ color: '#1677ff', cursor: 'pointer', fontSize: '15px' }} 
              onClick={() => showEditModal(record)}
            />
          <Popconfirm title="确定彻底删除吗？" onConfirm={() => handleDelete(record.company_id)}>
              <DeleteOutlined style={{ color: '#ff4d4f', cursor: 'pointer', fontSize: '15px' }} />
          </Popconfirm>
        </div>
      ) 
    }
  ];

  return (
    <div style={{ padding: "20px", background: "#f0f2f5", minHeight: "100vh" }}>
      <style>{`
        .ant-table { font-size: 16px !important; }
        .ant-table-thead > tr > th { font-size: 16px !important; background: #fafafa !important; }
        .ant-table-cell { white-space: nowrap !important; padding: 12px 8px !important; } 
      `}</style>

      {/* 顶部单行卡片 */}
      <Card style={{ marginBottom: 16, borderRadius: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space size="large">
            <DatabaseOutlined style={{ fontSize: 26, color: '#1677ff' }} />
            <Title level={3} style={{ margin: 0 }}>产业链洞察专家系统</Title>
            <Tag color="blue" style={{ fontSize: '16px' }}>{total} 样本</Tag>
          </Space>
          
          <Space size="middle">
            <Input.Search 
              placeholder="搜索企业名称..." 
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={(v) => fetchData(1, pageSize, v)} 
              style={{ width: 350 }} 
              size="large"
              allowClear 
            />
            <Button type="primary" size="large" icon={<PlusOutlined />} onClick={showAddModal}>新增</Button>
            <Button size="large" icon={<ImportOutlined />} onClick={() => setIsImportVisible(true)}>导入</Button>
            
            <Popconfirm 
              title={`确认删除选中的 ${selectedRowKeys.length} 项记录？`} 
              disabled={selectedRowKeys.length === 0} 
              onConfirm={handleBatchDelete}
            >
              <Button danger disabled={selectedRowKeys.length === 0}>批量删除</Button>
            </Popconfirm>

            <Button 
              size="large" 
              icon={<ReloadOutlined />} 
              onClick={handleRefresh} 
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        </div>
      </Card>

      <Card styles={{ body: { padding: 0 } }} style={{ borderRadius: 8, overflow: 'hidden' }}>
        <Table
          rowSelection={{
            selectedRowKeys,
            onChange: (keys) => setSelectedRowKeys(keys),
            columnWidth: 40,
          }}
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="company_id"
          size="large" 
          scroll={{ x: 3000, y: 'calc(100vh - 250px)' }} 
          pagination={{
            total: total,
            current: currentPage,
            pageSize: pageSize,
            showSizeChanger: true,
            pageSizeOptions: ['30', '50', '100'],
            showTotal: (t) => `共 ${t} 条记录`,
            onChange: (p, s) => { setPageSize(s); fetchData(p, s, searchText); } 
          }}
          bordered
        />
      </Card>

      {/* 新增/编辑弹窗：15个字段全部归位，绝对没少！ */}
      <Modal
        title={<Title level={4} style={{margin:0}}>{editingId ? '编辑医药企业画像' : '录入新增医药企业画像'}</Title>}
        open={isModalVisible}
        onOk={handleFormSubmit}
        onCancel={() => setIsModalVisible(false)}
        width={1000}
        okText="确认保存"
        cancelText="取消"
        centered
      >
        <Form form={form} layout="vertical" style={{ marginTop: 20 }}>
          <Row gutter={24}>
            <Col span={12}><Form.Item name="company_name" label="企业名称" rules={[{ required: true }]}><Input disabled={!!editingId}/></Form.Item></Col>
            <Col span={12}><Form.Item name="credit_code" label="统一社会信用代码" rules={[{ required: true }]}><Input disabled={!!editingId}/></Form.Item></Col>
            <Col span={8}><Form.Item name="legal_representative" label="法定代表人" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="establish_date" label="成立日期" rules={[{ required: true }]}><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={8}>
              <Form.Item name="industry_belong" label="所属行业" rules={[{ required: true }]}>
                <Select>
                  <Select.Option value="中药生产">中药生产</Select.Option>
                  <Select.Option value="生物制药">生物制药</Select.Option>
                  <Select.Option value="医疗器械">医疗器械</Select.Option>
                  <Select.Option value="医药流通">医药流通</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}><Form.Item name="register_capital" label="注册资本"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="paid_capital" label="实缴资本"><Input /></Form.Item></Col>
            <Col span={8}>
              <Form.Item name="financing_round" label="融资轮次">
                <Select>
                  <Select.Option value="未融资">未融资</Select.Option>
                  <Select.Option value="种子轮">种子轮</Select.Option>
                  <Select.Option value="天使轮">天使轮</Select.Option>
                  <Select.Option value="A轮">A轮</Select.Option>
                  <Select.Option value="B轮">B轮</Select.Option>
                  <Select.Option value="C轮">C轮</Select.Option>
                  <Select.Option value="D轮及以上">D轮及以上</Select.Option>
                  <Select.Option value="IPO已上市">IPO已上市</Select.Option>
                  <Select.Option value="战略融资">战略融资</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}><Form.Item name="company_type" label="企业类型"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="company_scale" label="人员规模"><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="contact_phone" label="联系电话"><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="email_business" label="电子邮箱"><Input /></Form.Item></Col>
            <Col span={12}><Form.Item name="register_address" label="注册地址"><Input /></Form.Item></Col>
            <Col span={24}><Form.Item name="shareholders" label="主要股东信息"><Input.TextArea rows={2} /></Form.Item></Col>
            <Col span={24}><Form.Item name="business_scope" label="经营范围"><Input.TextArea rows={3} /></Form.Item></Col>
            
            {/* 隐藏字段或不常用字段映射 */}
            <Col span={0}><Form.Item name="organization_type"><Input /></Form.Item></Col>
            <Col span={0}><Form.Item name="investment_type"><Input /></Form.Item></Col>
            <Col span={0}><Form.Item name="org_code"><Input /></Form.Item></Col>
            <Col span={0}><Form.Item name="register_number"><Input /></Form.Item></Col>
          </Row>
        </Form>
      </Modal>

      {/* 导入弹窗 */}
      <Modal title="批量导入" open={isImportVisible} onCancel={() => setIsImportVisible(false)} footer={null} centered width={500}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
          <Button type="primary" ghost icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>下载模板</Button>
        </div>
        <Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">点击或拖拽文件上传</p>
        </Dragger>
      </Modal>
    </div>
  );
};

export default EnterpriseData;