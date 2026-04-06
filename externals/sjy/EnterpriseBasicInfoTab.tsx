import React from "react";
import { Descriptions, Tag, Button, message } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import ProfileListCard from "./ProfileListCard";

interface EnterpriseBasicInfoTabProps {
  profile: any;
}

const EnterpriseBasicInfoTab: React.FC<EnterpriseBasicInfoTabProps> = ({ profile }) => {
  const { baseInfo, basicInfoData } = profile;

  const SECTION_STYLE: React.CSSProperties = {
    padding: "24px",
    marginBottom: 16,
    background: "#fff",
    borderRadius: 8,
    boxShadow: "0 1px 4px rgba(0,0,0,0.05)",
    scrollMarginTop: 160 
  };

  const HEADER_STYLE: React.CSSProperties = {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 16,
  };

  const handleExport = (title: string) => {
    message.success(`正在导出${title}数据...`);
  };

  const renderHeader = (title: string, showExport: boolean = true) => (
    <div style={HEADER_STYLE}>
      <div style={{ display: 'flex', alignItems: 'center', fontSize: 16, fontWeight: 'bold', color: '#333' }}>
        <div style={{ width: 4, height: 16, backgroundColor: '#1890ff', borderRadius: 2, marginRight: 8 }} />
        {title}
      </div>
      {showExport && (
        <Button type="link" icon={<DownloadOutlined />} size="small" onClick={() => handleExport(title)} style={{ paddingRight: 0, fontSize: 13 }}>
          导出数据
        </Button>
      )}
    </div>
  );

  const renderBusinessInfo = () => (
    <div id="basic-business" style={SECTION_STYLE}>
      {renderHeader("工商信息", false)}
      <Descriptions column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }} bordered size="small" labelStyle={{ background: "#fafafa", width: 160, color: "#666" }} contentStyle={{ color: "#333" }}>
        <Descriptions.Item label="法定代表人">{baseInfo.legalPerson}</Descriptions.Item>
        <Descriptions.Item label="经营状态"><Tag color="success">{baseInfo.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="成立日期">{baseInfo.establishDate}</Descriptions.Item>
        <Descriptions.Item label="注册资本">{baseInfo.regCapital}</Descriptions.Item>
        <Descriptions.Item label="实缴资本">{baseInfo.paidInCapital}</Descriptions.Item>
        <Descriptions.Item label="企业类型">{baseInfo.type}</Descriptions.Item>
        <Descriptions.Item label="统一社会信用代码">{baseInfo.creditCode}</Descriptions.Item>
        <Descriptions.Item label="纳税人识别号">{baseInfo.taxId}</Descriptions.Item>
        <Descriptions.Item label="所属行业">{baseInfo.industry}</Descriptions.Item>
        <Descriptions.Item label="参保人数">219 人</Descriptions.Item>
        <Descriptions.Item label="核准日期">2023-11-15</Descriptions.Item>
        <Descriptions.Item label="登记机关">北京市朝阳区市场监督管理局</Descriptions.Item>
        <Descriptions.Item label="注册地址" span={3}>{baseInfo.address}</Descriptions.Item>
        <Descriptions.Item label="经营范围" span={3}>{baseInfo.scope}</Descriptions.Item>
      </Descriptions>
    </div>
  );

  const renderSection = (id: string, title: string, columns: any[], data: any[]) => (
    <div id={id} style={SECTION_STYLE}>
      {renderHeader(title, true)}
      <ProfileListCard columns={columns} data={data} />
    </div>
  );

  return (
    <div style={{ background: "transparent" }}>
      {renderBusinessInfo()}

      {renderSection(
        "basic-shareholder", "股东信息",
        [{ title: "股东名称", dataIndex: "name" }, { title: "持股比例", dataIndex: "ratio", align: "center", width: 120 }, { title: "认缴出资额", dataIndex: "capital", align: "right", width: 180 }],
        basicInfoData?.shareholders || []
      )}

      {renderSection(
        "basic-personnel", "主要人员",
        [{ title: "姓名", dataIndex: "name", width: 150 }, { title: "职务", dataIndex: "title" }],
        basicInfoData?.keyPersonnel || []
      )}

      {renderSection(
        "basic-branch", "分支机构",
        [{ title: "机构名称", dataIndex: "name" }, { title: "负责人", dataIndex: "principal", width: 120 }, { title: "成立日期", dataIndex: "date", width: 150 }],
        basicInfoData?.branches || []
      )}
    </div>
  );
};

export default EnterpriseBasicInfoTab;