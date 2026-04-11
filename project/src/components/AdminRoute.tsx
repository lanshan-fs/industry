import React, { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { Result, Spin } from "antd";
import { resolveAdminStatus } from "../utils/auth";

const AdminRoute: React.FC = () => {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;
    void resolveAdminStatus().then((admin) => {
      if (!active) {
        return;
      }
      setIsAdmin(admin);
    });
    return () => {
      active = false;
    };
  }, []);

  if (isAdmin === null) {
    return (
      <div
        style={{
          minHeight: "calc(100vh - 64px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Spin size="large" tip="正在校验系统管理权限..." />
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <Result
        status="403"
        title="无权访问"
        subTitle="系统管理模块仅对系统管理员开放。"
      />
    );
  }

  return <Outlet />;
};

export default AdminRoute;
