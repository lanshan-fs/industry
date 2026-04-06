import React, { useState } from "react";
import {
  Row, Col, Typography, Space, Tag, Avatar, Descriptions, Table, Statistic, Progress, Timeline, Alert, Grid, List, Card, Button
} from "antd";
import {
  GlobalOutlined, EnvironmentOutlined, BankOutlined, ExperimentOutlined, ThunderboltOutlined, UserOutlined, WarningOutlined, RiseOutlined,
  DownOutlined, UpOutlined
} from "@ant-design/icons";
import { Radar } from "@ant-design/plots";

import EnterpriseBasicInfoTab from "./EnterpriseBasicInfoTab";
import ProfileListCard from "./ProfileListCard";

const { Title, Text } = Typography;
const { useBreakpoint } = Grid;

const COLORS = {
  primary: "#1890ff", gold: "#faad14", green: "#52c41a", bg: "#fff",
  borderColor: "#f0f0f0", textSecondary: "#666", riskHigh: "#ff4d4f",
};

const SectionTitle = ({ title }: { title: string }) => (
  <div style={{ display: 'flex', alignItems: 'center', fontSize: 16, fontWeight: 'bold', color: '#262626', marginBottom: 16 }}>
    <div style={{ width: 4, height: 16, backgroundColor: '#1890ff', borderRadius: 2, marginRight: 8 }} />
    {title}
  </div>
);

const MAIN_RADAR_CONFIG = (data: any[]) => ({
  data: data || [],
  xField: "item",
  yField: "score",
  area: { style: { fill: "l(90) 0:#1890ff 1:rgba(24,144,255,0.1)", fillOpacity: 0.4 } },
  line: { style: { stroke: "#1890ff", lineWidth: 2 } },
  point: { size: 3, shape: "circle", style: { fill: "#fff", stroke: "#1890ff", lineWidth: 2 } },
  scale: { y: { min: 0, max: 100, tickCount: 5 } },
  axis: { x: { grid: { line: { style: { stroke: "#eee" } } } } },
  height: 220,
});

const NEW_TAB_CONFIG = [
  { key: "basic", label: "基本信息" },
  { key: "risk", label: "经营风险" },
  { key: "operating", label: "经营信息" },
  { key: "ip", label: "知识产权" }
];

interface EnterpriseOverviewTabProps { profile: any; }

