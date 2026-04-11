import React, { useEffect, useMemo, useState } from "react";
import { Layout, Empty, Spin, Button, message, Space } from "antd";
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  ShareAltOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import dayjs from "dayjs";

import EnterpriseOverviewTab from "./components/EnterpriseOverviewTab";

const { Content } = Layout;

const EnterpriseProfile: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  const navigate = useNavigate();
  const location = useLocation();

  const queryParams = new URLSearchParams(location.search);
  const companyId = queryParams.get("id");
  const companyName = queryParams.get("company");
  const source = queryParams.get("from");
  const industryName = queryParams.get("industryName");

  useEffect(() => {
    const fetchProfile = async () => {
      const identifier = companyId || companyName;
      if (!identifier) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const search = companyId
          ? `id=${encodeURIComponent(companyId)}`
          : `company=${encodeURIComponent(companyName || "")}`;
        const response = await fetch(`/api/scoring/enterprise-profile/?${search}`);
        const json = await response.json();

        if (json.success && json.data) {
          setProfile(json.data);
        } else {
          message.warning("未找到该企业详细画像数据");
        }
      } catch (error) {
        console.error("Fetch profile error:", error);
        message.error("加载画像数据失败");
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [companyId, companyName]);

  const normalizedProfile = useMemo(() => {
    if (!profile) return null;

    const riskOverview =
      Array.isArray(profile.riskOverview) && profile.riskOverview.length > 0
        ? profile.riskOverview
        : (profile.riskTableData || [])
            .filter((item: any) => Number(item?.count || 0) > 0)
            .slice(0, 5)
            .map((item: any) => ({
              name: item.item,
              count: Number(item.count || 0),
            }));

    return {
      ...profile,
      baseInfo: {
        ...profile.baseInfo,
        updateTime: profile.baseInfo?.updateTime || dayjs().format("YYYY-MM-DD"),
      },
      riskOverview,
      tags: Array.isArray(profile.tags) ? profile.tags.filter(Boolean) : [],
      honors: Array.isArray(profile.honors) ? profile.honors : [],
    };
  }, [profile]);

  const handleExport = () => {
    window.print();
  };

  const handleShare = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      message.success("页面链接已复制");
    } catch (error) {
      console.error("Share failed:", error);
      message.error("复制链接失败");
    }
  };

  const handleReturn = () => {
    if (source === "industry-profile") {
      navigate(
        industryName
          ? `/industry-portrait/industry-profile?industryName=${encodeURIComponent(industryName)}`
          : "/industry-portrait/industry-profile",
      );
      return;
    }
    if (source === "industry-class") {
      navigate("/industry-class");
      return;
    }
    if (source === "enterprise-data") {
      navigate("/system-mgmt/enterprise-data");
      return;
    }
    navigate(-1);
  };

  const returnLabel =
    source === "industry-profile"
      ? "返回行业画像"
      : source === "industry-class"
        ? "返回行业分类"
        : source === "enterprise-data"
          ? "返回企业数据管理"
          : "返回上一页";

  if (loading) {
    return (
      <div style={{ textAlign: "center", marginTop: 200 }}>
        <Spin size="large" tip="企业全景画像加载中..." />
      </div>
    );
  }

  if (!normalizedProfile) {
    return (
      <div style={{ textAlign: "center", marginTop: 150 }}>
        <Empty description="未检索到企业多维数据" />
        <Button type="primary" onClick={() => navigate(-1)} style={{ marginTop: 16 }}>
          返回搜索
        </Button>
      </div>
    );
  }

  return (
    <Layout style={{ minHeight: "100vh", background: "#f5f7fa" }}>
      <div
        style={{
          background: "#ffffff",
          padding: "16px 24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid #e8e8e8",
        }}
      >
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={handleReturn}
          style={{ fontSize: 14, fontWeight: 600, color: "#333" }}
        >
          {returnLabel}
        </Button>
        <Space size="middle">
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            导出评估报告
          </Button>
          <Button
            icon={<ShareAltOutlined />}
            onClick={handleShare}
            style={{ color: "#1677ff", borderColor: "#1677ff" }}
          >
            分享结果
          </Button>
        </Space>
      </div>

      <Content
        id="enterprise-report-content"
        style={{ padding: "20px 24px", maxWidth: 1600, margin: "0 auto", width: "100%" }}
      >
        <EnterpriseOverviewTab profile={normalizedProfile} />
      </Content>
    </Layout>
  );
};

export default EnterpriseProfile;
