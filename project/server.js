import express from "express";
import mysql from "mysql2/promise";
import cors from "cors";
import crypto from "crypto";
import dotenv from "dotenv";
import path from "path";
import { fileURLToPath } from "url";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import nodemailer from "nodemailer";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.join(__dirname, "../.env") });

const app = express();
const PORT = process.env.PORT || 3001;
const JWT_SECRET = process.env.JWT_SECRET || "chaoyang_industrial_secret_2026";
const AGENT_API_URL = process.env.AGENT_API_URL || "http://127.0.0.1:8001";
const FIXED_INVITE_CODE = "CY2026";
const DOMAIN_CONFIG = {
  digital_medical: { domainName: "数字医疗", userType: 1 },
  digital_wellness: { domainName: "数字康养", userType: 2 },
};

app.use(cors());
app.use(express.json());

async function agentRequest(agentPath, options = {}) {
  const response = await fetch(`${AGENT_API_URL}${agentPath}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const message = data.detail || data.message || `Agent request failed: ${response.status}`;
    throw new Error(message);
  }

  return data;
}

// --- 数据库连接池 ---
const pool = mysql.createPool({
  host: (process.env.DB_HOST || "localhost").replace(/\r/g, "").trim(),
  user: (process.env.DB_USER || "root").replace(/\r/g, "").trim(),
  password: (process.env.DB_PASSWORD || "").replace(/\r/g, "").trim(),
  database: (process.env.DB_NAME || "industrial_chain").replace(/\r/g, "").trim(),
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

// --- 邮件服务配置 ---
const codeCache = new Map();
const emailPort = parseInt(process.env.EMAIL_PORT) || 465;
const emailUser = (process.env.EMAIL_USER || "").replace(/\r/g, "").trim();
const emailPass = (process.env.EMAIL_PASS || "").replace(/\r/g, "").trim();
const transporter = nodemailer.createTransport({
  host: (process.env.EMAIL_HOST || "smtp.163.com").replace(/\r/g, "").trim(),
  port: emailPort,
  secure: emailPort === 465,
  auth: { user: emailUser, pass: emailPass },
  tls: { rejectUnauthorized: false },
  connectionTimeout: 3000,
  greetingTimeout: 3000,
  socketTimeout: 5000,
});

// ==========================================
// 1. 用户认证模块 (Auth)
// ==========================================

function normalizeText(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/\r/g, "").trim();
}

function getDomainConfig(domainKey) {
  return DOMAIN_CONFIG[normalizeText(domainKey)];
}

function buildAuthUser(row) {
  return {
    id: row.user_id,
    username: row.user_name,
    role: row.user_role || "user",
    realName: row.user_real_name || row.user_name,
    domain: row.domain_key || null,
    organization: row.organization || row.org_name || null,
  };
}

function makePasswordHash(password) {
  const iterations = 870000;
  const salt = crypto.randomBytes(16).toString("base64url");
  const digest = crypto.pbkdf2Sync(password, salt, iterations, 32, "sha256").toString("base64");
  return `pbkdf2_sha256$${iterations}$${salt}$${digest}`;
}

function timingSafeEqualText(left, right) {
  const leftBuffer = Buffer.from(left, "utf8");
  const rightBuffer = Buffer.from(right, "utf8");
  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }
  return crypto.timingSafeEqual(leftBuffer, rightBuffer);
}

async function verifyPasswordHash(password, passwordHash) {
  if (!passwordHash) {
    return false;
  }

  if (passwordHash.startsWith("pbkdf2_sha256$")) {
    const [algorithm, iterationsText, salt, expectedDigest] = passwordHash.split("$");
    if (algorithm !== "pbkdf2_sha256" || !iterationsText || !salt || !expectedDigest) {
      return false;
    }
    const iterations = Number.parseInt(iterationsText, 10);
    if (!Number.isFinite(iterations) || iterations <= 0) {
      return false;
    }
    const actualDigest = crypto.pbkdf2Sync(password, salt, iterations, 32, "sha256").toString("base64");
    return timingSafeEqualText(actualDigest, expectedDigest);
  }

  if (passwordHash.startsWith("$2a$") || passwordHash.startsWith("$2b$") || passwordHash.startsWith("$2y$")) {
    return bcrypt.compare(password, passwordHash);
  }

  return false;
}

function getBearerToken(req) {
  const authHeader = normalizeText(req.headers.authorization);
  if (!authHeader.toLowerCase().startsWith("bearer ")) {
    return null;
  }
  return authHeader.slice(7).trim();
}

function requireAuth(req, res, next) {
  const token = getBearerToken(req);
  if (!token) {
    return res.status(401).json({ success: false, message: "请先登录" });
  }

  try {
    const payload = jwt.verify(token, JWT_SECRET);
    req.authUser = {
      id: payload.id,
      username: payload.username,
      role: payload.role,
    };
    next();
  } catch {
    return res.status(401).json({ success: false, message: "登录状态已失效，请重新登录" });
  }
}

async function resolveDomainId(connection, domainKey) {
  const config = getDomainConfig(domainKey);
  if (!config) {
    throw new Error("所属领域无效");
  }

  const [rows] = await connection.query(
    "SELECT domain_id FROM user_domains WHERE domain_name = ? LIMIT 1",
    [config.domainName],
  );
  if (rows.length > 0) {
    return rows[0].domain_id;
  }

  const [result] = await connection.query(
    "INSERT INTO user_domains (domain_name, domain_description) VALUES (?, ?)",
    [config.domainName, `${config.domainName}用户领域`],
  );
  return result.insertId;
}

async function findAuthUserByUsername(username) {
  const [rows] = await pool.query(
    `
      SELECT
        u.user_id,
        u.user_name,
        u.password_hash,
        u.email,
        u.phone,
        u.organization,
        u.position,
        d.domain_name,
        CASE
          WHEN d.domain_name = '数字医疗' THEN 'digital_medical'
          WHEN d.domain_name = '数字康养' THEN 'digital_wellness'
          ELSE NULL
        END AS domain_key,
        u.user_nickname,
        u.user_type,
        u.is_superuser,
        u.user_role,
        u.date_joined,
        u.last_login_time,
        u.last_login_ip,
        u.password_update_time,
        u.user_real_name,
        u.org_name,
        u.org_id,
        u.dept_name,
        u.dept_id,
        u.user_status
      FROM users u
      LEFT JOIN user_domains d ON u.domain_id = d.domain_id
      WHERE u.user_name = ?
      LIMIT 1
    `,
    [username],
  );
  return rows[0] || null;
}

app.post("/api/auth/register", async (req, res) => {
  const username = normalizeText(req.body.username);
  const password = normalizeText(req.body.password);
  const email = normalizeText(req.body.email);
  const phone = normalizeText(req.body.phone);
  const company = normalizeText(req.body.company);
  const job = normalizeText(req.body.job);
  const inviteCode = normalizeText(req.body.inviteCode);
  const domainConfig = getDomainConfig(req.body.domain);

  if (!domainConfig) {
    return res.status(400).json({ success: false, message: "请选择有效的所属领域" });
  }
  if (!username || !password || !email || !phone || !company) {
    return res.status(400).json({ success: false, message: "请完整填写注册信息" });
  }
  if (inviteCode !== FIXED_INVITE_CODE) {
    return res.status(400).json({ success: false, message: "邀请码无效" });
  }

  let connection;
  try {
    connection = await pool.getConnection();
    await connection.beginTransaction();

    const [existingUsers] = await connection.query(
      "SELECT user_id, user_name, email, phone FROM users WHERE user_name = ? OR email = ? OR phone = ?",
      [username, email, phone],
    );
    if (existingUsers.length > 0) {
      await connection.rollback();
      return res.status(400).json({ success: false, message: "用户名、邮箱或手机号已存在" });
    }

    const domainId = await resolveDomainId(connection, req.body.domain);
    const hashedPassword = makePasswordHash(password);
    const now = new Date();

    await connection.query(
      `
        INSERT INTO users (
          user_name, password_hash, email, phone, organization, position, user_nickname,
          user_type, is_superuser, user_role, date_joined, password_update_time,
          user_real_name, org_name, dept_name, user_status, domain_id, registered_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'user', ?, ?, ?, ?, ?, 1, ?, ?)
      `,
      [
        username,
        hashedPassword,
        email,
        phone,
        company,
        job || null,
        username,
        domainConfig.userType,
        now,
        now,
        username,
        company,
        job || null,
        domainId,
        now,
      ],
    );

    await connection.commit();
    res.json({ success: true, message: "注册成功" });
  } catch (error) {
    if (connection) {
      await connection.rollback();
    }
    res.status(500).json({ success: false, message: error.message });
  } finally {
    connection?.release();
  }
});

app.post("/api/auth/login", async (req, res) => {
  const username = normalizeText(req.body.username);
  const password = normalizeText(req.body.password);
  const expectedDomain = getDomainConfig(req.body.domain);

  if (!username || !password) {
    return res.status(400).json({ success: false, message: "请输入用户名和密码" });
  }

  try {
    const user = await findAuthUserByUsername(username);
    if (!user) {
      return res.status(400).json({ success: false, message: "用户不存在" });
    }
    if (user.user_status === 0) {
      return res.status(403).json({ success: false, message: "账号已被禁用" });
    }
    if (expectedDomain) {
      const userDomainKey =
        user.domain_key ||
        (user.user_type === 1 ? "digital_medical" : user.user_type === 2 ? "digital_wellness" : null);
      if (userDomainKey && userDomainKey !== req.body.domain) {
        return res.status(400).json({ success: false, message: "所属领域与账号不匹配" });
      }
    }

    const isMatch = await verifyPasswordHash(password, user.password_hash);
    if (!isMatch) {
      return res.status(400).json({ success: false, message: "密码错误" });
    }

    await pool.query(
      `
        UPDATE users
        SET last_login_at = NOW(),
            last_login_time = NOW(),
            last_login_ip = ?,
            user_status = IF(user_status = 2, 1, user_status),
            updated_at = NOW()
        WHERE user_name = ?
      `,
      [req.ip, username],
    );

    const authUser = buildAuthUser(user);
    const token = jwt.sign(
      { id: authUser.id, username: authUser.username, role: authUser.role },
      JWT_SECRET,
      { expiresIn: "24h" },
    );

    res.json({ success: true, data: { token, user: authUser } });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.post("/api/auth/send-code", async (req, res) => {
  const username = normalizeText(req.body.username);
  const email = normalizeText(req.body.email);

  if (!username || !email) {
    return res.status(400).json({ success: false, message: "请输入用户名和绑定邮箱" });
  }

  try {
    const [rows] = await pool.query(
      `
        SELECT u.user_id
        FROM users u
        WHERE u.user_name = ? AND u.email = ?
        LIMIT 1
      `,
      [username, email],
    );
    if (rows.length === 0) {
      return res.status(400).json({ success: false, message: "用户名与绑定的邮箱不匹配" });
    }

    const code = Math.floor(100000 + Math.random() * 900000).toString();
    codeCache.set(username, { code, email, expire: Date.now() + 5 * 60 * 1000 });
    if (emailUser && emailPass) {
      try {
        await transporter.sendMail({
          from: `"朝阳产业链平台" <${emailUser}>`,
          to: email,
          subject: "【安全验证】找回您的登录密码",
          html: `<p>您好，您正在申请重置密码。</p><p>您的验证码是：<b>${code}</b></p><p>验证码 5 分钟内有效。</p>`,
        });
        return res.json({ success: true, message: "验证码已发送至您的邮箱" });
      } catch (error) {
        console.warn("sendMail failed, fallback to mock code:", error.message);
      }
    }
    res.json({ success: true, message: `(模拟) 验证码：${code}` });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.post("/api/auth/reset-password", async (req, res) => {
  const username = normalizeText(req.body.username);
  const code = normalizeText(req.body.code);
  const newPassword = normalizeText(req.body.newPassword);

  if (!username || !code || !newPassword) {
    return res.status(400).json({ success: false, message: "请完整填写重置信息" });
  }

  try {
    const cached = codeCache.get(username);
    if (!cached || cached.code !== code || Date.now() > cached.expire) {
      return res.status(400).json({ success: false, message: "验证码无效或已过期" });
    }
    const hashedPassword = makePasswordHash(newPassword);
    await pool.query(
      "UPDATE users SET password_hash = ?, password_update_time = NOW(), updated_at = NOW() WHERE user_name = ?",
      [hashedPassword, username],
    );
    codeCache.delete(username);
    res.json({ success: true, message: "密码重置成功" });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// ==========================================
// 2. 基础数据与元数据模块 (Meta)
// ==========================================

app.get("/api/meta/all", async (req, res) => {
  try {
    const [dictRows] = await pool.query("SELECT group_code, name FROM sys_dictionary ORDER BY sort_order");
    const dictionary = {};
    dictRows.forEach(row => { if (!dictionary[row.group_code]) dictionary[row.group_code] = []; dictionary[row.group_code].push({ label: row.name, value: row.name }); });
    
    const tagMapping = { 103: "PAID_CAPITAL", 104: "BIZ_STATUS", 105: "ENT_TYPE", 106: "ORG_TYPE", 108: "BRANCH_STATUS", 109: "ADDR_INFO", 110: "FINANCING", 201: "STAFF_RANGE", 202: "INSURED_RANGE", 203: "LISTING_STATUS", 204: "ABOVE_SCALE", 205: "CONTACT_TYPE", 206: "NUMBER_STATUS", 207: "EMAIL_STATUS", 208: "SMALL_MICRO", 209: "CHANGE_INFO", 210: "TAX_PAYER", 211: "FINANCING", 212: "BIDDING", 213: "RECRUITMENT", 214: "TAX_RATING", 215: "IMPORT_EXPORT", 216: "BANK_TYPE", 301: "PATENT_TYPE", 302: "TECH_ATTR", 303: "CERT_TYPE", 304: "IP_STATUS_TRADEMARK", 305: "IP_STATUS_PATENT", 306: "IP_STATUS_COPYRIGHT", 307: "IP_STATUS_SOFTWARE", 308: "IP_STATUS_HIGH_TECH", 309: "IP_STATUS_WECHAT", 310: "IP_STATUS_STANDARD", 311: "IP_STATUS_IC", 312: "IP_STATUS_CONST", 313: "IP_STATUS_WEB", 314: "IP_STATUS_ICP", 315: "IP_STATUS_FRANCHISE", 401: "RISK_DISHONEST", 402: "RISK_MORTGAGE", 403: "RISK_ABNORMAL", 404: "RISK_LEGAL_DOC", 405: "RISK_PENALTY", 406: "RISK_BANKRUPTCY", 407: "RISK_LIQUIDATION", 408: "RISK_ENV_PENALTY", 409: "RISK_EQUITY_FREEZE", 410: "RISK_EXECUTOR", 411: "RISK_LIMIT_CONSUMPTION", 501: "scenario" };
    
    const [tagRows] = await pool.query("SELECT sub_dimension_id, tag_name FROM tag_library ORDER BY sort_order");
    const scenarios = [];
    tagRows.forEach(row => { 
      const k = tagMapping[row.sub_dimension_id]; 
      if (k === "scenario") scenarios.push({ label: row.tag_name, value: row.tag_name }); 
      else if (k) { 
        if (!dictionary[k]) dictionary[k] = []; 
        if (!dictionary[k].some(item => item.value === row.tag_name)) dictionary[k].push({ label: row.tag_name, value: row.tag_name }); 
      } 
    });

    const [indRows] = await pool.query("SELECT id, parent_id, name FROM industry_categories ORDER BY sort_order");
    const buildTree = (items, pid = null) => items.filter(i => i.parent_id === pid).map(i => ({ title: i.name, value: i.name, key: i.id, children: buildTree(items, i.id) }));
    
    const [regRows] = await pool.query("SELECT name, type FROM sys_region ORDER BY sort_order");
    
    res.json({ 
      success: true, 
      data: { 
        dictionary, 
        industryTree: buildTree(indRows, null), 
        scenarios, 
        regions: { 
          street: regRows.filter(r => r.type === 'STREET').map(r => ({ label: r.name, value: r.name })), 
          area: regRows.filter(r => r.type === 'AREA').map(r => ({ label: r.name, value: r.name })) 
        } 
      } 
    });
  } catch (e) { res.status(500).json({ success: false, message: e.message }); }
});

// ==========================================
// 3. 产业链与行业分析模块
// ==========================================

/**
 * 产业链树谱数据 (恢复)
 */
app.get("/api/industry/tree", async (req, res) => {
  try {
    const [cats] = await pool.query("SELECT * FROM industry_categories ORDER BY sort_order");
    const [sm] = await pool.query("SELECT * FROM tags_chain_stage_map");
    const stageMap = {}; sm.forEach(r => stageMap[r.level1] = r.chain_stage);
    
    const [cnts] = await pool.query("SELECT tag_id, COUNT(DISTINCT company_id) as count FROM company_tag_map GROUP BY tag_id");
    const countMap = {}; cnts.forEach(c => countMap[c.tag_id] = c.count);
    
    const nodeMap = {}; cats.forEach(c => { nodeMap[c.id] = { key: c.id, title: c.name, level: c.level, children: [], count: countMap[c.id] || 0, isTag: true }; });
    const finalTree = [{ key: "stage_upstream", title: "上游", children: [], isStage: true }, { key: "stage_midstream", title: "中游", children: [], isStage: true }, { key: "stage_downstream", title: "下游", children: [], isStage: true }];
    
    cats.forEach(c => { 
      const n = nodeMap[c.id]; 
      if (c.parent_id && nodeMap[c.parent_id]) nodeMap[c.parent_id].children.push(n); 
      if (c.level === 1) { 
        const t = finalTree.find(x => x.title === stageMap[c.name]); 
        if (t) t.children.push(n); 
      } 
    });
    res.json({ success: true, data: finalTree });
  } catch (e) { res.status(500).json({ success: false, message: e.message }); }
});

/**
 * 首页总览统计 (恢复)
 */
app.get("/api/dashboard/overview", async (req, res) => {
  try {
    const [tRows] = await pool.query("SELECT COUNT(*) as total FROM companies");
    const [stats] = await pool.query("SELECT m.chain_stage as stage, ic.name as tagName, COUNT(DISTINCT ctm.company_id) as count FROM tags_chain_stage_map m JOIN industry_categories ic ON m.level1 = ic.name LEFT JOIN company_tag_map ctm ON ic.id = ctm.tag_id GROUP BY m.chain_stage, ic.name ORDER BY count DESC");
    const sMap = { "上游": { type: "upstream", title: "上游 · 研发与技术", color: "#1890ff", list: [] }, "中游": { type: "midstream", title: "中游 · 生产与制造", color: "#52c41a", list: [] }, "下游": { type: "downstream", title: "下游 · 服务与应用", color: "#fa8c16", list: [] } };
    stats.forEach(r => { if (sMap[r.stage]) sMap[r.stage].list.push({ name: r.tagName, count: r.count, isWeak: r.count === 0 }); });
    res.json({ success: true, data: { totalCompanies: tRows[0].total, chainData: Object.values(sMap).map(s => ({...s, total: s.list.reduce((a, b) => a + b.count, 0), subTags: s.list})) } });
  } catch (e) { res.status(500).json({ success: false, message: e.message }); }
});

/**
 * 行业画像/高级搜索 - 企业列表查询
 */
app.get("/api/industry/companies", async (req, res) => {
  const { keyword, tagId } = req.query;
  try {
    let sql = "SELECT DISTINCT c.company_id, c.company_name, c.reg_capital as registeredCapital, c.legal_person as legalPerson, c.establishment_date_desc as establishmentDate, c.enterprise_scale as scale, c.district, c.street, c.phone_gs as phone, c.email_gs as email, c.financing_round FROM companies c";
    const params = []; const conds = ["1=1"];
    if (tagId) { sql += " JOIN company_tag_map ctm ON c.company_id = ctm.company_id "; conds.push("ctm.tag_id = ?"); params.push(tagId); }
    if (keyword) { conds.push("(c.company_name LIKE ? OR c.company_id LIKE ?)"); params.push(`%${keyword}%`, `%${keyword}%`); }
    const [rows] = await pool.query(`${sql} WHERE ${conds.join(" AND ")} LIMIT 100`, params);
    if (rows.length > 0) {
      const [tRows] = await pool.query("SELECT m.company_id, t.tag_name FROM company_tag_map m JOIN tag_library t ON m.tag_id = t.id WHERE m.company_id IN (?)", [rows.map(r => r.company_id)]);
      rows.forEach(r => { r.tags = tRows.filter(t => t.company_id === r.company_id).map(t => t.tag_name); r.key = r.company_id; });
    }
    res.json({ success: true, data: rows });
  } catch (e) { res.status(500).json({ success: false, message: e.message }); }
});

/**
 * 企业详情
 */
app.get("/api/companies/:id", async (req, res) => {
  const { id } = req.params;
  try {
    const [rows] = await pool.query("SELECT * FROM companies WHERE company_id = ? OR company_name = ?", [id, id]);
    if (rows.length === 0) return res.status(404).json({ success: false, message: "未找到企业" });
    const raw = rows[0];
    const [tRows] = await pool.query("SELECT t.tag_name FROM company_tag_map ctm JOIN tag_library t ON ctm.tag_id = t.id WHERE ctm.company_id = ?", [raw.company_id]);
    const parseList = (s) => s ? s.split(/[;；,，\n]/).filter(x => x.trim()).map((x, i) => ({ key: i, name: x.trim() })) : [];
    res.json({ success: true, data: { baseInfo: { id: raw.company_id, name: raw.company_name, legalPerson: raw.legal_person, status: "存续", establishDate: raw.establishment_date_desc, regCapital: raw.reg_capital, paidInCapital: raw.paid_capital, address: raw.address_detail || raw.address_info, industry: raw.industry_gs, scope: raw.business_scope }, basicInfoData: { shareholders: parseList(raw.shareholders), branches: parseList(raw.is_branch_info), keyPersonnel: [{ key: 1, name: raw.legal_person, title: "法定代表人" }], social: [{ key: 1, year: '2024', pension: raw.insured_count || 0 }] }, tags: tRows.map(t => t.tag_name), metrics: { totalScore: raw.total_score || 85, rank: 12 }, migrationRisk: { level: "低", score: 20, color: "#52c41a", factors: [] }, overallRadar: [{ item: "基础实力", score: 80 }, { item: "科技属性", score: 90 }, { item: "专业能力", score: 75 }, { item: "成长潜力", score: 85 }, { item: "合规风险", score: 95 }], models: { basic: { score: 85, dimensions: [] }, tech: { score: 80, dimensions: [] }, ability: { score: 75, dimensions: [] } }, honors: raw.qualifications ? raw.qualifications.split('|').map(q => ({ year: '-', name: q.trim() })) : [] } });
  } catch (e) { res.status(500).json({ success: false, message: e.message }); }
});

// ==========================================
// 4. 智能诊断 AI 模块 (恢复)
// ==========================================

app.post("/api/chat", requireAuth, async (req, res) => {
  const { messages, sessionId } = req.body;
  try {
    const data = await agentRequest("/chat", {
      method: "POST",
      body: JSON.stringify({
        messages,
        sessionId: sessionId || crypto.randomUUID(),
        userId: req.authUser.id,
      }),
    });
    res.json(data);
  } catch (error) {
    res.json({
      success: false,
      message: `Qwen + RAG demo 服务不可用，请先启动 AGENT 服务 (${AGENT_API_URL})。${error.message}`,
    });
  }
});

app.post("/api/chat/stream", requireAuth, async (req, res) => {
  const { messages, sessionId } = req.body;
  const controller = new AbortController();
  req.on("aborted", () => controller.abort());
  res.on("close", () => {
    if (!res.writableEnded) {
      controller.abort();
    }
  });

  try {
    const response = await fetch(`${AGENT_API_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages,
        sessionId: sessionId || crypto.randomUUID(),
        userId: req.authUser.id,
      }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const text = await response.text();
      let errorMessage = `Agent request failed: ${response.status}`;
      if (text) {
        try {
          const data = JSON.parse(text);
          errorMessage = data.detail || data.message || errorMessage;
        } catch {
          errorMessage = text;
        }
      }
      throw new Error(errorMessage);
    }

    res.status(200);
    res.setHeader("Content-Type", "application/x-ndjson; charset=utf-8");
    res.setHeader("Cache-Control", "no-cache, no-transform");
    res.setHeader("Connection", "keep-alive");
    if (typeof res.flushHeaders === "function") {
      res.flushHeaders();
    }

    if (!response.body) {
      res.end();
      return;
    }

    const reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (value) {
        res.write(Buffer.from(value));
      }
    }
    res.end();
  } catch (error) {
    if (controller.signal.aborted || res.destroyed) {
      return;
    }
    res.status(200);
    res.setHeader("Content-Type", "application/x-ndjson; charset=utf-8");
    res.end(
      `${JSON.stringify({
        type: "error",
        message: `Qwen + RAG 服务不可用，请先启动 AGENT 服务 (${AGENT_API_URL})。${error.message}`,
      })}\n`,
    );
  }
});

