import React, { useEffect, useMemo, useState } from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Collapse,
  Col,
  Input,
  Layout,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Tag,
  Typography,
  message,
} from "antd";
import {
  AppstoreOutlined,
  DeploymentUnitOutlined,
  ExperimentOutlined,
  ReloadOutlined,
  SearchOutlined,
} from "@ant-design/icons";

const { Content } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;

interface IndustryNode {
  name: string;
  value?: number | null;
  children?: IndustryNode[];
  company_count?: number;
}

const MAX_TOTAL_SCORE = 355;
const ROOT_CARD_COLORS = ["#1677ff", "#52c41a", "#fa8c16", "#722ed1", "#13c2c2", "#eb2f96"];

const SCORE_RANGES = {
  high: [160, MAX_TOTAL_SCORE],
  mid: [89, 159.99],
  low: [0, 88.99],
  all: [0, MAX_TOTAL_SCORE],
} as const;

const findNodesWithTag = (nodes: IndustryNode[], tag: string): IndustryNode[] => {
  const result: IndustryNode[] = [];
  const traverse = (currentNodes: IndustryNode[]) => {
    currentNodes.forEach((node) => {
      if (node.name === tag) {
        result.push({ ...node });
      } else if (node.children?.length) {
        const filteredChildren = findNodesWithTag(node.children, tag);
        if (filteredChildren.length > 0) {
          result.push({ ...node, children: filteredChildren });
        }
      }
    });
  };
  traverse(nodes);
  return result;
};

const filterData = (
  rawData: IndustryNode[],
  text: string,
  range: [number, number],
  industry: string,
  tags: string[],
) => {
  let filteredNodes = rawData;

  if (industry !== "all") {
    filteredNodes = rawData.filter((item) => item.name === industry);
  }

  if (tags.length > 0) {
    const filteredByTags: IndustryNode[] = [];
    tags.forEach((tag) => {
      filteredByTags.push(...findNodesWithTag(filteredNodes, tag));
    });
    filteredNodes = filteredByTags;
  }

  if (text) {
    const filterByText = (nodes: IndustryNode[]): IndustryNode[] =>
      nodes
        .map((node) => {
          const matchName = node.name.toLowerCase().includes(text.toLowerCase());
          if (!node.children?.length) {
            const value = Number(node.value || 0);
            return matchName && value >= range[0] && value <= range[1] ? node : null;
          }
          const filteredChildren = filterByText(node.children);
          return filteredChildren.length > 0 ? { ...node, children: filteredChildren } : null;
        })
        .filter((node): node is IndustryNode => node !== null);

    filteredNodes = filterByText(filteredNodes);
  }

  if (range[0] !== 0 || range[1] !== MAX_TOTAL_SCORE) {
    const filterByScore = (nodes: IndustryNode[]): IndustryNode[] =>
      nodes
        .map((node) => {
          const value = Number(node.value || 0);
          if (!node.children?.length) {
            return value >= range[0] && value <= range[1] ? node : null;
          }
          const filteredChildren = filterByScore(node.children);
          return filteredChildren.length > 0 ? { ...node, children: filteredChildren } : null;
        })
        .filter((node): node is IndustryNode => node !== null);

    filteredNodes = filterByScore(filteredNodes);
  }

  return filteredNodes;
};

const organizeTagsByLevel = (rawData: IndustryNode[]) => {
  const organized: Record<string, Record<string, IndustryNode[]>> = {};
  rawData.forEach((industry) => {
    organized[industry.name] = {};
    industry.children?.forEach((level1) => {
      organized[industry.name][level1.name] = level1.children || [];
    });
  });
  return organized;
};

const topLevelMetrics = (rawData: IndustryNode[]) =>
  rawData
    .filter((item) => item.value !== undefined && item.value !== null)
    .map((item) => ({
      name: item.name,
      value: Number(item.value || 0),
      companyCount: Number(item.company_count || 0),
    }))
    .sort((a, b) => b.value - a.value);

