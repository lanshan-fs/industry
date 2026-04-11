import React, { useState, useEffect, useRef, useMemo } from "react";
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
  AutoComplete,
  Space,
  Divider,
  Modal,
  Table,
  Progress,
  Avatar,
  Rate,
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
  GithubOutlined,
  InfoCircleOutlined,
  BellOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import type { ColumnsType } from "antd/es/table";

// 引入自定义组件
import MoreButton from "../../components/Home/MoreButton";
import RankList, { type RankItem } from "../../components/Home/RankList";
import SuggestionList, {
  type SuggestionItem,
} from "../../components/Home/SuggestionList";
import StatsGrid, { type StatItem } from "../../components/Home/StatsGrid";
import { type SearchScope } from "../../utils/searchRouting";
import { useSmartSearch } from "../../components/search/useSmartSearch";
import {
  fetchDashboardOverview,
  peekDashboardOverview,
} from "../../utils/apiCache";

const { Title, Text } = Typography;
const { Panel } = Collapse;

// ================== 数据定义接口 ==================

// 弹窗用：补链建议数据结构
interface WeakLinkDetail {
  id: string;
  name: string;
  layer: string;
  urgency: number;
  count: number;
}

interface WeakLinkItem extends SuggestionItem {
  layer?: string;
  count?: number;
  urgency?: number;
}

// 弹窗用：推荐引育数据结构
interface RecommendEnterpriseDetail {
  id: string;
  name: string;
  matchScore: number;
  location: string;
  tags: string[];
  disabled?: boolean;
}

interface NoticeItem {
  id: number;
  title: string;
  type: string;
  date: string;
  content: string;
}

// ================== 静态数据准备 ==================

// 1. 顶部驾驶舱关键指标
const DEFAULT_KEY_METRICS = [
  { label: "收录总数", value: 0, suffix: "家", color: "#fff" },
  { label: "综合评分", value: 0, suffix: "分", color: "#73d13d" },
  { label: "协同效率", value: 0, suffix: "%", color: "#ffec3d" },
];

// 2. 企业资质分布
const QUALIFICATION_STATS_META = [
  { label: "上市企业", value: 35, icon: <GlobalOutlined />, color: "#cf1322" },
  { label: "外资企业", value: 128, icon: <GlobalOutlined />, color: "#d48806" },
  { label: "独角兽", value: 12, icon: <CrownOutlined />, color: "#eb2f96" },
  { label: "专精特新", value: 185, icon: <TrophyOutlined />, color: "#722ed1" },
  { label: "高新技术", value: 456, icon: <RocketOutlined />, color: "#1890ff" },
  { label: "科技中小", value: 890, icon: <ShopOutlined />, color: "#52c41a" },
];

// 3. 热门区域分布
const DEFAULT_HOTSPOT_STREETS: RankItem[] = [
  { name: "酒仙桥街道", count: 156, percent: 85 },
  { name: "望京街道", count: 132, percent: 72 },
  { name: "朝外街道", count: 98, percent: 54 },
  { name: "大屯街道", count: 76, percent: 42 },
  { name: "奥运村街道", count: 65, percent: 36 },
  { name: "建外街道", count: 54, percent: 30 },
  { name: "三里屯", count: 42, percent: 25 },
  { name: "呼家楼", count: 38, percent: 22 },
  { name: "团结湖", count: 35, percent: 20 },
  { name: "麦子店", count: 29, percent: 18 },
  { name: "劲松街道", count: 25, percent: 15 },
];

// 4. 平台公告
const DEFAULT_NOTICES: NoticeItem[] = [
  {
    id: 1,
    title: "关于2026年第一季度高新技术企业申报的预通知",
    type: "通知",
    date: "2026-01-29",
    content:
      "平台现已同步本地企业资质数据，可用于提前梳理高新技术企业申报对象。建议相关企业优先核查知识产权、研发投入和人员结构信息，以便后续正式申报时直接复用。",
  },
  {
    id: 2,
    title: "朝阳区新增3家国家级专精特新“小巨人”企业名单公示",
    type: "动态",
    date: "2026-01-28",
    content:
      "本批次公示企业已纳入本地企业画像与评分体系，可在产业分类、企业画像和评分详情页中查看对应企业的资质标签、风险状态与行业位置。",
  },
  {
    id: 3,
    title: "产业链平台将于本周日凌晨 02:00 进行系统维护升级",
    type: "系统",
    date: "2026-01-27",
    content:
      "维护窗口预计持续 30 分钟，期间首页总览、行业画像与高级搜索功能可能出现短时不可用。评分结果与企业数据不会受影响。",
  },
  {
    id: 4,
    title: "2025年度全区数字经济产业发展报告已发布",
    type: "报告",
    date: "2026-01-25",
    content:
      "报告聚焦数字医疗、严肃医疗与医疗零售等重点方向，结合企业分布、评分结果和重点风险，给出当前产业链结构和未来补链建议。",
  },
  {
    id: 5,
    title: "关于举办“数据要素×”产业沙龙的邀请函",
    type: "活动",
    date: "2026-01-24",
    content:
      "活动将围绕产业数据治理、企业画像构建与场景落地展开，平台用户可结合高级搜索结果和企业评分报告准备交流材料。",
  },
];

// 5. 热搜数据
const DEFAULT_HOT_SEARCHES = {
  industries: ["暂无行业热词"],
  enterprises: ["暂无企业热词"],
};

// 6. 热门产业标签
const DEFAULT_HOT_TAGS: RankItem[] = [
  { name: "生物医药", count: 320, percent: 90 },
  { name: "跨境电商", count: 280, percent: 82 },
  { name: "元宇宙", count: 210, percent: 70 },
  { name: "自动驾驶", count: 180, percent: 65 },
  { name: "绿色能源", count: 150, percent: 55 },
  { name: "区块链", count: 120, percent: 45 },
  { name: "SaaS", count: 98, percent: 35 },
  { name: "智能制造", count: 85, percent: 30 },
  { name: "光子计算", count: 60, percent: 20 },
  { name: "工业互联", count: 45, percent: 15 },
];