app.get("/api/chat/history", requireAuth, async (req, res) => {
  try {
    const data = await agentRequest(`/history?userId=${encodeURIComponent(req.authUser.id)}`);
    res.json(data);
  } catch (error) {
    res.json({ success: false, data: [], message: error.message });
  }
});

app.get("/api/chat/history/:sessionId", requireAuth, async (req, res) => {
  try {
    const data = await agentRequest(
      `/history/${req.params.sessionId}?userId=${encodeURIComponent(req.authUser.id)}`,
    );
    res.json(data);
  } catch (error) {
    res.status(404).json({ success: false, message: error.message });
  }
});

app.delete("/api/chat/history/:sessionId", requireAuth, async (req, res) => {
  try {
    const response = await fetch(
      `${AGENT_API_URL}/history/${req.params.sessionId}?userId=${encodeURIComponent(req.authUser.id)}`,
      {
      method: "DELETE",
      },
    );
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) {
      throw new Error(data.detail || data.message || "删除会话失败");
    }
    res.json(data);
  } catch (error) {
    res.status(404).json({ success: false, message: error.message });
  }
});

app.patch("/api/chat/history/:sessionId", requireAuth, async (req, res) => {
  try {
    const response = await fetch(
      `${AGENT_API_URL}/history/${req.params.sessionId}?userId=${encodeURIComponent(req.authUser.id)}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req.body),
      },
    );
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) {
      throw new Error(data.detail || data.message || "更新会话失败");
    }
    res.json(data);
  } catch (error) {
    res.status(404).json({ success: false, message: error.message });
  }
});

app.delete("/api/chat/history", requireAuth, async (req, res) => {
  try {
    const response = await fetch(`${AGENT_API_URL}/history?userId=${encodeURIComponent(req.authUser.id)}`, {
      method: "DELETE",
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) {
      throw new Error(data.detail || data.message || "清空历史失败");
    }
    res.json(data);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// ==========================================
// 5. 系统管理模块
// ==========================================

/**
 * 系统管理：企业数据列表 (带聚合标签)
 */
app.get("/api/system/companies", async (req, res) => {
  const { page = 1, pageSize = 15, keyword = "" } = req.query;
  const offset = (page - 1) * pageSize;
  try {
    let where = "WHERE 1=1";
    const params = [];
    if (keyword) { where += " AND (company_name LIKE ? OR company_id LIKE ?)"; params.push(`%${keyword}%`, `%${keyword}%`); }
    const [totalRows] = await pool.query(`SELECT COUNT(*) as total FROM companies ${where}`, params);
    const [rows] = await pool.query(`SELECT company_id as \`key\`, company_name as name, legal_person as legalPerson, reg_capital_rmb as registeredCapital, establishment_date_desc as establishmentDate, update_time as updateTime FROM companies ${where} ORDER BY create_time DESC LIMIT ? OFFSET ?`, [...params, parseInt(pageSize), offset]);
    if (rows.length === 0) return res.json({ success: true, data: [], total: 0 });
    const [tagRows] = await pool.query(`SELECT ctm.company_id, tl.tag_name FROM company_tag_map ctm JOIN tag_library tl ON ctm.tag_id = tl.id WHERE ctm.company_id IN (?)`, [rows.map(r => r.key)]);
    const result = rows.map(r => ({ ...r, variants: tagRows.filter(t => t.company_id === r.key).map(t => t.tag_name).join(" | ") }));
    res.json({ success: true, data: result, total: totalRows[0].total });
  } catch (error) { res.status(500).json({ success: false, message: error.message }); }
});

