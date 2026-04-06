import React, { useState, useEffect } from "react";
import { Layout, Empty, Spin, Button, message, Space } from "antd";
import { ArrowLeftOutlined, DownloadOutlined, ShareAltOutlined } from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import dayjs from "dayjs";

// 引入你的组件
import EnterpriseOverviewTab from "./components/EnterpriseOverviewTab";

const { Content } = Layout;

const EnterpriseProfile: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [profileData, setProfileData] = useState<any>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const queryParams = new URLSearchParams(location.search);
  const companyId = queryParams.get("id");

  useEffect(() => {
    const fetchAllData = async () => {
      if (!companyId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        // 1. 并发请求：获取企业详情接口 + 获取模型评分接口
        const [resDetail, resScore] = await Promise.all([
          fetch(`http://127.0.0.1:8000/api/companies/${companyId}/`),
          fetch(`http://127.0.0.1:8000/api/companies/recommend/?id=${companyId}`)
        ]);

        const jsonDetail = await resDetail.json();
        const jsonScore = await resScore.json();

        if (jsonDetail.code === 200 && jsonScore.code === 200) {
          const dbData = jsonDetail.data; 
          const scData = jsonScore.data;  

          const formatDate = (d: any) => d ? String(d).substring(0, 10) : "-";

          // ================= 【极度强韧的数据解析函数】 =================
          const getRiskStatus = (flag: any, count: any) => (Number(count) > 0 || flag == 1 || String(flag) === "1") ? "有记录" : "无";
          const getQualStatus = (flag: any, count?: any) => (Number(count) > 0 || flag == 1 || String(flag) === "1") ? "是" : "否";
          const getHaveStatus = (flag: any, count?: any) => (Number(count) > 0 || flag == 1 || String(flag) === "1") ? "有" : "无";
          const getCount = (count: any) => Number(count) > 0 ? Number(count) : 0;
          const getString = (val: any) => (val === null || val === undefined || val === '') ? "-" : String(val);
          
          // ================= 1. 组装经营风险表格数据 =================
          const risk = dbData.risk_info || {};
          const riskTableData = [
            { key: 1, item: "司法案件", hasRisk: getRiskStatus(risk.judicial_cases_count > 0, risk.judicial_cases_count), count: getCount(risk.judicial_cases_count) },
            { key: 2, item: "裁判文书", hasRisk: getRiskStatus(risk.has_legal_documents, risk.judgment_documents_count), count: getCount(risk.judgment_documents_count) },
            { key: 3, item: "失信被执行", hasRisk: getRiskStatus(risk.has_dishonest_executor, risk.dishonest_executor_count), count: getCount(risk.dishonest_executor_count) },
            { key: 4, item: "被执行人", hasRisk: getRiskStatus(risk.has_executor, risk.executor_count), count: getCount(risk.executor_count) },
            { key: 5, item: "限制高消费", hasRisk: getRiskStatus(risk.has_high_consumption_restriction, risk.high_consumption_restriction_count), count: getCount(risk.high_consumption_restriction_count) },
            { key: 6, item: "经营异常", hasRisk: getRiskStatus(risk.has_business_abnormal, risk.business_abnormal_count), count: getCount(risk.business_abnormal_count) },
            { key: 7, item: "行政处罚", hasRisk: getRiskStatus(risk.has_admin_penalty, risk.admin_penalty_count), count: getCount(risk.admin_penalty_count) },
            { key: 8, item: "环保处罚", hasRisk: getRiskStatus(risk.has_environmental_penalty, risk.environmental_penalty_count), count: getCount(risk.environmental_penalty_count) },
            { key: 9, item: "股权冻结", hasRisk: getRiskStatus(risk.has_equity_freeze, risk.equity_freeze_count), count: getCount(risk.equity_freeze_count) },
            { key: 10, item: "动产抵押", hasRisk: getRiskStatus(risk.has_chattel_mortgage, risk.chattel_mortgage_count), count: getCount(risk.chattel_mortgage_count) },
            { key: 11, item: "破产重整", hasRisk: getRiskStatus(risk.has_bankruptcy_restructuring, risk.bankruptcy_restructuring_count), count: getCount(risk.bankruptcy_restructuring_count) },
            { key: 12, item: "清算信息", hasRisk: getRiskStatus(risk.has_liquidation_info, risk.liquidation_info_count), count: getCount(risk.liquidation_info_count) },
          ];

          // ================= 2. 组装知识产权与资质表格数据 =================
          const qual = dbData.qualification_info || {};
          const qualTableData = [
            { key: 'q1', item: "是否有作品著作", status: getQualStatus(qual.has_work_copyright, qual.work_copyright_count), count: "-" },
            { key: 'q2', item: "作品著作权数量", status: "-", count: getCount(qual.work_copyright_count) },
            { key: 'q3', item: "是否有软件著作", status: getQualStatus(qual.has_software_copyright, qual.software_copyright_count), count: "-" },
            { key: 'q4', item: "软件著作权数量", status: "-", count: getCount(qual.software_copyright_count) },
            { key: 'q5', item: "是否是高新技术企业", status: getQualStatus(qual.is_high_tech), count: "-" },
            { key: 'q6', item: "是否是专精特新中小企业", status: getQualStatus(qual.is_srdi_sme), count: "-" },
            { key: 'q7', item: "是否是瞪羚企业", status: getQualStatus(qual.is_gazelle), count: "-" },
            { key: 'q8', item: "是否是科技型中小企业", status: getQualStatus(qual.is_tech_sme), count: "-" },
            { key: 'q9', item: "是否是雏鹰企业", status: getQualStatus(qual.is_eagle), count: "-" },
            { key: 'q10', item: "是否是专精特新小巨人", status: getQualStatus(qual.is_srdi_little_giant), count: "-" },
            { key: 'q11', item: "是否是创新型中小企业", status: getQualStatus(qual.is_innovative_sme), count: "-" },
            { key: 'q12', item: "是否是创新型企业", status: getQualStatus(qual.is_innovative_enterprise), count: "-" },
            { key: 'q13', item: "是否是企业技术中心", status: getQualStatus(qual.is_tech_center), count: "-" },
            { key: 'q14', item: "是否有专利", status: getQualStatus(qual.has_patent, qual.patent_count), count: "-" },
            { key: 'q15', item: "专利数量", status: "-", count: getCount(qual.patent_count) },
          ];

          // ================= 3. 新增：组装企业经营信息表格数据 =================
          const op = dbData.operation_info || {};
          const operateTableData = [
            { key: 'o1', item: "员工人数", status: getString(op.employee_count), count: "-" },
            { key: 'o2', item: "社保人数", status: "-", count: getCount(op.social_security_count) },
            { key: 'o3', item: "上市状态", status: getString(op.listing_status), count: "-" },
            { key: 'o4', item: "国标行业", status: getString(op.national_industry), count: "-" },
            { key: 'o5', item: "联系方式", status: getString(op.contact_info), count: "-" },
            { key: 'o6', item: "同企业电话", status: getString(op.same_company_phone), count: "-" },
            { key: 'o7', item: "邮箱（工商信息）", status: getString(op.email_business_y), count: "-" },
            { key: 'o8', item: "是否小微企业", status: getQualStatus(op.is_micro_small), count: "-" },
            { key: 'o9', item: "是否有变更信息", status: getHaveStatus(op.has_change_info), count: "-" },
            { key: 'o10', item: "是否为一般纳税人", status: getQualStatus(op.is_general_taxpayer), count: "-" },
            { key: 'o11', item: "有无融资信息", status: getHaveStatus(op.has_financing_info), count: "-" },
            { key: 'o12', item: "有无招投标", status: getHaveStatus(op.has_bidding, op.bidding_count), count: "-" },
            { key: 'o13', item: "招投标数量", status: "-", count: getCount(op.bidding_count) },
            { key: 'o14', item: "有无招聘", status: getHaveStatus(op.has_recruitment, op.recruitment_count), count: "-" },
            { key: 'o15', item: "招聘信息数量", status: "-", count: getCount(op.recruitment_count) },
            { key: 'o16', item: "是否有客户信息", status: getHaveStatus(op.has_customer_info, op.customer_count), count: "-" },
            { key: 'o17', item: "客户数量", status: "-", count: getCount(op.customer_count) },
            { key: 'o18', item: "是否有上榜榜单", status: getHaveStatus(op.has_ranking_list, op.ranking_list_count), count: "-" },
            { key: 'o19', item: "上榜榜单数量", status: "-", count: getCount(op.ranking_list_count) },
          ];

          const formattedData = {
            baseInfo: {
              name: dbData.company_name || "未命名企业",
              legalPerson: dbData.legal_representative || "-",
              establishDate: formatDate(dbData.establish_date),
              regCapital: dbData.register_capital || "-",
              type: dbData.company_type || "-",
              industry: dbData.industry_belong || "-",
              address: dbData.register_address || "-",
              creditCode: dbData.credit_code || "尚未公开",
              website: dbData.email_business || "暂无",
              score: scData.total_score || 0,
              updateTime: dayjs().format('YYYY-MM-DD'),
            },
            tags: [dbData.industry_belong, dbData.company_type, dbData.financing_round].filter(Boolean),
            metrics: { totalScore: scData.total_score || 0 },
            overallRadar: [
              { item: "基础信用", score: scData.radar_scores?.basic_credit || 0 },
              { item: "经营能力", score: scData.radar_scores?.operation || 0 },
              { item: "科技实力", score: scData.radar_scores?.tech_power || 0 },
              { item: "资本背景", score: scData.radar_scores?.capital || 0 },
              { item: "司法合规", score: scData.radar_scores?.compliance || 0 },
            ],
            models: {
              basic: { 
                score: scData.radar_scores?.basic_credit || 0, 
                dimensions: [
                  { name: "注册资本表现", weight: 60, score: scData.radar_scores?.basic_credit || 0 },
                  { name: "人员规模评定", weight: 40, score: 85 }
                ] 
              },
              tech: { 
                score: scData.radar_scores?.tech_power || 0, 
                dimensions: [
                  { name: "知识产权储备", weight: 70, score: scData.radar_scores?.tech_power || 0 },
                  { name: "研发认证资质", weight: 30, score: 75 }
                ] 
              },
              ability: { 
                score: scData.radar_scores?.operation || 0, 
                dimensions: [
                  { name: "分支机构规模", weight: 100, score: scData.radar_scores?.operation || 0 }
                ] 
              },
              compliance: scData.radar_scores?.compliance || 0
            },
            migrationRisk: {
              level: (scData.radar_scores?.compliance || 0) > 80 ? "低" : "高",
              color: (scData.radar_scores?.compliance || 0) > 80 ? "#52c41a" : "#ff4d4f",
              score: 100 - (scData.radar_scores?.compliance || 0),
              factors: [
                { name: "司法涉诉频率", desc: `检测到 ${dbData.risk_info?.judicial_cases_count || 0} 条案件`, impact: "High" },
                { name: "经营异常表现", desc: dbData.risk_info?.business_abnormal_count > 0 ? "存在异常记录" : "状态稳健", impact: "Low" }
              ]
            },
            riskOverview: [
              { name: "司法案件", count: dbData.risk_info?.judicial_cases_count || 0 },
              { name: "经营异常", count: dbData.risk_info?.business_abnormal_count || 0 },
              { name: "行政处罚", count: dbData.risk_info?.admin_penalty_count || 0 },
            ],
            honors: dbData.company_qualification ? [{ year: "2024", name: dbData.company_qualification }] : [],
            basicInfoData: {
              shareholders: dbData.shareholders_list || [],
              branches: dbData.branches_list || [],
              keyPersonnel: dbData.key_personnel_list || []
            },
            // 将组装好的三个表格数据全部传递下去
            riskTableData: riskTableData,
            qualTableData: qualTableData,
            operateTableData: operateTableData // <--- 新增传递经营信息
          };

          setProfileData(formattedData);
        } else {
          message.error("无法获取该企业的完整模型数据");
        }
      } catch (error) {
        console.error("Fetch Error:", error);
        message.error("连接后端评分模型失败，请检查 Django 服务");
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, [companyId]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", marginTop: 200 }}>
        <Spin size="large" tip="五维评分模型正在进行全景画像建模..." />
      </div>
    );
  }

  if (!profileData) {
    return (
      <div style={{ textAlign: "center", marginTop: 150 }}>
        <Empty description="未检索到企业多维数据" />
        <Button type="primary" onClick={() => navigate(-1)} style={{ marginTop: 16 }}>返回搜索</Button>
      </div>
    );
  }

  return (
    <Layout style={{ minHeight: "100vh", background: "#f5f7fa" }}>
      <div style={{
        background: "#ffffff",
        padding: "16px 24px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderBottom: "1px solid #e8e8e8",
      }}>
        <Button 
          type="text" 
          icon={<ArrowLeftOutlined />} 
          onClick={() => navigate(-1)} 
          style={{ fontSize: 14, fontWeight: 600, color: '#333' }}
        >
          返回企业列表
        </Button>
        <Space size="middle">
          <Button icon={<DownloadOutlined />}>导出评估报告</Button>
          <Button 
            icon={<ShareAltOutlined />} 
            style={{ color: '#1677ff', borderColor: '#1677ff' }}
          >
            分享结果
          </Button>
        </Space>
      </div>

      <Content style={{ padding: "20px 24px", maxWidth: 1600, margin: "0 auto", width: "100%" }}>
        <EnterpriseOverviewTab profile={profileData} />
      </Content>
    </Layout>
  );
};

export default EnterpriseProfile;