const EnterpriseOverviewTab: React.FC<EnterpriseOverviewTabProps> = ({ profile }) => {
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [activeTabKey, setActiveTabKey] = useState("basic");

  // ================= 新增：记录每个表格是否处于展开状态 =================
  const [expandedTabs, setExpandedTabs] = useState<Record<string, boolean>>({});
  const toggleExpand = (key: string) => {
    setExpandedTabs(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const renderPlaceholderTab = (title: string) => (
    <Card bordered={false} style={{ borderRadius: 8, minHeight: 300, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
      <Alert message={`此处展示${title}详细信息`} type="info" showIcon style={{ marginBottom: 24 }} />
      <ProfileListCard columns={[{ title: "项目", dataIndex: "name" }, { title: "详情", dataIndex: "desc" }]} data={[{ key: 1, name: "示例数据", desc: "暂无记录" }]} />
    </Card>
  );

  // ================= 1. 渲染经营风险表格 =================
  const renderRiskTab = () => {
    const isExpanded = expandedTabs['risk'];
    const fullData = profile.riskTableData || [];
    const displayData = isExpanded ? fullData : fullData.slice(0, 6); // 默认只显示前6行
    const hasMore = fullData.length > 6;

    const riskColumns = [
      { title: "风险维度", dataIndex: "item", key: "item", width: 200 },
      { 
        title: "是否存在记录", 
        dataIndex: "hasRisk", 
        key: "hasRisk",
        render: (text: string) => (
          <Tag color={text === "有记录" ? "error" : "success"}>{text}</Tag>
        )
      },
      { 
        title: "记录数量 (条)", 
        dataIndex: "count", 
        key: "count",
        render: (count: number) => (
          <Text style={{ color: count > 0 ? COLORS.riskHigh : COLORS.textSecondary, fontWeight: count > 0 ? "bold" : "normal" }}>
            {count}
          </Text>
        )
      }
    ];

    return (
      <Card bordered={false} style={{ borderRadius: 8, minHeight: 300, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ marginBottom: 20 }}>
          <Alert message="基于后端实时动态计算的企业风险全景图，涉及红线的风险项已高亮标出。" type="warning" showIcon />
        </div>
        
        <Table 
          columns={riskColumns} 
          dataSource={displayData} 
          pagination={false} 
          bordered
          size="middle"
          locale={{ emptyText: "暂无数据（请确认后端已成功返回风险信息）" }}
        />
        {hasMore && (
          <div style={{ textAlign: "center", marginTop: 16 }}>
            <Button type="link" onClick={() => toggleExpand('risk')} style={{ fontWeight: 500 }}>
              {isExpanded ? <><UpOutlined /> 收起表格</> : <><DownOutlined /> 展开剩余 {fullData.length - 6} 项</>}
            </Button>
          </div>
        )}
      </Card>
    );
  };

  // ================= 2. 渲染知识产权与资质表格 =================
  const renderIntellectualTab = () => {
    const isExpanded = expandedTabs['ip'];
    const fullData = profile.qualTableData || [];
    const displayData = isExpanded ? fullData : fullData.slice(0, 6);
    const hasMore = fullData.length > 6;

    const ipColumns = [
      { title: "资质/知识产权名称", dataIndex: "item", key: "item" },
      { 
        title: "认定状态", 
        dataIndex: "status", 
        key: "status",
        render: (text: string) => (
          <Tag color={text === "是" || text === "有" ? "blue" : "default"}>{text}</Tag>
        )
      },
      { 
        title: "数量", 
        dataIndex: "count", 
        key: "count",
        align: "center" as const
      }
    ];

    return (
      <Card bordered={false} style={{ borderRadius: 8, minHeight: 300, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ marginBottom: 16 }}>
          <SectionTitle title="资质荣誉与知识产权明细" />
        </div>
        <Table 
          columns={ipColumns} 
          dataSource={displayData} 
          pagination={false} 
          bordered
          size="middle"
          locale={{ emptyText: "暂无知识产权与资质数据" }}
        />
        {hasMore && (
          <div style={{ textAlign: "center", marginTop: 16 }}>
            <Button type="link" onClick={() => toggleExpand('ip')} style={{ fontWeight: 500 }}>
              {isExpanded ? <><UpOutlined /> 收起表格</> : <><DownOutlined /> 展开剩余 {fullData.length - 6} 项</>}
            </Button>
          </div>
        )}
      </Card>
    );
  };

  // ================= 3. 渲染企业经营信息表格 =================
  const renderOperationTab = () => {
    const isExpanded = expandedTabs['op'];
    const fullData = profile.operateTableData || [];
    const displayData = isExpanded ? fullData : fullData.slice(0, 6);
    const hasMore = fullData.length > 6;

    const opColumns = [
      { title: "经营信息维度", dataIndex: "item", key: "item", width: "40%" },
      { 
        title: "状态/内容", 
        dataIndex: "status", 
        key: "status",
        render: (text: string) => {
          if (text === "-") return <Text type="secondary">-</Text>;
          if (text === "是" || text === "有") return <Tag color="blue">{text}</Tag>;
          if (text === "否" || text === "无") return <Tag color="default">{text}</Tag>;
          return <Text>{text}</Text>; 
        }
      },
      { 
        title: "数量", 
        dataIndex: "count", 
        key: "count",
        align: "center" as const
      }
    ];

    return (
      <Card bordered={false} style={{ borderRadius: 8, minHeight: 300, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ marginBottom: 16 }}>
          <SectionTitle title="企业经营信息明细" />
        </div>
        <Table 
          columns={opColumns} 
          dataSource={displayData} 
          pagination={false} 
          bordered
          size="middle"
          locale={{ emptyText: "暂无经营信息数据" }}
        />
        {hasMore && (
          <div style={{ textAlign: "center", marginTop: 16 }}>
            <Button type="link" onClick={() => toggleExpand('op')} style={{ fontWeight: 500 }}>
              {isExpanded ? <><UpOutlined /> 收起表格</> : <><DownOutlined /> 展开剩余 {fullData.length - 6} 项</>}
            </Button>
          </div>
        )}
      </Card>
    );
  };

  const renderSubModelCard = (title: string, icon: React.ReactNode, modelData: any, color: string) => {
    const dataSource = modelData?.dimensions?.length > 0 
      ? modelData.dimensions 
      : [{ name: "核心权重指标", weight: 100, score: modelData?.score || 0 }];
    
    const columns: any[] = [
      { title: "评分维度", dataIndex: "name", ellipsis: true, align: "left", render: (t: string) => <Text style={{ fontSize: 13 }}>{t}</Text> },
      { title: "权重", dataIndex: "weight", width: 80, align: "center", render: (t: number) => <Tag style={{ marginRight: 0 }}>{t}%</Tag> },
      { title: "得分", dataIndex: "score", width: 80, align: "center", render: (s: number) => <Text strong style={{ color: s < 60 ? "red" : color }}>{s}</Text> },
    ];

    return (
      <Card bordered={false} bodyStyle={{ padding: 0 }} style={{ height: "100%", borderRadius: 8, overflow: "hidden", boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <div style={{ padding: "16px 20px", borderBottom: `1px solid ${COLORS.borderColor}`, display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "#fafafa" }}>
          <Space>{icon}<Text strong>{title}</Text></Space>
          <Statistic value={modelData?.score || 0} valueStyle={{ color: color, fontWeight: "bold", fontSize: 18 }} suffix={<span style={{ fontSize: 12, color: "#999" }}>分(总)</span>} />
        </div>
        <div style={{ flex: 1, padding: 0 }}>
          <Table dataSource={dataSource} rowKey="name" pagination={false} size="small" columns={columns} scroll={{ y: 250 }} bordered={false} />
        </div>
      </Card>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      
      <Card bordered={false} style={{ borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }} bodyStyle={{ padding: 24 }}>
        <Row gutter={24} align="middle">
          <Col flex="100px">
            <Avatar shape="square" size={88} style={{ backgroundColor: COLORS.primary, fontSize: 32, borderRadius: 8 }}>
              {profile.baseInfo.name?.charAt(0) || '企'}
            </Avatar>
          </Col>
          <Col flex="auto">
            <Space direction="vertical" size={6} style={{ width: "100%" }}>
              <Space align="center">
                <Title level={3} style={{ margin: 0 }}>{profile.baseInfo.name}</Title>
                <Tag color="success">在业</Tag>
                <Tag color="blue">{profile.baseInfo.type}</Tag>
              </Space>
              <Space size={24} style={{ color: COLORS.textSecondary }}>
                <span><UserOutlined /> 法人：{profile.baseInfo.legalPerson}</span>
                <span><EnvironmentOutlined /> 地址：{profile.baseInfo.address}</span>
                <span><GlobalOutlined /> 官网：{profile.baseInfo.website}</span>
              </Space>
              <Space style={{ marginTop: 8 }} wrap>
                {profile.tags?.map((t: string) => <Tag key={t} color="geekblue" style={{ border: 'none', background: '#e6f4ff', color: '#1677ff' }}>{t}</Tag>)}
              </Space>
            </Space>
          </Col>
          <Col flex="200px" style={{ textAlign: "right", borderLeft: "1px solid #f0f0f0", paddingLeft: 24 }}>
            <Statistic title="综合健康分" value={profile.metrics.totalScore} valueStyle={{ color: COLORS.primary, fontSize: 48, fontWeight: "bold", lineHeight: 1 }} suffix={<span style={{ fontSize: 16, color: "#999", fontWeight: 'normal' }}>/ 100</span>} />
            <div style={{ marginTop: 8 }}><Text type="secondary" style={{ fontSize: 12 }}>更新于：{profile.baseInfo.updateTime}</Text></div>
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        <Col xs={24} lg={16}>
          <Card bordered={false} style={{ height: '100%', borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <SectionTitle title="工商信息全景" />
            <Descriptions column={3} bordered size="small" labelStyle={{ width: 130, background: "#fafafa", color: '#666' }}>
              <Descriptions.Item label="统一信用代码">{profile.baseInfo.creditCode}</Descriptions.Item>
              <Descriptions.Item label="成立日期">{profile.baseInfo.establishDate}</Descriptions.Item>
              <Descriptions.Item label="企业类型">{profile.baseInfo.type}</Descriptions.Item>
              <Descriptions.Item label="注册资本">{profile.baseInfo.regCapital}</Descriptions.Item>
              <Descriptions.Item label="所属行业">{profile.baseInfo.industry}</Descriptions.Item>
              <Descriptions.Item label="参保人数">
                {profile.basicInfoData?.social?.[0]?.pension || "暂无数据"}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card bordered={false} style={{ height: '100%', borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
            <SectionTitle title="资质与荣誉概览" />
            {profile.honors?.length > 0 ? (
              <Timeline items={profile.honors.map((h: any) => ({
                color: "blue",
                children: (<><Text type="secondary" style={{ fontSize: 12 }}>{h.year}</Text><div style={{ fontWeight: 500 }}>{h.name}</div></>)
              }))} />
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', marginTop: 10 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', border: '2px solid #1890ff', marginRight: 8 }}></div>
                <span style={{ color: '#333', fontWeight: 'bold' }}>暂未获得特殊资质</span>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Card bordered={false} bodyStyle={{ padding: 0, backgroundColor: 'transparent' }} style={{ borderRadius: 8, background: 'transparent', boxShadow: 'none' }}>
        <div style={{ background: "#fff", borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.04)', marginBottom: 16 }}>
          <Row>
            {NEW_TAB_CONFIG.map((tab) => {
              const isActive = activeTabKey === tab.key;
              return (
                <Col key={tab.key} flex={1} style={{ textAlign: "center" }}>
                  <div 
                    onClick={() => setActiveTabKey(tab.key)} 
                    style={{ 
                      cursor: "pointer", 
                      height: 48, 
                      lineHeight: "48px", 
                      fontSize: 14, 
                      fontWeight: isActive ? 600 : 400, 
                      color: isActive ? COLORS.primary : "#333", 
                      borderBottom: isActive ? `3px solid ${COLORS.primary}` : "3px solid transparent", 
                      transition: "all 0.2s" 
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
          {activeTabKey === "ip" && renderIntellectualTab()}
        </div>
      </Card>

      <Card bordered={false} style={{ borderRadius: 8, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
        <SectionTitle title="企业综合评估" />
        <Row gutter={24} style={{ marginTop: 24 }}>
          <Col xs={24} lg={14} style={{ borderRight: !isMobile ? "1px solid #f0f0f0" : "none", paddingRight: !isMobile ? 24 : 0 }}>
            <Title level={5} style={{ fontSize: 14, marginBottom: 24, color: '#262626' }}>企业综合能力可视化</Title>
            <Row gutter={24} align="middle">
              <Col xs={24} md={10} style={{ textAlign: "center" }}>
                <Progress type="dashboard" percent={profile.metrics.totalScore} strokeColor={COLORS.primary} width={180} format={(percent) => (<div style={{ color: COLORS.primary }}><div style={{ fontSize: 32 }}>{percent}</div><div style={{ fontSize: 14, color: "#999" }}>综合得分</div></div>)} />
                <div style={{ marginTop: 16 }}>
                  <Alert 
                    message={profile.metrics.totalScore > 60 ? "经营稳健，潜力巨大" : "存在风险，需谨慎观察"} 
                    type={profile.metrics.totalScore > 60 ? "success" : "warning"} 
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
          <Col xs={24} lg={10} style={{ paddingLeft: !isMobile ? 24 : 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <Title level={5} style={{ fontSize: 14, margin: 0, color: '#262626' }}>关键风险因素监控</Title>
              <WarningOutlined style={{ color: "#faad14" }} />
            </div>
            <div style={{ background: "#fafafa", borderRadius: 8, padding: "20px", border: '1px solid #f0f0f0' }}>
              <Row align="middle" gutter={16} style={{ marginBottom: 20 }}>
                <Col><Text type="secondary">当前风险等级：</Text></Col>
                <Col><Tag color={profile.migrationRisk?.color || 'blue'} style={{ fontSize: 14, padding: "4px 12px", fontWeight: "bold" }}>{profile.migrationRisk?.level}风险</Tag></Col>
                <Col><Progress percent={profile.migrationRisk?.score || 0} size="small" status="normal" strokeColor={profile.migrationRisk?.color || 'blue'} style={{ width: 100 }} showInfo={false} /></Col>
              </Row>
              <Text strong style={{ fontSize: 12, color: "#999" }}>数据监控因子 (基于后端真实记录)</Text>
              <List
                size="small" split={false} dataSource={profile.riskOverview || []}
                renderItem={(item: any, index: number) => (
                  <List.Item style={{ padding: "8px 0", borderBottom: "1px dashed #e8e8e8" }}>
                    <Space style={{ width: "100%" }}>
                      <Avatar size={18} style={{ backgroundColor: item.count > 0 ? "#ffccc7" : "#e6f4ff", color: item.count > 0 ? "#cf1322" : "#1677ff", fontSize: 10 }}>{index + 1}</Avatar>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <Text style={{ fontSize: 13 }}>{item.name}</Text>
                          <Space size={4}>
                            {item.count > 0 && <RiseOutlined style={{ color: COLORS.riskHigh, fontSize: 10 }} />}
                            <Text type="secondary" style={{ fontSize: 12 }}>检测到 {item.count} 条记录</Text>
                          </Space>
                        </div>
                      </div>
                    </Space>
                  </List.Item>
                )}
              />
            </div>
          </Col>
        </Row>
      </Card>

      <Row gutter={16}>
        <Col xs={24} md={8}>{renderSubModelCard("企业基础评分", <BankOutlined style={{ color: COLORS.gold }} />, profile.models.basic, COLORS.gold)}</Col>
        <Col xs={24} md={8}>{renderSubModelCard("科技属性评分", <ExperimentOutlined style={{ color: COLORS.primary }} />, profile.models.tech, COLORS.primary)}</Col>
        <Col xs={24} md={8}>{renderSubModelCard("专业能力评分", <ThunderboltOutlined style={{ color: COLORS.green }} />, profile.models.ability, COLORS.green)}</Col>
      </Row>
    </div>
  );
};

export default EnterpriseOverviewTab;