app.post("/api/system/companies", async (req, res) => {
  const { key, name, legalPerson, registeredCapital, establishmentDate } = req.body;
  try {
    await pool.query(`INSERT INTO companies (company_id, company_name, legal_person, reg_capital_rmb, establishment_date_desc) VALUES (?, ?, ?, ?, ?)`, [key, name, legalPerson, registeredCapital, establishmentDate]);
    res.json({ success: true });
  } catch (error) { res.status(500).json({ success: false, message: error.message }); }
});

app.put("/api/system/companies/:id", async (req, res) => {
  const { id } = req.params;
  const { name, legalPerson, registeredCapital, establishmentDate } = req.body;
  try {
    await pool.query(`UPDATE companies SET company_name = ?, legal_person = ?, reg_capital_rmb = ?, establishment_date_desc = ? WHERE company_id = ?`, [name, legalPerson, registeredCapital, establishmentDate, id]);
    res.json({ success: true });
  } catch (error) { res.status(500).json({ success: false, message: error.message }); }
});

app.delete("/api/system/companies/:id", async (req, res) => {
  const { id } = req.params;
  try {
    await pool.query("DELETE FROM companies WHERE company_id = ?", [id]);
    res.json({ success: true });
  } catch (error) { res.status(500).json({ success: false, message: error.message }); }
});