const IndustryScore: React.FC = () => {
  const navigate = useNavigate();
  const [rawData, setRawData] = useState<IndustryNode[]>([]);
  const [treeData, setTreeData] = useState<IndustryNode[]>([]);
  const [searchText, setSearchText] = useState("");
  const [scoreRange, setScoreRange] = useState<[number, number]>([0, MAX_TOTAL_SCORE]);
  const [selectedIndustry, setSelectedIndustry] = useState<string>("all");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/scoring/industry-tree/");
      const data = await response.json();
      if (!Array.isArray(data)) {
        throw new Error("后端返回数据格式错误，应为数组");
      }
      setRawData(data);
      setTreeData(data);
    } catch (error: any) {
      message.error(`加载失败: ${error?.message || "请检查后端服务是否运行"}`);
      setRawData([]);
      setTreeData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const organizedTags = useMemo(() => organizeTagsByLevel(rawData), [rawData]);
  const metricCards = useMemo(() => topLevelMetrics(rawData).slice(0, 4), [rawData]);
  const availableIndustries = useMemo(() => rawData.map((item) => item.name), [rawData]);

  const handleSearch = (value: string) => {
    setSearchText(value);
    setTreeData(filterData(rawData, value, scoreRange, selectedIndustry, selectedTags));
  };

  const handleScoreChange = (value: string) => {
    const selectedRange = SCORE_RANGES[value as keyof typeof SCORE_RANGES] || SCORE_RANGES.all;
    const range: [number, number] = [selectedRange[0], selectedRange[1]];
    setScoreRange(range);
    setTreeData(filterData(rawData, searchText, range, selectedIndustry, selectedTags));
  };

  const handleIndustryChange = (value: string) => {
    setSelectedIndustry(value);
    setTreeData(filterData(rawData, searchText, scoreRange, value, selectedTags));
  };

  const handleTagChange = (tag: string) => {
    const newSelectedTags = selectedTags.includes(tag)
      ? selectedTags.filter((item) => item !== tag)
      : [...selectedTags, tag];
    setSelectedTags(newSelectedTags);
    setTreeData(filterData(rawData, searchText, scoreRange, selectedIndustry, newSelectedTags));
  };

  const getOption = () => ({
    tooltip: {
      formatter(info: any) {
        const treePath = info.treePathInfo.slice(1).map((item: any) => item.name);
        return [
          `<div class="tooltip-title">${echarts.format.encodeHTML(treePath.join(" / "))}</div>`,
          `产业评分: ${info.value ?? "-"} / ${MAX_TOTAL_SCORE} 分`,
          info.data.company_count !== undefined ? `企业数量: ${info.data.company_count}` : "",
        ]
          .filter(Boolean)
          .join("<br/>");
      },
    },
    series: [
      {
        name: "产业评分",
        type: "treemap",
        visibleMin: 100,
        label: {
          show: true,
          formatter: (params: any) => `${params.name}\n${params.value ?? "-"}分`,
          fontSize: 12,
          fontWeight: "bold",
          color: "#fff",
          overflow: "truncate",
          ellipsis: "...",
        },
        upperLabel: {
          show: true,
          height: 30,
          color: "#fff",
          backgroundColor: "rgba(0,0,0,0.3)",
          formatter: (params: any) => `${params.name}  ${params.value ?? "-"}分`,
          fontSize: 12,
        },
        itemStyle: {
          borderColor: "#fff",
          borderWidth: 0,
          gapWidth: 0,
        },
        nodeClick: "zoomToNode",
        breadcrumb: {
          show: true,
          height: 30,
          itemStyle: { textStyle: { fontSize: 14, lineHeight: 14 } },
        },
        roam: false,
        data: treeData,
        levels: [
          {
            itemStyle: { borderColor: "#ffffff", borderWidth: 0, gapWidth: 1 },
            upperLabel: { show: false },
          },
          {
            itemStyle: { borderColor: "#ffffff", borderWidth: 0, gapWidth: 0 },
            emphasis: { itemStyle: { borderColor: "#aaa" } },
          },
          {
            colorSaturation: [0.35, 0.5],
            itemStyle: { borderWidth: 0.3, gapWidth: 0, borderColorSaturation: 0.7 },
          },
        ],
      },
    ],
  });

  const renderMetricCard = (node: { name: string; value: number; companyCount: number }, index: number) => (
    <Card bordered={false} style={{ borderTop: `4px solid ${ROOT_CARD_COLORS[index % ROOT_CARD_COLORS.length]}` }}>
      <Statistic
        title={
          <Space>
            <DeploymentUnitOutlined style={{ color: ROOT_CARD_COLORS[index % ROOT_CARD_COLORS.length] }} />
            <span>{node.name}</span>
          </Space>
        }
        value={Number(node.value || 0).toFixed(1)}
        suffix="分"
        valueStyle={{ fontWeight: 600 }}
      />
      <Text type="secondary">覆盖企业 {node.companyCount} 家</Text>
    </Card>
  );

  return (
    <Layout style={{ minHeight: "100vh", background: "#f0f2f5" }}>
      <Content style={{ padding: 24 }}>
        <div style={{ marginBottom: 24 }}>
          <Row gutter={[16, 16]} align="middle" justify="space-between">
            <Col xs={24} md={12}>
              <Title level={3} style={{ margin: 0 }}>
                <ExperimentOutlined style={{ marginRight: 12 }} />
                产业评分全景图
              </Title>
              <Space size={8} wrap>
                <Text type="secondary">基于 `score_industry_path` 的当前产业赛道评分视图</Text>
                <Tag color="blue" bordered={false}>
                  最新总分口径 355 分
                </Tag>
              </Space>
            </Col>
            <Col xs={24} md={12} style={{ textAlign: "right" }}>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={() => void fetchData()} loading={loading}>
                  刷新评分
                </Button>
              </Space>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
            {metricCards.map((item, index) => (
              <Col key={item.name} span={6}>
                {renderMetricCard(item, index)}
              </Col>
            ))}
          </Row>
        </div>

        <Card bodyStyle={{ padding: "16px 24px" }} style={{ marginBottom: 16 }}>
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Input
                placeholder="搜索产业链节点、赛道或细分环节"
                prefix={<SearchOutlined style={{ color: "#bfbfbf" }} />}
                size="large"
                allowClear
                onChange={(event) => handleSearch(event.target.value)}
                disabled={loading}
              />
            </Col>
            <Col>
              <Select defaultValue="all" size="large" style={{ width: 180 }} onChange={handleScoreChange} disabled={loading}>
                <Option value="all">全部分值</Option>
                <Option value="high">高评分 (160-355)</Option>
                <Option value="mid">中评分 (89-159)</Option>
                <Option value="low">低评分 (0-88)</Option>
              </Select>
            </Col>
            <Col>
              <Select defaultValue="all" size="large" style={{ width: 180 }} onChange={handleIndustryChange} disabled={loading}>
                <Option value="all">全部行业</Option>
                {availableIndustries.map((industry) => (
                  <Option key={industry} value={industry}>
                    {industry}
                  </Option>
                ))}
              </Select>
            </Col>
          </Row>
        </Card>

        <Card
          bodyStyle={{ padding: "16px 24px" }}
          style={{ marginBottom: 16 }}
          title={
            <Space>
              <AppstoreOutlined />
              <span>细分赛道标签筛选</span>
              {selectedTags.length > 0 && <span style={{ color: "#52c41a" }}>(已选择 {selectedTags.length} 个标签)</span>}
            </Space>
          }
        >
          {loading ? (
            <div style={{ textAlign: "center", padding: 20 }}>
              <Spin tip="加载标签..." />
            </div>
          ) : (
            <>
              <Collapse
                accordion
                items={Object.entries(organizedTags).map(([industryName, industryData]) => ({
                  key: industryName,
                  label: (
                    <div>
                      <Tag
                        color={selectedTags.includes(industryName) ? "blue" : "default"}
                        onClick={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          handleTagChange(industryName);
                        }}
                        style={{ cursor: "pointer", userSelect: "none", fontSize: 14, padding: "4px 8px" }}
                      >
                        <strong>{industryName}（0级）</strong>
                      </Tag>
                    </div>
                  ),
                  children: (
                    <div style={{ paddingLeft: 20 }}>
                      {Object.entries(industryData).map(([level1Name, level2Items]) => (
                        <div key={level1Name} style={{ marginBottom: 10 }}>
                          <Tag
                            color={selectedTags.includes(level1Name) ? "blue" : "default"}
                            onClick={() => handleTagChange(level1Name)}
                            style={{ cursor: "pointer", userSelect: "none", fontSize: 14, padding: "4px 8px", marginBottom: 8 }}
                          >
                            <strong>{level1Name}（1级）</strong>
                          </Tag>
                          ：
                          {level2Items.map((level2Item, index) => (
                            <span key={level2Item.name}>
                              <Tag
                                color={selectedTags.includes(level2Item.name) ? "blue" : "default"}
                                onClick={() => handleTagChange(level2Item.name)}
                                style={{ cursor: "pointer", userSelect: "none", margin: "2px" }}
                              >
                                {level2Item.name}（2级）
                              </Tag>
                              {index < level2Items.length - 1 && "、"}
                            </span>
                          ))}
                          ；
                        </div>
                      ))}
                    </div>
                  ),
                }))}
              />

              {selectedTags.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Text type="secondary">已选标签：</Text>
                  <Space wrap>
                    {selectedTags.map((tag) => (
                      <Tag key={tag} closable onClose={() => handleTagChange(tag)} color="blue">
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                </div>
              )}
            </>
          )}
        </Card>

        <Card bordered={false}>
          <ReactECharts
            style={{ height: "70vh" }}
            option={getOption()}
            notMerge
            lazyUpdate
            onEvents={{
              click: (params: any) => {
                if (!params.data.children) {
                  navigate(`/industry-portrait/industry-profile?industryName=${encodeURIComponent(params.data.name)}`);
                }
              },
            }}
          />
        </Card>
      </Content>
    </Layout>
  );
};

export default IndustryScore;
