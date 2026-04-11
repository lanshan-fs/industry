import React from "react";
import { Descriptions, Tag, Button, message, Row, Col, Card, Empty, Table, Typography, Space } from "antd";
import { DownloadOutlined, ApartmentOutlined, TeamOutlined, UserOutlined } from "@ant-design/icons";

const { Text, Paragraph } = Typography;

interface EnterpriseBasicInfoTabProps {
  profile: any;
}

const SECTION_STYLE: React.CSSProperties = {
  padding: 24,
  marginBottom: 16,
  background: "#fff",
  borderRadius: 16,
  boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
  scrollMarginTop: 160,
};

const TITLE_STYLE: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  fontSize: 16,
  fontWeight: 700,
  color: "#333",
};

const titleMarkerStyle: React.CSSProperties = {
  width: 4,
  height: 16,
  backgroundColor: "#1890ff",
  borderRadius: 2,
  marginRight: 8,
};

const EnterpriseBasicInfoTab: React.FC<EnterpriseBasicInfoTabProps> = ({ profile }) => {
  const { baseInfo, basicInfoData } = profile;

  const shareholders = basicInfoData?.shareholders || [];
  const keyPersonnel = basicInfoData?.keyPersonnel || [];
  const branches = basicInfoData?.branches || [];

  const handleExport = (title: string) => {
    message.success(`正在导出${title}数据...`);
  };

  const renderHeader = (title: string, showExport: boolean = true) => (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 16,
      }}
    >
      <div style={TITLE_STYLE}>
        <div style={titleMarkerStyle} />
        {title}
      </div>
      {showExport ? (
        <Button
          type="link"
          icon={<DownloadOutlined />}
          size="small"
          onClick={() => handleExport(title)}
          style={{ paddingRight: 0, fontSize: 13 }}
        >
          导出数据
        </Button>
      ) : null}
    </div>
  );

  const renderOverviewChip = (label: string, value: React.ReactNode) => (
    <div
      style={{
        minHeight: 72,
        padding: "14px 16px",
        borderRadius: 14,
        background: "#fafafa",
        border: "1px solid #f0f0f0",
      }}
    >
      <Text type="secondary" style={{ fontSize: 12 }}>
        {label}
      </Text>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#262626", marginTop: 6 }}>{value || "-"}</div>
    </div>
  );

  const renderStructureCard = ({
    icon,
    title,
    count,
    columns,
    data,
    emptyText,
    helperText,
  }: {
    icon: React.ReactNode;
    title: string;
    count: number;
    columns: any[];
    data: any[];
    emptyText: string;
    helperText: string;
  }) => (
    <Card
      bordered={false}
      style={{
        height: "100%",
        borderRadius: 16,
        border: "1px solid #f0f0f0",
        boxShadow: "none",
      }}
      bodyStyle={{ padding: 0 }}
    >
      <div style={{ padding: "16px 18px 12px", borderBottom: "1px solid #f0f0f0" }}>
        <Space align="center" size={8}>
          <span style={{ fontSize: 16, color: "#1677ff" }}>{icon}</span>
          <Text strong>{title}</Text>
          <Tag color="blue" style={{ marginRight: 0 }}>
            {count} 条
          </Tag>
        </Space>
        <div style={{ marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12, lineHeight: 1.6 }}>
            {helperText}
          </Text>
        </div>
      </div>
      {data.length > 0 ? (
        <>
          <Table
            size="small"
            pagination={false}
            rowKey="key"
            columns={columns}
            dataSource={data.slice(0, 4)}
            locale={{ emptyText }}
          />
          {data.length > 4 ? (
            <div style={{ padding: "0 18px 16px" }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                仅展示前 4 条，完整数据可通过导出查看。
              </Text>
            </div>
          ) : null}
        </>
      ) : (
        <div style={{ padding: "28px 16px" }}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} />
        </div>
      )}
    </Card>
  );

  return (
    <div style={{ background: "transparent" }}>
      <div id="basic-business" style={SECTION_STYLE}>
        {renderHeader("工商信息", false)}

        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          <Col xs={12} lg={6}>
            {renderOverviewChip("法定代表人", baseInfo.legalPerson || "-")}
          </Col>
          <Col xs={12} lg={6}>
            {renderOverviewChip("经营状态", <Tag color="success">{baseInfo.status || "-"}</Tag>)}
          </Col>
          <Col xs={12} lg={6}>
            {renderOverviewChip("成立日期", baseInfo.establishDate || "-")}
          </Col>
          <Col xs={12} lg={6}>
            {renderOverviewChip("参保人数", baseInfo.insuredCount ? `${baseInfo.insuredCount} 人` : "-")}
          </Col>
        </Row>

        <Descriptions
          column={{ xxl: 2, xl: 2, lg: 2, md: 2, sm: 1, xs: 1 }}
          bordered
          size="small"
          labelStyle={{ background: "#fafafa", width: 160, color: "#666" }}
          contentStyle={{ color: "#333" }}
        >
          <Descriptions.Item label="注册资本">{baseInfo.regCapital || "-"}</Descriptions.Item>
          <Descriptions.Item label="实缴资本">{baseInfo.paidInCapital || "-"}</Descriptions.Item>
          <Descriptions.Item label="企业类型">{baseInfo.type || "-"}</Descriptions.Item>
          <Descriptions.Item label="所属行业">{baseInfo.industry || "-"}</Descriptions.Item>
          <Descriptions.Item label="统一社会信用代码">{baseInfo.creditCode || "-"}</Descriptions.Item>
          <Descriptions.Item label="纳税人识别号">{baseInfo.taxId || "-"}</Descriptions.Item>
          <Descriptions.Item label="核准日期">{baseInfo.approvedDate || "-"}</Descriptions.Item>
          <Descriptions.Item label="登记机关">{baseInfo.registrationAuthority || "-"}</Descriptions.Item>
          <Descriptions.Item label="注册地址" span={2}>
            {baseInfo.address || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="官网" span={2}>
            {baseInfo.website || "-"}
          </Descriptions.Item>
          <Descriptions.Item label="经营范围" span={2}>
            <Paragraph style={{ marginBottom: 0 }} ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}>
              {baseInfo.scope || "-"}
            </Paragraph>
          </Descriptions.Item>
        </Descriptions>
      </div>

      <div id="basic-structure" style={SECTION_STYLE}>
        {renderHeader("企业结构信息")}
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={8}>
            {renderStructureCard({
              icon: <TeamOutlined />,
              title: "股东信息",
              count: shareholders.length,
              columns: [
                { title: "股东名称", dataIndex: "name", ellipsis: true },
                { title: "持股比例", dataIndex: "ratio", width: 96, align: "center" as const },
              ],
              data: shareholders,
              emptyText: "库内暂未同步结构化股东信息",
              helperText: "当前展示已入库的结构化股东条目；若源侧未同步，这里会保持为空。",
            })}
          </Col>

          <Col xs={24} xl={8}>
            {renderStructureCard({
              icon: <UserOutlined />,
              title: "主要人员",
              count: keyPersonnel.length,
              columns: [
                { title: "姓名", dataIndex: "name", width: 120 },
                { title: "职务", dataIndex: "title", ellipsis: true },
              ],
              data: keyPersonnel,
              emptyText: "库内暂未同步主要人员名录",
              helperText:
                keyPersonnel.length <= 1
                  ? "当前后端主要同步法定代表人，因此这里通常较少，不代表企业实际人员结构为空。"
                  : "当前展示已同步的主要人员名录。",
            })}
          </Col>

          <Col xs={24} xl={8}>
            {renderStructureCard({
              icon: <ApartmentOutlined />,
              title: "分支机构",
              count: branches.length,
              columns: [
                { title: "机构名称", dataIndex: "name", ellipsis: true },
                { title: "负责人", dataIndex: "principal", width: 120, ellipsis: true },
              ],
              data: branches,
              emptyText: "库内暂未同步分支机构信息",
              helperText: "这里只保留与当前企业成功关联的分支机构记录，未匹配到时会为空。",
            })}
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default EnterpriseBasicInfoTab;