// 7. 产业生态圈分类
const ecologyCategoriesRaw = [
  { name: "科研院校", icon: <BankOutlined />, count: 42 },
  { name: "行业协会", icon: <ClusterOutlined />, count: 15 },
  { name: "投资基金", icon: <RiseOutlined />, count: 88 },
  { name: "孵化器", icon: <BulbOutlined />, count: 26 },
  { name: "专业园区", icon: <EnvironmentOutlined />, count: 18 },
  { name: "概念验证", icon: <ExperimentOutlined />, count: 9 },
];

// ================== 主页面组件 ==================

const Overview: React.FC = () => {
  const navigate = useNavigate();
  const carouselRef = useRef<any>(null);

  // 状态管理
  const [loading, setLoading] = useState(() => !peekDashboardOverview());
  const [chainData, setChainData] = useState<any[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [keyMetricsData, setKeyMetricsData] =
    useState(DEFAULT_KEY_METRICS);
  const [hotspotStreetsData, setHotspotStreetsData] = useState<RankItem[]>(
    DEFAULT_HOTSPOT_STREETS,
  );
  const [hotTagsRankData, setHotTagsRankData] =
    useState<RankItem[]>(DEFAULT_HOT_TAGS);
  const [hotSearchData, setHotSearchData] =
    useState(DEFAULT_HOT_SEARCHES);
  const [qualificationStatsRaw, setQualificationStatsRaw] = useState<
    { label: string; value: number }[]
  >([]);
  const [ecologyStatsRaw, setEcologyStatsRaw] = useState<
    { label: string; value: number }[]
  >([]);
  const [noticeItems, setNoticeItems] = useState<NoticeItem[]>(DEFAULT_NOTICES);
  const [selectedNotice, setSelectedNotice] = useState<NoticeItem | null>(null);

  // 首页展示用的简略数据
  const [weakLinksFull, setWeakLinksFull] = useState<WeakLinkItem[]>([]);
  const [recommendEnterprisesFull, setRecommendEnterprisesFull] = useState<
    SuggestionItem[]
  >([]);

  // 弹窗展示用的详细数据
  const [weakLinksDetail, setWeakLinksDetail] = useState<WeakLinkDetail[]>([]);
  const [recEnterprisesDetail, setRecEnterprisesDetail] = useState<
    RecommendEnterpriseDetail[]
  >([]);

  const [searchScope, setSearchScope] = useState<SearchScope | "">("");
  const [activeNoticeIndex, setActiveNoticeIndex] = useState(0);
  const { options: searchOptions, handleResolvedSearch } = useSmartSearch(searchInput, searchScope);

  // 弹窗控制
  const [isWeakLinksModalVisible, setIsWeakLinksModalVisible] = useState(false);
  const [isRecModalVisible, setIsRecModalVisible] = useState(false);
  const [isNoticeModalVisible, setIsNoticeModalVisible] = useState(false);

  // 企业资质统计
  const chaoyangStatsData: StatItem[] = QUALIFICATION_STATS_META.map((item) => ({
    icon: item.icon,
    value:
      qualificationStatsRaw.find((stat) => stat.label === item.label)?.value ??
      0,
    label: item.label,
    color: item.color,
    onClick: () => {
      navigate(
        `/industry-class?qualification=${encodeURIComponent(item.label)}`,
      );
    },
  }));

  // 生态圈统计
  const ecologyStatsData: StatItem[] = ecologyCategoriesRaw.map((item) => ({
    icon: item.icon,
    value:
      ecologyStatsRaw.find((stat) => stat.label === item.name)?.value ??
      item.count,
    label: item.name,
    color: "#1890ff",
    onClick: () =>
      navigate(
        `/industry-class?ecology=${encodeURIComponent(item.name)}&searchScope=ecology`,
      ),
  }));

  const heroHighlights = useMemo(
    () => [
      {
        label: "库内企业",
        value: `${Number(keyMetricsData[0]?.value || 0).toLocaleString()}家`,
        tone: "#e6f4ff",
        color: "#1677ff",
      },
      {
        label: "平均评分",
        value: `${Number(keyMetricsData[1]?.value || 0)}分`,
        tone: "#f6ffed",
        color: "#389e0d",
      },
      {
        label: "待补链环节",
        value: `${weakLinksFull.filter((item) => !item.disabled).length}项`,
        tone: "#fff7e6",
        color: "#d46b08",
      },
      {
        label: "平台公告",
        value: `${noticeItems.length}条`,
        tone: "#f9f0ff",
        color: "#722ed1",
      },
    ],
    [keyMetricsData, noticeItems.length, weakLinksFull],
  );

  const activeWeakLinks = useMemo(
    () => weakLinksFull.filter((item) => !item.disabled),
    [weakLinksFull],
  );

  const activeRecommendations = useMemo(
    () => recEnterprisesDetail.filter((item) => !item.disabled),
    [recEnterprisesDetail],
  );

  const openNotice = (notice: NoticeItem, index?: number) => {
    setSelectedNotice(notice);
    setIsNoticeModalVisible(true);
    if (typeof index === "number") {
      setActiveNoticeIndex(index);
      carouselRef.current?.goTo(index);
    }
  };

  const openIndustryProfile = (industryName: string) => {
    navigate(
      `/industry-portrait/industry-profile?industryName=${encodeURIComponent(industryName)}`,
    );
  };

  const openEnterpriseProfile = (companyName: string) => {
    navigate(
      `/industry-portrait/enterprise-profile?company=${encodeURIComponent(companyName)}`,
    );
  };

  // 初始化数据
  useEffect(() => {
    const fallbackChainData = [
      {
        title: "上游 · 研发与技术",
        type: "upstream",
        total: 0,
        subTags: [],
      },
      {
        title: "中游 · 产品与制造",
        type: "midstream",
        total: 0,
        subTags: [],
      },
      {
        title: "下游 · 应用与服务",
        type: "downstream",
        total: 0,
        subTags: [],
      },
    ];

    const buildWeakLinkDetails = (basicLinks: WeakLinkItem[]) =>
      basicLinks.map((item, index) => ({
        id: String(index + 1),
        name: item.name,
        layer: item.layer || "待补充",
        urgency: Number(item.urgency || 0),
        count: Number(item.count || 0),
      }));

    const applyDashboardData = (data: any) => {
      const nextChainData =
        Array.isArray(data?.chainData) && data.chainData.length > 0
          ? data.chainData
          : fallbackChainData;
      setChainData(nextChainData);

      const computedWeakLinks = nextChainData.flatMap((layer: any) =>
        (layer.subTags || [])
          .filter((tag: any) => tag.isWeak)
          .map((tag: any) => ({
            name: tag.name,
            highlight: true,
            desc: tag.count ? `库内${tag.count}家` : "库内暂缺",
            layer: layer.title || layer.type || "待补充",
            count: Number(tag.count || 0),
            urgency:
              Number(tag.count || 0) === 0
                ? 5
                : Number(tag.count || 0) <= 3
                  ? 4
                  : Number(tag.count || 0) <= 10
                    ? 3
                    : Number(tag.count || 0) <= 30
                      ? 2
                      : 1,
          })),
      );
      const weakLinks = computedWeakLinks.length
        ? computedWeakLinks
        : [
            {
              name: "暂无待补链环节",
              desc: "待更多产业链数据",
              disabled: true,
              layer: "待补充",
              count: 0,
              urgency: 0,
            },
          ];
      setWeakLinksFull(weakLinks);
      setWeakLinksDetail(buildWeakLinkDetails(weakLinks));

      const recommendations = Array.isArray(data?.recommendedEnterprises)
        ? data.recommendedEnterprises
        : [];
      setRecEnterprisesDetail(
        recommendations.length > 0
          ? recommendations.map((item: any) => ({
              id: String(item.id),
              name: item.name,
              matchScore: Number(item.matchScore || 0),
              location: item.location || "北京市",
              tags: Array.isArray(item.tags) ? item.tags : [],
            }))
          : [
              {
                id: "placeholder",
                name: "暂无推荐引育企业",
                matchScore: 0,
                location: "待更多评分数据",
                tags: [],
                disabled: true,
              },
            ],
      );
      setRecommendEnterprisesFull(
        recommendations.length > 0
          ? recommendations.map((item: any) => ({
              name: item.name,
              desc: item.location
                ? `${item.location} · 匹配度 ${Number(item.matchScore || 0)}%`
                : `匹配度 ${Number(item.matchScore || 0)}%`,
            }))
          : [{ name: "暂无推荐引育企业", desc: "待更多评分数据", disabled: true }],
      );

      setKeyMetricsData([
        {
          label: "收录总数",
          value: Number(data?.metrics?.totalCompanies ?? data?.totalCompanies ?? 0),
          suffix: "家",
          color: "#fff",
        },
        {
          label: "综合评分",
          value: Number(data?.metrics?.averageScore ?? 0),
          suffix: "分",
          color: "#73d13d",
        },
        {
          label: "协同效率",
          value: Number(data?.metrics?.synergyRate ?? 0),
          suffix: "%",
          color: "#ffec3d",
        },
      ]);
      setQualificationStatsRaw(
        Array.isArray(data?.qualificationStats) ? data.qualificationStats : [],
      );
      setEcologyStatsRaw(
        Array.isArray(data?.ecologyStats) ? data.ecologyStats : [],
      );
      setHotspotStreetsData(
        Array.isArray(data?.hotspotStreets) && data.hotspotStreets.length
          ? data.hotspotStreets
          : DEFAULT_HOTSPOT_STREETS,
      );
      setHotTagsRankData(
        Array.isArray(data?.hotTags) && data.hotTags.length
          ? data.hotTags
          : DEFAULT_HOT_TAGS,
      );
      setHotSearchData({
        industries:
          Array.isArray(data?.hotSearches?.industries) &&
          data.hotSearches.industries.length
            ? data.hotSearches.industries
            : ["暂无行业热词"],
        enterprises:
          Array.isArray(data?.hotSearches?.enterprises) &&
          data.hotSearches.enterprises.length
            ? data.hotSearches.enterprises
            : ["暂无企业热词"],
      });
      setNoticeItems(
        Array.isArray(data?.notices) && data.notices.length
          ? data.notices
          : DEFAULT_NOTICES,
      );
    };

    const cachedOverview = peekDashboardOverview<any>();
    if (cachedOverview?.success && cachedOverview.data) {
      applyDashboardData(cachedOverview.data);
      setLoading(false);
    }

    const fetchData = async () => {
      if (!cachedOverview) {
        setLoading(true);
      }
      try {
        const json = await fetchDashboardOverview<any>();
        if (json.success && json.data) {
          applyDashboardData(json.data);
        } else {
          applyDashboardData({});
        }
      } catch (error) {
        console.error("Fetch error:", error);
        applyDashboardData({});
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleListNoticeClick = (index: number) => {
    if (noticeItems[index]) {
      openNotice(noticeItems[index], index);
    }
  };

  const styles = {
    fullWidthContainer: {
      width: "100vw",
      position: "relative" as const,
      left: "50%",
      right: "50%",
      marginLeft: "-50vw",
      marginRight: "-50vw",
    },
    bannerSection: {
      background: "linear-gradient(135deg, #001529 0%, #003a8c 100%)",
      padding: "60px 0 60px 0",
      marginBottom: 0,
    },
    noticeBarSection: {
      background: "#fffbe6",
      borderBottom: "1px solid #ffe58f",
      height: 40,
    },
    contentInner: {
      maxWidth: 1280,
      margin: "0 auto",
      padding: "0 24px",
    },
    panelContainer: {
      background: "#fff",
      border: "1px solid #f0f0f0",
      marginTop: 24,
      borderRadius: 20,
      overflow: "hidden",
      boxShadow: "0 16px 48px rgba(15, 23, 42, 0.06)",
    },
    panelLeft: {
      borderRight: "1px solid #f0f0f0",
      padding: 28,
      background: "linear-gradient(180deg, #ffffff 0%, #fcfdff 100%)",
    },
    panelRightItem: {
      borderBottom: "1px solid #f0f0f0",
      padding: "20px 24px",
    },
    panelHeader: {
      fontSize: 16,
      fontWeight: 600,
      color: "#333",
      marginBottom: 16,
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
    },
    tagCard: {
      cursor: "pointer",
      borderRadius: 12,
      padding: "10px 14px",
      background: "#fff",
      border: "1px solid #f0f0f0",
      transition: "all 0.3s",
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      height: 54,
    },
    tagCardWeak: {
      background: "#fff7e6",
      border: "1px solid #ffd591",
    },
    footer: {
      background: "#001529",
      padding: "40px 0 20px 0",
      color: "rgba(255,255,255,0.65)",
      marginTop: 24,
      textAlign: "center" as const,
      fontSize: 14,
    },
  };

  const handleSearch = (value?: string) => {
    const trimmed = String(value ?? searchInput).trim();
    if (!trimmed) {
      message.warning("请输入搜索关键词");
      return;
    }
    if (!handleResolvedSearch(trimmed)) {
      message.warning("请输入搜索关键词");
    }
  };

  // 弹窗表格列定义 (简化版)
  const weakLinkColumns: ColumnsType<WeakLinkDetail> = [
    {
      title: "序号",
      dataIndex: "id",
      key: "id",
      width: 80,
      align: "center",
      render: (_: any, __: any, index: number) => index + 1,
    },
    {
      title: "行业环节名称",
      dataIndex: "name",
      key: "name",
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: "所属产业链层级",
      dataIndex: "layer",
      key: "layer",
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: "紧缺指数",
      dataIndex: "urgency",
      key: "urgency",
      width: 150,
      sorter: (a, b) => a.urgency - b.urgency,
      render: (value) => (
        value > 0 ? (
          <Rate
            disabled
            defaultValue={value}
            style={{ fontSize: 14, color: "#fa8c16" }}
          />
        ) : (
          <Text type="secondary">待补充</Text>
        )
      ),
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      align: "center",
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          onClick={() => openIndustryProfile(record.name)}
        >
          查看
        </Button>
      ),
    },
  ];

  return (
    <div>
      {/* 1. 顶部全屏 Banner (搜索区块) */}
      <div style={{ ...styles.fullWidthContainer, ...styles.bannerSection }}>
        <div style={styles.contentInner}>
          <div style={{ textAlign: "center" }}>
            <Title
              level={1}
              style={{
                color: "#fff",
                marginBottom: 12,
                fontWeight: 600,
                letterSpacing: 2,
              }}
            >
              产业链洞察专家
            </Title>
            <div
              style={{
                color: "rgba(255,255,255,0.72)",
                fontSize: 15,
                marginBottom: 28,
                letterSpacing: 0.2,
              }}
            >
              用企业评分、风险信号和产业链映射，快速定位重点行业、关键企业与待补链环节
            </div>

            <div style={{ maxWidth: 840, margin: "0 auto", textAlign: "left" }}>
              <Space size={12} wrap style={{ marginBottom: 12 }}>
                {[
                  { key: "industry", label: "查行业" },
                  { key: "company", label: "查企业" },
                  { key: "person", label: "查负责人" },
                  { key: "risk", label: "查风险" },
                  { key: "qualification", label: "查资质" },
                ].map((item) => {
                  const active = searchScope === item.key;
                  return (
                    <Button
                      key={item.key}
                      type={active ? "primary" : "default"}
                      ghost={!active}
                      onClick={() =>
                        setSearchScope((current) =>
                          current === item.key ? "" : (item.key as SearchScope),
                        )
                      }
                      style={{
                        borderRadius: 999,
                        height: 38,
                        padding: "0 18px",
                        fontWeight: active ? 600 : 500,
                        background: active ? "rgba(255,255,255,0.18)" : "rgba(255,255,255,0.06)",
                        borderColor: active ? "#ffffff" : "rgba(255,255,255,0.18)",
                        color: "#fff",
                      }}
                    >
                      {item.label}
                    </Button>
                  );
                })}
              </Space>
              <div style={{ color: "rgba(255,255,255,0.72)", fontSize: 13, marginBottom: 10 }}>
                {searchScope ? "已限定搜索类型，可再次点击标签取消限定。" : "未限定搜索类型，系统会根据输入内容智能识别。"}
              </div>

              <div
                style={{
                  display: "flex",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                  borderRadius: 8,
                }}
              >
                <AutoComplete
                  style={{ flex: 1 }}
                  options={searchOptions}
                  value={searchInput}
                  onChange={setSearchInput}
                  onSelect={(_value, option) =>
                    handleResolvedSearch(String(option?.value || ""), option as { exactPath?: string; exactScope?: SearchScope })
                  }
                >
                  <Input
                    size="large"
                    placeholder={`请输入${
                      searchScope === "industry"
                        ? "行业"
                        : searchScope === "company"
                          ? "企业"
                          : searchScope === "person"
                            ? "负责人"
                            : searchScope === "risk"
                              ? "风险"
                              : searchScope === "qualification"
                                ? "资质"
                                : "行业、企业、负责人、资质或风险"
                    }名称、关键词...`}
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    style={{
                      height: 56,
                      fontSize: 16,
                      border: "none",
                      borderRadius: "8px 0 0 8px",
                      paddingLeft: 24,
                    }}
                    suffix={
                      <span
                        style={{
                          cursor: "pointer",
                          color: "#1890ff",
                          fontWeight: 500,
                          padding: "0 16px",
                          borderLeft: "1px solid #f0f0f0",
                        }}
                        onClick={() => navigate("/advanced-search")}
                      >
                        高级搜索
                      </span>
                    }
                    onPressEnter={(e) => handleSearch(e.currentTarget.value)}
                  />
                </AutoComplete>
                <Button
                  type="primary"
                  size="large"
                  style={{
                    width: 120,
                    height: 56,
                    fontSize: 18,
                    borderRadius: "0 8px 8px 0",
                    border: "none",
                    background: "#1890ff",
                  }}
                  icon={<SearchOutlined />}
                  onClick={() => handleSearch()}
                >
                  搜索
                </Button>
              </div>

              {/* 热搜区域 */}
              <div
                style={{
                  marginTop: 16,
                  color: "rgba(255,255,255,0.8)",
                  fontSize: 13,
                }}
              >
                <FireOutlined style={{ marginRight: 8, color: "#ffec3d" }} />
                <span style={{ marginRight: 8 }}>热搜行业：</span>
                {hotSearchData.industries.map((item) => (
                  <Tag
                    key={item}
                    bordered={false}
                    style={{
                      background: "rgba(255,255,255,0.15)",
                      color: "#fff",
                      cursor: item.startsWith("暂无") ? "default" : "pointer",
                      border: "none",
                      opacity: item.startsWith("暂无") ? 0.75 : 1,
                    }}
                    onClick={() => {
                      if (!item.startsWith("暂无")) {
                        openIndustryProfile(item);
                      }
                    }}
                  >
                    {item}
                  </Tag>
                ))}
                <span style={{ margin: "0 16px", opacity: 0.5 }}>|</span>
                <span style={{ marginRight: 8 }}>热搜企业：</span>
                {hotSearchData.enterprises.map((item) => (
                  <span
                    key={item}
                    style={{
                      marginRight: 16,
                      cursor: item.startsWith("暂无") ? "default" : "pointer",
                      borderBottom: item.startsWith("暂无")
                        ? "none"
                        : "1px dashed rgba(255,255,255,0.5)",
                      opacity: item.startsWith("暂无") ? 0.75 : 1,
                    }}
                    onClick={() => {
                      if (!item.startsWith("暂无")) {
                        openEnterpriseProfile(item);
                      }
                    }}
                  >
                    {item}
                  </span>
                ))}
              </div>

              <Row gutter={[12, 12]} style={{ marginTop: 20 }}>
                {heroHighlights.map((item) => (
                  <Col xs={12} md={6} key={item.label}>
                    <div
                      style={{
                        padding: "14px 16px",
                        borderRadius: 14,
                        background: item.tone,
                        border: "1px solid rgba(255,255,255,0.14)",
                        backdropFilter: "blur(8px)",
                      }}
                    >
                      <div
                        style={{
                          color: "#5f6b7a",
                          fontSize: 12,
                          marginBottom: 6,
                        }}
                      >
                        {item.label}
                      </div>
                      <div
                        style={{
                          color: item.color,
                          fontSize: 22,
                          fontWeight: 700,
                        }}
                      >
                        {item.value}
                      </div>
                    </div>
                  </Col>
                ))}
              </Row>
            </div>
          </div>
        </div>
      </div>

      {/* 1.5 新增：独立公告轮播条 */}
      <div style={{ ...styles.fullWidthContainer, ...styles.noticeBarSection }}>
        <div
          style={{
            ...styles.contentInner,
            height: "100%",
            display: "flex",
            alignItems: "center",
          }}
        >
          <SoundOutlined
            style={{
              color: "#fa8c16",
              marginRight: 12,
              fontSize: 16,
              flexShrink: 0,
            }}
          />
          <div style={{ flex: 1, minWidth: 0, height: 40 }}>
            <Carousel
              ref={carouselRef}
              autoplay
              dots={false}
              effect="scrollx"
              afterChange={(current) => setActiveNoticeIndex(current)}
              style={{
                width: "100%",
                height: 40,
                lineHeight: "40px",
              }}
            >
              {noticeItems.map((n, index) => (
                <div key={n.id} style={{ width: "100%", height: 40 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      height: "100%",
                      cursor: "pointer",
                      paddingRight: 16,
                    }}
                    onClick={() => openNotice(n, index)}
                  >
                    <Tag
                      color="orange"
                      style={{ marginRight: 8, flexShrink: 0 }}
                    >
                      {n.type}
                    </Tag>
                    <span
                      style={{
                        color: "#333",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        marginRight: 8,
                      }}
                    >
                      {n.title}
                    </span>
                    <span
                      style={{
                        color: "#999",
                        fontSize: 12,
                        flexShrink: 0,
                      }}
                    >
                      {n.date}
                    </span>
                  </div>
                </div>
              ))}
            </Carousel>
          </div>
          <a
            onClick={() => noticeItems[activeNoticeIndex] && openNotice(noticeItems[activeNoticeIndex], activeNoticeIndex)}
            style={{
              color: "#1890ff",
              fontSize: 13,
              marginLeft: 24,
              cursor: "pointer",
              flexShrink: 0,
            }}
          >
            更多公告 &gt;
          </a>
        </div>
      </div>

      {/* 2. 主体内容 */}
      <Spin spinning={loading}>
        <div style={styles.panelContainer}>
          <Row gutter={0}>
            {/* === 左侧：产业链树谱 + 补链 + 引育 === */}
            <Col xs={24} lg={16} style={styles.panelLeft}>
              <div style={styles.panelHeader}>
                <Space>
                  <EnvironmentOutlined style={{ color: "#1890ff" }} />
                  <span>全景产业链树谱</span>
                  <Tag color="blue">数字医疗</Tag>
                </Space>
                <MoreButton onClick={() => navigate("/industry-class")} />
              </div>

              {/* 关键指标 */}
              <div
                style={{
                  background: "#f7faff",
                  padding: "12px",
                  borderRadius: 16,
                  marginBottom: 24,
                  border: "1px solid #e6f4ff",
                }}
              >
                <Row gutter={[12, 12]}>
                  {[...keyMetricsData, { label: "待补链环节", value: activeWeakLinks.length, suffix: "项", color: "#fa8c16" }].map(
                    (m, idx) => (
                    <Col
                      xs={12}
                      md={6}
                      key={idx}
                    >
                      <div
                        style={{
                          textAlign: "center",
                          background: "#fff",
                          borderRadius: 14,
                          border: "1px solid #edf2f7",
                          padding: "14px 12px",
                          height: "100%",
                        }}
                      >
                        <div style={{ fontSize: 12, color: "#667085", marginBottom: 6 }}>
                          {m.label}
                        </div>
                        <div>
                          <span
                            style={{
                              fontSize: 24,
                              fontWeight: "bold",
                              color: idx === 0 ? "#1890ff" : idx === 1 ? "#389e0d" : idx === 2 ? "#fa8c16" : "#d46b08",
                            }}
                          >
                            {m.value}
                          </span>
                          <span style={{ fontSize: 12, color: "#999", marginLeft: 4 }}>{m.suffix}</span>
                        </div>
                      </div>
                    </Col>
                    ),
                  )}
                </Row>
              </div>

              {/* 产业链树谱 */}
              <Collapse
                defaultActiveKey={["upstream", "midstream", "downstream"]}
                ghost
                expandIconPosition="end"
              >
                {chainData.map((cat) => (
                  <Panel
                    key={cat.type}
                    header={
                      <Space>
                        <span style={{ fontWeight: 600, fontSize: 15 }}>
                          {cat.title}
                        </span>
                        <Badge
                          count={cat.total}
                          overflowCount={9999}
                          style={{
                            backgroundColor: "#e6f7ff",
                            color: "#1890ff",
                          }}
                        />
                      </Space>
                    }
                    style={{ marginBottom: 16 }}
                  >
                    <List
                      grid={{ gutter: 16, xs: 2, sm: 2, md: 3, lg: 4, xl: 4 }}
                      dataSource={cat.subTags}
                      renderItem={(tag: any) => (
                        <List.Item style={{ marginBottom: 16 }}>
                          <Tooltip
                            title={
                              tag.isWeak
                                ? "存在缺口，建议关注"
                                : `收录 ${tag.count} 家`
                            }
                          >
                            <div
                              style={{
                                ...styles.tagCard,
                                ...(tag.isWeak ? styles.tagCardWeak : {}),
                              }}
                              onClick={() =>
                                openIndustryProfile(tag.name)
                              }
                            >
                              <div
                                style={{
                                  fontWeight: 500,
                                  color: tag.isWeak ? "#d46b08" : "#333",
                                  flex: 1,
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  whiteSpace: "nowrap",
                                  marginRight: 8,
                                }}
                              >
                                {tag.name}
                              </div>
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  flexShrink: 0,
                                }}
                              >
                                <Text
                                  type="secondary"
                                  style={{ fontSize: 12, marginRight: 4 }}
                                >
                                  {tag.count}家
                                </Text>
                                {tag.isWeak && (
                                  <ThunderboltFilled
                                    style={{ color: "#fa8c16", fontSize: 12 }}
                                  />
                                )}
                              </div>
                            </div>
                          </Tooltip>
                        </List.Item>
                      )}
                    />
                  </Panel>
                ))}
              </Collapse>

              <div
                style={{ height: 1, background: "#f0f0f0", margin: "24px 0" }}
              />

              {/* 补链建议 & 推荐引育 */}
              <Row gutter={[24, 24]}>
                <Col span={24}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: 16,
                    }}
                  >
                    <span style={{ fontSize: 16, fontWeight: 600 }}>
                      <LinkOutlined
                        style={{ color: "#fa8c16", marginRight: 8 }}
                      />
                      补链建议
                    </span>
                    <MoreButton
                      onClick={() => setIsWeakLinksModalVisible(true)}
                    />
                  </div>
                  <SuggestionList
                    data={weakLinksFull}
                    icon={<ThunderboltFilled />}
                    iconColor="#fa8c16"
                    onItemClick={(item) => openIndustryProfile(item.name)}
                  />
                </Col>

                <Col span={24}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: 16,
                      marginTop: 8,
                    }}
                  >
                    <span style={{ fontSize: 16, fontWeight: 600 }}>
                      <AimOutlined
                        style={{ color: "#1890ff", marginRight: 8 }}
                      />
                      推荐引育
                    </span>
                    <MoreButton onClick={() => setIsRecModalVisible(true)} />
                  </div>
                  <SuggestionList
                    data={recommendEnterprisesFull}
                    icon={<ShopOutlined />}
                    iconColor="#1890ff"
                    onItemClick={(item) => openEnterpriseProfile(item.name)}
                  />
                </Col>
              </Row>
            </Col>

            {/* === 右侧：分析看板 === */}
            {}
            <Col xs={24} lg={8}>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  height: "100%",
                  // fontSize: 15,
                }}
              >
                {/* 1. 资质构成 */}
                <div style={styles.panelRightItem}>
                  <div style={styles.panelHeader}>企业资质构成</div>
                  <StatsGrid data={chaoyangStatsData} />
                </div>

                {/* 2. 产业生态圈 */}
                <div style={styles.panelRightItem}>
                  <div style={styles.panelHeader}>产业生态圈</div>
                  <StatsGrid data={ecologyStatsData} />
                </div>

                {/* 3. 热门产业标签 */}
                <div style={styles.panelRightItem}>
                  <div style={styles.panelHeader}>热门产业标签</div>
                  <RankList
                    data={hotTagsRankData}
                    colorScale={true}
                    onItemClick={(item) => openIndustryProfile(item.name)}
                  />
                </div>

                {/* 4. 热门区域分布 */}
                <div style={{ ...styles.panelRightItem, borderBottom: "none" }}>
                  <div style={styles.panelHeader}>热门区域分布</div>
                  <RankList
                    data={hotspotStreetsData}
                    colorScale={true}
                    limit={10}
                    onItemClick={(item) =>
                      navigate(
                        `/industry-class?street=${encodeURIComponent(item.name)}`,
                      )
                    }
                  />
                </div>
              </div>
            </Col>
          </Row>
        </div>
      </Spin>

      {/* 3. 底部详细公告列表 */}
      <div id="notice-section" style={{ marginTop: 24 }}>
        <div style={{ ...styles.panelContainer, padding: 24 }}>
          {/* Header */}
          <div style={styles.panelHeader}>
            <Space>
              <SoundOutlined style={{ color: "#1890ff" }} />
              <span>平台公告中心</span>
            </Space>
            <Button
              type="link"
              style={{ padding: 0, height: "auto" }}
              onClick={() =>
                noticeItems[activeNoticeIndex] &&
                openNotice(noticeItems[activeNoticeIndex], activeNoticeIndex)
              }
            >
              查看全部 <ArrowRightOutlined />
            </Button>
          </div>

          <List
            grid={{ gutter: 60, column: 2 }}
            dataSource={noticeItems}
            renderItem={(item, index) => (
              <List.Item style={{ marginBottom: 12 }}>
                <div
                  onClick={() => handleListNoticeClick(index)}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    borderBottom: "1px solid #f0f0f0",
                    height: 52,
                    alignItems: "center",
                    width: "100%",
                    padding: "0 16px",
                    borderRadius: 4,
                    cursor: "pointer",
                    transition: "all 0.3s ease",
                    background:
                      activeNoticeIndex === index ? "#e6f7ff" : "transparent",
                    borderLeft:
                      activeNoticeIndex === index
                        ? "4px solid #1890ff"
                        : "4px solid transparent",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      flex: 1,
                      overflow: "hidden",
                      marginRight: 24,
                    }}
                  >
                    <Tag
                      color={
                        item.type === "通知"
                          ? "blue"
                          : item.type === "系统"
                            ? "red"
                            : "green"
                      }
                      style={{ marginRight: 12, flexShrink: 0 }}
                    >
                      {item.type}
                    </Tag>
                    <Text
                      ellipsis
                      style={{
                        fontSize: 14,
                        color: activeNoticeIndex === index ? "#1890ff" : "#333",
                        fontWeight: activeNoticeIndex === index ? 500 : 400,
                        flex: 1,
                      }}
                    >
                      {item.title}
                    </Text>
                  </div>
                  <span
                    style={{
                      color: "#999",
                      fontSize: 13,
                      whiteSpace: "nowrap",
                      flexShrink: 0,
                    }}
                  >
                    {item.date}
                  </span>
                </div>
              </List.Item>
            )}
          />
        </div>
      </div>

      {/* 4. Footer */}
      <div style={{ ...styles.fullWidthContainer, ...styles.footer }}>
        <div style={styles.contentInner}>
          <Row gutter={[32, 32]}>
            <Col xs={24} md={8} style={{ textAlign: "left" }}>
              <div
                style={{
                  color: "#fff",
                  fontSize: 18,
                  fontWeight: "bold",
                  marginBottom: 16,
                }}
              >
                朝阳区产业链洞察平台
              </div>
              <div style={{ marginBottom: 8 }}>
                专注于朝阳区产业数据分析与辅助决策
              </div>
              <div>
                <CopyrightOutlined /> 2026
              </div>
            </Col>
            <Col xs={24} md={8} style={{ textAlign: "left" }}>
              <div style={{ color: "#fff", fontSize: 16, marginBottom: 16 }}>
                快速链接
              </div>
              <Space
                direction="vertical"
                style={{ color: "rgba(255,255,255,0.65)" }}
              >
                <a style={{ color: "inherit" }} onClick={() => navigate("/")}>
                  首页
                </a>
                <a
                  style={{ color: "inherit" }}
                  onClick={() => navigate("/industry-class")}
                >
                  产业分类
                </a>
                <a
                  style={{ color: "inherit" }}
                  onClick={() => navigate("/industry-score")}
                >
                  产业评分
                </a>
                <a
                  style={{ color: "inherit" }}
                  onClick={() => navigate("/industry-portrait")}
                >
                  行业画像
                </a>
                <a
                  style={{ color: "inherit" }}
                  onClick={() => navigate("/industry-diag")}
                >
                  智能助手
                </a>
              </Space>
            </Col>
            <Col xs={24} md={8} style={{ textAlign: "left" }}>
              <div style={{ color: "#fff", fontSize: 16, marginBottom: 16 }}>
                联系我们
              </div>
              <div style={{ marginBottom: 8 }}>地址：北京市朝阳区xxxx号</div>
              <div style={{ marginBottom: 8 }}>电话：010-6509XXXX</div>
              <div>邮箱：support@chaoyang.gov.cn</div>
            </Col>
          </Row>
          <Divider
            style={{ borderColor: "rgba(255,255,255,0.15)", margin: "24px 0" }}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span></span>
            <Space size="large">
              <GithubOutlined
                style={{ fontSize: 20, cursor: "pointer" }}
                onClick={() =>
                  window.open("https://github.com/yunnuo-score/dcpt-f", "_blank")
                }
              />
              <GlobalOutlined
                style={{ fontSize: 20, cursor: "pointer" }}
                onClick={() => navigate("/industry-portrait")}
              />
            </Space>
          </div>
        </div>
      </div>

      <FloatButton.Group
        trigger="hover"
        style={{ right: 24, bottom: 80 }}
        icon={<RobotOutlined />}
      >
        <FloatButton
          tooltip="风险预警"
          icon={<SafetyCertificateOutlined />}
          onClick={() => navigate("/industry-class?riskAbnormal=1")}
        />
        <FloatButton
          tooltip="AI 产业链助手"
          icon={<RobotOutlined />}
          type="primary"
          onClick={() => navigate("/industry-diag")}
        />
      </FloatButton.Group>

      {/* ============== 弹窗 1：补链建议（统一宽度 800，简化表格） ============== */}
      <Modal
        title={
          <Space>
            <ThunderboltFilled style={{ color: "#fa8c16" }} />
            <span style={{ fontSize: 16, fontWeight: 600 }}>
              重点补链行业建议
            </span>
          </Space>
        }
        open={isWeakLinksModalVisible}
        onCancel={() => setIsWeakLinksModalVisible(false)}
        footer={null}
        width={800} // 统一宽度
        styles={{ body: { padding: "20px 24px" } }}
      >
        <div style={{ marginBottom: 16, color: "#666" }}>
          <InfoCircleOutlined style={{ marginRight: 6, color: "#1890ff" }} />
          {activeWeakLinks.length > 0
            ? `以下 ${activeWeakLinks.length} 个环节基于库内产业链映射被识别为相对薄弱项，紧缺指数按当前入库企业数倒推。`
            : "当前库内暂无可识别的待补链环节，待更多产业链映射数据补充。"}
        </div>
        <Table
          dataSource={weakLinksDetail}
          columns={weakLinkColumns}
          rowKey="id"
          pagination={false}
          size="middle"
          bordered
          scroll={{ y: 400 }}
        />
      </Modal>

      {/* ============== 弹窗 2：推荐引育（统一宽度 800，简化列表） ============== */}
      <Modal
        title={
          <Space>
            <ShopOutlined style={{ color: "#1890ff" }} />
            <span style={{ fontSize: 16, fontWeight: 600 }}>
              推荐引育企业库
            </span>
          </Space>
        }
        open={isRecModalVisible}
        onCancel={() => setIsRecModalVisible(false)}
        footer={null}
        width={800} // 统一宽度
        styles={{ body: { padding: "20px 24px" } }}
      >
        <div style={{ marginBottom: 16, color: "#666" }}>
          <InfoCircleOutlined style={{ marginRight: 6, color: "#1890ff" }} />
          {activeRecommendations.length > 0
            ? `当前共筛出 ${activeRecommendations.length} 家推荐引育企业，排序依据为库内综合评分与风险标签匹配结果。`
            : "当前库内暂无可推荐的引育企业，待更多评分结果补充。"}
        </div>
        <List
          itemLayout="horizontal"
          dataSource={recEnterprisesDetail}
          renderItem={(item) => (
            <List.Item
              actions={
                item.disabled
                  ? []
                  : [
                      <Button
                        key="view"
                        type="primary"
                        ghost
                        size="small"
                        onClick={() => {
                          setIsRecModalVisible(false);
                          navigate(
                            `/industry-portrait/enterprise-profile?company=${encodeURIComponent(
                              item.name,
                            )}`,
                          );
                        }}
                      >
                        查看详情
                      </Button>,
                    ]
              }
              style={{
                padding: "12px 16px",
                border: "1px solid #f0f0f0",
                borderRadius: 4,
                marginBottom: 12,
                transition: "all 0.3s",
              }}
            >
              <List.Item.Meta
                avatar={
                  <Avatar
                    shape="square"
                    size="large"
                    style={{ backgroundColor: "#e6f7ff", color: "#1890ff" }}
                  >
                    {item.name.substring(0, 1)}
                  </Avatar>
                }
                title={
                  <div
                    style={{ display: "flex", justifyContent: "space-between" }}
                  >
                    <span style={{ fontWeight: 600 }}>{item.name}</span>
                  </div>
                }
                description={
                  <Space size={12} style={{ marginTop: 4 }}>
                    <Tag bordered={false}>{item.location}</Tag>
                    {item.tags.map((tag) => (
                      <Tag key={tag} color="blue" bordered={false}>
                        {tag}
                      </Tag>
                    ))}
                  </Space>
                }
              />
              <div
                style={{
                  width: 140,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "flex-end",
                  justifyContent: "center",
                  marginRight: 24,
                }}
              >
                <div style={{ fontSize: 12, color: "#999", marginBottom: 4 }}>
                  {item.disabled ? "状态" : "匹配度"}
                </div>
                {item.disabled ? (
                  <Text type="secondary">待补充</Text>
                ) : (
                  <Progress
                    percent={item.matchScore}
                    size="small"
                    strokeColor="#1890ff"
                  />
                )}
              </div>
            </List.Item>
          )}
        />
      </Modal>

      <Modal
        title={
          <Space>
            <BellOutlined style={{ color: "#1890ff" }} />
            <span style={{ fontSize: 16, fontWeight: 600 }}>公告详情</span>
          </Space>
        }
        open={isNoticeModalVisible}
        onCancel={() => setIsNoticeModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setIsNoticeModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={720}
      >
        {selectedNotice && (
          <div>
            <div style={{ marginBottom: 16 }}>
              <Space size={12} wrap>
                <Tag color="blue">{selectedNotice.type}</Tag>
                <Text type="secondary">{selectedNotice.date}</Text>
              </Space>
            </div>
            <Title level={4} style={{ marginBottom: 16 }}>
              {selectedNotice.title}
            </Title>
            <Text style={{ color: "#595959", lineHeight: 1.9 }}>
              {selectedNotice.content}
            </Text>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Overview;
