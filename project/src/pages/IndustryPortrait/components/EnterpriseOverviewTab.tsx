import React, { useMemo, useState } from "react";
import {
  Row,
  Col,
  Typography,
  Space,
  Tag,
  Avatar,
  Descriptions,
  Table,
  Statistic,
  Progress,
  Timeline,
  Alert,
  Grid,
  List,
  Card,
  Button,
  Modal,
} from "antd";
import {
  GlobalOutlined,
  EnvironmentOutlined,
  BankOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  UserOutlined,
  RiseOutlined,
  DownOutlined,
  UpOutlined,
  TeamOutlined,
  ApartmentOutlined,
  TrophyOutlined,
  ProfileOutlined,
} from "@ant-design/icons";
import { Radar } from "@ant-design/plots";

import EnterpriseBasicInfoTab from "./EnterpriseBasicInfoTab";

const { Title, Text, Paragraph } = Typography;
const { useBreakpoint } = Grid;

const COLORS = {
  primary: "#1890ff",
  gold: "#faad14",
  green: "#52c41a",
  borderColor: "#f0f0f0",
  textSecondary: "#666",
  riskHigh: "#ff4d4f",
  riskMedium: "#fa8c16",
  panel: "#ffffff",
  softBlue: "#f4f9ff",
};

const TAB_CONFIG = [
  { key: "basic", label: "基本信息" },
  { key: "risk", label: "经营风险" },
  { key: "operating", label: "经营信息" },
  { key: "ip", label: "知识产权" },
];

interface EnterpriseOverviewTabProps {
  profile: any;
}

const sectionTitleStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  fontSize: 16,
  fontWeight: 700,
  color: "#262626",
  marginBottom: 16,
};

const SectionTitle = ({ title }: { title: string }) => (
  <div style={sectionTitleStyle}>
    <div
      style={{
        width: 4,
        height: 16,
        backgroundColor: COLORS.primary,
        borderRadius: 2,
        marginRight: 8,
      }}
    />
    {title}
  </div>
);

const MAIN_RADAR_CONFIG = (data: any[]) => ({
  data: data || [],
  xField: "item",
  yField: "score",
  area: {
    style: {
      fill: "l(90) 0:#1890ff 1:rgba(24,144,255,0.1)",
      fillOpacity: 0.32,
    },
  },
  line: { style: { stroke: "#1890ff", lineWidth: 2 } },
  point: {
    size: 3,
    shape: "circle",
    style: { fill: "#fff", stroke: "#1890ff", lineWidth: 2 },
  },
  scale: { y: { min: 0, max: 100, tickCount: 5 } },
  axis: { x: { grid: { line: { style: { stroke: "#eee" } } } } },
  height: 240,
});

