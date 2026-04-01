import React, { useState, useEffect, useMemo } from "react";
import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";
import axios from "axios";
import {
  Layout,
  Card,
  Input,
  Row,
  Col,
  Typography,
  Space,
  Button,
  Select,
  Statistic,
  message,
  Tag,
  Divider,
  Collapse,
  Spin
} from "antd";
import {
  SearchOutlined,
  ReloadOutlined,
  DeploymentUnitOutlined,
  MedicineBoxOutlined,
  ExperimentOutlined,
  UsergroupAddOutlined,
  AppstoreOutlined
} from "@ant-design/icons";

const { Content } = Layout;
const { Title, Text } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

// 定义四大行业的基础颜色（用于统计卡片）
const INDUSTRY_COLORS = {
  "数字医疗": "#B3D9FF",
  "药物": "#D9C2E0",
  "医疗器械": "#B3E6B3",
  "医疗服务": "#FFE0B3"
};

// 配置常量
const SCORE_RANGES = {
  high: [85, 100],
  mid: [70, 85],
  low: [0, 70],
  all: [0, 100]
} as const;

const INDUSTRIES = ["数字医疗", "药物", "医疗器械", "医疗服务"] as const;

// 计算特定行业平均分的函数
const calculateIndustryAverage = (data: any[], industryName: string) => {
  const industry = data.find(item => item.name === industryName);
  if (industry && industry.value !== undefined) {
    return industry.value.toFixed(1);
  }
  return "N/A";
};

// 递归查找包含指定标签的节点
const findNodesWithTag = (nodes: any[], tag: string) => {
  const result: any[] = [];

  const traverse = (currentNodes: any[]) => {
    currentNodes.forEach(node => {
      if (node.name === tag) {
        result.push({ ...node });
      } else if (node.children && node.children.length > 0) {
        const filteredChildren = findNodesWithTag(node.children, tag);
        if (filteredChildren.length > 0) {
          result.push({
            ...node,
            children: filteredChildren
          });
        }
      }
    });
  };

  traverse(nodes);
  return result;
};

// 递归过滤数据
const filterData = (
  rawData: any[],
  text: string,
  range: [number, number],
  industry: string,
  tags: string[]
) => {
  let filteredNodes = rawData;

  // 行业筛选
  if (industry !== "all") {
    filteredNodes = rawData.filter(item => item.name === industry);
  }

  // 标签筛选
  if (tags.length > 0) {
    const filteredByTags: any[] = [];
    tags.forEach(tag => {
      const nodesWithTag = findNodesWithTag(filteredNodes, tag);
      filteredByTags.push(...nodesWithTag);
    });
    filteredNodes = filteredByTags;
  }

  // 搜索文本筛选
  if (text) {
    const filterByText = (nodes: any[]) => {
      return nodes
        .map(node => {
          const matchName = node.name.toLowerCase().includes(text.toLowerCase());

          if (!node.children || node.children.length === 0) {
            const matchScore = node.value >= range[0] && node.value <= range[1];
            return matchName && matchScore ? node : null;
          } else {
            const filteredChildren = filterByText(node.children);
            if (filteredChildren.length > 0) {
              return { ...node, children: filteredChildren };
            }
            return null;
          }
        })
        .filter(n => n !== null);
    };

    filteredNodes = filterByText(filteredNodes);
  }

  // 分数范围筛选（注意：此逻辑应在搜索后执行，但为简化保留）
  if (range[0] !== 0 || range[1] !== 100) {
    const filterByScore = (nodes: any[]) => {
      return nodes
        .map(node => {
          const matchScore = node.value >= range[0] && node.value <= range[1];

          if (!node.children || node.children.length === 0) {
            return matchScore ? node : null;
          } else {
            const filteredChildren = filterByScore(node.children);
            if (filteredChildren.length > 0) {
              return { ...node, children: filteredChildren };
            }
            return null;
          }
        })
        .filter(n => n !== null);
    };

    filteredNodes = filterByScore(filteredNodes);
  }

  return filteredNodes;
};

// 按层级组织标签
const organizeTagsByLevel = (rawData: any[]) => {
  const organized: Record<string, Record<string, any[]>> = {};

  rawData.forEach(industry => {
    organized[industry.name] = {};
    if (industry.children) {
      industry.children.forEach(level1 => {
        organized[industry.name][level1.name] = level1.children || [];
      });
    }
  });

  return organized;
};

