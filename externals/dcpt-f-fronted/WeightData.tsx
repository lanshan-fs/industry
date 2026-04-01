import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Card, Row, Col, Button, Slider, Table, InputNumber, Typography, Space,
  Divider, Segmented, Progress, message, Alert, Popconfirm, Steps
} from "antd";
import {
  SaveOutlined, SafetyCertificateOutlined,
  CheckCircleFilled, ExclamationCircleFilled, UndoOutlined,
  DatabaseOutlined, BulbOutlined, TrophyOutlined, PartitionOutlined,
  PieChartOutlined, RocketOutlined, InfoCircleOutlined
} from "@ant-design/icons";
import * as echarts from "echarts";

const { Title, Text, Paragraph } = Typography;

// --- 类型定义 ---
type ConfigLevel = "TOTAL" | "BASIC" | "TECH" | "PROFESSIONAL";

interface WeightItem {
  key: string;
  name: string;
  weight: number;
}

const WeightData: React.FC = () => {
  const [level, setLevel] = useState<ConfigLevel>("TOTAL");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [dataMap, setDataMap] = useState<Record<ConfigLevel, WeightItem[]>>({
    TOTAL: [], BASIC: [], TECH: [], PROFESSIONAL: []
  });

  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // --- 主题配置 ---
  const theme = useMemo(() => {
    const maps = {
      TOTAL: { color: "#9270CA", icon: <SafetyCertificateOutlined />, label: "总权重" },
      BASIC: { color: "#5B8FF9", icon: <DatabaseOutlined />, label: "基础指标" },
      TECH: { color: "#5AD8A6", icon: <BulbOutlined />, label: "科技指标" },
      PROFESSIONAL: { color: "#F6BD16", icon: <TrophyOutlined />, label: "专业指标" }
    };
    return maps[level];
  }, [level]);

  // --- Token 清洗 ---
  const getCleanToken = () => {
    let token = localStorage.getItem("token") || "";
    return token.trim().replace(/^["']+|["']+$/g, '');
  };

  // --- 数据获取 ---
  const fetchAllWeights = async (isReset = false) => {
    setLoading(true);
    try {
      const token = getCleanToken();
      const res = await fetch("http://localhost:8000/api/weights/all/", {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const result = await res.json();
      if (result.success) {
        setDataMap({
          TOTAL: result.data.total || [],
          BASIC: result.data.basic || [],
          TECH: result.data.tech || [],
          PROFESSIONAL: result.data.professional || []
        });
        if (isReset) message.success("数据已同步至最新保存版本");
      }
    } catch (e) {
      message.error("网络连接异常");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAllWeights(); }, []);

  // --- 核心计算 ---
  const currentData = useMemo(() => dataMap[level] || [], [dataMap, level]);
  const currentSum = useMemo(() => {
    const sum = currentData.reduce((acc, cur) => acc + (Number(cur.weight) || 0), 0);
    return parseFloat(sum.toFixed(2));
  }, [currentData]);

  // --- 交互逻辑 ---
  const handleWeightChange = (key: string, val: number | null) => {
    const newData = currentData.map(item =>
      item.key === key ? { ...item, weight: val || 0 } : item
    );
    setDataMap(prev => ({ ...prev, [level]: newData }));
  };

  const handleAutoBalance = () => {
    if (currentData.length === 0) return;
    const avg = Math.floor(100 / currentData.length);
    const remainder = 100 % currentData.length;
    const balanced = currentData.map((d, i) => ({
      ...d, weight: i === 0 ? avg + remainder : avg
    }));
    setDataMap(prev => ({ ...prev, [level]: balanced }));
    message.info("已按数量平均分配权重");
  };

  const saveAction = async (targetLevel: ConfigLevel, data: WeightItem[]) => {
    const token = getCleanToken();
    const res = await fetch("http://localhost:8000/api/weights/update/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ level: targetLevel, data })
    });
    return await res.json();
  };

  const handleSave = async () => {
    if (currentSum !== 100) {
      message.error(`权重总和必须为100%（当前${currentSum}%）`);
      return;
    }
    setSaving(true);
    try {
      const result = await saveAction(level, currentData);
      if (result.success) {
        message.success(`${theme.label}保存成功`);
        fetchAllWeights();
      }
    } catch (e) {
      message.error("服务器响应异常");
    } finally {
      setSaving(false);
    }
  };

  // --- 轮询逻辑 ---
  const startPolling = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(async () => {
      try {
        const res = await fetch("http://localhost:8000/api/weights/status/");
        const data = await res.json();
        if (data.status === "completed") {
          stopPolling("success");
        } else if (data.status.startsWith("failed")) {
          stopPolling("error", data.status);
        }
      } catch (e) {
        console.error("状态轮询失败", e);
      }
    }, 3000);
  };

  const stopPolling = (type: "success" | "error", errorMsg?: string) => {
    if (timerRef.current) clearInterval(timerRef.current);
    setScoring(false);
    message.destroy();
    if (type === "success") {
      message.success({ content: "🎉 全量企业评分任务已完成！", duration: 5 });
    } else {
      message.error(`评分任务失败: ${errorMsg}`);
    }
  };

  const handleRunScoring = async () => {
    if (currentSum !== 100) {
      message.error("当前权重不平衡，无法开始评分");
      return;
    }
    setScoring(true);
    message.loading({ content: "启动评分引擎...", key: "scoring_task", duration: 0 });
    try {
      const token = getCleanToken();
      await saveAction(level, currentData);
      const res = await fetch("http://localhost:8000/api/weights/run/", {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      const result = await res.json();
      if (result.success) {
        startPolling();
      } else {
        setScoring(false);
        message.error({ content: "启动失败：" + result.message, key: "scoring_task" });
      }
    } catch (e) {
      setScoring(false);
      message.error({ content: "评分请求异常", key: "scoring_task" });
    }
  };

  useEffect(() => {
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, []);

  // --- ECharts 渲染 ---
  useEffect(() => {
    if (!chartRef.current) return;
    if (!chartInstance.current) chartInstance.current = echarts.init(chartRef.current);
    const option = {
      tooltip: { trigger: 'item', formatter: '{b}: <b style="color:#1890ff">{c}%</b>' },
      legend: { bottom: '0%', left: 'center', type: 'scroll' },
      series: [{
        name: theme.label,
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '40%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        data: currentData.map(d => ({ value: d.weight, name: d.name })),
        color: [theme.color, '#5B8FF9', '#5AD8A6', '#F6BD16', '#E8684A', '#6DC8EC', '#9270CA']
      }]
    };
    chartInstance.current.setOption(option);
  }, [currentData, theme]);

  return (
    <div style={{ padding: "24px", background: "#f0f2f5", minHeight: "100vh" }}>
      {/* 状态统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {(["TOTAL", "BASIC", "TECH", "PROFESSIONAL"] as ConfigLevel[]).map(lvl => {
          const items = dataMap[lvl] || [];
          const sum = items.reduce((a, b) => a + (Number(b.weight) || 0), 0);
          const active = level === lvl;
          return (
            <Col span={6} key={lvl}>
              <Card
                size="small" hoverable onClick={() => setLevel(lvl)}
                style={{
                  cursor: 'pointer', borderRadius: 8,
                  borderTop: active ? `4px solid ${theme.color}` : '4px solid transparent',
                  transition: 'all 0.3s'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>{lvl} 配置状态</Text>
                  {sum === 100 ? <CheckCircleFilled style={{color:'#52c41a'}}/> : <ExclamationCircleFilled style={{color:'#ff4d4f'}}/>}
                </div>
                <Title level={3} style={{ margin: '8px 0' }}>{sum}%</Title>
                <Progress percent={sum} size="small" showInfo={false} status={sum === 100 ? "success" : "exception"} />
              </Card>
            </Col>
          );
        })}
      </Row>

      <Row gutter={24}>
        {/* 左侧配置区 */}
        <Col span={14}>
          <Card
            title={<Space>{theme.icon} <Text strong>{theme.label}详细配置</Text></Space>}
            styles={{ body: { padding: '20px' } }}
          >
            <Segmented
              block value={level}
              onChange={(v) => setLevel(v as ConfigLevel)}
              options={['TOTAL', 'BASIC', 'TECH', 'PROFESSIONAL']}
              style={{ marginBottom: 20 }}
            />

            <Table
              dataSource={currentData}
              rowKey="key"
              pagination={false}
              scroll={{ y: 400 }}
              size="middle"
              loading={loading}
              columns={[
                { title: '指标项', dataIndex: 'name', key: 'name', width: '35%' },
                {
                  title: '权重分配 (总计100%)',
                  key: 'weight',
                  render: (_, record) => (
                    <Row gutter={16} align="middle">
                      <Col span={14}>
                        <Slider min={0} max={100} value={record.weight} onChange={(v) => handleWeightChange(record.key, v)} />
                      </Col>
                      <Col span={10}>
                        <InputNumber min={0} max={100} value={record.weight} onChange={(v) => handleWeightChange(record.key, v as number)} formatter={v => `${v}%`} />
                      </Col>
                    </Row>
                  )
                }
              ]}
            />

            <Divider />

            {/* 底部操作工具栏 */}
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Space>
                <Button icon={<UndoOutlined />} onClick={() => fetchAllWeights(true)}>重置</Button>
                <Button icon={<PartitionOutlined />} onClick={handleAutoBalance}>平均分配</Button>
              </Space>
              <Space>
                <Button icon={<SaveOutlined />} onClick={handleSave} loading={saving}>保存当前权重</Button>
                <Popconfirm
                  title="确认执行评分？"
                  description="这将保存当前配置并重新计算所有企业分数。"
                  onConfirm={handleRunScoring}
                  disabled={currentSum !== 100 || scoring}
                >
                  <Button type="primary" danger icon={<RocketOutlined />} loading={scoring} disabled={currentSum !== 100}>
                    {scoring ? "计算中..." : "保存并执行评分"}
                  </Button>
                </Popconfirm>
              </Space>
            </div>
          </Card>
        </Col>

        {/* 右侧预览与指引区 */}
        <Col span={10}>
          {/* 操作步骤指引 */}
          <Card title={<Space><InfoCircleOutlined />操作指引</Space>} size="small" style={{ marginBottom: 16 }}>
            <Steps
              direction="vertical"
              size="small"
              current={currentSum === 100 ? 2 : 1}
              status={currentSum > 100 ? "error" : "process"}
              items={[
                {
                  title: '切换指标维度',
                  description: '点击上方卡片或分段控制器切换需要调整的指标组'
                },
                {
                  title: '调整权重比例',
                  description: `拖动滑块或输入数值。当前总计：${currentSum}% (目标100%)`,
                },
                {
                  title: '执行任务控制',
                  description: '权重配平后，点击下方“保存”或“评分”按钮应用更改'
                },
              ]}
            />
          </Card>

          <Card title={<Space><PieChartOutlined />权重分布预览</Space>}>
            <div ref={chartRef} style={{ height: 320, width: '100%' }} />
            <div style={{ marginTop: 16 }}>
              <Alert
                message="合规性检查"
                type={currentSum === 100 ? "success" : "warning"}
                showIcon
                description={currentSum === 100 ? "配置已达到 100%，可以执行评分。" : `当前总权重为 ${currentSum}%，请调整至 100% 后再进行保存。`}
              />
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default WeightData;