// --- 系统管理：标签管理 ---

/**
 * 标签管理：获取企业列表及聚合标签
 */
app.get("/api/tags/companies", async (req, res) => {
  const { page = 1, pageSize = 10, keyword = "" } = req.query;
  const offset = (page - 1) * pageSize;
  try {
    let where = "WHERE 1=1";
    const params = [];
    if (keyword) { where += " AND (company_name LIKE ? OR company_id LIKE ?)"; params.push(`%${keyword}%`, `%${keyword}%`); }
    const [totalRows] = await pool.query(`SELECT COUNT(*) as total FROM companies ${where}`, params);
    const [rows] = await pool.query(`SELECT company_id, company_name FROM companies ${where} LIMIT ? OFFSET ?`, [...params, parseInt(pageSize), offset]);
    if (rows.length === 0) return res.json({ success: true, data: { list: [], total: 0 } });
    const [tagRows] = await pool.query(`SELECT ctm.company_id, tl.tag_name, td.name as dimensionName FROM company_tag_map ctm JOIN tag_library tl ON ctm.tag_id = tl.id JOIN tag_sub_dimensions tsd ON tl.sub_dimension_id = tsd.id JOIN tag_dimensions td ON tsd.dimension_id = td.id WHERE ctm.company_id IN (?)`, [rows.map(r => r.company_id)]);
    const dimMap = { "基本信息": "basic", "经营状况": "business", "知识产权": "tech", "风险信息": "risk", "产业链环节": "market" };
    const list = rows.map(r => {
      const dimensions = { basic: [], business: [], tech: [], risk: [], market: [] };
      tagRows.filter(t => t.company_id === r.company_id).forEach(t => { const key = dimMap[t.dimensionName]; if (key) dimensions[key].push(t.tag_name); });
      return { key: r.company_id, name: r.company_name, code: r.company_id, dimensions };
    });
    res.json({ success: true, data: { list, total: totalRows[0].total } });
  } catch (error) { res.status(500).json({ success: false, message: error.message }); }
});