const EnterpriseOverviewTab: React.FC<EnterpriseOverviewTabProps> = ({ profile }) => {
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const maxScore = Number(profile.metrics?.maxScore || 100);
  const totalScore = Number(profile.metrics?.totalScore || 0);
  const extraScore = Number(profile.metrics?.extraScore || 0);
  const totalScorePercent = maxScore > 0 ? Math.min(100, Math.max(0, (totalScore / maxScore) * 100)) : 0;
  const scoreHealthy = totalScore >= maxScore * 0.6;
  const [activeTabKey, setActiveTabKey] = useState("basic");
  const [expandedTabs, setExpandedTabs] = useState<Record<string, boolean>>({});
  const [ipDetailModal, setIpDetailModal] = useState<{
    open: boolean;
    title: string;
    columns: any[];
    data: any[];
  }>({ open: false, title: "", columns: [], data: [] });

  const toggleExpand = (key: string) => {
    setExpandedTabs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const getOperateItem = (label: string) =>
    (profile.operateTableData || []).find((item: any) => item.item === label);

  const relocationRisk = useMemo(() => {
    if (profile.migrationRisk) {
      return profile.migrationRisk;
    }
    const recruitCount = Number(getOperateItem("招聘信息数量")?.count || 0);
    const recruitStatus = String(getOperateItem("有无招聘")?.status || "无");

    if (recruitCount >= 5 || recruitStatus === "有") {
      return {
        level: "低",
        color: COLORS.green,
        score: 22,
        label: "招聘活跃度良好",
        factors: [
          { name: "招聘信息数量", desc: `库内检出 ${recruitCount} 条招聘记录`, impact: "Low" },
          { name: "本地吸附信号", desc: "仍存在持续招聘动作", impact: "Low" },
          { name: "判定口径", desc: "仅依据库内招聘数据：0 条高风险，1-4 条中风险，>=5 条低风险", impact: "Low" },
        ],
      };
    }

    if (recruitCount >= 1) {
      return {
        level: "中",
        color: COLORS.riskMedium,
        score: 58,
        label: "招聘活跃度偏弱",
        factors: [
          { name: "招聘信息数量", desc: `库内检出 ${recruitCount} 条招聘记录`, impact: "Medium" },
          { name: "本地吸附信号", desc: "存在零散招聘，但持续性不足", impact: "Medium" },
          { name: "判定口径", desc: "仅依据库内招聘数据：0 条高风险，1-4 条中风险，>=5 条低风险", impact: "Low" },
        ],
      };
    }

    return {
      level: "高",
      color: COLORS.riskHigh,
      score: 86,
      label: "未检出招聘吸附信号",
      factors: [
        { name: "招聘信息数量", desc: "库内未检出招聘记录", impact: "High" },
        { name: "本地吸附信号", desc: "当前无法从招聘侧证明企业仍在扩大本地投入", impact: "High" },
        { name: "判定口径", desc: "仅依据库内招聘数据：0 条高风险，1-4 条中风险，>=5 条低风险", impact: "Low" },
      ],
    };
  }, [profile.migrationRisk, profile.operateTableData]);

  const riskOverview = useMemo(() => {
    return (profile.riskTableData || [])
      .filter((item: any) => Number(item.count || 0) > 0)
      .slice(0, 3)
      .map((item: any) => ({ name: item.item, count: Number(item.count || 0) }));
  }, [profile.riskTableData]);

  const ipDetailConfigs = useMemo(
    () => ({
      专利数量: {
        title: "专利明细",
        data: profile.ipDetails?.["专利数量"] || [],
        columns: [
          { title: "专利名称", dataIndex: "name", key: "name", ellipsis: true },
          { title: "专利号", dataIndex: "number", key: "number", width: 180 },
          { title: "申请日期", dataIndex: "applicationDate", key: "applicationDate", width: 120 },
          { title: "授权日期", dataIndex: "authDate", key: "authDate", width: 120 },
          { title: "技术属性", dataIndex: "techAttribute", key: "techAttribute", width: 140, ellipsis: true },
        ],
      },
      软件著作权数量: {
        title: "软件著作权明细",
        data: profile.ipDetails?.["软件著作权数量"] || [],
        columns: [
          { title: "名称", dataIndex: "name", key: "name", ellipsis: true },
          { title: "登记号", dataIndex: "number", key: "number", width: 200 },
          { title: "简称", dataIndex: "shortName", key: "shortName", width: 160, ellipsis: true },
          { title: "登记日期", dataIndex: "registerDate", key: "registerDate", width: 120 },
          { title: "状态", dataIndex: "status", key: "status", width: 120 },
        ],
      },
      作品著作权数量: {
        title: "作品著作权明细",
        data: profile.ipDetails?.["作品著作权数量"] || [],
        columns: [
          { title: "名称", dataIndex: "name", key: "name", ellipsis: true },
          { title: "登记号", dataIndex: "number", key: "number", width: 180 },
          { title: "类型", dataIndex: "type", key: "type", width: 140 },
          { title: "发表日期", dataIndex: "publishDate", key: "publishDate", width: 120 },
          { title: "登记日期", dataIndex: "registerDate", key: "registerDate", width: 120 },
        ],
      },
      商标数量: {
        title: "商标明细",
        data: profile.ipDetails?.["商标数量"] || [],
        columns: [
          { title: "商标名称", dataIndex: "name", key: "name", ellipsis: true },
          { title: "注册号", dataIndex: "number", key: "number", width: 180 },
          { title: "申请日期", dataIndex: "applicationDate", key: "applicationDate", width: 120 },
        ],
      },
    }),
    [profile.ipDetails],
  );

  const openIpDetailModal = (itemName: string) => {
    const config = (ipDetailConfigs as Record<string, any>)[itemName];
    if (!config || !Array.isArray(config.data) || config.data.length === 0) return;
    setIpDetailModal({
      open: true,
      title: config.title,
      columns: config.columns,
      data: config.data,
    });
  };

  const summaryCards = useMemo(
    () => [
      {
        key: "extra",
        label: "附加分",
        value: `${extraScore} / 55`,
        icon: <ExperimentOutlined style={{ color: "#722ed1" }} />,
      },
      {
        key: "capital",
        label: "注册资本",
        value: profile.baseInfo.regCapital || "-",
        icon: <BankOutlined style={{ color: COLORS.primary }} />,
      },
      {
        key: "insured",
        label: "参保人数",
        value: profile.baseInfo.insuredCount ? `${profile.baseInfo.insuredCount} 人` : "-",
        icon: <TeamOutlined style={{ color: COLORS.green }} />,
      },
      {
        key: "rank",
        label: "库内排名",
        value: profile.metrics.rank ? `#${profile.metrics.rank}` : "-",
        icon: <TrophyOutlined style={{ color: COLORS.gold }} />,
      },
      {
        key: "honors",
        label: "资质荣誉",
        value: `${profile.honors?.length || 0} 项`,
        icon: <ProfileOutlined style={{ color: "#722ed1" }} />,
      },
    ],
    [extraScore, profile.baseInfo.insuredCount, profile.baseInfo.regCapital, profile.honors, profile.metrics.rank],
  );

  const renderExpandableTable = (
    expandKey: string,
    data: any[],
    columns: any[],
    emptyText: string,
    title: string,
    alert?: React.ReactNode,
  ) => {
    const isExpanded = expandedTabs[expandKey];
    const fullData = data || [];
    const displayData = isExpanded ? fullData : fullData.slice(0, 6);
    const hasMore = fullData.length > 6;

    return (
      <Card
        bordered={false}
        style={{
          borderRadius: 12,
          minHeight: 300,
          boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
        }}
      >
        <SectionTitle title={title} />
        {alert}
        <Table
          columns={columns}
          dataSource={displayData}
          pagination={false}
          bordered
          size="middle"
          locale={{ emptyText }}
        />
        {hasMore ? (
          <div style={{ textAlign: "center", marginTop: 16 }}>
            <Button type="link" onClick={() => toggleExpand(expandKey)} style={{ fontWeight: 500 }}>
              {isExpanded ? (
                <>
                  <UpOutlined /> 收起表格
                </>
              ) : (
                <>
                  <DownOutlined /> 展开剩余 {fullData.length - 6} 项
                </>
              )}
            </Button>
          </div>
        ) : null}
      </Card>
    );
  };

  const renderRiskTab = () =>
    renderExpandableTable(
      "risk",
      profile.riskTableData,
      [
        { title: "风险维度", dataIndex: "item", key: "item", width: 200 },
        {
          title: "是否存在记录",
          dataIndex: "hasRisk",
          key: "hasRisk",
          render: (text: string) => (
            <Tag color={text === "有记录" ? "error" : "success"}>{text}</Tag>
          ),
        },
        {
          title: "记录数量 (条)",
          dataIndex: "count",
          key: "count",
          render: (count: number) => (
            <Text
              style={{
                color: count > 0 ? COLORS.riskHigh : COLORS.textSecondary,
                fontWeight: count > 0 ? 700 : 400,
              }}
            >
              {count}
            </Text>
          ),
        },
      ],
      "暂无经营风险数据",
      "经营风险明细",
      <Alert
        message="这里展示的是企业风险记录本身，与下方“迁出风险识别”口径不同。"
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />,
    );

  const renderOperationTab = () =>
    renderExpandableTable(
      "operating",
      profile.operateTableData,
      [
        { title: "经营信息维度", dataIndex: "item", key: "item", width: "42%" },
        {
          title: "状态/内容",
          dataIndex: "status",
          key: "status",
          render: (text: string) => {
            if (text === "-") return <Text type="secondary">-</Text>;
            if (text === "是" || text === "有") return <Tag color="blue">{text}</Tag>;
            if (text === "否" || text === "无") return <Tag>{text}</Tag>;
            return <Text>{text}</Text>;
          },
        },
        {
          title: "数量",
          dataIndex: "count",
          key: "count",
          align: "center" as const,
          width: 120,
        },
      ],
      "暂无经营信息数据",
      "企业经营信息明细",
    );

  const renderIpTab = () =>
    renderExpandableTable(
      "ip",
      profile.qualTableData,
      [
        { title: "资质/知识产权名称", dataIndex: "item", key: "item" },
        {
          title: "认定状态",
          dataIndex: "status",
          key: "status",
          width: 160,
          render: (text: string) => {
            if (text === "-") return <Text type="secondary">-</Text>;
            return <Tag color={text === "是" || text === "有" ? "processing" : "default"}>{text}</Tag>;
          },
        },
        {
          title: "数量",
          dataIndex: "count",
          key: "count",
          align: "center" as const,
          width: 120,
          render: (count: number, record: any) => {
            const hasDetail =
              count > 0 &&
              Boolean((ipDetailConfigs as Record<string, any>)[record.item]?.data?.length);
            return hasDetail ? (
              <Button
                type="link"
                style={{ padding: 0 }}
                onClick={() => openIpDetailModal(record.item)}
              >
                {count}
              </Button>
            ) : (
              count
            );
          },
        },
        {
          title: "明细",
          key: "detail",
          width: 110,
          align: "center" as const,
          render: (_: any, record: any) => {
            const count = Number(record.count || 0);
            const hasDetail =
              count > 0 &&
              Boolean((ipDetailConfigs as Record<string, any>)[record.item]?.data?.length);
            return hasDetail ? (
              <Button size="small" onClick={() => openIpDetailModal(record.item)}>
                查看明细
              </Button>
            ) : (
              <Text type="secondary">-</Text>
            );
          },
        },
      ],
      "暂无知识产权与资质数据",
      "资质荣誉与知识产权明细",
    );

  const renderSubModelCard = (title: string, icon: React.ReactNode, modelData: any, color: string) => {
    const dataSource =
      modelData?.dimensions?.length > 0
        ? modelData.dimensions
        : [{ name: "核心权重指标", weight: 100, score: modelData?.score || 0 }];

    const columns: any[] = [
      {
        title: "评分维度",
        dataIndex: "name",
        ellipsis: true,
        align: "left",
        render: (text: string) => <Text style={{ fontSize: 13 }}>{text}</Text>,
      },
      {
        title: "权重",
        dataIndex: "weight",
        width: 80,
        align: "center",
        render: (weight: number) => <Tag style={{ marginRight: 0 }}>{weight}%</Tag>,
      },
      {
        title: "得分",
        dataIndex: "score",
        width: 80,
        align: "center",
        render: (score: number) => (
          <Text strong style={{ color: score < 60 ? COLORS.riskHigh : color }}>
            {score}
          </Text>
        ),
      },
    ];

    return (
      <Card
        bordered={false}
        bodyStyle={{ padding: 0 }}
        style={{
          height: "100%",
          borderRadius: 12,
          overflow: "hidden",
          boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
        }}
      >
        <div
          style={{
            padding: "16px 20px",
            borderBottom: `1px solid ${COLORS.borderColor}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            backgroundColor: "#fafafa",
          }}
        >
          <Space>
            {icon}
            <Text strong>{title}</Text>
          </Space>
          <Statistic
            value={modelData?.score || 0}
            valueStyle={{ color, fontWeight: "bold", fontSize: 18 }}
            suffix={<span style={{ fontSize: 12, color: "#999" }}>分(总)</span>}
          />
        </div>
        <Table
          dataSource={dataSource}
          rowKey="name"
          pagination={false}
          size="small"
          columns={columns}
          scroll={{ y: 250 }}
          bordered={false}
        />
      </Card>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Card
        bordered={false}
        style={{
          borderRadius: 16,
          boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
          background: "linear-gradient(135deg, #ffffff 0%, #f7fbff 100%)",
        }}
        bodyStyle={{ padding: 24 }}
      >
        <Row gutter={[24, 24]} align="middle">
          <Col flex="88px">
            <Avatar
              shape="square"
              size={88}
              style={{
                backgroundColor: COLORS.primary,
                fontSize: 32,
                borderRadius: 16,
                boxShadow: "0 12px 24px rgba(24,144,255,0.18)",
              }}
            >
              {profile.baseInfo.name?.charAt(0) || "企"}
            </Avatar>
          </Col>
          <Col flex="auto">
            <Space direction="vertical" size={8} style={{ width: "100%" }}>
              <Space align="center" wrap>
                <Title level={3} style={{ margin: 0 }}>
                  {profile.baseInfo.name}
                </Title>
                <Tag color="success">{profile.baseInfo.status || "在业"}</Tag>
                <Tag color="blue">{profile.baseInfo.type}</Tag>
              </Space>
              <Space size={20} style={{ color: COLORS.textSecondary, flexWrap: "wrap" }}>
                <span>
                  <UserOutlined /> 法人：{profile.baseInfo.legalPerson}
                </span>
                <span>
                  <EnvironmentOutlined /> 地址：{profile.baseInfo.address}
                </span>
                <span>
                  <GlobalOutlined /> 官网：{profile.baseInfo.website}
                </span>
              </Space>
              <Space wrap size={[8, 8]}>
                {(profile.tags || []).slice(0, 8).map((tag: string) => (
                  <Tag
                    key={tag}
                    style={{
                      marginRight: 0,
                      border: "none",
                      background: "#e6f4ff",
                      color: "#1677ff",
                      padding: "4px 10px",
                      borderRadius: 999,
                    }}
                  >
                    {tag}
                  </Tag>
                ))}
              </Space>
            </Space>
          </Col>
          <Col xs={24} lg={6}>
            <div
              style={{
                padding: 18,
                borderRadius: 16,
                background: COLORS.panel,
                border: `1px solid ${COLORS.borderColor}`,
                textAlign: "center",
              }}
            >
              <Text type="secondary">综合健康分 / {maxScore}</Text>
              <div
                style={{
                  fontSize: 52,
                  lineHeight: 1,
                  fontWeight: 800,
                  color: COLORS.primary,
                  marginTop: 8,
                }}
              >
                {totalScore}
              </div>
              <Text type="secondary" style={{ fontSize: 12, display: "block", marginTop: 8 }}>
                其中附加分 {extraScore} / 55
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                更新于：{profile.baseInfo.updateTime}
              </Text>
            </div>
          </Col>
        </Row>

        <Row gutter={[12, 12]} style={{ marginTop: 20 }}>
          {summaryCards.map((item) => (
            <Col xs={12} lg={6} key={item.key}>
              <div
                style={{
                  height: "100%",
                  padding: "14px 16px",
                  borderRadius: 14,
                  background: item.key === "rank" ? "#fff8e6" : COLORS.softBlue,
                  border: `1px solid ${COLORS.borderColor}`,
                }}
              >
                <Space align="start">
                  <div style={{ fontSize: 18 }}>{item.icon}</div>
                  <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {item.label}
                    </Text>
                    <div style={{ fontSize: 18, fontWeight: 700, color: "#262626", marginTop: 2 }}>
                      {item.value}
                    </div>
                  </div>
                </Space>
              </div>
            </Col>
          ))}
        </Row>
      </Card>

      <Row gutter={16}>
        <Col xs={24} xl={15}>
          <Card
            bordered={false}
            style={{ height: "100%", borderRadius: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}
          >
            <SectionTitle title="工商信息全景" />
            <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
              <Col xs={12} md={6}>
                <div style={{ padding: 14, borderRadius: 12, background: "#fafafa" }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    行业
                  </Text>
                  <div style={{ fontWeight: 700, marginTop: 4 }}>{profile.baseInfo.industry}</div>
                </div>
              </Col>
              <Col xs={12} md={6}>
                <div style={{ padding: 14, borderRadius: 12, background: "#fafafa" }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    成立日期
                  </Text>
                  <div style={{ fontWeight: 700, marginTop: 4 }}>{profile.baseInfo.establishDate}</div>
                </div>
              </Col>
              <Col xs={12} md={6}>
                <div style={{ padding: 14, borderRadius: 12, background: "#fafafa" }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    注册资本
                  </Text>
                  <div style={{ fontWeight: 700, marginTop: 4 }}>{profile.baseInfo.regCapital}</div>
                </div>
              </Col>
              <Col xs={12} md={6}>
                <div style={{ padding: 14, borderRadius: 12, background: "#fafafa" }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    参保人数
                  </Text>
                  <div style={{ fontWeight: 700, marginTop: 4 }}>
                    {profile.baseInfo.insuredCount ? `${profile.baseInfo.insuredCount} 人` : "-"}
                  </div>
                </div>
              </Col>
            </Row>
            <Descriptions
              column={2}
              bordered
              size="middle"
              labelStyle={{ width: 150, background: "#fafafa", color: "#666" }}
            >
              <Descriptions.Item label="统一社会信用代码">
                {profile.baseInfo.creditCode}
              </Descriptions.Item>
              <Descriptions.Item label="纳税人识别号">
                {profile.baseInfo.taxId}
              </Descriptions.Item>
              <Descriptions.Item label="企业类型">{profile.baseInfo.type}</Descriptions.Item>
              <Descriptions.Item label="经营状态">{profile.baseInfo.status || "-"}</Descriptions.Item>
              <Descriptions.Item label="法定代表人">{profile.baseInfo.legalPerson}</Descriptions.Item>
              <Descriptions.Item label="核准日期">{profile.baseInfo.approvedDate || "-"}</Descriptions.Item>
              <Descriptions.Item label="登记机关">
                {profile.baseInfo.registrationAuthority || "-"}
              </Descriptions.Item>
              <Descriptions.Item label="官网">{profile.baseInfo.website}</Descriptions.Item>
              <Descriptions.Item label="注册地址" span={2}>
                {profile.baseInfo.address}
              </Descriptions.Item>
              <Descriptions.Item label="经营范围" span={2}>
                <Paragraph style={{ marginBottom: 0 }} ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}>
                  {profile.baseInfo.scope}
                </Paragraph>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        <Col xs={24} xl={9}>
          <Card
            bordered={false}
            style={{ height: "100%", borderRadius: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}
          >
            <SectionTitle title="资质与荣誉概览" />
            {profile.honors?.length > 0 ? (
              <Timeline
                items={profile.honors.slice(0, 8).map((item: any) => ({
                  color: "blue",
                  children: (
                    <>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {item.year}
                      </Text>
                      <div style={{ fontWeight: 500 }}>{item.name}</div>
                    </>
                  ),
                }))}
              />
            ) : (
              <Alert
                type="info"
                showIcon
                message="暂无高价值资质荣誉"
                description="当前企业在画像接口中没有同步到榜单或资质时间轴数据。"
              />
            )}
          </Card>
        </Col>
      </Row>

      <Card
        bordered={false}
        bodyStyle={{ padding: 0, backgroundColor: "transparent" }}
        style={{ borderRadius: 12, background: "transparent", boxShadow: "none" }}
      >
        <div
          style={{
            background: "#fff",
            borderRadius: 14,
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
            marginBottom: 16,
          }}
        >
          <Row>
            {TAB_CONFIG.map((tab) => {
              const isActive = activeTabKey === tab.key;
              return (
                <Col key={tab.key} flex={1} style={{ textAlign: "center" }}>
                  <div
                    onClick={() => setActiveTabKey(tab.key)}
                    style={{
                      cursor: "pointer",
                      height: 50,
                      lineHeight: "50px",
                      fontSize: 14,
                      fontWeight: isActive ? 700 : 500,
                      color: isActive ? COLORS.primary : "#333",
                      borderBottom: isActive
                        ? `3px solid ${COLORS.primary}`
                        : "3px solid transparent",
                      transition: "all 0.2s",
                    }}
                  >
                    {tab.label}
                  </div>
                </Col>
              );
            })}
          </Row>
        </div>

        <div>
          {activeTabKey === "basic" && <EnterpriseBasicInfoTab profile={profile} />}
          {activeTabKey === "risk" && renderRiskTab()}
          {activeTabKey === "operating" && renderOperationTab()}
          {activeTabKey === "ip" && renderIpTab()}
        </div>
      </Card>

      <Card
        bordered={false}
        style={{ borderRadius: 16, boxShadow: "0 1px 3px rgba(0,0,0,0.04)" }}
      >
        <SectionTitle title="企业综合评估" />
        <Row gutter={24} style={{ marginTop: 8 }}>
          <Col
            xs={24}
            xl={14}
            style={{
              borderRight: !isMobile ? "1px solid #f0f0f0" : "none",
              paddingRight: !isMobile ? 24 : 0,
            }}
          >
            <Title level={5} style={{ fontSize: 14, marginBottom: 24, color: "#262626" }}>
              企业综合能力可视化
            </Title>
            <Row gutter={24} align="middle">
              <Col xs={24} md={10} style={{ textAlign: "center" }}>
                <Progress
                  type="dashboard"
                  percent={totalScorePercent}
                  strokeColor={COLORS.primary}
                  width={180}
                  format={(percent) => (
                    <div style={{ color: COLORS.primary }}>
                      <div style={{ fontSize: 32 }}>{totalScore}</div>
                      <div style={{ fontSize: 14, color: "#999" }}>{`${Math.round(percent || 0)}% / ${maxScore}`}</div>
                    </div>
                  )}
                />
                <div style={{ marginTop: 16 }}>
                  <Alert
                    message={scoreHealthy ? "经营稳健，潜力较强" : "仍需持续观察"}
                    type={scoreHealthy ? "success" : "warning"}
                    showIcon
                    style={{ display: "inline-flex", fontSize: 12, padding: "4px 12px" }}
                  />
                </div>
              </Col>
              <Col xs={24} md={14}>
                <Radar {...MAIN_RADAR_CONFIG(profile.overallRadar || [])} />
              </Col>
            </Row>
          </Col>

          <Col xs={24} xl={10} style={{ paddingLeft: !isMobile ? 24 : 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <Title level={5} style={{ fontSize: 14, margin: 0, color: "#262626" }}>
                企业迁出风险识别
              </Title>
              <ApartmentOutlined style={{ color: relocationRisk.color }} />
            </div>
            <div
              style={{
                background: "#fafafa",
                borderRadius: 12,
                padding: 20,
                border: "1px solid #f0f0f0",
              }}
            >
              <Row align="middle" gutter={16} style={{ marginBottom: 18 }}>
                <Col>
                  <Text type="secondary">当前风险等级：</Text>
                </Col>
                <Col>
                  <Tag
                    color={relocationRisk.color}
                    style={{ fontSize: 14, padding: "4px 12px", fontWeight: 700 }}
                  >
                    {relocationRisk.level}风险
                  </Tag>
                </Col>
                <Col flex="auto">
                  <Progress
                    percent={relocationRisk.score}
                    size="small"
                    strokeColor={relocationRisk.color}
                    showInfo={false}
                  />
                </Col>
              </Row>

              <Alert
                type={relocationRisk.level === "高" ? "error" : relocationRisk.level === "中" ? "warning" : "success"}
                showIcon
                message={relocationRisk.label}
                description="当前规则仅依据库内招聘数据构建；有招聘记录时，以在京招聘占比 >=60% 判低风险、30%-60% 判中风险、<30% 判高风险。"
                style={{ marginBottom: 16 }}
              />

              <Text strong style={{ fontSize: 12, color: "#999" }}>
                识别因子
              </Text>
              <List
                size="small"
                split={false}
                dataSource={relocationRisk.factors}
                renderItem={(item: any, index: number) => (
                  <List.Item style={{ padding: "10px 0", borderBottom: "1px dashed #e8e8e8" }}>
                    <Space style={{ width: "100%", alignItems: "flex-start" }}>
                      <Avatar
                        size={18}
                        style={{
                          backgroundColor:
                            item.impact === "High"
                              ? "#ffccc7"
                              : item.impact === "Medium"
                                ? "#ffe7ba"
                                : "#e6f4ff",
                          color:
                            item.impact === "High"
                              ? "#cf1322"
                              : item.impact === "Medium"
                                ? "#d46b08"
                                : "#1677ff",
                          fontSize: 10,
                        }}
                      >
                        {index + 1}
                      </Avatar>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                          <Text style={{ fontSize: 13 }}>{item.name}</Text>
                          <Space size={4}>
                            {item.impact !== "Low" ? (
                              <RiseOutlined style={{ color: relocationRisk.color, fontSize: 10 }} />
                            ) : null}
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {item.desc}
                            </Text>
                          </Space>
                        </div>
                      </div>
                    </Space>
                  </List.Item>
                )}
              />

              {riskOverview.length > 0 ? (
                <div style={{ marginTop: 16 }}>
                  <Text strong style={{ fontSize: 12, color: "#999" }}>
                    风险记录补充观察
                  </Text>
                  <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {riskOverview.map((item: { name: string; count: number }) => (
                      <Tag key={item.name} color="default" style={{ marginRight: 0 }}>
                        {item.name} {item.count}条
                      </Tag>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        <Col xs={24} md={8}>
          {renderSubModelCard(
            "企业基础评分",
            <BankOutlined style={{ color: COLORS.gold }} />,
            profile.models.basic,
            COLORS.gold,
          )}
        </Col>
        <Col xs={24} md={8}>
          {renderSubModelCard(
            "科技属性评分",
            <ExperimentOutlined style={{ color: COLORS.primary }} />,
            profile.models.tech,
            COLORS.primary,
          )}
        </Col>
        <Col xs={24} md={8}>
          {renderSubModelCard(
            "专业能力评分",
            <ThunderboltOutlined style={{ color: COLORS.green }} />,
            profile.models.ability,
            COLORS.green,
          )}
        </Col>
      </Row>

      <Modal
        title={ipDetailModal.title}
        open={ipDetailModal.open}
        onCancel={() =>
          setIpDetailModal({ open: false, title: "", columns: [], data: [] })
        }
        footer={null}
        width={960}
      >
        <Table
          rowKey="key"
          columns={ipDetailModal.columns}
          dataSource={ipDetailModal.data}
          pagination={{ pageSize: 10, hideOnSinglePage: true }}
          size="middle"
          scroll={{ x: 860 }}
          locale={{ emptyText: "暂无可展示的知识产权明细" }}
        />
      </Modal>
    </div>
  );
};

export default EnterpriseOverviewTab;
