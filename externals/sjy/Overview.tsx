import React, { useState, useEffect, useRef } from "react";
import {
  Row,
  Col,
  List,
  Tag,
  Typography,
  Collapse,
  FloatButton,
  Badge,
  Tooltip,
  Button,
  Spin,
  message,
  Carousel,
  Input,
  Tabs,
  Space,
  Divider,
  Modal,
  Table,
  Progress,
  Rate,
  ConfigProvider,
} from "antd";
import {
  SafetyCertificateOutlined,
  RocketOutlined,
  TrophyOutlined,
  CrownOutlined,
  ShopOutlined,
  RobotOutlined,
  LinkOutlined,
  EnvironmentOutlined,
  ThunderboltFilled,
  SoundOutlined,
  AimOutlined,
  FireOutlined,
  GlobalOutlined,
  BankOutlined,
  ClusterOutlined,
  RiseOutlined,
  BulbOutlined,
  ArrowRightOutlined,
  ExperimentOutlined,
  SearchOutlined,
  CopyrightOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";

// 引入自定义组件
import MoreButton from "../../components/Home/MoreButton";
import RankList, { type RankItem } from "../../components/Home/RankList";
import SuggestionList, { type SuggestionItem } from "../../components/Home/SuggestionList";
import StatsGrid, { type StatItem } from "../../components/Home/StatsGrid";

const { Title, Text } = Typography;
const { Panel } = Collapse;

// ================== 数据定义接口 ==================
interface WeakLinkDetail {
  id: string;
  name: string;
  layer: string;
  urgency: number;
  count: number;
}

// ================== 静态兜底数据 ==================
const chaoyangStatsRaw = [
  { label: "上市企业", value: 0, icon: <GlobalOutlined />, color: "#cf1322" },
  { label: "外资企业", value: 0, icon: <GlobalOutlined />, color: "#d48806" },
  { label: "独角兽", value: 0, icon: <CrownOutlined />, color: "#eb2f96" },
  { label: "专精特新", value: 0, icon: <TrophyOutlined />, color: "#722ed1" },
  { label: "高新技术", value: 0, icon: <RocketOutlined />, color: "#1890ff" },
  { label: "科技中小", value: 0, icon: <ShopOutlined />, color: "#52c41a" },
];

const notices = [
  { id: 1, title: "关于2026年第一季度高新技术企业申报的预通知", type: "通知", date: "2026-01-29" },
  { id: 2, title: "朝阳区新增3家国家级专精特新“小巨人”企业名单公示", type: "动态", date: "2026-01-28" },
  { id: 3, title: "产业链平台将于本周日凌晨 02:00 进行系统维护升级", type: "系统", date: "2026-01-27" },
  { id: 4, title: "2025年度全区数字经济产业发展报告已发布", type: "报告", date: "2025-12-25" },
];

const hotSearches = {
  industries: ["AI+特定领域研发", "互联网医疗", "装备制造", "智慧医疗"],
  enterprises: ["京东方", "阿里云", "美团", "泡泡玛特"],
};

const ecologyCategoriesRaw = [
  { name: "科研院校", icon: <BankOutlined />, count: 42 },
  { name: "行业协会", icon: <ClusterOutlined />, count: 15 },
  { name: "投资基金", icon: <RiseOutlined />, count: 88 },
  { name: "孵化器", icon: <BulbOutlined />, count: 26 },
  { name: "专业园区", icon: <EnvironmentOutlined />, count: 18 },
  { name: "概念验证", icon: <ExperimentOutlined />, count: 9 },
];

// 【仅改动此处】：更新为全量 29 个产业细分标签
const fallbackChainData = [
  {
    title: "上游 · 研发与原料",
    type: "upstream",
    total: 0,
    subTags: [
      { name: "AI CRO/技术服务商", count: 0 }, { name: "AI 药物研发平台", count: 0 },
      { name: "AI软件/工具平台", count: 0 }, { name: "前沿技术融合", count: 0 }, { name: "装备制造", count: 0 },
    ],
  },
  {
    title: "中游 · 生产与制造",
    type: "midstream",
    total: 0,
    subTags: [
      { name: "AI自研管线企业", count: 0 }, { name: "中药", count: 0 }, { name: "低值医用耗材", count: 0 },
      { name: "体外诊断(IVD)", count: 0 }, { name: "化学制药", count: 0 }, { name: "治疗设备", count: 0 },
      { name: "植入器械/材料", count: 0 }, { name: "智慧医疗", count: 0 }, { name: "影像设备", count: 0 },
      { name: "康复设备", count: 0 }, { name: "生命信息支持设备", count: 0 }, { name: "生物制品", count: 0 },
      { name: "辅助设备", count: 0 }, { name: "高值医用耗材", count: 0 },
    ],
  },
  {
    title: "下游 · 应用与服务",
    type: "downstream",
    total: 0,
    subTags: [
      { name: "严肃医疗", count: 0 }, { name: "互联网+健康", count: 0 }, { name: "互联网医疗", count: 0 },
      { name: "保险支付", count: 0 }, { name: "医疗零售", count: 0 }, { name: "医药商业/流通", count: 0 },
      { name: "家用医疗设备", count: 0 }, { name: "数字疗法", count: 0 }, { name: "消费医疗", count: 0 }, { name: "第三方中心", count: 0 },
    ],
  },
];

const Overview: React.FC = () => {
  const navigate = useNavigate();
  const carouselRef = useRef<any>(null);

  const [loading, setLoading] = useState(true);
  const [chainData, setChainData] = useState<any[]>(fallbackChainData);
  const [weakLinksFull, setWeakLinksFull] = useState<SuggestionItem[]>([]);
  const [recommendEnterprisesFull, setRecommendEnterprisesFull] = useState<SuggestionItem[]>([]);
  const [weakLinksDetail, setWeakLinksDetail] = useState<WeakLinkDetail[]>([]);
  const [searchScope, setSearchScope] = useState("industry");
  const [activeNoticeIndex, setActiveNoticeIndex] = useState(0);
  const [isWeakLinksModalVisible, setIsWeakLinksModalVisible] = useState(false);
  const [isRecModalVisible, setIsRecModalVisible] = useState(false);

  // ================== 后端动态状态 ==================
  const [totalEnterprises, setTotalEnterprises] = useState(0); 
  const [dynamicStatsRaw, setDynamicStatsRaw] = useState(chaoyangStatsRaw);
  const [dynamicHotTags, setDynamicHotTags] = useState<RankItem[]>([]);
  const [dynamicHotRegions, setDynamicHotRegions] = useState<RankItem[]>([]);

  const keyMetrics = [
    { label: "收录总数", value: totalEnterprises, suffix: "家", color: "#1890ff" },
    { label: "综合评分", value: 85.2, suffix: "分", color: "#52c41a" },
    { label: "协同效率", value: 78.5, suffix: "%", color: "#fa8c16" },
  ];

  const chaoyangStatsData: StatItem[] = dynamicStatsRaw.map((item) => ({
    icon: item.icon,
    value: item.value,
    label: item.label,
    color: item.color,
    onClick: () => navigate(`/industry-class?qualification=${encodeURIComponent(item.label)}`),
  }));

  const ecologyStatsData: StatItem[] = ecologyCategoriesRaw.map((item) => ({
    icon: item.icon,
    value: item.count,
    label: item.name,
    color: "#1890ff",
    onClick: () => navigate(`/industry-class?ecology=${encodeURIComponent(item.name)}`),
  }));

  useEffect(() => {
    // 🌟 核心：统一向 Django 获取动态真实数据
    const fetchDjangoStats = async () => {
      setLoading(true);
      try {
        const response = await fetch("http://127.0.0.1:8000/api/companies/dashboard/stats/");
        const json = await response.json();
        
        if (json.code === 200) {
          const d = json.data;
          
          setTotalEnterprises(d.total || 0);
          
          // 如果后端成功传来了带有 29 个子标签的全景图谱数据，直接覆盖页面
          if (d.chainData) {
            setChainData(d.chainData);
          }
          
          if (d.qualifications) {
            setDynamicStatsRaw([
              { label: "上市企业", value: d.qualifications.listed || 0, icon: <GlobalOutlined />, color: "#cf1322" },
              { label: "外资企业", value: d.qualifications.foreign || 0, icon: <GlobalOutlined />, color: "#d48806" },
              { label: "独角兽", value: d.qualifications.unicorn || 0, icon: <CrownOutlined />, color: "#eb2f96" },
              { label: "专精特新", value: d.qualifications.srdi || 0, icon: <TrophyOutlined />, color: "#722ed1" },
              { label: "高新技术", value: d.qualifications.high_tech || 0, icon: <RocketOutlined />, color: "#1890ff" },
              { label: "科技中小", value: d.qualifications.tech_sme || 0, icon: <ShopOutlined />, color: "#52c41a" },
            ]);
          }

          if (d.hot_industries) setDynamicHotTags(d.hot_industries);
          if (d.hot_regions) setDynamicHotRegions(d.hot_regions);
        }
      } catch (error) {
        console.error("数据加载失败，将使用兜底静态数据展示", error);
        message.warning("已切换至离线演示数据");
      } finally {
        setLoading(false);
      }
    };

    fetchDjangoStats();

    setWeakLinksFull([
      { name: "AI+特定领域研发", highlight: true }, 
      { name: "AICRO/技术服务商", highlight: true },
      { name: "AI 药物研发平台", highlight: true },
      { name: "AI软件/工具平台", highlight: true }
    ]);

    setRecommendEnterprisesFull([
      { name: "北京神州生物原料有限公司", desc: "匹配度 98%" }, 
      { name: "中关村工业软件研发院", desc: "匹配度 95%" },
      { name: "京北医药冷链物流集团", desc: "匹配度 92%" },
      { name: "智谱AI科技有限公司", desc: "匹配度 88%" }
    ]);

    setWeakLinksDetail([
      { id: "1", name: "AI+特定领域研发", layer: "上游 · 研发", urgency: 5, count: 145 },
      { id: "2", name: "AICRO/技术服务商", layer: "上游 · 研发", urgency: 5, count: 32 },
      { id: "3", name: "AI 药物研发平台", layer: "上游 · 研发", urgency: 4, count: 28 },
      { id: "4", name: "AI软件/工具平台", layer: "上游 · 研发", urgency: 4, count: 45 },
    ]);
  }, []);

  const styles = {
    fullWidthContainer: { width: "100vw", position: "relative" as const, left: "50%", right: "50%", marginLeft: "-50vw", marginRight: "-50vw" },
    bannerSection: { background: "linear-gradient(135deg, #001529 0%, #003a8c 100%)", padding: "32px 0", position: "relative" as const, overflow: "hidden" },
    noticeBarSection: { background: "rgba(255, 251, 230, 0.8)", backdropFilter: "blur(4px)", borderBottom: "1px solid #ffe58f", height: 32 },
    contentInner: { maxWidth: 1400, margin: "0 auto", padding: "0 40px" },
    glassCard: { background: "#fff", borderRadius: "12px", border: "1px solid #f0f0f0", boxShadow: "0 4px 20px rgba(0,0,0,0.05)", padding: "16px", marginBottom: "16px" },
    metricBox: { textAlign: "center" as const, padding: "28px 16px", background: "#f8faff", borderRadius: "8px", border: "1px solid #eef2f8", transition: "all 0.3s" },
    panelHeader: { fontSize: 16, fontWeight: 700, color: "#1a1a1a", marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center" },
    industryTag: { cursor: "pointer", borderRadius: "8px", padding: "10px 12px", background: "#fff", border: "1px solid #f0f0f0", transition: "all 0.3s", display: "flex", flexDirection: "column" as const, justifyContent: "center", height: 64 },
    mapHeader: { padding: "8px 0", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
    collapsePanel: { padding: "0 !important" },
    listGutter: { gutter: 12, column: 4 },
    footer: { background: "#001529", padding: "48px 0 24px 0", color: "rgba(255,255,255,0.65)", marginTop: 32, width: "100vw" },
  };

  const handleSearch = (value: string) => {
    message.info(`正在搜索：${value}`);
    navigate(`/industry-class?q=${value}`);
  };

  const weakLinkColumns: ColumnsType<WeakLinkDetail> = [
    { title: "行业环节名称", dataIndex: "name", key: "name", render: (text) => <Text strong>{text}</Text> },
    { title: "所属层级", dataIndex: "layer", key: "layer", render: (text) => <Tag color="blue">{text}</Tag> },
    { title: "紧缺指数", dataIndex: "urgency", key: "urgency", render: (value) => <Rate disabled defaultValue={value} style={{ fontSize: 12, color: "#fa8c16" }} /> },
    { title: "现有企业", dataIndex: "count", key: "count", render: (val) => `${val} 家` },
  ];

  return (
    <ConfigProvider theme={{ token: { borderRadius: 8 } }}>
      <style>{`
        .industry-card-hover:hover { transform: translateY(-3px); border-color: #1890ff !important; boxShadow: 0 6px 16px rgba(24,144,255,0.08) !important; }
        .metric-hover:hover { background: #fff !important; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transform: translateY(-2px); }
        .ant-collapse-header { padding: 8px 0 !important; }
        .ant-collapse-content-box { padding: 12px 0 0 0 !important; }
        .home-search-tabs .ant-tabs-nav { margin-bottom: 12px; }
        .home-search-tabs .ant-tabs-ink-bar { height: 3px !important; border-radius: 2px; }
        .home-search-tabs .ant-tabs-tab { padding: 4px 0; }
        .home-search-input-btn { width: 120px; height: 48px; borderRadius: 8px; fontSize: 16px; fontWeight: 600; }
        .map-space-items > .ant-space-item { display: flex; align-items: center; }
        .ant-progress-small.ant-progress-line { font-size: 12px; }
        
        .suggestion-list-wrapper .ant-list-item { padding: 4px 0 !important; min-height: 40px !important; height: 40px !important; display: flex !important; align-items: center !important; overflow: hidden !important; margin: 0 !important; }
        .suggestion-list-wrapper > div > div > div { padding-top: 4px !important; padding-bottom: 4px !important; }
      `}</style>

      {/* 1. 顶部 Banner */}
      <div style={{ ...styles.fullWidthContainer, ...styles.bannerSection }}>
        <div style={styles.contentInner}>
          <div style={{ textAlign: "center" }}>
            <Title level={1} style={{ color: "#fff", marginBottom: 24, fontWeight: 700, fontSize: "36px", letterSpacing: "3px" }}>产业链洞察专家</Title>
            <div style={{ maxWidth: 840, margin: "0 auto" }}>
              <Tabs
                activeKey={searchScope}
                onChange={setSearchScope}
                className="home-search-tabs"
                items={["查行业", "查企业", "查负责人", "查风险", "查资质"].map((label, i) => ({
                  key: ["industry", "company", "person", "risk", "qualification"][i],
                  label: <span style={{ color: searchScope === ["industry", "company", "person", "risk", "qualification"][i] ? "#fff" : "rgba(255,255,255,0.6)", fontSize: 16, padding: "0 8px" }}>{label}</span>
                }))}
              />
              <div style={{ display: "flex", background: "#fff", borderRadius: 10, padding: 4, boxShadow: "0 8px 24px rgba(0,0,0,0.15)" }}>
                <Input size="large" variant="borderless" placeholder={`请输入${searchScope === "industry" ? "行业" : "企业"}名称、关键词...`} style={{ flex: 1, fontSize: 16, paddingLeft: 16, height: 48 }} suffix={<Button type="link" size="small" onClick={() => navigate("/advanced-search")}>高级搜索</Button>} onPressEnter={(e) => handleSearch(e.currentTarget.value)} />
                <Button type="primary" size="large" className="home-search-input-btn" icon={<SearchOutlined />} onClick={() => handleSearch("")}>搜索</Button>
              </div>
              <div style={{ marginTop: 16, color: "rgba(255,255,255,0.7)", fontSize: 13 }}>
                <FireOutlined style={{ marginRight: 6, color: "#ffec3d" }} />
                热搜：{hotSearches.industries.map(item => <Tag key={item} size="small" color="rgba(255,255,255,0.12)" style={{ border: "none", cursor: "pointer", color: "#fff", marginRight: 6 }}>{item}</Tag>)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 1.5 公告条 */}
      <div style={{ ...styles.fullWidthContainer, ...styles.noticeBarSection }}>
        <div style={{ ...styles.contentInner, height: "100%", display: "flex", alignItems: "center" }}>
          <SoundOutlined style={{ color: "#fa8c16", marginRight: 12, fontSize: 13 }} />
          <Carousel ref={carouselRef} autoplay dots={false} style={{ flex: 1, height: 32, lineHeight: "32px" }}>
            {notices.map(n => (
              <div key={n.id} onClick={() => document.getElementById("notice-section")?.scrollIntoView({ behavior: "smooth" })} style={{ cursor: "pointer", fontSize: 13 }}>
                <Badge status="processing" color="orange" text={<Text strong style={{ marginRight: 10, fontSize: 13 }}>[{n.type}]</Text>} />
                <Text style={{ fontSize: 13 }}>{n.title}</Text>
                <Text type="secondary" style={{ marginLeft: 16, fontSize: 11 }}>{n.date}</Text>
              </div>
            ))}
          </Carousel>
          <Button type="link" size="small" icon={<ArrowRightOutlined />} style={{ fontSize: 13 }} onClick={() => document.getElementById("notice-section")?.scrollIntoView()}>更多</Button>
        </div>
      </div>

      {/* 2. 主体内容 */}
      <Spin spinning={loading} size="large">
        <div style={{ ...styles.contentInner, marginTop: 24 }}>
          <Row gutter={24} style={{ display: "flex", alignItems: "stretch" }}>
            <Col xs={24} lg={17} style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ ...styles.glassCard, flex: 1, display: "flex", flexDirection: "column", marginBottom: 0 }}>
                <div style={styles.mapHeader}>
                  <Space className="map-space-items" size={8}><EnvironmentOutlined style={{ color: "#1890ff", fontSize: 17 }} /> <Text style={{ fontSize: 16, fontWeight: 700 }}>全景产业链图谱</Text> <Tag color="blue" bordered={false} style={{ fontSize: 13, padding: "1px 8px" }}>数字医疗</Tag></Space>
                  <MoreButton size="small" onClick={() => navigate("/industry-class")} />
                </div>
                
                <Row gutter={12} style={{ marginBottom: 24 }}>
                  {keyMetrics.map((m, idx) => (
                    <Col span={8} key={idx}>
                      <div style={styles.metricBox} className="metric-hover">
                        <Text type="secondary" style={{ display: "block", marginBottom: 6, fontSize: 13 }}>{m.label}</Text>
                        <Space align="baseline" size={4}>
                          <Text style={{ fontSize: 36, fontWeight: 800, color: m.color, lineHeight: 1 }}>{m.value}</Text>
                          <Text type="secondary" style={{ fontSize: 13 }}>{m.suffix}</Text>
                        </Space>
                        <Progress percent={m.value > 100 ? 100 : m.value} showInfo={false} strokeColor={m.color} size="small" style={{ marginTop: 6, marginBottom: 0 }} />
                      </div>
                    </Col>
                  ))}
                </Row>
                
                <Collapse defaultActiveKey={["upstream", "midstream", "downstream"]} ghost expandIconPosition="end">
                  {chainData.map((cat) => (
                    <Panel key={cat.type} header={<Space size={6}><Text strong style={{ fontSize: 15 }}>{cat.title}</Text><Badge count={cat.total} overflowCount={999} style={{ backgroundColor: "#e6f7ff", color: "#1890ff", fontSize: 11, height: 18, lineHeight: '18px' }} /></Space>}>
                      <List
                        grid={styles.listGutter}
                        dataSource={cat.subTags}
                        renderItem={(tag: any) => (
                          <List.Item style={{ marginBottom: 12 }}>
                            <Tooltip title={tag.isWeak ? "高紧缺环节" : `已入驻企业 ${tag.count} 家`}>
                              <div style={{ ...styles.industryTag, borderLeft: tag.isWeak ? "3px solid #fa8c16" : "1px solid #f0f0f0", background: tag.isWeak ? "#fffbf0" : "#fff" }} className="industry-card-hover" onClick={() => navigate(`/industry-class?tag=${tag.name}`)}>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
                                  <Text strong ellipsis style={{ maxWidth: "75%", fontSize: 13 }}>{tag.name}</Text>
                                  {tag.isWeak && <ThunderboltFilled style={{ color: "#fa8c16", fontSize: 13 }} />}
                                </div>
                                <Text type="secondary" style={{ fontSize: 11 }}>{tag.count} 家企业</Text>
                              </div>
                            </Tooltip>
                          </List.Item>
                        )}
                      />
                    </Panel>
                  ))}
                </Collapse>
                
                <div style={{ marginTop: "auto" }}>
                  <Divider style={{ margin: "16px 0" }} />
                  <Row gutter={16}>
                    <Col span={12}>
                      <div style={{ ...styles.panelHeader, fontSize: 14, marginBottom: 12 }}><Space size={6}><LinkOutlined style={{ color: "#fa8c16" }} />补链建议</Space><MoreButton size="small" onClick={() => setIsWeakLinksModalVisible(true)} /></div>
                      <div className="suggestion-list-wrapper">
                        <SuggestionList data={weakLinksFull.slice(0, 4)} icon={<ThunderboltFilled />} iconColor="#fa8c16" />
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ ...styles.panelHeader, fontSize: 14, marginBottom: 12 }}><Space size={6}><AimOutlined style={{ color: "#1890ff" }} />推荐引育</Space><MoreButton size="small" onClick={() => setIsRecModalVisible(true)} /></div>
                      <div className="suggestion-list-wrapper">
                        <SuggestionList data={recommendEnterprisesFull.slice(0, 4)} icon={<ShopOutlined />} iconColor="#1890ff" />
                      </div>
                    </Col>
                  </Row>
                </div>
              </div>
            </Col>

            <Col xs={24} lg={7} style={{ display: "flex", flexDirection: "column" }}>
              <div style={styles.glassCard}><div style={styles.panelHeader}>企业资质分布</div><StatsGrid data={chaoyangStatsData} /></div>
              <div style={styles.glassCard}><div style={styles.panelHeader}>产业生态要素</div><StatsGrid data={ecologyStatsData} /></div>
              <div style={styles.glassCard}><div style={styles.panelHeader}>热门产业排行</div><RankList data={dynamicHotTags} colorScale={true} /></div>
              <div style={{ ...styles.glassCard, marginBottom: 0 }}><div style={styles.panelHeader}>热点区域分布</div><RankList data={dynamicHotRegions} colorScale={true} /></div>
            </Col>
          </Row>
        </div>
      </Spin>

      {/* 3. 公告中心 */}
      <div id="notice-section" style={styles.contentInner}>
        <div style={{ ...styles.glassCard, marginTop: 16 }}>
          <div style={styles.panelHeader}><Space><SoundOutlined style={{ color: "#1890ff" }} />平台公告中心</Space><Button type="link">查看全部 <ArrowRightOutlined /></Button></div>
          <List
            grid={{ gutter: 32, column: 2 }}
            dataSource={notices}
            renderItem={(item, index) => (
              <List.Item onClick={() => setActiveNoticeIndex(index)} style={{ cursor: "pointer", padding: "12px", borderRadius: 8, background: activeNoticeIndex === index ? "#e6f7ff" : "transparent", transition: "all 0.3s" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Space><Tag color={item.type === "通知" ? "blue" : "green"}>{item.type}</Tag><Text strong={activeNoticeIndex === index}>{item.title}</Text></Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>{item.date}</Text>
                </div>
              </List.Item>
            )}
          />
        </div>
      </div>

      {/* 4. Footer */}
      <footer style={{ ...styles.footer, ...styles.fullWidthContainer }}>
        <div style={styles.contentInner}>
          <Row gutter={64}>
            <Col span={10}>
              <Title level={4} style={{ color: "#fff", marginBottom: 16, fontSize: 18 }}>朝阳区产业链洞察平台</Title>
              <Text style={{ color: "rgba(255,255,255,0.5)", fontSize: 13 }}>专注于朝阳区产业数据分析与辅助决策</Text>
              <div style={{ marginTop: 20, fontSize: 13 }}><CopyrightOutlined /> @2026</div>
            </Col>
            <Col span={7}>
              <Title level={5} style={{ color: "#fff", marginBottom: 16, fontSize: 14 }}>快速链接</Title>
              <Space direction="vertical" size={6}><a style={{ color: "inherit", fontSize: 13 }}>产业画像</a><a style={{ color: "inherit", fontSize: 13 }}>智能诊断</a><a style={{ color: "inherit", fontSize: 13 }}>风险预警</a></Space>
            </Col>
            <Col span={7}>
              <Title level={5} style={{ color: "#fff", marginBottom: 16, fontSize: 14 }}>联系我们</Title>
              <Text style={{ color: "inherit", display: "block", fontSize: 13, marginBottom: 4 }}>地址：北京市朝阳区霄云路x号</Text>
              <Text style={{ color: "inherit", display: "block", fontSize: 13, marginBottom: 4 }}>电话：010-6509XXXX</Text>
              <Text style={{ color: "inherit", fontSize: 13 }}>邮箱：support@chaoyang.gov.cn</Text>
            </Col>
          </Row>
        </div>
      </footer>

      <Modal title="重点补链建议" open={isWeakLinksModalVisible} onCancel={() => setIsWeakLinksModalVisible(false)} footer={null} width={800}>
        <Table dataSource={weakLinksDetail} columns={weakLinkColumns} rowKey="id" pagination={false} size="middle" />
      </Modal>

      <FloatButton.Group trigger="hover" style={{ right: 40, bottom: 40 }} icon={<RobotOutlined />}>
        <FloatButton tooltip="AI助手" icon={<RobotOutlined />} type="primary" />
        <FloatButton tooltip="风险预警" icon={<SafetyCertificateOutlined />} />
      </FloatButton.Group>
    </ConfigProvider>
  );
};

export default Overview;