/**
 * 标签管理：添加标签
 */
app.post("/api/tags/add", async (req, res) => {
  const { companyId, tagName } = req.body;
  try {
    const [tagRows] = await pool.query("SELECT id FROM tag_library WHERE tag_name = ? LIMIT 1", [tagName]);
    if (tagRows.length === 0) return res.status(400).json({ success: false, message: "标签不存在" });
    await pool.query("INSERT IGNORE INTO company_tag_map (company_id, tag_id) VALUES (?, ?)", [companyId, tagRows[0].id]);
    res.json({ success: true });
  } catch (error) { res.status(500).json({ success: false, message: error.message }); }
});

/**
 * 标签管理：删除标签
 */
app.post("/api/tags/delete", async (req, res) => {
  const { companyId, tagName } = req.body;
  try {
    const [tagRows] = await pool.query("SELECT id FROM tag_library WHERE tag_name = ? LIMIT 1", [tagName]);
    if (tagRows.length > 0) {
      await pool.query("DELETE FROM company_tag_map WHERE company_id = ? AND tag_id = ?", [companyId, tagRows[0].id]);
    }
    res.json({ success: true });
  } catch (error) { res.status(500).json({ success: false, message: error.message }); }
});

/**
 * 标签管理：维度统计 (恢复)
 */
