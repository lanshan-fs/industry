import React, { useState, useEffect, useRef } from "react";
import {
  Layout,
  Tree,
  List,
  Card,
  Tag,
  Typography,
  Space,
  Button,
  theme,
  Empty,
  Spin,
  Grid,
  Row,
  Col,
  Divider,
  Dropdown,
  Avatar,
  message,
  Rate,
  Tooltip,
} from "antd";
import type { MenuProps } from "antd";
import {
  DeploymentUnitOutlined,
  LeftOutlined,
  RightOutlined,
  UserOutlined,
  BankOutlined,
  EnvironmentOutlined,
  ExportOutlined,
  SortAscendingOutlined,
  GlobalOutlined,
  PhoneOutlined,
  MailOutlined,
  ArrowRightOutlined,
  DownOutlined,
  ShopOutlined,
  RiseOutlined,
  UpOutlined,
  SearchOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  RocketOutlined,
  AuditOutlined,
  SecurityScanOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import type { DataNode } from "antd/es/tree";

const { Sider, Content } = Layout;
const { Title, Text, Link } = Typography;
const { useBreakpoint } = Grid;

// --- 颜色与配置 ---
const STAGE_COLORS: Record<string, string> = {
  stage_upstream: "#1677ff",
  stage_midstream: "#13c2c2",
  stage_downstream: "#fa8c16",
};
const STAGE_BG_COLORS: Record<string, string> = {
  stage_upstream: "#f0f5ff",
  stage_midstream: "#e6fffb",
  stage_downstream: "#fff7e6",
};
const STAGE_BORDER_COLORS: Record<string, string> = {
  stage_upstream: "#adc6ff",
  stage_midstream: "#87e8de",
  stage_downstream: "#ffd591",
};
const LOGO_COLORS = ["#1677ff", "#722ed1", "#fa8c16", "#13c2c2", "#f5222d", "#52c41a"];

// --- 产业链树谱静态配置 ---
const STATIC_TREE_DATA: DataNode[] = [
  {
    title: "上游 · 研发与原料",
    key: "stage_upstream",
    children: [
      { title: "AI CRO/技术服务商", key: "AI CRO/技术服务商" },
      { title: "AI 药物研发平台", key: "AI 药物研发平台" },
      { title: "AI软件/工具平台", key: "AI软件/工具平台" },
      { title: "前沿技术融合", key: "前沿技术融合" },
      { title: "装备制造", key: "装备制造" },
    ],
  },
  {
    title: "中游 · 生产与制造",
    key: "stage_midstream",
    children: [
      { title: "AI自研管线企业", key: "AI自研管线企业" }, { title: "中药", key: "中药" },
      { title: "低值医用耗材", key: "低值医用耗材" }, { title: "体外诊断(IVD)", key: "体外诊断(IVD)" },
      { title: "化学制药", key: "化学制药" }, { title: "治疗设备", key: "治疗设备" },
      { title: "植入器械/材料", key: "植入器械/材料" }, { title: "智慧医疗", key: "智慧医疗" },
      { title: "影像设备", key: "影像设备" }, { title: "康复设备", key: "康复设备" },
      { title: "生命信息支持设备", key: "生命信息支持设备" }, { title: "生物制品", key: "生物制品" },
      { title: "辅助设备", key: "辅助设备" }, { title: "高值医用耗材", key: "高值医用耗材" },
    ],
  },
  {
    title: "下游 · 应用与服务",
    key: "stage_downstream",
    children: [
      { title: "严肃医疗", key: "严肃医疗" }, { title: "互联网+健康", key: "互联网+健康" },
      { title: "互联网医疗", key: "互联网医疗" }, { title: "保险支付", key: "保险支付" },
      { title: "医疗零售", key: "医疗零售" }, { title: "医药商业/流通", key: "医药商业/流通" },
      { title: "家用医疗设备", key: "家用医疗设备" }, { title: "数字疗法", key: "数字疗法" },
      { title: "消费医疗", key: "消费医疗" }, { title: "第三方中心", key: "第三方中心" },
    ],
  },
];

// --- 辅助组件：筛选行 ---
const FilterRow: React.FC<{
  label: string; groupKey: string; options: string[]; activeValue: string; onSelect: (key: string, val: string) => void;
}> = ({ label, groupKey, options, activeValue, onSelect }) => {
  const [expanded, setExpanded] = useState(false);
  const LIMIT = 10;
  const showExpand = options.length > LIMIT;
  const visibleOptions = expanded ? options : options.slice(0, LIMIT);

  return (
    <div style={{ display: "flex", marginBottom: 10, lineHeight: "26px" }}>
      <div style={{ width: 100, color: "#8c8c8c", fontWeight: 500, flexShrink: 0 }}>{label}</div>
      <div style={{ flex: 1, display: "flex", alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <Space wrap size={[4, 4]}>
            <Tag.CheckableTag checked={!activeValue} onChange={() => onSelect(groupKey, "")} style={{ border: "none", padding: "1px 10px" }}>不限</Tag.CheckableTag>
            {visibleOptions.map((opt) => (
              <Tag.CheckableTag key={opt} checked={activeValue === opt} onChange={() => onSelect(groupKey, opt)} style={{ border: "none", padding: "1px 10px", color: activeValue === opt ? undefined : "#595959" }}>{opt}</Tag.CheckableTag>
            ))}
          </Space>
        </div>
        {showExpand && (
          <Button type="link" size="small" onClick={() => setExpanded(!expanded)} style={{ padding: "0 8px", fontSize: 12, height: 24, marginLeft: 8 }}>
            {expanded ? "收起" : "更多"} {expanded ? <UpOutlined /> : <DownOutlined />}
          </Button>
        )}
      </div>
    </div>
  );
};

const IndustryClass: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();
  const screens = useBreakpoint();

  const [loadingList, setLoadingList] = useState(false);
  const [treeData] = useState<DataNode[]>(STATIC_TREE_DATA);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]); 
  const [companyList, setCompanyList] = useState<any[]>([]);
  const [preciseList, setPreciseList] = useState<any[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<React.Key[]>([]);
  const [activeFilters, setActiveFilters] = useState<Record<string, string>>({});
  const [searchTime, setSearchTime] = useState(0.0);
  const [totalResult, setTotalResult] = useState(0);
  const [sortLabel, setSortLabel] = useState("默认排序");

  const scrollRef = useRef<HTMLDivElement>(null);

  const getParentKey = (key: string, tree: DataNode[]): string | null => {
    for (const node of tree) {
      if (node.children) {
        if (node.children.some((item) => item.key === key)) return node.key as string;
        const parentKey = getParentKey(key, node.children);
        if (parentKey) return parentKey;
      }
    }
    return null;
  };

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const keyword = params.get("keyword") || params.get("q") || "";
    // 🌟 修正：确保能拿到首页传过来的任意标签参数
    const tag = params.get("tag") || params.get("tagId"); 
    
    if (tag) {
      setSelectedKeys([tag]);
      const parentKey = getParentKey(tag, treeData);
      if (parentKey) {
        setExpandedKeys((prev) => Array.from(new Set([...prev, parentKey])));
      }
      setTimeout(() => {
        const element = document.getElementById(`tree-node-${tag}`);
        if (element) {
          element.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 500);
    }

    // 🌟 修正：优先使用 url 里的标签作为搜索关键词传给后端，确保下方列表有数据
    const fetchKeyword = tag || keyword;
    fetchCompanies({ keyword: fetchKeyword, ...activeFilters });
  }, [location.search, activeFilters]);

  const fetchCompanies = async (params: any) => {
    setLoadingList(true);
    const startTime = performance.now();
    try {
      const query = new URLSearchParams();
      if (params.keyword) query.append("keyword", params.keyword);
      Object.keys(params).forEach(key => {
        if (key !== 'keyword' && params[key]) query.append(key, params[key]);
      });
      query.append("page", "1");
      query.append("pageSize", "30");

      const res = await fetch(`http://127.0.0.1:8000/api/companies/?${query.toString()}`);
      const json = await res.json();

      if (json.code === 200) {
        setCompanyList(json.data);
        // 🌟 核心需求修复：优质推荐锁定最多五个企业
        if (preciseList.length === 0) {
          setPreciseList(json.data.slice(0, 5));
        }
        setTotalResult(json.total || json.data.length);
      } else {
        setCompanyList([]); setTotalResult(0);
      }
    } catch (err) {
      message.error("连接后端失败");
    } finally {
      const endTime = performance.now();
      setSearchTime(parseFloat(((endTime - startTime) / 1000).toFixed(3)));
      setLoadingList(false);
    }
  };

  const findParentStageKey = (nodeKey: string): string => {
    for (const root of treeData) {
      if (root.key === nodeKey) return root.key as string;
      if (root.children) {
        const hasChild = (nodes: any[], targetKey: string): boolean => {
          return nodes.some((n) => n.key === targetKey || (n.children && hasChild(n.children, targetKey)));
        };
        if (hasChild(root.children as any[], nodeKey)) return root.key as string;
      }
    }
    return "";
  };

  const titleRender = (node: any) => {
    const isSelected = selectedKeys.includes(node.key);
    const isStage = String(node.key).startsWith("stage_");
    let stageKey = isStage ? (node.key as string) : findParentStageKey(node.key as string);
    const primaryColor = STAGE_COLORS[stageKey] || token.colorPrimary;
    const bgColor = STAGE_BG_COLORS[stageKey] || "#fafafa";
    const borderColor = STAGE_BORDER_COLORS[stageKey] || "#d9d9d9";

    return (
      <div
        id={`tree-node-${node.key}`}
        style={{
          display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%",
          padding: isStage ? "12px 16px" : "10px 12px", margin: "6px 0", borderRadius: 8,
          background: isSelected ? "#fff" : isStage ? bgColor : "transparent",
          border: isSelected ? `2px solid ${primaryColor}` : isStage ? `1px solid ${borderColor}` : "1px solid transparent",
          boxShadow: isSelected ? `0 2px 10px ${primaryColor}33` : "none", cursor: "pointer", transition: "all 0.3s",
        }}
      >
        <Space size={10}>
          {isStage ? <DeploymentUnitOutlined style={{ color: primaryColor, fontSize: 18 }} /> : <div style={{ width: 8, height: 8, borderRadius: "50%", background: isSelected ? primaryColor : borderColor }} />}
          <Text strong={isStage || isSelected} style={{ color: isSelected ? primaryColor : "#262626", fontSize: isStage ? 15 : 14 }}>{node.title}</Text>
        </Space>
      </div>
    );
  };

  const onSelect = (keys: React.Key[]) => {
    setSelectedKeys(keys);
    const key = keys[0] as string;
    if (key && !key.startsWith("stage_")) {
      navigate(`?tagId=${key}`);
    }
  };

  const handleFilterClick = (groupKey: string, value: string) => {
    setActiveFilters((prev) => ({ ...prev, [groupKey]: prev[groupKey] === value ? "" : value }));
  };

  const scrollLeft = () => scrollRef.current?.scrollBy({ left: -320, behavior: "smooth" });
  const scrollRight = () => scrollRef.current?.scrollBy({ left: 320, behavior: "smooth" });

  const handleSortChange: MenuProps["onClick"] = (e) => {
    const item = sortItems.find(i => i.key === e.key);
    if (item) setSortLabel((item as any).label);
  };

  const sortItems = [
    { key: "default", label: "默认排序" }, { key: "capital_desc", label: "注册资本 (高->低)" },
    { key: "date_desc", label: "成立日期 (晚->早)" }, { key: "score_desc", label: "企业评分 (高->低)" },
  ];

  const renderFilterSection = () => {
    const filterGroups = [
     { key: "entType", name: "企业类型", options: ["有限责任公司", "股份有限公司", "国有企业", "私营企业", "外商投资", "港澳台投资", "联营企业", "集体所有制", "个体工商户"] },
      { key: "techAttr", name: "科技属性", options: ["高新企业", "科技型中小企业", "瞪羚企业", "国家级技术创新示范企业", "省级技术创新示范企业", "国家级企业技术中心", "省级企业技术中心", "国家备案众创空间", "国家级科技企业孵化器", "省级科技企业孵化器"] },
      { key: "techField", name: "技术领域", options: ["人工智能", "大数据", "云计算", "物联网", "区块链", "5G通信", "数字孪生", "边缘计算", "量子计算", "元宇宙"] },
      { key: "scenario", name: "应用场景", options: ["健康管理", "患者社区", "健康和疾病咨询", "就诊挂号", "就诊服务", "转诊服务", "诊后服务", "疾病诊断", "疾病治疗", "康复治疗"] },
      { key: "financing", name: "融资轮次", options: ["种子轮", "天使轮", "A轮", "B轮", "C轮", "D轮及以上", "IPO上市", "战略融资", "未融资"] },
      { key: "street", name: "街道地区", options: ["朝外街道", "劲松街道", "建外街道", "呼家楼街道", "八里庄街道", "三里屯街道", "团结湖街道", "双井街道", "垡头街道", "左家庄街道"] },
    ];
    return (
      <div style={{ background: "#fff", padding: "20px 32px", borderBottom: "1px solid #f0f0f0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
          <Space><div style={{ width: 4, height: 18, background: "linear-gradient(to bottom, #1677ff, #36cfc9)", borderRadius: 2 }}></div><Text strong style={{ fontSize: 16 }}>多维打标筛选</Text></Space>
          <Button type="link" size="small" onClick={() => navigate("/advanced-search")}>更多筛选条件，试试高级搜索 <RightOutlined /></Button>
        </div>
        <div style={{ fontSize: 13 }}>
          {filterGroups.map((group) => (
            <FilterRow key={group.key} label={group.name} groupKey={group.key} options={group.options} activeValue={activeFilters[group.key]} onSelect={handleFilterClick} />
          ))}
        </div>
      </div>
    );
  };

  const renderPreciseBlock = () => {
    // 🌟 修正：移除 loadingList 的判断，确保推荐模块始终显示不消失
    if (preciseList.length === 0) return null;
    return (
      <div style={{ background: "#fff", padding: "24px 32px 32px", borderBottom: "1px solid #f0f0f0", position: "relative" }}>
        <div style={{ marginBottom: 20, display: "flex", alignItems: "center", color: "#595959", fontSize: 14 }}>
          <Space size={24}>
            <Space><ShopOutlined style={{ color: "#1677ff" }} /><Text strong>优质推荐</Text></Space>
            <Divider type="vertical" />
            <Space><RiseOutlined style={{ color: "#fa8c16" }} /><Text strong>重点关注企业</Text></Space>
          </Space>
        </div>
        <div style={{ display: "flex", alignItems: "center" }}>
          <Button shape="circle" icon={<LeftOutlined />} onClick={scrollLeft} style={{ marginRight: 20, background: "#f5f5f5", border: "none", color: "#999" }} />
          <div ref={scrollRef} style={{ display: "flex", overflowX: "hidden", gap: 20, flex: 1, scrollBehavior: "smooth", padding: "8px 4px" }}>
            {preciseList.map((item, idx) => (
              <Card key={`p-${item.company_id}`} hoverable onClick={() => navigate(`/industry-portrait/enterprise-profile?id=${item.company_id}`)} style={{ minWidth: 260, maxWidth: 260, borderRadius: 8, border: "1px solid #f0f0f0", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }} bodyStyle={{ padding: "20px" }}>
                <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
                  <Avatar shape="square" size={40} style={{ backgroundColor: LOGO_COLORS[idx % 6], marginRight: 12, borderRadius: 6 }}>{item.company_name?.charAt(0)}</Avatar>
                  <div style={{ overflow: "hidden" }}>
                    <Text strong ellipsis style={{ display: "block", fontSize: 15 }}>{item.company_name}</Text>
                    <Tag color="geekblue" style={{ fontSize: 10, margin: 0 }}>行业龙头</Tag>
                  </div>
                </div>
                <Row gutter={[8, 12]}>
                  <Col span={12}><Text type="secondary" style={{ fontSize: 12, display: "block" }}>注册资本</Text><Text strong style={{ fontSize: 12 }}>{item.register_capital || "-"}</Text></Col>
                  <Col span={12}><Text type="secondary" style={{ fontSize: 12, display: "block" }}>成立日期</Text><Text strong style={{ fontSize: 12 }}>{item.establish_date?.substring(0, 10) || "-"}</Text></Col>
                </Row>
              </Card>
            ))}
          </div>
          <Button shape="circle" icon={<RightOutlined />} onClick={scrollRight} style={{ marginLeft: 20, background: "#f5f5f5", border: "none", color: "#999" }} />
        </div>
      </div>
    );
  };

  const renderListItem = (item: any, index: number) => {
    // 🌟 修正：透视区展示后端的 11 个打标字段数据
    const tags = [
      { label: "基本", val: item.basic_info_tags, icon: <UserOutlined /> },
      { label: "经营", val: item.operation_tags, icon: <RiseOutlined /> },
      { label: "科技", val: item.tech_tags, icon: <RocketOutlined /> },
      { label: "市场", val: item.market_tags, icon: <SecurityScanOutlined /> },
      { label: "风险", val: item.risk_tags, icon: <SafetyOutlined /> },
      { label: "场景", val: item.scenario_tags, icon: <AuditOutlined /> },
    ];

    return (
      <List.Item style={{ padding: "32px", background: "#fff", borderBottom: "1px solid #f0f0f0" }} className="list-item-hover">
        <Row gutter={24} style={{ width: "100%" }}>
          <Col span={13} style={{ borderRight: "1px dashed #f0f0f0" }}>
            <div style={{ display: "flex", alignItems: "flex-start" }}>
              <div style={{ width: 68, height: 68, background: LOGO_COLORS[index % 6], borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", marginRight: 20, color: "#fff", fontSize: 28, fontWeight: "bold", flexShrink: 0 }}>
                {item.company_name?.charAt(0)}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ marginBottom: 10, display: "flex", alignItems: "center", gap: 8 }}>
                  <Link strong style={{ fontSize: 18, color: "#262626" }} onClick={() => navigate(`/industry-portrait/enterprise-profile?id=${item.company_id}`)}>{item.company_name}</Link>
                </div>
                <Row gutter={16} style={{ marginBottom: 12 }}>
                  <Col span={8}><Text type="secondary" style={{ fontSize: 12 }}>法定代表人</Text><div style={{ marginTop: 2 }}><UserOutlined style={{ color: token.colorPrimary, marginRight: 6 }} /><Text>{item.legal_representative || "-"}</Text></div></Col>
                  <Col span={8}><Text type="secondary" style={{ fontSize: 12 }}>注册资本</Text><div style={{ marginTop: 2 }}><BankOutlined style={{ color: "#fa8c16", marginRight: 6 }} /><Text>{item.register_capital || "-"}</Text></div></Col>
                  <Col span={8}><Text type="secondary" style={{ fontSize: 12 }}>成立日期</Text><div style={{ marginTop: 2 }}><GlobalOutlined style={{ color: "#52c41a", marginRight: 6 }} /><Text>{item.establish_date?.substring(0, 10) || "-"}</Text></div></Col>
                </Row>
                <div style={{ fontSize: 13, color: "#8c8c8c" }}><EnvironmentOutlined style={{ marginRight: 6 }} />{item.register_address || "暂无地址"}</div>
                <div style={{ marginTop: 12 }}><Tag color="blue">信用代码：{item.credit_code || "暂无"}</Tag></div>
              </div>
            </div>
          </Col>
          <Col span={11} style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", paddingLeft: 24 }}>
             <div>
              <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>打标透视：</Text>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                {tags.map((t, i) => t.val && (
                  <Tooltip title={t.val} key={i}>
                    <div style={{ fontSize: 12, background: "#f9f9f9", padding: "4px 8px", borderRadius: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      <span style={{ color: token.colorPrimary, marginRight: 4 }}>{t.icon}</span><Text type="secondary">{t.label}:</Text> <Text strong>{String(t.val).split(',')[0]}</Text>
                    </div>
                  </Tooltip>
                ))}
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
              <Button type="primary" shape="round" icon={<ArrowRightOutlined />} onClick={() => navigate(`/industry-portrait/enterprise-profile?id=${item.company_id}`)}>查看画像</Button>
            </div>
          </Col>
        </Row>
      </List.Item>
    );
  };

  return (
    <Layout style={{ height: "calc(100vh - 64px)", background: "#fff" }}>
      <Sider width={360} breakpoint="lg" collapsedWidth="0" style={{ background: "#fafafa", borderRight: "1px solid #f0f0f0", overflowY: "auto", padding: "24px 20px" }} theme="light">
        <div style={{ marginBottom: 24 }}>
          <Title level={4} style={{ margin: 0 }}>产业链树谱</Title>
          <Text type="secondary" style={{ fontSize: 13 }}>点击具体节点精确定位</Text>
        </div>
        <Tree blockNode showLine={{ showLeafIcon: false }} expandedKeys={expandedKeys} onExpand={setExpandedKeys} selectedKeys={selectedKeys} onSelect={onSelect} titleRender={titleRender} treeData={treeData} style={{ background: "transparent" }} />
      </Sider>

      <Content style={{ display: "flex", flexDirection: "column", overflowY: "auto", background: "#fff" }}>
        {renderPreciseBlock()}
        {renderFilterSection()}
        <div style={{ flex: 1, padding: "0 24px" }}>
          <div style={{ padding: "16px 0", borderBottom: "1px solid #f0f0f0", display: "flex", justifyContent: "space-between" }}>
            <Text>为您找到 <Text strong style={{ color: token.colorPrimary }}>{totalResult}</Text> 家企业，用时 {searchTime} 秒</Text>
            <Space>
              <Dropdown menu={{ items: sortItems, onClick: handleSortChange }} trigger={["click"]}>
                <Button type="text" icon={<SortAscendingOutlined />}>{sortLabel} <DownOutlined /></Button>
              </Dropdown>
              <Button type="text" icon={<ExportOutlined />}>导出数据</Button>
            </Space>
          </div>
          {loadingList ? (
            <div style={{ textAlign: "center", padding: 60 }}><Spin tip="加载中..." /></div>
          ) : (
            <List dataSource={companyList} renderItem={renderListItem} locale={{ emptyText: <Empty description="暂无符合条件的企业" /> }} pagination={{ pageSize: 10, total: totalResult, align: "center", showSizeChanger: true }} />
          )}
        </div>
      </Content>
    </Layout>
  );
};

export default IndustryClass;