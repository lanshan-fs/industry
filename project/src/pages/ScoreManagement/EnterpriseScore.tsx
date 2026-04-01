import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Input,
  List,
  Row,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  CalculatorOutlined,
  CheckCircleOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { Radar } from "@ant-design/plots";

const { Title, Text } = Typography;

const EnterpriseScore: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const initialKeyword = searchParams.get("id") || searchParams.get("company") || searchParams.get("keyword") || "";

  const [keyword, setKeyword] = useState(initialKeyword);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [activeDimension, setActiveDimension] = useState("基础评分");

  const fetchScore = async (target: string) => {
    const trimmed = target.trim();
    if (!trimmed) return;
    setLoading(true);
    try {
      const query = searchParams.get("id")
        ? `id=${encodeURIComponent(trimmed)}`
        : `keyword=${encodeURIComponent(trimmed)}`;
      const response = await fetch(`/api/scoring/enterprise-score/?${query}`);
      const result = await response.json();
      if (result.success) {
        setData(result.data);
        const dimensionKeys = Object.keys(result.data.dimensionDetails || {});
        if (dimensionKeys.length > 0) {
          setActiveDimension(dimensionKeys[0]);
        }
      } else {
        setData(null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialKeyword) {
      fetchScore(initialKeyword);
    }
  }, [initialKeyword]);

  const radarConfig = {
    data: data?.radarData || [],
    xField: "item",
    yField: "score",
    area: { style: { fillOpacity: 0.2 } },
    point: { size: 4, shape: "circle" },
    scale: { y: { min: 0, max: 100 } },
    style: { lineWidth: 2 },
  };

  const detailColumns = [
    { title: "评分项", dataIndex: "item", key: "item", width: "20%" },
    {
      title: "依据说明",
      dataIndex: "value",
      key: "value",
      render: (text: string) => <Text>{text}</Text>,
    },
    { title: "得分", dataIndex: "rawScore", key: "rawScore", width: 100 },
    { title: "时间", dataIndex: "time", key: "time", width: 100 },
  ];

  if (!loading && !data && initialKeyword) {
    return (
      <Card bordered={false}>
        <Empty description="未找到匹配的企业评分详情" />
      </Card>
    );
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: "100%" }}>
      <Card bordered={false} bodyStyle={{ padding: "16px 24px" }}>
        <Input.Search
          placeholder="输入企业名称、统一社会信用代码或企业 ID"
          enterButton="查询评分"
          size="large"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          onSearch={fetchScore}
          loading={loading}
          style={{ maxWidth: 640 }}
        />
      </Card>

      {loading ? (
        <Card bordered={false}>
          <div style={{ textAlign: "center", padding: "80px 0" }}>
            <Spin size="large" tip="评分详情加载中..." />
          </div>
        </Card>
      ) : null}

      {!loading && data ? (
        <>
          <Card bordered={false} title="企业基本信息">
            <Descriptions bordered column={{ xxl: 4, xl: 3, lg: 3, md: 2, sm: 1, xs: 1 }}>
              <Descriptions.Item label="企业名称">{data.enterprise.name}</Descriptions.Item>
              <Descriptions.Item label="统一社会信用代码">{data.enterprise.creditCode}</Descriptions.Item>
              <Descriptions.Item label="所属产业">{data.enterprise.industry}</Descriptions.Item>
              <Descriptions.Item label="产业路径">
                <Tag color="cyan">{data.enterprise.chainPosition}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="注册资本">{data.enterprise.regCapital}</Descriptions.Item>
              <Descriptions.Item label="成立日期">{data.enterprise.estDate}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Row gutter={16}>
            <Col xs={24} md={6}>
              <Card bordered={false} style={{ height: "100%", textAlign: "center" }}>
                <div style={{ padding: "40px 0" }}>
                  <Title level={5} type="secondary">
                    企业综合评分
                  </Title>
                  <Title style={{ fontSize: 64, margin: "10px 0", color: "#1890ff" }}>
                    {data.overview.totalScore}
                  </Title>
                  <div style={{ marginBottom: 20 }}>
                    <Tag color="gold" style={{ fontSize: 16, padding: "5px 15px" }}>
                      评级：{data.overview.level}
                    </Tag>
                  </div>
                  <Text type="secondary">
                    行业排名：
                    <b style={{ color: "#333", marginLeft: 6 }}>
                      {data.overview.rank ? `第 ${data.overview.rank} 名` : "暂无"}
                    </b>
                  </Text>
                </div>
              </Card>
            </Col>

            <Col xs={24} md={10}>
              <Card bordered={false} title="维度能力分析" style={{ height: "100%" }}>
                <div style={{ height: 300 }}>
                  <Radar {...radarConfig} />
                </div>
              </Card>
            </Col>

            <Col xs={24} md={8}>
              <Card bordered={false} title="评分维度明细" style={{ height: "100%" }} bodyStyle={{ padding: "0 12px" }}>
                <List
                  itemLayout="horizontal"
                  dataSource={data.radarData}
                  renderItem={(item: any) => (
                    <List.Item
                      onClick={() => setActiveDimension(item.item)}
                      style={{
                        cursor: "pointer",
                        padding: "12px",
                        backgroundColor: activeDimension === item.item ? "#e6f7ff" : "transparent",
                        borderLeft: activeDimension === item.item ? "3px solid #1890ff" : "3px solid transparent",
                        transition: "all 0.3s",
                      }}
                    >
                      <List.Item.Meta
                        avatar={<CheckCircleOutlined style={{ color: item.score >= 60 ? "#52c41a" : "#faad14" }} />}
                        title={<span>{item.item}</span>}
                      />
                      <div style={{ fontWeight: "bold", fontSize: 16, color: "#1890ff" }}>{item.score} 分</div>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>

          <Card
            bordered={false}
            title={
              <Space>
                <CalculatorOutlined />
                <span>评分计算依据与数据溯源</span>
              </Space>
            }
            extra={
              <Button onClick={() => navigate(-1)}>
                返回
              </Button>
            }
          >
            <Space direction="vertical" size="large" style={{ width: "100%" }}>
              {Object.entries(data.dimensionDetails || {}).map(([key, detail]: [string, any]) => (
                <div key={key}>
                  <Alert
                    message={
                      <Space direction="vertical">
                        <Text strong style={{ fontSize: 16 }}>
                          <FileTextOutlined /> {key}
                        </Text>
                        <Text code style={{ fontSize: 14 }}>
                          {detail.formula}
                        </Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {detail.desc}
                        </Text>
                      </Space>
                    }
                    type={activeDimension === key ? "info" : "warning"}
                    showIcon={false}
                    style={{ marginBottom: 16, border: activeDimension === key ? "1px solid #91caff" : undefined }}
                  />
                  {activeDimension === key ? (
                    <Table
                      columns={detailColumns}
                      dataSource={detail.tableData || []}
                      pagination={{ pageSize: 8 }}
                      size="middle"
                      bordered
                      locale={{ emptyText: "该维度暂无详细记录" }}
                    />
                  ) : null}
                </div>
              ))}
            </Space>
          </Card>
        </>
      ) : null}
    </Space>
  );
};

export default EnterpriseScore;