app.get("/api/tags/dimensions/stats", async (req, res) => {
  try {
    const [totalRows] = await pool.query("SELECT COUNT(*) as total FROM companies");
    const totalCompanies = totalRows[0].total || 1;
    const [rows] = await pool.query(`
      SELECT td.id, td.name, COUNT(DISTINCT tl.id) as tagCount, COUNT(DISTINCT ctm.company_id) as usedCount
      FROM tag_dimensions td
      LEFT JOIN tag_sub_dimensions tsd ON td.id = tsd.dimension_id
      LEFT JOIN tag_library tl ON tsd.id = tl.sub_dimension_id
      LEFT JOIN company_tag_map ctm ON tl.id = ctm.tag_id
      GROUP BY td.id, td.name ORDER BY td.sort_order
    `);
    const colorMap = ["#1890ff", "#52c41a", "#fa8c16", "#722ed1", "#13c2c2", "#f5222d", "#eb2f96", "#faad14"];
    const data = rows.map((r, i) => ({ ...r, color: colorMap[i % colorMap.length], coverage: Math.round((r.usedCount / totalCompanies) * 100) }));
    res.json({ success: true, data: { dimensions: data, overview: { totalTags: data.reduce((a, c) => a + c.tagCount, 0), coveredEnterprises: data.reduce((a, c) => Math.max(a, c.usedCount), 0), totalCompanies } } });
  } catch (error) { res.status(500).json({ success: false, message: error.message }); }
});

export function startServer(port = PORT) {
  return app.listen(port, () => console.log(`Backend running at http://localhost:${port}`));
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  startServer();
}

export { app };
