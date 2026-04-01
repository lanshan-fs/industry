import React, { useState, useEffect } from "react";
import {
  Typography,
  Checkbox,
  Button,
  Tag,
  Space,
  message,
  Row,
  Col,
  TreeSelect,
  Spin,
  theme,
} from "antd";
import {
  DeleteOutlined,
  SaveOutlined,
  SearchOutlined,
  FilterOutlined,
  DownOutlined,
  UpOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
// 引入类型定义
import { FILTER_CONFIG, type FilterGroup } from "./constants";

const { Title, Text } = Typography;

const AdvancedSearch: React.FC = () => {
  const navigate = useNavigate();
  const { token } = theme.useToken();

  // 状态管理
  const [selectedFilters, setSelectedFilters] = useState<
    Record<string, string[]>
  >({});
  const [metaData, setMetaData] = useState<any>({
    dictionary: {},
    industryTree: [],
    scenarios: [],
    regions: { street: [], area: [] },
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(
    {},
  );

  // 初始化数据
  useEffect(() => {
    const fetchMetaData = async () => {
      try {
        const res = await fetch("/api/meta/all");
        const json = await res.json();
        if (json.success) {
          setMetaData(json.data);
        } else {
          message.error("加载筛选数据失败");
        }
      } catch (error) {
        console.error("Fetch meta error", error);
      } finally {
        setLoading(false);
      }
    };
    fetchMetaData();
  }, []);

  // 获取选项数据
  const getOptionsForGroup = (group: FilterGroup) => {
    if (group.sourceType === "static") return group.options || [];
    if (group.sourceType === "dictionary") {
      return (metaData.dictionary[group.sourceKey!] || []).map(
        (i: any) => i.value,
      );
    }
    if (group.sourceType === "list" && group.sourceKey === "scenario") {
      return metaData.scenarios.map((s: any) => s.value);
    }
    if (group.sourceType === "region") {
      return (metaData.regions[group.sourceKey!] || []).map(
        (r: any) => r.value,
      );
    }
    return [];
  };

  const handleFilterChange = (key: string, values: string[]) => {
    setSelectedFilters((prev) => {
      const newState = { ...prev, [key]: values };
      if (!values || values.length === 0) {
        delete newState[key];
      }
      return newState;
    });
  };

  const handleSingleOptionToggle = (
    key: string,
    option: string,
    checked: boolean,
  ) => {
    const current = selectedFilters[key] || [];
    const nextValues = checked
      ? Array.from(new Set([...current, option]))
      : current.filter((item) => item !== option);
    handleFilterChange(key, nextValues);
  };

  const toggleGroupExpanded = (key: string) => {
    setExpandedGroups((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleClear = () => {
    setSelectedFilters({});
    message.info("已清空所有条件");
  };

  const handleSave = () => {
    if (Object.keys(selectedFilters).length === 0) {
      message.warning("请先选择筛选条件");
      return;
    }
    message.success("筛选条件保存成功 (模拟)");
  };

  const handleSearch = () => {
    const params = new URLSearchParams();
    params.set("advanced", "true");
    params.set("filterData", JSON.stringify(selectedFilters));
    navigate(`/industry-class?${params.toString()}`);
  };

  // 渲染筛选内容行
  const renderFilterRow = (group: FilterGroup) => {
    // 行业分类：树选择器
    if (group.component === "treeSelect" && group.sourceKey === "industry") {
      return (
        <TreeSelect
          treeData={metaData.industryTree}
          value={selectedFilters[group.key]}
          onChange={(val) => handleFilterChange(group.key, val)}
          treeCheckable
          showCheckedStrategy={TreeSelect.SHOW_PARENT}
          placeholder="请选择行业分类 (支持多选)"
          style={{ width: "100%", maxWidth: 500 }}
          maxTagCount={3}
          allowClear
          treeDefaultExpandAll={false}
          size="middle"
          variant="filled" // 填充模式，更有质感
        />
      );
    }

    const options = getOptionsForGroup(group);
    const isManyOptions = options.length > 12;
    const isExpanded = !!expandedGroups[group.key];
    const visibleOptions = isExpanded ? options : options.slice(0, 12);

    return (
      <div style={{ padding: "2px 0" }}>
        {options.length > 0 ? (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: 10,
              }}
            >
              {visibleOptions.map((option: string) => {
                const checked = (selectedFilters[group.key] || []).includes(
                  option,
                );
                return (
                  <div
                    key={option}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      minHeight: 40,
                      padding: "8px 10px",
                      borderRadius: 10,
                      border: checked
                        ? `1px solid ${token.colorPrimary}`
                        : `1px solid ${token.colorBorderSecondary}`,
                      background: checked ? token.colorPrimaryBg : "#fafafa",
                      transition: "all 0.2s ease",
                    }}
                  >
                    <Checkbox
                      checked={checked}
                      onChange={(event) =>
                        handleSingleOptionToggle(
                          group.key,
                          option,
                          event.target.checked,
                        )
                      }
                    >
                      <span
                        style={{
                          fontSize: 13,
                          lineHeight: 1.5,
                          wordBreak: "break-word",
                        }}
                      >
                        {option}
                      </span>
                    </Checkbox>
                  </div>
                );
              })}
            </div>
            {isManyOptions && (
              <Button
                type="link"
                size="small"
                onClick={() => toggleGroupExpanded(group.key)}
                style={{ padding: 0, marginTop: 10, fontSize: 12 }}
              >
                {isExpanded ? "收起" : `展开剩余 ${options.length - 12} 项`}{" "}
                {isExpanded ? <UpOutlined /> : <DownOutlined />}
              </Button>
            )}
          </>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            暂无数据
          </Text>
        )}
      </div>
    );
  };

  // 渲染大类区块
  const renderCategoryBlock = (
    category: (typeof FILTER_CONFIG)[0],
    index: number,
  ) => {
    const isLast = index === FILTER_CONFIG.length - 1;
    return (
      <div
        key={category.title}
        style={{
          borderBottom: isLast ? "none" : `1px solid ${token.colorSplit}`,
          backgroundColor: "#fff",
        }}
      >
        {/* 标题栏：使用渐变背景，增加色彩层次 */}
        <div
          style={{
            padding: "12px 32px", // 紧凑一些
            background: `linear-gradient(90deg, ${token.colorFillAlter} 0%, #ffffff 100%)`, // 渐变背景
            display: "flex",
            alignItems: "center",
          }}
        >
          {/* 左侧装饰条：高亮渐变 */}
          <div
            style={{
              width: 4,
              height: 16,
              background: `linear-gradient(to bottom, ${token.colorPrimary}, ${token.colorPrimaryActive})`,
              marginRight: 12,
              borderRadius: 2,
            }}
          ></div>
          <Text strong style={{ fontSize: 15, color: token.colorTextHeading }}>
            {category.title}
          </Text>
        </div>

        {/* 内容区 */}
        <div style={{ padding: "16px 32px 24px 32px" }}>
          {category.groups.map((group, gIndex) => (
            <Row
              key={group.key}
              gutter={24}
              align="top"
              style={{
                marginTop: gIndex > 0 ? 16 : 0, // 适中的行间距
              }}
            >
              <Col
                flex="110px" // 加宽一点，适应大字号
                style={{
                  textAlign: "right",
                  color: token.colorText, // 改用主文本色，加深
                  fontWeight: 500,
                  paddingTop: 3, // 微调对齐
                  fontSize: 15, // 增大字号
                }}
              >
                {group.name}
              </Col>
              <Col flex="auto">{renderFilterRow(group)}</Col>
            </Row>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div
      style={{
        minHeight: "100%",
        display: "flex",
        flexDirection: "column",
        background: "#fff",
      }}
    >
      {/* 顶部 Header：大气的渐变背景 */}
      <div
        style={{
          padding: "24px 32px",
          borderBottom: `1px solid ${token.colorSplit}`,
          // 顶部使用非常淡的品牌色渐变，打破纯白
          background: `linear-gradient(180deg, ${token.colorFillQuaternary} 0%, #ffffff 100%)`,
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <div>
            <Title
              level={4}
              style={{
                margin: 0,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <FilterOutlined style={{ color: token.colorPrimary }} />
              高级搜索
            </Title>
            <Text
              type="secondary"
              style={{ fontSize: 13, marginTop: 6, display: "block" }}
            >
              基于产业链全景数据，支持多维度组合筛选，精准定位目标企业。
            </Text>
          </div>
          <Space>
            <Button
              type="link"
              size="small"
              onClick={handleClear}
              style={{ color: token.colorTextSecondary }}
            >
              重置所有条件
            </Button>
          </Space>
        </div>
      </div>

      {/* 筛选内容区 */}
      <div style={{ flex: 1 }}>
        <Spin spinning={loading} tip="正在加载筛选配置...">
          {FILTER_CONFIG.map((category, index) =>
            renderCategoryBlock(category, index),
          )}
        </Spin>
      </div>

      {/* 底部吸底操作栏 */}
      <div
        style={{
          position: "sticky",
          bottom: 0,
          zIndex: 100,
          backgroundColor: "rgba(255, 255, 255, 0.9)", // 微透明
          backdropFilter: "blur(10px)", // 毛玻璃效果
          borderTop: `1px solid ${token.colorSplit}`,
          boxShadow: "0 -4px 16px rgba(0,0,0,0.06)",
          padding: "16px 32px",
        }}
      >
        <Row justify="space-between" align="middle" gutter={24}>
          <Col style={{ flex: 1, overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              <Text
                strong
                style={{ whiteSpace: "nowrap", paddingTop: 4, fontSize: 14 }}
              >
                已选条件：
              </Text>

              <div
                style={{
                  flex: 1,
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                  maxHeight: 68,
                  overflowY: "auto",
                  alignContent: "flex-start",
                  paddingRight: 4,
                }}
              >
                {Object.entries(selectedFilters).length > 0 ? (
                  Object.entries(selectedFilters).map(
                    ([key, values]) =>
                      values &&
                      values.length > 0 && (
                        <Tag
                          key={key}
                          color="blue"
                          closable
                          onClose={() => handleFilterChange(key, [])}
                          style={{
                            margin: 0,
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          <span
                            style={{
                              opacity: 0.6,
                              marginRight: 4,
                              fontSize: 12,
                            }}
                          >
                            {
                              FILTER_CONFIG.flatMap((c) => c.groups).find(
                                (g) => g.key === key,
                              )?.name
                            }
                            :
                          </span>
                          <strong>
                            {values.length > 3
                              ? `${values[0]} 等${values.length}项`
                              : values.join(", ")}
                          </strong>
                        </Tag>
                      ),
                  )
                ) : (
                  <Text
                    type="secondary"
                    style={{ paddingTop: 4, fontSize: 13 }}
                  >
                    暂无选择
                  </Text>
                )}
              </div>
            </div>
          </Col>

          <Col style={{ flexShrink: 0 }}>
            <Space size="middle">
              <Button icon={<DeleteOutlined />} onClick={handleClear}>
                清空
              </Button>
              <Button icon={<SaveOutlined />} onClick={handleSave}>
                保存条件
              </Button>
              <Button
                type="primary"
                icon={<SearchOutlined />}
                size="large"
                onClick={handleSearch}
                style={{
                  minWidth: 140,
                  background: `linear-gradient(90deg, ${token.colorPrimary} 0%, ${token.colorPrimaryActive} 100%)`,
                  border: "none",
                }}
              >
                查看结果
              </Button>
            </Space>
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default AdvancedSearch;