const IndustryHeatmap: React.FC = () => {
  const [rawData, setRawData] = useState<any[]>([]);
  const [treeData, setTreeData] = useState<any[]>([]);
  const [searchText, setSearchText] = useState("");
  const [scoreRange, setScoreRange] = useState<[number, number]>(SCORE_RANGES.all);
  const [selectedIndustry, setSelectedIndustry] = useState<string>("all");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // 从后端加载真实数据
  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await axios.get("http://localhost:8000/api/scoring/industry-tree/");
      const data = response.data;

      // 确保数据是数组
      if (!Array.isArray(data)) {
        throw new Error("后端返回数据格式错误，应为数组");
      }

      setRawData(data);
      setTreeData(data);
    } catch (error: any) {
      console.error("获取产业热力图数据失败:", error);
      message.error(`加载失败: ${error.message || "请检查后端服务是否运行"}`);
      setRawData([]);
      setTreeData([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const organizedTags = useMemo(() => organizeTagsByLevel(rawData), [rawData]);

  const handleSearch = (value: string) => {
    setSearchText(value);
    const filtered = filterData(rawData, value, scoreRange, selectedIndustry, selectedTags);
    setTreeData(filtered);
  };

  const handleScoreChange = (val: string) => {
    const range = SCORE_RANGES[val as keyof typeof SCORE_RANGES] || SCORE_RANGES.all;
    setScoreRange(range);
    const filtered = filterData(rawData, searchText, range, selectedIndustry, selectedTags);
    setTreeData(filtered);
  };

  const handleIndustryChange = (value: string) => {
    setSelectedIndustry(value);
    const filtered = filterData(rawData, searchText, scoreRange, value, selectedTags);
    setTreeData(filtered);
  };

  const handleTagChange = (tag: string) => {
    let newSelectedTags;
    if (selectedTags.includes(tag)) {
      newSelectedTags = selectedTags.filter(t => t !== tag);
    } else {
      newSelectedTags = [...selectedTags, tag];
    }
    setSelectedTags(newSelectedTags);
    const filtered = filterData(rawData, searchText, scoreRange, selectedIndustry, newSelectedTags);
    setTreeData(filtered);
  };

  const refreshScores = () => {
    fetchData();
  };

  const onChartClick = (params: any) => {
    if (!params.data.children) {
      message.success(`跳转到 ${params.data.name} 行业画像`);
    }
  };

  const getOption = () => {
    return {
      tooltip: {
        formatter: function (info: any) {
          const treePathInfo = info.treePathInfo;
          const treePath = treePathInfo.slice(1).map((item: any) => item.name);

          return [
            '<div class="tooltip-title">' + echarts.format.encodeHTML(treePath.join(' / ')) + '</div>',
            '产业评分: ' + info.value + ' 分 ',
            info.data.companies ? '代表企业: ' + info.data.companies : ''
          ].join('<br/>');
        }
      },
      series: [
        {
          name: '产业评分',
          type: 'treemap',
          visibleMin: 100,
          label: {
            show: true,
            formatter: (params: any) => `${params.name}\n${params.value}分`,
            fontSize: 12,
            fontWeight: 'bold',
            color: '#fff',
            overflow: 'truncate',
            ellipsis: '...'
          },
          upperLabel: {
            show: true,
            height: 30,
            color: '#fff',
            backgroundColor: 'rgba(0,0,0,0.3)',
            formatter: (params: any) => `${params.name}  ${params.value}分`,
            fontSize: 12
          },
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 0,
            gapWidth: 0
          },
          nodeClick: 'zoomToNode',
          breadcrumb: {
            show: true,
            height: 30,
            itemStyle: {
              textStyle: { fontSize: 14, lineHeight: 14 }
            }
          },
          roam: false,
          data: treeData,
          levels: [
            {
              itemStyle: {
                borderColor: '#ffffff',
                borderWidth: 0,
                gapWidth: 1
              },
              upperLabel: { show: false }
            },
            {
              itemStyle: {
                borderColor: '#ffffff',
                borderWidth: 0,
                gapWidth: 0
              },
              emphasis: {
                itemStyle: { borderColor: '#aaa' }
              }
            },
            {
              colorSaturation: [0.35, 0.5],
              itemStyle: {
                borderWidth: 0.3,
                gapWidth: 0,
                borderColorSaturation: 0.7
              }
            }
          ],
        }
      ]
    };
  };

  const renderMetricCard = (title: string, icon: React.ReactNode, color: string) => {
    const industryName = title.replace("研发", "");
    const avgScore = calculateIndustryAverage(rawData, industryName);

    return (
      <Card
        bordered={false}
        className="metric-card"
        style={{ borderTop: `4px solid ${color}` }}
      >
        <Statistic
          title={<Space>{icon}<span>{title}</span></Space>}
          value={avgScore}
          suffix="Avg"
          valueStyle={{ fontWeight: 600 }}
        />
      </Card>
    );
  };

  return (
    <Layout style={{ minHeight: "100vh", background: "#f0f2f5" }}>
      <Content style={{ padding: "24px" }}>

        {/* 顶部控制栏与统计 */}
        <div style={{ marginBottom: 24 }}>
          <Row gutter={[16, 16]} align="middle" justify="space-between">
            <Col xs={24} md={12}>
              <Title level={3} style={{ margin: 0 }}>
                <ExperimentOutlined style={{ marginRight: 12 }} />
                产业评分全景图 (Industry Heatmap)
              </Title>
              <Text type="secondary">基于多维数据的实时产业赛道评分监控体系</Text>
            </Col>
            <Col xs={24} md={12} style={{ textAlign: 'right' }}>
              <Space>
                <Button icon={<ReloadOutlined />} onClick={refreshScores} loading={loading}>
                  刷新评分
                </Button>
              </Space>
            </Col>
          </Row>

          <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
            <Col span={6}>
              {renderMetricCard("数字医疗", <DeploymentUnitOutlined />, INDUSTRY_COLORS["数字医疗"])}
            </Col>
            <Col span={6}>
              {renderMetricCard("药物研发", <MedicineBoxOutlined />, INDUSTRY_COLORS["药物"])}
            </Col>
            <Col span={6}>
              {renderMetricCard("医疗器械", <ExperimentOutlined />, INDUSTRY_COLORS["医疗器械"])}
            </Col>
            <Col span={6}>
              {renderMetricCard("医疗服务", <UsergroupAddOutlined />, INDUSTRY_COLORS["医疗服务"])}
            </Col>
          </Row>
        </div>

        {/* 搜索与筛选 */}
        <Card bodyStyle={{ padding: "16px 24px" }} style={{ marginBottom: 16 }}>
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Input
                placeholder="搜索赛道、细分领域 (如: AI药物, 基因测序...)"
                prefix={<SearchOutlined style={{ color: "#bfbfbf" }} />}
                size="large"
                allowClear
                onChange={(e) => handleSearch(e.target.value)}
                disabled={loading}
              />
            </Col>
            <Col>
              <Select
                defaultValue="all"
                size="large"
                style={{ width: 180 }}
                onChange={handleScoreChange}
                disabled={loading}
              >
                <Option value="all">全部分值</Option>
                <Option value="high">高评分 (85-100)</Option>
                <Option value="mid">中评分 (70-85)</Option>
                <Option value="low">低评分 (0-70)</Option>
              </Select>
            </Col>
            <Col>
              <Select
                defaultValue="all"
                size="large"
                style={{ width: 180 }}
                onChange={handleIndustryChange}
                disabled={loading}
              >
                <Option value="all">全部行业</Option>
                {INDUSTRIES.map(industry => (
                  <Option key={industry} value={industry}>{industry}</Option>
                ))}
              </Select>
            </Col>
            <Col>
              <Button type="default" size="large" disabled>
                矩形面积 = 评分权重
              </Button>
            </Col>
          </Row>
        </Card>

        {/* 标签筛选区域 */}
        <Card
          bodyStyle={{ padding: "16px 24px" }}
          style={{ marginBottom: 16 }}
          title={
            <Space>
              <AppstoreOutlined />
              <span>细分赛道标签筛选</span>
              {selectedTags.length > 0 && (
                <span style={{ color: '#52c41a' }}>
                  (已选择 {selectedTags.length} 个标签)
                </span>
              )}
            </Space>
          }
        >
          {loading ? (
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <Spin tip="加载标签..." />
            </div>
          ) : (
            <>
              <Collapse accordion>
                {Object.entries(organizedTags).map(([industryName, industryData]) => (
                  <Panel
                    header={
                      <div>
                        <Tag
                          color={selectedTags.includes(industryName) ? 'blue' : 'default'}
                          onClick={() => handleTagChange(industryName)}
                          style={{ cursor: 'pointer', userSelect: 'none', fontSize: '14px', padding: '4px 8px' }}
                        >
                          <strong>{industryName}（0级）</strong>
                        </Tag>
                      </div>
                    }
                    key={industryName}
                  >
                    <div style={{ paddingLeft: '20px' }}>
                      {Object.entries(industryData).map(([level1Name, level2Items]) => (
                        <div key={level1Name} style={{ marginBottom: '10px' }}>
                          <Tag
                            color={selectedTags.includes(level1Name) ? 'blue' : 'default'}
                            onClick={() => handleTagChange(level1Name)}
                            style={{ cursor: 'pointer', userSelect: 'none', fontSize: '14px', padding: '4px 8px', marginBottom: '8px' }}
                          >
                            <strong>{level1Name}（1级）</strong>
                          </Tag>：
                          {(level2Items as any[]).map((level2Item, index) => (
                            <span key={level2Item.name}>
                              <Tag
                                color={selectedTags.includes(level2Item.name) ? 'blue' : 'default'}
                                onClick={() => handleTagChange(level2Item.name)}
                                style={{ cursor: 'pointer', userSelect: 'none', margin: '2px' }}
                              >
                                {level2Item.name}（2级）
                              </Tag>
                              {index < (level2Items as any[]).length - 1 && '、'}
                            </span>
                          ))}
                          ；
                        </div>
                      ))}
                    </div>
                  </Panel>
                ))}
              </Collapse>

              {selectedTags.length > 0 && (
                <>
                  <Divider style={{ margin: '16px 0' }} />
                  <div>
                    <Text strong>已选择的标签:</Text>
                    <Space style={{ marginLeft: 16 }}>
                      {selectedTags.map(tag => (
                        <Tag
                          key={tag}
                          color="blue"
                          closable
                          onClose={(e) => {
                            e.preventDefault();
                            handleTagChange(tag);
                          }}
                        >
                          {tag}
                        </Tag>
                      ))}
                      <Button
                        type="link"
                        size="small"
                        onClick={() => {
                          setSelectedTags([]);
                          const filtered = filterData(rawData, searchText, scoreRange, selectedIndustry, []);
                          setTreeData(filtered);
                        }}
                      >
                        清除全部
                      </Button>
                    </Space>
                  </div>
                </>
              )}
            </>
          )}
        </Card>

        {/* 核心可视化区域 */}
        <Card
          bodyStyle={{ padding: 0, height: "calc(160vh - 500px)", minHeight: "600px" }}
          title={
            <Space>
              <AppstoreOutlined />
              <span>产业赛道热力分布</span>
              {searchText && <span style={{ color: '#faad14' }}>(搜索模式)</span>}
              {selectedIndustry !== "all" && <span style={{ color: '#52c41a' }}>(行业: {selectedIndustry})</span>}
              {selectedTags.length > 0 && <span style={{ color: '#1890ff' }}>(标签筛选: {selectedTags.length}个)</span>}
            </Space>
          }
        >
          {loading ? (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Spin size="large" tip="正在加载产业评分数据..." />
            </div>
          ) : treeData && treeData.length > 0 ? (
            <ReactECharts
              option={getOption()}
              style={{ height: "100%", width: "100%" }}
              onEvents={{
                click: onChartClick
              }}
            />
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
              未找到匹配的赛道数据
            </div>
          )}
        </Card>
      </Content>

      {/* 样式覆盖 */}
      <style>{`
        .metric-card {
          transition: all 0.3s;
          box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        .metric-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .ant-statistic-title {
          margin-bottom: 8px;
        }
        .echarts-for-react div {
          font-family: 'Arial', sans-serif;
        }
        .ant-collapse-content-box {
          padding-top: 10px !important;
          padding-bottom: 10px !important;
        }
      `}</style>
    </Layout>
  );
};

export default IndustryHeatmap;