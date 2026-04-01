import React, { useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  Modal,
  Result,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import type { TableProps } from "antd";
import {
  EyeOutlined,
  NotificationOutlined,
  ReloadOutlined,
  SearchOutlined,
  ShopOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";

const { Text, Paragraph } = Typography;

interface EnterpriseDataType {
  key: string;
  companyId: number;
  creditCode: string;
  name: string;
  legalPerson: string;
  registeredCapital: number;
  variants: string;
  tags: string[];
  updateTime: string;
  establishmentDate?: string;
  qualificationLabel?: string;
  companyStatus?: string;
  score?: number;
  isHighTech?: boolean;
}

interface EnterpriseStats {
  total: number;
  highTech: number;
  scored: number;
  recentUpdated: number;
}

interface EnterpriseDetail {
  companyId: number;
  name: string;
  creditCode: string;
  legalPerson: string;
  registeredCapital: string;
  paidCapital: string;
  establishmentDate: string;
  updateTime: string;
  qualificationLabel: string;
  companyStatus: string;
  companyType: string;
  orgType: string;
  companyScale: string;
  taxRating: string;
  financingRound: string;
  address: string;
  district: string;
  street: string;
  phone: string;
  email: string;
  insuredNum: number;
  businessScope: string;
  tags: string[];
  flags: {
    highTech: boolean;
    techSme: boolean;
    srdi: boolean;
    gazelle: boolean;
  };
  score: {
    total: number;
    basic: number;
    tech: number;
    professional: number;
  };
  recordCounts: {
    patents: number;
    softwareCopyrights: number;
    qualifications: number;
    customers: number;
    suppliers: number;
    risks: number;
  };
}

const EMPTY_STATS: EnterpriseStats = {
  total: 0,
  highTech: 0,
  scored: 0,
  recentUpdated: 0,
};

const EnterpriseData: React.FC = () => {
  const navigate = useNavigate();
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [data, setData] = useState<EnterpriseDataType[]>([]);
  const [stats, setStats] = useState<EnterpriseStats>(EMPTY_STATS);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [searchText, setSearchText] = useState("");
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<EnterpriseDetail | null>(null);

  const getToken = () => {
    const token = localStorage.getItem("token") || "";
    return token.trim().replace(/^["']+|["']+$/g, "");
  };

  const fetchData = async (page = 1, size = 15, keyword = "") => {
    setLoading(true);
    try {
      const query = new URLSearchParams({
        page: String(page),
        pageSize: String(size),
        keyword,
      });
      const response = await fetch(`/api/system/companies?${query.toString()}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const result = await response.json();
      if (result.success) {
        setData(result.data || []);
        setTotal(result.total || 0);
        setStats(result.stats || EMPTY_STATS);
        setCurrentPage(page);
      } else {
        message.error(result.message || "获取企业数据失败");
      }
    } catch {
      message.error("网络请求错误");
    } finally {
      setLoading(false);
    }
  };

  const fetchDetail = async (record: EnterpriseDataType) => {
    setDetailLoading(true);
    try {
      const response = await fetch(`/api/system/companies/${encodeURIComponent(record.companyId)}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      const result = await response.json();
      if (result.success) {
        setDetail(result.data);
        setDetailOpen(true);
      } else {
        message.error(result.message || "获取企业详情失败");
      }
    } catch {
      message.error("获取企业详情失败");
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    try {
      const user = JSON.parse(localStorage.getItem("user") || "{}");
      const role = String(user.role || "").toUpperCase();
      if (role === "ADMIN") {
        setIsAdmin(true);
        void fetchData(1, pageSize, "");
      } else {
        setIsAdmin(false);
      }
    } catch {
      setIsAdmin(false);
    }
  }, []);

  const handleSearch = (value: string) => {
    setSearchText(value);
    void fetchData(1, pageSize, value.trim());
  };

  const columns: TableProps<EnterpriseDataType>["columns"] = [
    {
      title: "企业名称",
      dataIndex: "name",
      key: "name",
      width: 240,
      ellipsis: true,
      render: (text, record) => (
        <Space direction="vertical" size={2}>
          <Text strong style={{ color: "#1677ff" }}>
            {text}
          </Text>
          <Space size={6} wrap>
            {record.isHighTech && (
              <Tag color="blue" bordered={false}>
                高新技术
              </Tag>
            )}
            {record.qualificationLabel ? (
              <Tag color="purple" bordered={false}>
                {record.qualificationLabel}
              </Tag>
            ) : null}
          </Space>
        </Space>
      ),
    },
    {
      title: "信用代码",
      dataIndex: "creditCode",
      key: "creditCode",
      width: 190,
      render: (text) => <Text type="secondary" copyable>{text || "-"}</Text>,
    },
    {
      title: "法定代表人",
      dataIndex: "legalPerson",
      key: "legalPerson",
      width: 110,
    },
    {
      title: "注册资本",
      dataIndex: "registeredCapital",
      key: "registeredCapital",
      width: 120,
      render: (val) => (val ? `${val} 万` : "-"),
    },
    {
      title: "企业评分",
      dataIndex: "score",
      key: "score",
      width: 100,
      render: (val: number) =>
        val ? (
          <Text strong style={{ color: "#1677ff" }}>
            {val.toFixed(2)}
          </Text>
        ) : (
          "-"
        ),
    },
    {
      title: "行业标签",
      dataIndex: "variants",
      key: "variants",
      width: 260,
      ellipsis: true,
      render: (_text: string, record) =>
        record.tags?.length ? (
          <Space size={[4, 4]} wrap>
            {record.tags.slice(0, 4).map((tag) => (
              <Tag color="cyan" key={tag} bordered={false}>
                {tag}
              </Tag>
            ))}
            {record.tags.length > 4 ? <Tag bordered={false}>+{record.tags.length - 4}</Tag> : null}
          </Space>
        ) : (
          <Text type="secondary">无标签</Text>
        ),
    },
    {
      title: "更新时间",
      dataIndex: "updateTime",
      key: "updateTime",
      width: 170,
      render: (val) => val || "-",
    },
    {
      title: "操作",
      key: "action",
      width: 180,
      align: "center",
      render: (_value, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => void fetchDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<ShopOutlined />}
            onClick={() =>
              navigate(`/industry-portrait/enterprise-profile?id=${record.companyId}`)
            }
          >
            画像
          </Button>
        </Space>
      ),
    },
  ];

  if (isAdmin === false) {
    return (
      <Result
        status="403"
        title="无权访问"
        subTitle="仅系统管理员可浏览企业主数据管理页面。"
      />
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <Card style={{ marginBottom: 16 }} styles={{ body: { padding: "16px 24px" } }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={6}>
            <Statistic title="企业总数" value={stats.total} suffix="家" />
          </Col>
          <Col xs={24} md={6}>
            <Statistic title="高新技术企业" value={stats.highTech} suffix="家" />
          </Col>
          <Col xs={24} md={6}>
            <Statistic title="已完成评分" value={stats.scored} suffix="家" />
          </Col>
          <Col xs={24} md={6}>
            <Statistic title="近30天更新" value={stats.recentUpdated} suffix="家" />
          </Col>
        </Row>
      </Card>

      <Card style={{ marginBottom: 16 }} styles={{ body: { padding: "16px 24px" } }}>
        <Row justify="space-between" gutter={[16, 16]}>
          <Col>
            <Input.Search
              placeholder="按企业名称或信用代码搜索"
              onSearch={handleSearch}
              enterButton={<><SearchOutlined /> 搜索</>}
              style={{ width: 360 }}
              allowClear
            />
          </Col>
          <Col>
            <Space>
              <Tooltip title="企业主数据仍以导入和同步脚本为准，当前页面提供浏览与校验。">
                <Button icon={<NotificationOutlined />}>主数据只读</Button>
              </Tooltip>
              <Button
                onClick={() => void fetchData(currentPage, pageSize, searchText)}
                icon={<ReloadOutlined />}
              >
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Card styles={{ body: { padding: 0 } }}>
        <Table
          columns={columns}
          dataSource={data}
          loading={loading}
          rowKey="key"
          scroll={{ x: 1300 }}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (page, size) => {
              setPageSize(size);
              void fetchData(page, size, searchText);
            },
          }}
        />
      </Card>

      <Modal
        title={detail?.name || "企业详情"}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        width={920}
        footer={[
          <Button key="profile" type="primary" onClick={() => detail && navigate(`/industry-portrait/enterprise-profile?id=${detail.companyId}`)}>
            查看企业画像
          </Button>,
          <Button key="close" onClick={() => setDetailOpen(false)}>
            关闭
          </Button>,
        ]}
      >
        {detailLoading || !detail ? (
          <Card loading={detailLoading} bordered={false} />
        ) : (
          <Space direction="vertical" size={20} style={{ width: "100%" }}>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="统一社会信用代码">{detail.creditCode || "-"}</Descriptions.Item>
              <Descriptions.Item label="法定代表人">{detail.legalPerson}</Descriptions.Item>
              <Descriptions.Item label="注册资本">{detail.registeredCapital}</Descriptions.Item>
              <Descriptions.Item label="实缴资本">{detail.paidCapital}</Descriptions.Item>
              <Descriptions.Item label="成立日期">{detail.establishmentDate}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{detail.updateTime}</Descriptions.Item>
              <Descriptions.Item label="经营状态">{detail.companyStatus}</Descriptions.Item>
              <Descriptions.Item label="融资轮次">{detail.financingRound}</Descriptions.Item>
              <Descriptions.Item label="企业类型">{detail.companyType}</Descriptions.Item>
              <Descriptions.Item label="组织类型">{detail.orgType}</Descriptions.Item>
              <Descriptions.Item label="企业规模">{detail.companyScale}</Descriptions.Item>
              <Descriptions.Item label="税务评级">{detail.taxRating}</Descriptions.Item>
              <Descriptions.Item label="地区 / 街道">{`${detail.district} / ${detail.street}`}</Descriptions.Item>
              <Descriptions.Item label="参保人数">{detail.insuredNum}</Descriptions.Item>
              <Descriptions.Item label="联系电话">{detail.phone}</Descriptions.Item>
              <Descriptions.Item label="工商邮箱">{detail.email}</Descriptions.Item>
              <Descriptions.Item label="企业地址" span={2}>
                {detail.address}
              </Descriptions.Item>
              <Descriptions.Item label="经营范围" span={2}>
                <Paragraph style={{ marginBottom: 0 }}>{detail.businessScope}</Paragraph>
              </Descriptions.Item>
            </Descriptions>

            <Card size="small" title="标签与资质">
              <Space size={[8, 8]} wrap>
                {detail.tags.length ? detail.tags.map((tag) => (
                  <Tag key={tag} color="cyan" bordered={false}>
                    {tag}
                  </Tag>
                )) : <Text type="secondary">暂无聚合标签</Text>}
                {detail.qualificationLabel !== "-" ? (
                  <Tag color="purple" bordered={false}>
                    {detail.qualificationLabel}
                  </Tag>
                ) : null}
                {detail.flags.highTech ? <Tag color="blue">高新技术</Tag> : null}
                {detail.flags.techSme ? <Tag color="green">科技中小</Tag> : null}
                {detail.flags.srdi ? <Tag color="gold">专精特新</Tag> : null}
                {detail.flags.gazelle ? <Tag color="magenta">瞪羚/独角兽</Tag> : null}
              </Space>
            </Card>

            <Row gutter={[16, 16]}>
              <Col xs={24} md={12}>
                <Card size="small" title="评分概览">
                  <Row gutter={[16, 16]}>
                    <Col span={12}>
                      <Statistic title="综合评分" value={detail.score.total} precision={2} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="基础评分" value={detail.score.basic} precision={2} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="科技评分" value={detail.score.tech} precision={2} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="专业评分" value={detail.score.professional} precision={2} />
                    </Col>
                  </Row>
                </Card>
              </Col>
              <Col xs={24} md={12}>
                <Card size="small" title="关联记录">
                  <Row gutter={[16, 16]}>
                    <Col span={12}>
                      <Statistic title="专利" value={detail.recordCounts.patents} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="软著" value={detail.recordCounts.softwareCopyrights} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="资质" value={detail.recordCounts.qualifications} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="客户" value={detail.recordCounts.customers} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="供应商" value={detail.recordCounts.suppliers} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="风险记录" value={detail.recordCounts.risks} />
                    </Col>
                  </Row>
                </Card>
              </Col>
            </Row>
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default EnterpriseData;
