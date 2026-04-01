import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Breadcrumb,
  Button,
  Card,
  Col,
  Empty,
  Input,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  ArrowLeftOutlined,
  BankOutlined,
  SearchOutlined,
  TagsOutlined,
} from "@ant-design/icons";
import type { TableProps } from "antd";

const { Title, Text } = Typography;

interface DimensionInfo {
  id: number;
  name: string;
  key: string;
  color: string;
  description: string;
  tagCount: number;
  usedCount: number;
  coverage: number;
  totalCompanies: number;
}

interface SubdimensionRow {
  id: number;
  name: string;
  tagCount: number;
  usedCount: number;
}

interface TagRow {
  id: number;
  name: string;
  subdimensionId: number;
  subdimensionName: string;
  usedCount: number;
}

interface CompanyRow {
  id: number;
  name: string;
  code: string;
  tagCount: number;
  tags: string[];
  lastUsed?: string;
}

interface CompanyListState {
  list: CompanyRow[];
  total: number;
  page: number;
  pageSize: number;
}

interface DetailHighlights {
  topSubdimension?: SubdimensionRow | null;
  topTags?: TagRow[];
  industry?: {
    chain?: SubdimensionRow | null;
    category?: SubdimensionRow | null;
  } | null;
}

const DimensionDetail: React.FC = () => {
  const { dimensionId } = useParams<{ dimensionId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dimension, setDimension] = useState<DimensionInfo | null>(null);
  const [subdimensions, setSubdimensions] = useState<SubdimensionRow[]>([]);
  const [tags, setTags] = useState<TagRow[]>([]);
  const [companies, setCompanies] = useState<CompanyListState>({ list: [], total: 0, page: 1, pageSize: 10 });
  const [highlights, setHighlights] = useState<DetailHighlights>({});
  const [tagSearchText, setTagSearchText] = useState("");
  const [companyKeyword, setCompanyKeyword] = useState("");
  const [selectedSubdimensionId, setSelectedSubdimensionId] = useState<number | undefined>(undefined);
  const [selectedTagId, setSelectedTagId] = useState<number | undefined>(undefined);
  const [companyPage, setCompanyPage] = useState(1);
  const [companyPageSize, setCompanyPageSize] = useState(10);

  useEffect(() => {
    const fetchDetail = async () => {
      if (!dimensionId) return;
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (selectedSubdimensionId) params.set("subdimensionId", String(selectedSubdimensionId));
        if (selectedTagId) params.set("tagId", String(selectedTagId));
        if (companyKeyword.trim()) params.set("keyword", companyKeyword.trim());
        params.set("companyPage", String(companyPage));
        params.set("companyPageSize", String(companyPageSize));
        const response = await fetch(`/api/tags/dimensions/${dimensionId}/detail?${params.toString()}`);
        const result = await response.json();
        if (!result.success) {
          message.error(result.message || "加载维度详情失败");
          setDimension(null);
          return;
        }
        setDimension(result.data.dimension);
        setSubdimensions(result.data.subdimensions || []);
        setTags(result.data.tags || []);
        setHighlights(result.data.highlights || {});
        setCompanies(result.data.companies || { list: [], total: 0, page: 1, pageSize: companyPageSize });
      } catch (error) {
        console.error(error);
        message.error("加载维度详情失败");
        setDimension(null);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [companyKeyword, companyPage, companyPageSize, dimensionId, selectedSubdimensionId, selectedTagId]);

  useEffect(() => {
    setCompanyPage(1);
  }, [companyKeyword, selectedSubdimensionId, selectedTagId]);

  const filteredTags = useMemo(() => {
    const keyword = tagSearchText.trim().toLowerCase();
    return tags.filter((item) => {
      if (selectedSubdimensionId && item.subdimensionId !== selectedSubdimensionId) {
        return false;
      }
      if (!keyword) return true;
      return item.name.toLowerCase().includes(keyword) || item.subdimensionName.toLowerCase().includes(keyword);
    });
  }, [selectedSubdimensionId, tagSearchText, tags]);

  const tagOptions = useMemo(
    () =>
      tags
        .filter((item) => !selectedSubdimensionId || item.subdimensionId === selectedSubdimensionId)
        .map((item) => ({ label: `${item.name} · ${item.usedCount} 家`, value: item.id })),
    [selectedSubdimensionId, tags],
  );

  const handleSubdimensionToggle = (value?: number) => {
    setSelectedSubdimensionId((current) => (current === value ? undefined : value));
    setSelectedTagId(undefined);
  };

  const resetFilters = () => {
    setSelectedSubdimensionId(undefined);
    setSelectedTagId(undefined);
    setCompanyKeyword("");
    setTagSearchText("");
  };

  const tagColumns: TableProps<TagRow>["columns"] = [
    {
      title: "标签名称",
      dataIndex: "name",
      key: "name",
      render: (value: string, record) => (
        <Button type="link" style={{ padding: 0, height: "auto" }} onClick={() => setSelectedTagId(record.id)}>
          <Text strong>{value}</Text>
        </Button>
      ),
    },
    {
      title: "所属子维度",
      dataIndex: "subdimensionName",
      key: "subdimensionName",
      render: (value: string, record) => (
        <Tag
          color={selectedSubdimensionId === record.subdimensionId ? "processing" : "default"}
          style={{ cursor: "pointer" }}
          onClick={() => handleSubdimensionToggle(record.subdimensionId)}
        >
          {value}
        </Tag>
      ),
    },
    {
      title: "覆盖企业",
      dataIndex: "usedCount",
      key: "usedCount",
      width: 120,
      render: (value: number) => <Tag color="blue">{value} 家</Tag>,
    },
  ];

  const companyColumns: TableProps<CompanyRow>["columns"] = [
    {
      title: "企业名称",
      dataIndex: "name",
      key: "name",
      render: (value: string, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{value}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.code}
          </Text>
        </Space>
      ),
    },
    {
      title: "标签数",
      dataIndex: "tagCount",
      key: "tagCount",
      width: 100,
      render: (value: number) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      render: (value: string[]) => (
        <Space size={[0, 6]} wrap>
          {value.map((tagName) => (
            <Tag
              key={tagName}
              color={selectedTagId && tags.find((item) => item.id === selectedTagId)?.name === tagName ? "processing" : "default"}
            >
              {tagName}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: "最近打标",
      dataIndex: "lastUsed",
      key: "lastUsed",
      width: 180,
      render: (value?: string) => (value ? new Date(value).toLocaleString() : "-"),
    },
  ];

  if (loading) {
    return (
      <div style={{ minHeight: 400, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Spin size="large" tip="加载维度详情中..." />
      </div>
    );
  }

  if (!dimension) {
    return (
      <Empty description="未找到该维度的详细信息" style={{ marginTop: 100 }}>
        <Button type="primary" onClick={() => navigate("/system-mgmt/tag-library")}>
          返回标签体系库
        </Button>
      </Empty>
    );
  }

  const activeTag = selectedTagId ? tags.find((item) => item.id === selectedTagId) || null : null;

  return (
    <div style={{ minHeight: "100%", paddingBottom: 24 }}>
      <Card bordered={false} style={{ marginBottom: 24 }} bodyStyle={{ padding: "16px 24px" }}>
        <Breadcrumb
          items={[
            { title: "系统管理" },
            { title: "数据管理" },
            {
              title: <a onClick={() => navigate("/system-mgmt/tag-library")}>标签体系库</a>,
            },
            { title: dimension.name },
          ]}
          style={{ marginBottom: 16 }}
        />

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
          <div style={{ display: "flex", gap: 16 }}>
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 12,
                background: dimension.color,
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 28,
                fontWeight: 700,
              }}
            >
              <TagsOutlined />
            </div>
            <div>
              <Title level={3} style={{ margin: 0 }}>
                {dimension.name}
              </Title>
              <Text type="secondary">{dimension.description}</Text>
              <div style={{ marginTop: 8 }}>
                <Tag color={dimension.color}>{dimension.key}</Tag>
                <Tag>{subdimensions.length} 个子维度</Tag>
              </div>
            </div>
          </div>

          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            返回
          </Button>
        </div>
      </Card>

      <Row gutter={24} style={{ marginBottom: 24 }}>
        <Col xs={24} md={8}>
          <Card bordered={false}>
            <Statistic title="标签总数" value={dimension.tagCount} prefix={<TagsOutlined style={{ color: dimension.color }} />} suffix="个" />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card bordered={false}>
            <Statistic title="覆盖企业" value={dimension.usedCount} prefix={<BankOutlined style={{ color: "#52c41a" }} />} suffix="家" />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card bordered={false}>
            <Statistic title="覆盖率" value={dimension.coverage} suffix="%" />
            <Progress percent={dimension.coverage} strokeColor={dimension.color} showInfo={false} style={{ marginTop: 12 }} />
          </Card>
        </Col>
      </Row>

      {dimension.key === "industry" && (
        <Row gutter={24} style={{ marginBottom: 24 }}>
          <Col xs={24} md={8}>
            <Card bordered={false}>
              <Statistic
                title="产业链标签"
                value={highlights.industry?.chain?.tagCount || 0}
                suffix={`个 / ${highlights.industry?.chain?.usedCount || 0} 家`}
              />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card bordered={false}>
              <Statistic
                title="行业分类标签"
                value={highlights.industry?.category?.tagCount || 0}
                suffix={`个 / ${highlights.industry?.category?.usedCount || 0} 家`}
              />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card bordered={false}>
              <Statistic
                title="重点子维度"
                value={highlights.topSubdimension?.name || "-"}
                valueStyle={{ fontSize: 20 }}
                suffix={highlights.topSubdimension ? `${highlights.topSubdimension.usedCount} 家` : ""}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Row gutter={24} style={{ marginBottom: 24 }}>
        <Col xs={24} xl={8}>
          <Card title="子维度概览" bordered={false}>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              {subdimensions.map((item) => (
                <div
                  key={item.id}
                  style={{
                    padding: "12px 14px",
                    border: selectedSubdimensionId === item.id ? `1px solid ${dimension.color}` : "1px solid #f0f0f0",
                    borderRadius: 8,
                    cursor: "pointer",
                    background: selectedSubdimensionId === item.id ? "rgba(24, 144, 255, 0.04)" : "#fff",
                  }}
                  onClick={() => handleSubdimensionToggle(item.id)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                    <Text strong>{item.name}</Text>
                    <Tag color="blue">{item.tagCount} 个标签</Tag>
                  </div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    已覆盖 {item.usedCount} 家企业
                  </Text>
                </div>
              ))}
            </Space>
          </Card>
        </Col>

        <Col xs={24} xl={16}>
          <Card
            title="标签列表"
            bordered={false}
            extra={(
              <Space wrap>
                <Select
                  allowClear
                  placeholder="筛选子维度"
                  style={{ width: 180 }}
                  value={selectedSubdimensionId}
                  options={subdimensions.map((item) => ({ label: item.name, value: item.id }))}
                  onChange={(value) => handleSubdimensionToggle(value)}
                />
                <Input
                  allowClear
                  placeholder="搜索标签或子维度"
                  prefix={<SearchOutlined />}
                  style={{ width: 220 }}
                  value={tagSearchText}
                  onChange={(event) => setTagSearchText(event.target.value)}
                />
              </Space>
            )}
          >
            <Table rowKey="id" columns={tagColumns} dataSource={filteredTags} pagination={{ pageSize: 10 }} />
          </Card>
        </Col>
      </Row>

      <Card
        title="重点标签与企业筛选"
        bordered={false}
        style={{ marginBottom: 24 }}
        extra={activeTag ? <Tag color="processing">当前标签: {activeTag.name}</Tag> : null}
      >
        {highlights.topTags && highlights.topTags.length > 0 ? (
          <Space size={[8, 8]} wrap>
            {highlights.topTags.map((item) => (
              <Tag
                key={item.id}
                color={selectedTagId === item.id ? "processing" : "default"}
                style={{ cursor: "pointer", padding: "4px 10px" }}
                onClick={() => setSelectedTagId((current) => (current === item.id ? undefined : item.id))}
              >
                {item.name} · {item.usedCount} 家
              </Tag>
            ))}
          </Space>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无重点标签" />
        )}
      </Card>

      <Card
        title="已打标企业示例"
        bordered={false}
        extra={(
          <Space wrap>
            <Select
              allowClear
              placeholder="企业标签筛选"
              style={{ width: 240 }}
              value={selectedTagId}
              options={tagOptions}
              onChange={(value) => setSelectedTagId(value)}
              showSearch
              optionFilterProp="label"
            />
            <Input
              allowClear
              placeholder="搜索企业名称或信用代码"
              prefix={<SearchOutlined />}
              style={{ width: 240 }}
              value={companyKeyword}
              onChange={(event) => setCompanyKeyword(event.target.value)}
            />
            <Button onClick={resetFilters}>重置筛选</Button>
          </Space>
        )}
      >
        <Table
          rowKey="id"
          columns={companyColumns}
          dataSource={companies.list}
          pagination={{
            current: companies.page,
            pageSize: companies.pageSize,
            total: companies.total,
            showSizeChanger: true,
          }}
          onChange={(pagination) => {
            setCompanyPage(pagination.current || 1);
            setCompanyPageSize(pagination.pageSize || 10);
          }}
        />
      </Card>
    </div>
  );
};

export default DimensionDetail;
