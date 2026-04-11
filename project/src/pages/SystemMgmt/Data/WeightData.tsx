import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  InputNumber,
  Popconfirm,
  Progress,
  Row,
  Segmented,
  Slider,
  Space,
  Steps,
  Table,
  Typography,
  message,
} from "antd";
import {
  BulbOutlined,
  CheckCircleFilled,
  DatabaseOutlined,
  ExclamationCircleFilled,
  InfoCircleOutlined,
  PartitionOutlined,
  PieChartOutlined,
  RocketOutlined,
  SaveOutlined,
  TrophyOutlined,
  UndoOutlined,
} from "@ant-design/icons";
import * as echarts from "echarts";
import { getAuthToken } from "../../../utils/auth";

const { Title, Text } = Typography;

type ConfigLevel = "BASIC" | "TECH" | "PROFESSIONAL";

interface WeightItem {
  key: string;
  name: string;
  weight: number;
}

const LEVEL_EXPECTED_TOTALS: Record<ConfigLevel, number> = {
  BASIC: 100,
  TECH: 100,
  PROFESSIONAL: 100,
};

const WeightData: React.FC = () => {
  const [level, setLevel] = useState<ConfigLevel>("BASIC");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [scoring, setScoring] = useState(false);
  const [dataMap, setDataMap] = useState<Record<ConfigLevel, WeightItem[]>>({
    BASIC: [],
    TECH: [],
    PROFESSIONAL: [],
  });

  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const timerRef = useRef<number | null>(null);

  const theme = useMemo(() => {
    const maps = {
      BASIC: { color: "#5B8FF9", icon: <DatabaseOutlined />, label: "基础指标" },
      TECH: { color: "#5AD8A6", icon: <BulbOutlined />, label: "科技指标" },
      PROFESSIONAL: { color: "#F6BD16", icon: <TrophyOutlined />, label: "专业指标" },
    };
    return maps[level];
  }, [level]);

  const getCleanToken = () => {
    return getAuthToken();
  };

  const fetchAllWeights = async (isReset = false) => {
    setLoading(true);
    try {
      const res = await fetch("/api/weights/all/", {
        headers: { Authorization: `Bearer ${getCleanToken()}` },
      });
      const result = await res.json();
      if (result.success) {
        setDataMap({
          BASIC: result.data.basic || [],
          TECH: result.data.tech || [],
          PROFESSIONAL: result.data.professional || [],
        });
        if (isReset) {
          message.success("数据已同步至最新保存版本");
        }
      } else {
        message.error(result.message || "获取权重数据失败");
      }
    } catch {
      message.error("网络连接异常");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchAllWeights();
  }, []);

  const currentData = useMemo(() => dataMap[level] || [], [dataMap, level]);
  const expectedTotal = LEVEL_EXPECTED_TOTALS[level];
  const currentSum = useMemo(() => {
    const sum = currentData.reduce((acc, cur) => acc + (Number(cur.weight) || 0), 0);
    return parseFloat(sum.toFixed(2));
  }, [currentData]);
  const currentBalanced = useMemo(() => Math.abs(currentSum - expectedTotal) < 0.01, [currentSum, expectedTotal]);

  const handleWeightChange = (key: string, val: number | null) => {
    const newData = currentData.map((item) => (item.key === key ? { ...item, weight: val || 0 } : item));
    setDataMap((prev) => ({ ...prev, [level]: newData }));
  };

  const handleAutoBalance = () => {
    if (currentData.length === 0) {
      return;
    }
    const avg = Math.floor(expectedTotal / currentData.length);
    const remainder = expectedTotal - (avg * currentData.length);
    const balanced = currentData.map((item, index) => ({ ...item, weight: index === 0 ? avg + remainder : avg }));
    setDataMap((prev) => ({ ...prev, [level]: balanced }));
    message.info("已按数量平均分配权重");
  };

  const saveAction = async (targetLevel: ConfigLevel, data: WeightItem[]) => {
    const res = await fetch("/api/weights/update/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getCleanToken()}`,
      },
      body: JSON.stringify({ level: targetLevel, data }),
    });
    return await res.json();
  };

  const handleSave = async () => {
    if (!currentBalanced) {
      message.error(`当前分组总值必须为 ${expectedTotal}（当前 ${currentSum}）`);
      return;
    }
    setSaving(true);
    try {
      const result = await saveAction(level, currentData);
      if (result.success) {
        message.success(`${theme.label}保存成功`);
        void fetchAllWeights();
      } else {
        message.error(result.message || "保存失败");
      }
    } catch {
      message.error("服务器响应异常");
    } finally {
      setSaving(false);
    }
  };

  const stopPolling = (type: "success" | "error", errorMsg?: string) => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setScoring(false);
    message.destroy("scoring_task");
    if (type === "success") {
      message.success({ content: errorMsg || "评分任务已完成", duration: 4 });
    } else {
      message.error(errorMsg || "评分任务失败");
    }
  };

  const startPolling = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
    }
    timerRef.current = window.setInterval(async () => {
      try {
        const res = await fetch("/api/weights/status/", {
          headers: { Authorization: `Bearer ${getCleanToken()}` },
        });
        const data = await res.json();
        if (data.status === "completed") {
          stopPolling("success", data.message || "评分任务已完成");
        } else if (String(data.status).startsWith("failed")) {
          stopPolling("error", data.message || data.status);
        }
      } catch {
        stopPolling("error", "状态轮询失败");
      }
    }, 1500);
  };

  const handleRunScoring = async () => {
    if (!currentBalanced) {
      message.error("当前权重不平衡，无法开始评分");
      return;
    }
    setScoring(true);
    message.loading({ content: "启动评分任务...", key: "scoring_task", duration: 0 });
    try {
      const saveResult = await saveAction(level, currentData);
      if (!saveResult.success) {
        setScoring(false);
        message.error({ content: saveResult.message || "保存失败", key: "scoring_task" });
        return;
      }

      const res = await fetch("/api/weights/run/", {
        method: "POST",
        headers: { Authorization: `Bearer ${getCleanToken()}` },
      });
      const result = await res.json();
      if (result.success) {
        startPolling();
      } else {
        setScoring(false);
        message.error({ content: result.message || "启动失败", key: "scoring_task" });
      }
    } catch {
      setScoring(false);
      message.error({ content: "评分请求异常", key: "scoring_task" });
    }
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current) {
      return;
    }
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    chartInstance.current.setOption({
      tooltip: { trigger: "item", formatter: "{b}: <b style='color:#1890ff'>{c}%</b>" },
      legend: { bottom: "0%", left: "center", type: "scroll" },
      series: [
        {
          name: theme.label,
          type: "pie",
          radius: ["40%", "65%"],
          center: ["50%", "40%"],
          itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
          data: currentData.map((item) => ({ value: item.weight, name: item.name })),
          color: [theme.color, "#5B8FF9", "#5AD8A6", "#F6BD16", "#E8684A", "#6DC8EC", "#9270CA"],
        },
      ],
    });
  }, [currentData, theme]);

  return (
    <div style={{ padding: 24, background: "#f0f2f5", minHeight: "100vh" }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {(["BASIC", "TECH", "PROFESSIONAL"] as ConfigLevel[]).map((itemLevel) => {
          const items = dataMap[itemLevel] || [];
          const sum = items.reduce((acc, item) => acc + (Number(item.weight) || 0), 0);
          const expected = LEVEL_EXPECTED_TOTALS[itemLevel];
          const balanced = Math.abs(sum - expected) < 0.01;
          const active = level === itemLevel;
          return (
            <Col span={8} key={itemLevel}>
              <Card
                size="small"
                hoverable
                onClick={() => setLevel(itemLevel)}
                style={{
                  cursor: "pointer",
                  borderRadius: 8,
                  borderTop: active ? `4px solid ${theme.color}` : "4px solid transparent",
                  transition: "all 0.3s",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {itemLevel} 配置状态
                  </Text>
                  {balanced ? <CheckCircleFilled style={{ color: "#52c41a" }} /> : <ExclamationCircleFilled style={{ color: "#ff4d4f" }} />}
                </div>
                <Title level={3} style={{ margin: "8px 0" }}>
                  {sum} / {expected}
                </Title>
                <Progress percent={Math.min(100, Number(((sum / expected) * 100).toFixed(2)))} size="small" showInfo={false} status={balanced ? "success" : "exception"} />
              </Card>
            </Col>
          );
        })}
      </Row>

      <Row gutter={24}>
        <Col span={14}>
          <Card title={<Space>{theme.icon}<Text strong>{theme.label}详细配置</Text></Space>} styles={{ body: { padding: 20 } }}>
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message="当前总分规则"
              description="总分 = 基础评分 + 科技评分 + 专业评分 + 附加分。TOTAL 总权重已停用；科技附加分 55 分不在本页配置。"
            />
            <Segmented
              block
              value={level}
              onChange={(value) => setLevel(value as ConfigLevel)}
              options={["BASIC", "TECH", "PROFESSIONAL"]}
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
                { title: "指标项", dataIndex: "name", key: "name", width: "35%" },
                {
                  title: `配置值（目标合计 ${expectedTotal}）`,
                  key: "weight",
                  render: (_value, record: WeightItem) => (
                    <Row gutter={16} align="middle">
                      <Col span={14}>
                        <Slider min={0} max={Math.max(expectedTotal, 100)} value={record.weight} onChange={(value) => handleWeightChange(record.key, value)} />
                      </Col>
                      <Col span={10}>
                        <InputNumber
                          min={0}
                          max={Math.max(expectedTotal, 100)}
                          value={record.weight}
                          onChange={(value) => handleWeightChange(record.key, value)}
                        />
                      </Col>
                    </Row>
                  ),
                },
              ]}
            />

            <Divider />

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <Space>
                <Button icon={<UndoOutlined />} onClick={() => void fetchAllWeights(true)}>
                  重置
                </Button>
                <Button icon={<PartitionOutlined />} onClick={handleAutoBalance}>
                  平均分配
                </Button>
              </Space>
              <Space>
                <Button icon={<SaveOutlined />} onClick={() => void handleSave()} loading={saving}>
                  保存当前权重
                </Button>
                <Popconfirm
                  title="确认执行评分？"
                  description="这会先保存当前配置，再触发基于 Django 评分引擎的全量重算。"
                  onConfirm={() => void handleRunScoring()}
                  disabled={!currentBalanced || scoring}
                >
                  <Button type="primary" danger icon={<RocketOutlined />} loading={scoring} disabled={!currentBalanced}>
                    {scoring ? "执行中..." : "保存并执行评分"}
                  </Button>
                </Popconfirm>
              </Space>
            </div>
          </Card>
        </Col>

        <Col span={10}>
          <Card title={<Space><InfoCircleOutlined />操作指引</Space>} size="small" style={{ marginBottom: 16 }}>
            <Steps
              direction="vertical"
              size="small"
              current={currentBalanced ? 2 : 1}
              status={currentSum > expectedTotal ? "error" : "process"}
              items={[
                { title: "切换指标维度", description: "点击上方卡片或分段控制器切换需要调整的指标组" },
                { title: "调整权重比例", description: `拖动滑块或输入数值。当前总计：${currentSum} (目标${expectedTotal})` },
                { title: "执行任务控制", description: "权重配平后，点击下方保存或评分按钮应用更改" },
              ]}
            />
          </Card>

          <Card title={<Space><PieChartOutlined />权重分布预览</Space>}>
            <div ref={chartRef} style={{ height: 320, width: "100%" }} />
            <div style={{ marginTop: 16 }}>
              <Alert
                message="合规性检查"
                type={currentBalanced ? "success" : "warning"}
                showIcon
                description={
                  currentBalanced
                    ? `配置已达到目标合计 ${expectedTotal}，可以保存并执行全量评分。`
                    : `当前总值为 ${currentSum}，请调整至 ${expectedTotal} 后再进行保存。`
                }
              />
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default WeightData;
