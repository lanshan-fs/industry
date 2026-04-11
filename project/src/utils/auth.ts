export type StoredUser = {
  id?: number;
  username?: string;
  realName?: string;
  role?: string;
  roleName?: string;
  role_name?: string;
  user_role?: string;
  domain?: string | null;
  organization?: string | null;
  isAdmin?: boolean;
  is_superuser?: boolean;
};

export function getStoredUser(): StoredUser {
  try {
    return JSON.parse(localStorage.getItem("user") || "{}");
  } catch {
    return {};
  }
}

export function setStoredUser(user: StoredUser) {
  localStorage.setItem("user", JSON.stringify(user));
}

export function getAuthToken(): string {
  const token = localStorage.getItem("token") || "";
  return token.trim().replace(/^["']+|["']+$/g, "");
}

function normalizeStoredRole(user: StoredUser): string {
  const rawRole =
    user.role ??
    user.user_role ??
    user.roleName ??
    user.role_name ??
    "";
  const normalized = String(rawRole).trim().toUpperCase();
  if (normalized === "系统管理员") {
    return "ADMIN";
  }
  return normalized;
}

export function isAdminUser(user: StoredUser | null | undefined): boolean {
  if (!user) {
    return false;
  }
  return (
    Boolean(user.isAdmin) ||
    Boolean(user.is_superuser) ||
    normalizeStoredRole(user) === "ADMIN" ||
    String(user.username || "").trim().toLowerCase() === "admin"
  );
}

export async function syncCurrentUserProfile(): Promise<StoredUser> {
  const token = getAuthToken();
  const stored = getStoredUser();
  if (!token) {
    return stored;
  }

  const response = await fetch("/api/auth/users/profile", {
    headers: { Authorization: `Bearer ${token}` },
  });
  const result = await response.json();
  if (!result.success) {
    return stored;
  }

  const profile = result.data || {};
  const nextUser: StoredUser = {
    ...stored,
    username: profile.user_name || stored.username,
    realName: stored.realName || profile.user_name || stored.username,
    role: profile.role || stored.role,
    roleName: profile.role_name || stored.roleName,
    organization: profile.organization || stored.organization,
    isAdmin: Boolean(profile.is_superuser) || String(profile.role || "").toUpperCase() === "ADMIN",
  };
  setStoredUser(nextUser);
  return nextUser;
}

export async function resolveAdminStatus(): Promise<boolean> {
  const stored = getStoredUser();
  if (isAdminUser(stored)) {
    return true;
  }
  try {
    const fresh = await syncCurrentUserProfile();
    return isAdminUser(fresh);
  } catch {
    return false;
  }
}
