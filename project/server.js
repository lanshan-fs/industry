import express from "express";
import mysql from "mysql2/promise";
import cors from "cors";
import crypto from "crypto";
import dotenv from "dotenv";
import fs from "fs/promises";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import nodemailer from "nodemailer";
import { execFile } from "child_process";
import { promisify } from "util";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, "..");
const AUTO_TAG_RULE_SCRIPT = path.join(PROJECT_ROOT, "SQL", "scripts", "apply_company_tag_auto_rules.py");
const IMPORT_AUTO_TAG_EVALUATE_SCRIPT = path.join(PROJECT_ROOT, "SQL", "scripts", "evaluate_import_company_tags.py");
dotenv.config({ path: path.join(__dirname, "../.env") });
const execFileAsync = promisify(execFile);

const app = express();
const PORT = process.env.PORT || 3001;
const JWT_SECRET = process.env.JWT_SECRET || "chaoyang_industrial_secret_2026";
const AGENT_API_URL = process.env.AGENT_API_URL || "http://127.0.0.1:8001";
const DASHSCOPE_API_KEY = (process.env.DASHSCOPE_API_KEY || "").replace(/\r/g, "").trim();
const DASHSCOPE_MODEL = (process.env.QWEN_MODEL || "qwen-plus").replace(/\r/g, "").trim();
const DEFAULT_DASHSCOPE_BASE_URLS = [
  "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
];
const DASHSCOPE_BASE_URLS = [
  process.env.QWEN_BASE_URL,
  process.env.QWEN_BASE_URL_INTL,
  ...DEFAULT_DASHSCOPE_BASE_URLS,
]
  .map((value) => normalizeText(value).replace(/\/+$/, ""))
  .filter(Boolean)
  .filter((value, index, values) => values.indexOf(value) === index);
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

const TAG_DIMENSION_META_BY_NAME = {
  基本信息: { key: "basic", color: "#1890ff" },
  经营状况: { key: "business", color: "#fa8c16" },
  知识产权: { key: "tech", color: "#722ed1" },
  风险信息: { key: "risk", color: "#f5222d" },
  街道地区: { key: "region", color: "#13c2c2" },
  行业标签: { key: "industry", color: "#fa8c16" },
  应用场景: { key: "scene", color: "#52c41a" },
};

const TAG_BUCKET_KEYS = ["basic", "business", "tech", "risk", "region", "industry", "scene"];
const AUTO_TAG_BATCH_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
};
const AUTO_TAG_BATCH_ITEM_STATUS = {
  PENDING: "pending",
  SUCCESS: "success",
  FAILED: "failed",
};
const AUTO_TAG_LLM_BATCH_STATUS = {
  PENDING: "pending",
  RUNNING: "running",
  COMPLETED: "completed",
  FAILED: "failed",
};
const AUTO_TAG_LLM_CANDIDATE_TYPE = {
  MAPPED: "mapped_tag",
  UNMAPPED: "unmapped_term",
};
const AUTO_TAG_LLM_CANDIDATE_STATUS = {
  PENDING: "pending",
  UNMAPPED: "unmapped",
  APPLIED: "applied",
  REJECTED: "rejected",
};
const INDUSTRY_DIMENSION_NAME = "行业标签";
const INDUSTRY_CHAIN_SUBDIMENSION_NAME = "产业链";
const INDUSTRY_CATEGORY_SUBDIMENSION_NAME = "行业分类";
const SCENE_DIMENSION_NAME = "应用场景";
const SCENE_SUBDIMENSION_NAME = "应用场景";
let industryTagCatalogPromise = null;

function emptyTagBuckets() {
  return {
    basic: [],
    business: [],
    tech: [],
    risk: [],
    region: [],
    industry: [],
    scene: [],
  };
}

function getTagDimensionMeta(dimensionName) {
  return TAG_DIMENSION_META_BY_NAME[normalizeText(dimensionName)] || { key: "other", color: "#8c8c8c" };
}

function toPositiveInt(value, fallback = 0) {
  const parsed = Number.parseInt(String(value ?? ""), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function normalizeIntList(values) {
  if (!Array.isArray(values)) return [];
  return [...new Set(values.map((item) => Number.parseInt(String(item), 10)).filter((item) => Number.isFinite(item) && item > 0))];
}

function normalizeIdentifierList(values) {
  if (!Array.isArray(values)) return [];
  return [
    ...new Set(
      values
        .map((item) => normalizeText(item).replace(/^[，,;；\s]+|[，,;；\s]+$/g, ""))
        .filter(Boolean),
    ),
  ];
}

async function fetchCompanyCandidateListByIds(companyIds) {
  if (!Array.isArray(companyIds) || companyIds.length === 0) {
    return [];
  }

  const [rows] = await pool.query(
    `
      SELECT
        b.company_id AS companyId,
        b.company_name AS companyName,
        b.credit_code AS creditCode,
        b.establish_date AS establishDate,
        b.updated_at AS updateTime,
        COUNT(DISTINCT m.company_tag_id) AS tagCount
      FROM company_basic b
      LEFT JOIN company_tag_map m
        ON b.company_id = m.company_id
      WHERE b.company_id IN (?)
      GROUP BY b.company_id, b.company_name, b.credit_code, b.establish_date, b.updated_at
      ORDER BY b.updated_at DESC, b.company_id DESC
    `,
    [companyIds],
  );

  return rows.map((row) => ({
    key: row.companyId,
    companyId: row.companyId,
    name: row.companyName,
    code: row.creditCode || String(row.companyId),
    establishDate: row.establishDate,
    updateTime: row.updateTime,
    tagCount: row.tagCount,
  }));
}

async function fetchIndustryCategoryDefinitions(executor = pool) {
  const [rows] = await executor.query(
    `
      SELECT
        c.category_id AS categoryId,
        c.category_name AS categoryName,
        c.category_level_code AS categoryLevelCode
      FROM (
        SELECT DISTINCT category_id
        FROM category_industry_company_map
      ) used
      JOIN category_industry c
        ON used.category_id = c.category_id
      ORDER BY c.category_level, c.sort_order, c.category_id
    `,
  );
  return rows;
}

function buildIndustryCategoryTagNameMap(
  categoryRows,
  existingTagRows,
  categorySubdimensionId,
  additionalReservedNames = [],
) {
  const nameCounts = new Map();
  for (const row of categoryRows) {
    nameCounts.set(row.categoryName, (nameCounts.get(row.categoryName) || 0) + 1);
  }

  const reservedNames = new Set(
    existingTagRows
      .filter((row) => row.subdimensionId !== categorySubdimensionId)
      .map((row) => row.tagName),
  );
  for (const tagName of additionalReservedNames) {
    if (tagName) {
      reservedNames.add(tagName);
    }
  }

  return new Map(
    categoryRows.map((row) => [
      row.categoryId,
      (nameCounts.get(row.categoryName) || 0) > 1 || reservedNames.has(row.categoryName)
        ? `${row.categoryName}（${row.categoryLevelCode}）`
        : row.categoryName,
    ]),
  );
}

async function syncIndustryTagCatalog() {
  const connection = await pool.getConnection();
  try {
    await connection.beginTransaction();

    let [dimensionRows] = await connection.query(
      `
        SELECT company_tag_dimension_id AS id
        FROM company_tag_dimension
        WHERE company_tag_dimension_name = ?
        LIMIT 1
      `,
      [INDUSTRY_DIMENSION_NAME],
    );
    let industryDimensionId = dimensionRows[0]?.id;
    if (!industryDimensionId) {
      const [sortRows] = await connection.query(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 AS nextSortOrder FROM company_tag_dimension",
      );
      const [insertResult] = await connection.query(
        `
          INSERT INTO company_tag_dimension (
            company_tag_dimension_name,
            company_tag_dimension_des,
            sort_order
          ) VALUES (?, ?, ?)
        `,
        [INDUSTRY_DIMENSION_NAME, "行业分类与产业链归属标签", sortRows[0]?.nextSortOrder || 7],
      );
      industryDimensionId = insertResult.insertId;
    }

    const ensureSubdimension = async (name, sortOrder) => {
      const [rows] = await connection.query(
        `
          SELECT company_tag_subdimension_id AS id
          FROM company_tag_subdimension
          WHERE company_tag_dimension_id = ? AND company_tag_subdimension_name = ?
          LIMIT 1
        `,
        [industryDimensionId, name],
      );
      if (rows[0]?.id) {
        return rows[0].id;
      }
      const [insertResult] = await connection.query(
        `
          INSERT INTO company_tag_subdimension (
            company_tag_subdimension_name,
            company_tag_dimension_id,
            sort_order
          ) VALUES (?, ?, ?)
        `,
        [name, industryDimensionId, sortOrder],
      );
      return insertResult.insertId;
    };

    const chainSubdimensionId = await ensureSubdimension(INDUSTRY_CHAIN_SUBDIMENSION_NAME, 1);
    const categorySubdimensionId = await ensureSubdimension(INDUSTRY_CATEGORY_SUBDIMENSION_NAME, 2);

    const [allExistingTagRows] = await connection.query(
      `
        SELECT
          company_tag_name AS tagName,
          company_tag_subdimension_id AS subdimensionId
        FROM company_tag_library
      `,
    );
    const categoryRows = await fetchIndustryCategoryDefinitions(connection);
    const [chainRows] = await connection.query(
      `
        SELECT chain_id AS chainId, chain_name AS tagName
        FROM chain_industry
        ORDER BY chain_id
      `,
    );

    const categoryTagNameById = buildIndustryCategoryTagNameMap(
      categoryRows,
      allExistingTagRows,
      categorySubdimensionId,
      chainRows.map((row) => row.tagName),
    );
    const normalizedCategoryRows = categoryRows.map((row) => ({
      ...row,
      tagName: categoryTagNameById.get(row.categoryId),
    }));

    const [existingRows] = await connection.query(
      `
        SELECT
          company_tag_id AS tagId,
          company_tag_name AS tagName,
          company_tag_subdimension_id AS subdimensionId
        FROM company_tag_library
        WHERE company_tag_subdimension_id IN (?, ?)
      `,
      [chainSubdimensionId, categorySubdimensionId],
    );
    const existingKeys = new Set(existingRows.map((row) => `${row.subdimensionId}::${row.tagName}`));

    for (const row of chainRows) {
      const key = `${chainSubdimensionId}::${row.tagName}`;
      if (existingKeys.has(key)) continue;
      await connection.query(
        `
          INSERT INTO company_tag_library (
            company_tag_name,
            company_tag_subdimension_id,
            sort_order
          ) VALUES (?, ?, ?)
        `,
        [row.tagName, chainSubdimensionId, row.chainId],
      );
      existingKeys.add(key);
    }

    for (const row of normalizedCategoryRows) {
      const key = `${categorySubdimensionId}::${row.tagName}`;
      if (existingKeys.has(key)) continue;
      await connection.query(
        `
          INSERT INTO company_tag_library (
            company_tag_name,
            company_tag_subdimension_id,
            sort_order
          ) VALUES (?, ?, ?)
        `,
        [row.tagName, categorySubdimensionId, row.categoryId],
      );
      existingKeys.add(key);
    }

    await connection.commit();
    return {
      dimensionId: industryDimensionId,
      chainSubdimensionId,
      categorySubdimensionId,
    };
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    connection.release();
  }
}

async function ensureIndustryTagCatalog() {
  if (!industryTagCatalogPromise) {
    industryTagCatalogPromise = syncIndustryTagCatalog().finally(() => {
      industryTagCatalogPromise = null;
    });
  }
  return industryTagCatalogPromise;
}

async function fetchTagDimensionList() {
  await ensureIndustryTagCatalog();
  const [rows] = await pool.query(
    `
      SELECT
        company_tag_dimension_id AS id,
        company_tag_dimension_name AS name,
        company_tag_dimension_des AS description
      FROM company_tag_dimension
      ORDER BY sort_order, company_tag_dimension_id
    `,
  );
  return rows.map((row) => {
    const meta = getTagDimensionMeta(row.name);
    return {
      ...row,
      key: meta.key,
      color: meta.color,
      description: row.description || `${row.name}标签管理`,
    };
  });
}

async function fetchTagLibraryOptions() {
  await ensureIndustryTagCatalog();
  const [rows] = await pool.query(
    `
      SELECT
        d.company_tag_dimension_id AS dimensionId,
        d.company_tag_dimension_name AS dimensionName,
        sd.company_tag_subdimension_id AS subdimensionId,
        sd.company_tag_subdimension_name AS subdimensionName,
        l.company_tag_id AS tagId,
        l.company_tag_name AS tagName
      FROM company_tag_library l
      JOIN company_tag_subdimension sd
        ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
      JOIN company_tag_dimension d
        ON sd.company_tag_dimension_id = d.company_tag_dimension_id
      ORDER BY d.sort_order, sd.sort_order, l.sort_order, l.company_tag_name
    `,
  );

  const grouped = {};
  const dimensions = new Map();
  for (const row of rows) {
    const meta = getTagDimensionMeta(row.dimensionName);
    if (!grouped[meta.key]) {
      grouped[meta.key] = [];
    }
    grouped[meta.key].push({
      id: row.tagId,
      name: row.tagName,
      dimensionId: row.dimensionId,
      dimensionName: row.dimensionName,
      subdimensionId: row.subdimensionId,
      subdimensionName: row.subdimensionName,
    });

    if (!dimensions.has(row.dimensionId)) {
      dimensions.set(row.dimensionId, {
        id: row.dimensionId,
        key: meta.key,
        name: row.dimensionName,
        color: meta.color,
        tags: [],
      });
    }
    dimensions.get(row.dimensionId).tags.push({
      id: row.tagId,
      name: row.tagName,
      subdimensionId: row.subdimensionId,
      subdimensionName: row.subdimensionName,
    });
  }

  for (const key of TAG_BUCKET_KEYS) {
    if (!grouped[key]) {
      grouped[key] = [];
    }
  }

  return {
    grouped,
    dimensions: [...dimensions.values()],
  };
}

async function fetchCompanyTags(companyIds) {
  if (!Array.isArray(companyIds) || companyIds.length === 0) {
    return [];
  }

  const [rows] = await pool.query(
    `
      SELECT
        ctm.company_id AS companyId,
        ctm.create_time AS taggedAt,
        l.company_tag_id AS companyTagId,
        l.company_tag_name AS tagName,
        sd.company_tag_subdimension_id AS subdimensionId,
        sd.company_tag_subdimension_name AS subdimensionName,
        d.company_tag_dimension_id AS dimensionId,
        d.company_tag_dimension_name AS dimensionName
      FROM company_tag_map ctm
      JOIN company_tag_library l
        ON ctm.company_tag_id = l.company_tag_id
      JOIN company_tag_subdimension sd
        ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
      JOIN company_tag_dimension d
        ON sd.company_tag_dimension_id = d.company_tag_dimension_id
      WHERE ctm.company_id IN (?)
      ORDER BY ctm.company_id, d.sort_order, sd.sort_order, l.sort_order, l.company_tag_name
    `,
    [companyIds],
  );
  return rows;
}

function buildBatchResultFromTagRows(companyId, tagRows) {
  const relatedTags = tagRows.filter((row) => row.companyId === companyId);
  return {
    company_id: companyId,
    tag_count: relatedTags.length,
    tags: relatedTags.map((row) => ({
      company_tag_id: row.companyTagId,
      company_tag_name: row.tagName,
      company_tag_dimension_name: row.dimensionName,
      company_tag_subdimension_name: row.subdimensionName,
    })),
  };
}

async function fetchCompanyBaseRows(companyIds) {
  if (!Array.isArray(companyIds) || companyIds.length === 0) {
    return [];
  }

  const [rows] = await pool.query(
    `
      SELECT
        company_id AS companyId,
        company_name AS companyName,
        credit_code AS creditCode,
        establish_date AS establishDate,
        updated_at AS updateTime
      FROM company_basic
      WHERE company_id IN (?)
      ORDER BY company_name
    `,
    [companyIds],
  );
  return rows;
}

function buildCompanyTagView(companyRows, tagRows) {
  return companyRows.map((row) => {
    const dimensions = emptyTagBuckets();
    const relatedTags = tagRows.filter((tagRow) => tagRow.companyId === row.companyId);
    const tagDetails = relatedTags.map((tagRow) => ({
      id: tagRow.companyTagId,
      name: tagRow.tagName,
      dimensionId: tagRow.dimensionId,
      dimensionName: tagRow.dimensionName,
      subdimensionId: tagRow.subdimensionId,
      subdimensionName: tagRow.subdimensionName,
      taggedAt: tagRow.taggedAt,
    }));

    for (const tagRow of relatedTags) {
      const meta = getTagDimensionMeta(tagRow.dimensionName);
      if (dimensions[meta.key]) {
        dimensions[meta.key].push(tagRow.tagName);
      }
    }

    return {
      key: row.companyId,
      companyId: row.companyId,
      name: row.companyName,
      code: row.creditCode || String(row.companyId),
      updateTime: row.updateTime,
      dimensions,
      tagCount: tagDetails.length,
      tags: tagDetails,
    };
  });
}

function parseJsonValue(value, fallback = null) {
  if (!value) return fallback;
  if (typeof value === "object") return value;
  try {
    return JSON.parse(String(value));
  } catch {
    return fallback;
  }
}

function createBatchCode() {
  return `TAGBATCH_${Date.now()}_${crypto.randomBytes(3).toString("hex").toUpperCase()}`;
}

function createLlmBatchCode() {
  return `TAGLLM_${Date.now()}_${crypto.randomBytes(3).toString("hex").toUpperCase()}`;
}

function formatBatchRow(row) {
  return {
    batchId: row.batchId,
    batchCode: row.batchCode,
    batchName: row.batchName,
    status: row.status,
    requestedByUserId: row.requestedByUserId,
    dimensionIds: parseJsonValue(row.dimensionIds, []) || [],
    dimensionNames: parseJsonValue(row.dimensionNames, []) || [],
    requestedCompanyCount: row.requestedCompanyCount || 0,
    successCompanyCount: row.successCompanyCount || 0,
    failedCompanyCount: row.failedCompanyCount || 0,
    summary: parseJsonValue(row.summaryJson, null),
    errorMessage: row.errorMessage || "",
    startedAt: row.startedAt,
    finishedAt: row.finishedAt,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

function formatLlmBatchRow(row) {
  return {
    batchId: row.batchId,
    batchCode: row.batchCode,
    batchName: row.batchName,
    status: row.status,
    provider: row.provider,
    modelName: row.modelName,
    dimensionId: row.dimensionId,
    requestedByUserId: row.requestedByUserId,
    requestedCompanyCount: row.requestedCompanyCount || 0,
    successCompanyCount: row.successCompanyCount || 0,
    failedCompanyCount: row.failedCompanyCount || 0,
    summary: parseJsonValue(row.summaryJson, null),
    errorMessage: row.errorMessage || "",
    startedAt: row.startedAt,
    finishedAt: row.finishedAt,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

async function fetchBatchRow(batchId) {
  const [rows] = await pool.query(
    `
      SELECT
        company_tag_batch_id AS batchId,
        batch_code AS batchCode,
        batch_name AS batchName,
        status,
        requested_by_user_id AS requestedByUserId,
        dimension_ids AS dimensionIds,
        dimension_names AS dimensionNames,
        requested_company_count AS requestedCompanyCount,
        success_company_count AS successCompanyCount,
        failed_company_count AS failedCompanyCount,
        summary_json AS summaryJson,
        error_message AS errorMessage,
        started_at AS startedAt,
        finished_at AS finishedAt,
        created_at AS createdAt,
        updated_at AS updatedAt
      FROM company_tag_batch
      WHERE company_tag_batch_id = ?
      LIMIT 1
    `,
    [batchId],
  );
  return rows[0] ? formatBatchRow(rows[0]) : null;
}

async function fetchLlmBatchRow(batchId) {
  const [rows] = await pool.query(
    `
      SELECT
        company_tag_llm_batch_id AS batchId,
        batch_code AS batchCode,
        batch_name AS batchName,
        status,
        provider,
        model_name AS modelName,
        company_tag_dimension_id AS dimensionId,
        requested_by_user_id AS requestedByUserId,
        requested_company_count AS requestedCompanyCount,
        success_company_count AS successCompanyCount,
        failed_company_count AS failedCompanyCount,
        summary_json AS summaryJson,
        error_message AS errorMessage,
        started_at AS startedAt,
        finished_at AS finishedAt,
        created_at AS createdAt,
        updated_at AS updatedAt
      FROM company_tag_llm_batch
      WHERE company_tag_llm_batch_id = ?
      LIMIT 1
    `,
    [batchId],
  );
  return rows[0] ? formatLlmBatchRow(rows[0]) : null;
}

async function fetchSceneTagOptions() {
  const [rows] = await pool.query(
    `
      SELECT
        l.company_tag_id AS tagId,
        l.company_tag_name AS tagName
      FROM company_tag_library l
      JOIN company_tag_subdimension sd
        ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
      JOIN company_tag_dimension d
        ON sd.company_tag_dimension_id = d.company_tag_dimension_id
      WHERE d.company_tag_dimension_name = ?
        AND sd.company_tag_subdimension_name = ?
      ORDER BY l.sort_order, l.company_tag_name
    `,
    [SCENE_DIMENSION_NAME, SCENE_SUBDIMENSION_NAME],
  );
  return rows;
}

async function fetchCurrentSceneTagsByCompany(companyIds) {
  if (!Array.isArray(companyIds) || companyIds.length === 0) {
    return new Map();
  }

  const [rows] = await pool.query(
    `
      SELECT
        m.company_id AS companyId,
        l.company_tag_name AS tagName
      FROM company_tag_map m
      JOIN company_tag_library l
        ON m.company_tag_id = l.company_tag_id
      JOIN company_tag_subdimension sd
        ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
      JOIN company_tag_dimension d
        ON sd.company_tag_dimension_id = d.company_tag_dimension_id
      WHERE m.company_id IN (?)
        AND d.company_tag_dimension_name = ?
    `,
    [companyIds, SCENE_DIMENSION_NAME],
  );
  const result = new Map();
  for (const row of rows) {
    if (!result.has(row.companyId)) {
      result.set(row.companyId, []);
    }
    result.get(row.companyId).push(row.tagName);
  }
  return result;
}

async function fetchSceneLlmProfiles(companyIds) {
  if (!Array.isArray(companyIds) || companyIds.length === 0) {
    return [];
  }

  const [rows] = await pool.query(
    `
      SELECT
        company_id AS companyId,
        company_name AS companyName,
        credit_code AS creditCode,
        business_scope AS businessScope,
        qualification_label AS qualificationLabel,
        industry_belong AS industryBelong,
        subdistrict,
        register_address AS registerAddress,
        register_address_detail AS registerAddressDetail
      FROM company_basic
      WHERE company_id IN (?)
      ORDER BY company_id
    `,
    [companyIds],
  );
  return rows;
}

async function resolveAgentUserId(requestedByUserId) {
  const requested = toPositiveInt(requestedByUserId, 0);
  if (requested) {
    const [requestedRows] = await pool.query(
      "SELECT user_id AS userId FROM users WHERE user_id = ? LIMIT 1",
      [requested],
    );
    if (requestedRows[0]?.userId) {
      return requestedRows[0].userId;
    }
  }

  const [rows] = await pool.query(
    "SELECT user_id AS userId FROM users ORDER BY user_id LIMIT 1",
  );
  return rows[0]?.userId || 1;
}

async function requestDashscopeChat(messages, options = {}) {
  if (!DASHSCOPE_API_KEY) {
    throw new Error("未配置 DASHSCOPE_API_KEY");
  }

  const errors = [];
  for (const baseUrl of DASHSCOPE_BASE_URLS) {
    const chatUrl = `${baseUrl}/chat/completions`;
    try {
      const payloadBody = {
        model: DASHSCOPE_MODEL,
        messages,
        temperature: typeof options.temperature === "number" ? options.temperature : 0.2,
      };
      if (options.responseFormat) {
        payloadBody.response_format = options.responseFormat;
      }
      const response = await fetch(chatUrl, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${DASHSCOPE_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payloadBody),
      });
      const text = await response.text();
      const payload = text ? JSON.parse(text) : {};
      if (!response.ok) {
        throw new Error(payload.error?.message || payload.message || `HTTP ${response.status}`);
      }
      return {
        provider: "dashscope_compatible",
        modelName: payload?.model || DASHSCOPE_MODEL,
        rawText: payload?.choices?.[0]?.message?.content || "",
        baseUrl,
      };
    } catch (error) {
      errors.push(`${baseUrl}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  throw new Error(`DashScope 请求失败：${errors.join(" | ")}`);
}

function splitAssistantText(rawText, chunkSize = 80) {
  const text = String(rawText || "").trim();
  if (!text) {
    return [];
  }
  const chunks = [];
  for (let index = 0; index < text.length; index += chunkSize) {
    chunks.push(text.slice(index, index + chunkSize));
  }
  return chunks;
}

function writeNdjson(res, events) {
  res.status(200);
  res.setHeader("Content-Type", "application/x-ndjson; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");
  if (typeof res.flushHeaders === "function") {
    res.flushHeaders();
  }
  res.end(events.map((event) => JSON.stringify(event)).join("\n") + "\n");
}

async function buildDashscopeAssistantFallback(messages, sessionId) {
  const result = await requestDashscopeChat(messages, { temperature: 0.6 });
  const rawText = normalizeText(result.rawText) || "当前未获取到有效回答，请换个问法后再试。";
  return {
    success: true,
    data: rawText,
    meta: {
      sessionId,
      provider: result.provider,
      modelName: result.modelName,
      fallbackMode: "dashscope_direct",
    },
  };
}

async function writeDashscopeAssistantFallbackStream(res, messages, sessionId) {
  const result = await requestDashscopeChat(messages, { temperature: 0.6 });
  const rawText = normalizeText(result.rawText) || "当前未获取到有效回答，请换个问法后再试。";
  const events = [
    {
      type: "meta",
      sessionId,
      provider: result.provider,
      modelName: result.modelName,
      fallbackMode: "dashscope_direct",
    },
    {
      type: "status",
      content: "已切换至千问直连模式，正在生成回答。",
    },
    ...splitAssistantText(rawText).map((content) => ({ type: "delta", content })),
    {
      type: "done",
      sessionId,
      provider: result.provider,
      modelName: result.modelName,
      fallbackMode: "dashscope_direct",
    },
  ];
  writeNdjson(res, events);
}

function buildSceneLlmPrompt(profile, availableSceneTagNames, existingSceneTagNames) {
  const sections = [
    "你是企业标签审核助手，需要为企业生成“应用场景”候选标签。",
    "要求：",
    "1. 只能把“候选正式标签列表”中的标签放进 mapped_tags。",
    "2. 如果你判断企业很可能属于某类场景，但正式标签列表里没有合适标签，把该短语放进 unmapped_terms。",
    "3. 不要编造企业事实，不要输出 markdown，不要解释过程，只返回 JSON。",
    '4. 输出格式必须是：{"mapped_tags":[{"tag_name":"","confidence":0.00,"reason":""}],"unmapped_terms":[{"term":"","confidence":0.00,"reason":""}],"summary":""}',
    "5. mapped_tags 最多 3 个，unmapped_terms 最多 3 个，confidence 取值 0.50 到 0.95。",
    `6. 已有应用场景标签：${existingSceneTagNames.length > 0 ? existingSceneTagNames.join("、") : "无"}`,
    "7. 如果证据不足，返回空数组，不要输出任何解释文字。",
    "8. 你的回复必须以 { 开始，以 } 结束。",
    "",
    "企业资料：",
    `- 企业名称：${normalizeText(profile.companyName) || "无"}`,
    `- 统一社会信用代码：${normalizeText(profile.creditCode) || "无"}`,
    `- 所属行业：${normalizeText(profile.industryBelong) || "无"}`,
    `- 所属街道：${normalizeText(profile.subdistrict) || "无"}`,
    `- 企业资质：${normalizeText(profile.qualificationLabel) || "无"}`,
    `- 注册地址：${normalizeText(profile.registerAddress) || "无"}`,
    `- 地址明细：${normalizeText(profile.registerAddressDetail) || "无"}`,
    `- 经营范围：${normalizeText(profile.businessScope) || "无"}`,
    "",
    "候选正式标签列表：",
    availableSceneTagNames.join("、"),
    "",
    "直接输出 JSON，不要补充任何前言或说明。",
  ];
  return sections.join("\n");
}

function extractJsonPayload(text) {
  const cleaned = String(text || "")
    .replace(/```json/gi, "```")
    .trim();
  const fencedMatch = cleaned.match(/```([\s\S]*?)```/);
  const candidate = fencedMatch ? fencedMatch[1].trim() : cleaned;
  const start = candidate.indexOf("{");
  const end = candidate.lastIndexOf("}");
  if (start >= 0 && end > start) {
    return candidate.slice(start, end + 1);
  }
  return candidate;
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function buildSceneFallbackReason(rawText, startIndex, tagName) {
  const text = String(rawText || "").replace(/\s+/g, " ").trim();
  if (!text) {
    return "LLM 自然语言回复中提及该场景标签";
  }
  const snippetStart = Math.max(0, startIndex - 18);
  const snippetEnd = Math.min(text.length, startIndex + tagName.length + 18);
  const snippet = text.slice(snippetStart, snippetEnd).trim();
  return snippet || "LLM 自然语言回复中提及该场景标签";
}

function collectSceneCandidatesFromText(rawText, sceneTagMap, existingSet) {
  const text = String(rawText || "").replace(/\s+/g, " ").trim();
  if (!text) {
    return [];
  }

  const mentions = [];
  for (const sceneTag of sceneTagMap.values()) {
    if (!sceneTag?.tagName || existingSet.has(sceneTag.tagName)) {
      continue;
    }
    const index = text.indexOf(sceneTag.tagName);
    if (index >= 0) {
      mentions.push({ index, sceneTag });
    }
  }

  mentions.sort((left, right) => {
    if (left.index !== right.index) {
      return left.index - right.index;
    }
    return left.sceneTag.tagName.length - right.sceneTag.tagName.length;
  });

  const mapped = [];
  const mappedSeen = new Set();
  for (const mention of mentions) {
    if (mappedSeen.has(mention.sceneTag.tagId)) continue;
    mappedSeen.add(mention.sceneTag.tagId);
    mapped.push({
      candidateType: AUTO_TAG_LLM_CANDIDATE_TYPE.MAPPED,
      status: AUTO_TAG_LLM_CANDIDATE_STATUS.PENDING,
      companyTagId: mention.sceneTag.tagId,
      candidateName: mention.sceneTag.tagName,
      normalizedName: mention.sceneTag.tagName,
      confidence: 0.68,
      reasonText: buildSceneFallbackReason(text, mention.index, mention.sceneTag.tagName),
    });
    if (mapped.length >= 3) {
      break;
    }
  }

  return mapped;
}

function isAgentFallbackAnswer(rawText) {
  const text = normalizeText(rawText).replace(/\s+/g, " ");
  return (
    text.includes("现有资料可以支持初步判断") &&
    text.includes("还不足以形成完整结论") &&
    text.includes("补充更明确的对象")
  );
}

function normalizeSceneLlmResponse(rawText, sceneTagMap, existingSceneTagNames) {
  const existingSet = new Set((existingSceneTagNames || []).map((item) => normalizeText(item)));
  const payload = safeJsonParse(extractJsonPayload(rawText));
  if (!payload) {
    const fallbackMapped = collectSceneCandidatesFromText(rawText, sceneTagMap, existingSet);
    if (fallbackMapped.length === 0) {
      throw new Error(
        `LLM 返回非 JSON，且未识别到正式标签：${normalizeText(rawText).slice(0, 120) || "空响应"}`,
      );
    }
    return {
      mapped: fallbackMapped,
      unmapped: [],
      summary: normalizeText(rawText).replace(/\s+/g, " ").slice(0, 120),
      raw: {
        parse_mode: "text_fallback",
        raw_text: normalizeText(rawText),
      },
    };
  }

  const mappedTags = Array.isArray(payload.mapped_tags) ? payload.mapped_tags : [];
  const unmappedTerms = Array.isArray(payload.unmapped_terms) ? payload.unmapped_terms : [];
  const mapped = [];
  const mappedSeen = new Set();

  for (const item of mappedTags.slice(0, 3)) {
    const tagName = normalizeText(item?.tag_name);
    if (!tagName) continue;
    const sceneTag = sceneTagMap.get(tagName);
    if (!sceneTag) continue;
    if (existingSet.has(sceneTag.tagName) || mappedSeen.has(sceneTag.tagId)) continue;
    mappedSeen.add(sceneTag.tagId);
    mapped.push({
      candidateType: AUTO_TAG_LLM_CANDIDATE_TYPE.MAPPED,
      status: AUTO_TAG_LLM_CANDIDATE_STATUS.PENDING,
      companyTagId: sceneTag.tagId,
      candidateName: sceneTag.tagName,
      normalizedName: sceneTag.tagName,
      confidence: Math.max(0.5, Math.min(0.95, Number(item?.confidence) || 0.7)),
      reasonText: normalizeText(item?.reason) || "LLM 生成场景候选",
    });
  }

  const unmapped = [];
  const unmappedSeen = new Set();
  for (const item of unmappedTerms.slice(0, 3)) {
    const term = normalizeText(item?.term);
    if (!term) continue;
    if (sceneTagMap.has(term) || existingSet.has(term) || unmappedSeen.has(term)) continue;
    unmappedSeen.add(term);
    unmapped.push({
      candidateType: AUTO_TAG_LLM_CANDIDATE_TYPE.UNMAPPED,
      status: AUTO_TAG_LLM_CANDIDATE_STATUS.UNMAPPED,
      companyTagId: null,
      candidateName: term,
      normalizedName: term,
      confidence: Math.max(0.5, Math.min(0.95, Number(item?.confidence) || 0.65)),
      reasonText: normalizeText(item?.reason) || "LLM 生成未映射场景短语",
    });
  }

  return {
    mapped,
    unmapped,
    summary: normalizeText(payload.summary),
    raw: payload,
  };
}

async function requestSceneLlmCandidates(profile, sceneTagOptions, agentUserId, existingSceneTagNames) {
  const prompt = buildSceneLlmPrompt(
    profile,
    sceneTagOptions.map((item) => item.tagName),
    existingSceneTagNames,
  );
  const messages = [
    {
      role: "system",
      content: "你是企业标签审核助手，必须严格按照用户要求输出 JSON。",
    },
    {
      role: "user",
      content: prompt,
    },
  ];
  let provider = "dashscope_compatible";
  let modelName = null;
  let rawText = "";
  let dashscopeFailureMessage = "";

  try {
    const dashscopeResult = await requestDashscopeChat(messages, {
      temperature: 0.2,
      responseFormat: { type: "json_object" },
    });
    provider = dashscopeResult.provider;
    modelName = dashscopeResult.modelName;
    rawText = dashscopeResult.rawText;
  } catch (dashscopeError) {
    dashscopeFailureMessage = dashscopeError instanceof Error ? dashscopeError.message : String(dashscopeError);
    try {
      const data = await agentRequest("/chat", {
        method: "POST",
        body: JSON.stringify({
          messages,
          sessionId: `auto-tag-llm-${crypto.randomUUID()}`,
          userId: agentUserId,
        }),
      });
      provider = "agent_chat";
      rawText = typeof data?.data === "string" ? data.data : JSON.stringify(data?.data || {});
    } catch (agentError) {
      throw new Error(
        `DashScope 与 AGENT 均不可用：${dashscopeFailureMessage} | AGENT: ${agentError instanceof Error ? agentError.message : String(agentError)}`,
      );
    }
  }

  const sceneTagMap = new Map(sceneTagOptions.map((item) => [item.tagName, item]));
  if (provider === "agent_chat" && isAgentFallbackAnswer(rawText)) {
    throw new Error(
      dashscopeFailureMessage
        ? `DashScope 不可用，且 AGENT 当前未连接可用生成模型：${dashscopeFailureMessage}`
        : "AGENT 已启动，但当前未连接可用生成模型；请补充 .env 中的 SSH/PASSWORD 以建立 6006 隧道，或恢复 DashScope 网络访问。",
    );
  }
  const normalized = normalizeSceneLlmResponse(rawText, sceneTagMap, existingSceneTagNames);
  return {
    provider,
    modelName,
    prompt,
    rawText,
    normalized,
  };
}

async function fetchBatchItemRows(batchId, page = 1, pageSize = 20) {
  const currentPage = Math.max(1, toPositiveInt(page, 1));
  const currentPageSize = Math.max(1, toPositiveInt(pageSize, 20));
  const offset = (currentPage - 1) * currentPageSize;

  const [countRows] = await pool.query(
    "SELECT COUNT(*) AS total FROM company_tag_batch_item WHERE company_tag_batch_id = ?",
    [batchId],
  );
  const [itemRows] = await pool.query(
    `
      SELECT
        i.company_tag_batch_item_id AS batchItemId,
        i.company_id AS companyId,
        i.status,
        i.tag_count AS tagCount,
        i.result_json AS resultJson,
        i.error_message AS errorMessage,
        i.started_at AS startedAt,
        i.finished_at AS finishedAt
      FROM company_tag_batch_item i
      WHERE i.company_tag_batch_id = ?
      ORDER BY i.company_id
      LIMIT ? OFFSET ?
    `,
    [batchId, currentPageSize, offset],
  );

  const companyIds = itemRows.map((row) => row.companyId);
  const companyRows = await fetchCompanyBaseRows(companyIds);
  const companyViewById = new Map(companyRows.map((row) => [row.companyId, row]));

  return {
    list: itemRows.map((row) => {
      const companyView = companyViewById.get(row.companyId);
      const result = parseJsonValue(row.resultJson, null);
      const dimensions = emptyTagBuckets();
      const tags = Array.isArray(result?.tags)
        ? result.tags.map((tag) => {
            const meta = getTagDimensionMeta(tag.company_tag_dimension_name);
            if (dimensions[meta.key]) {
              dimensions[meta.key].push(tag.company_tag_name);
            }
            return {
              id: tag.company_tag_id,
              name: tag.company_tag_name,
              dimensionId: 0,
              dimensionName: tag.company_tag_dimension_name,
              subdimensionId: 0,
              subdimensionName: tag.company_tag_subdimension_name,
            };
          })
        : [];

      return {
        key: row.companyId,
        companyId: row.companyId,
        name: companyView?.companyName || `企业 ${row.companyId}`,
        code: companyView?.creditCode || String(row.companyId),
        updateTime: companyView?.updateTime || null,
        dimensions,
        tags,
        batchItemId: row.batchItemId,
        status: row.status,
        tagCount: row.tagCount || result?.tag_count || 0,
        errorMessage: row.errorMessage || "",
        startedAt: row.startedAt,
        finishedAt: row.finishedAt,
        result,
      };
    }),
    total: countRows[0]?.total || 0,
    page: currentPage,
    pageSize: currentPageSize,
  };
}

async function fetchLlmCandidateRows(batchId, page = 1, pageSize = 20) {
  const currentPage = Math.max(1, toPositiveInt(page, 1));
  const currentPageSize = Math.max(1, toPositiveInt(pageSize, 20));
  const offset = (currentPage - 1) * currentPageSize;
  const [countRows] = await pool.query(
    "SELECT COUNT(*) AS total FROM company_tag_llm_candidate WHERE company_tag_llm_batch_id = ?",
    [batchId],
  );
  const [rows] = await pool.query(
    `
      SELECT
        c.company_tag_llm_candidate_id AS candidateId,
        c.company_id AS companyId,
        b.company_name AS companyName,
        b.credit_code AS creditCode,
        c.company_tag_id AS companyTagId,
        l.company_tag_name AS companyTagName,
        c.candidate_type AS candidateType,
        c.candidate_name AS candidateName,
        c.normalized_name AS normalizedName,
        c.status,
        c.confidence,
        c.reason_text AS reasonText,
        c.reviewed_by_user_id AS reviewedByUserId,
        c.reviewed_at AS reviewedAt,
        c.applied_at AS appliedAt,
        c.created_at AS createdAt
      FROM company_tag_llm_candidate c
      JOIN company_basic b
        ON c.company_id = b.company_id
      LEFT JOIN company_tag_library l
        ON c.company_tag_id = l.company_tag_id
      WHERE c.company_tag_llm_batch_id = ?
      ORDER BY c.created_at DESC, c.company_tag_llm_candidate_id DESC
      LIMIT ? OFFSET ?
    `,
    [batchId, currentPageSize, offset],
  );
  return {
    list: rows.map((row) => ({
      candidateId: row.candidateId,
      companyId: row.companyId,
      companyName: row.companyName,
      creditCode: row.creditCode || String(row.companyId),
      companyTagId: row.companyTagId,
      companyTagName: row.companyTagName || null,
      candidateType: row.candidateType,
      candidateName: row.candidateName,
      normalizedName: row.normalizedName,
      status: row.status,
      confidence: row.confidence === null || row.confidence === undefined ? null : Number(row.confidence),
      reasonText: row.reasonText || "",
      reviewedByUserId: row.reviewedByUserId,
      reviewedAt: row.reviewedAt,
      appliedAt: row.appliedAt,
      createdAt: row.createdAt,
    })),
    total: countRows[0]?.total || 0,
    page: currentPage,
    pageSize: currentPageSize,
  };
}

function escapeCsvCell(value) {
  const text = String(value ?? "");
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, "\"\"")}"`;
  }
  return text;
}

function buildBatchExportCsv(rows) {
  const header = [
    "批次项ID",
    "企业ID",
    "统一社会信用代码",
    "企业名称",
    "状态",
    "标签总数",
    "基本信息",
    "经营状况",
    "知识产权",
    "风险信息",
    "街道地区",
    "行业标签",
    "应用场景",
    "错误信息",
  ];

  const body = rows.map((row) => [
    row.batchItemId,
    row.companyId,
    row.code,
    row.name,
    row.status,
    row.tagCount,
    row.dimensions.basic.join(" | "),
    row.dimensions.business.join(" | "),
    row.dimensions.tech.join(" | "),
    row.dimensions.risk.join(" | "),
    row.dimensions.region.join(" | "),
    row.dimensions.industry.join(" | "),
    row.dimensions.scene.join(" | "),
    row.errorMessage || "",
  ]);

  return [header, ...body]
    .map((line) => line.map((cell) => escapeCsvCell(cell)).join(","))
    .join("\n");
}

function mergeAutoTagSummaries(summaries, companyIds) {
  const resultsByCompanyId = new Map();
  const conflicts = [];
  let ruleCount = 0;
  let assignmentCount = 0;

  for (const summary of summaries) {
    if (!summary) continue;
    ruleCount += summary.rule_count || 0;
    assignmentCount += summary.assignment_count || 0;
    if (Array.isArray(summary.conflicts)) {
      conflicts.push(...summary.conflicts);
    }
    for (const result of summary.results || []) {
      if (!resultsByCompanyId.has(result.company_id)) {
        resultsByCompanyId.set(result.company_id, {
          company_id: result.company_id,
          tag_count: 0,
          tags: [],
        });
      }
      const current = resultsByCompanyId.get(result.company_id);
      current.tags.push(...(result.tags || []));
      current.tag_count = current.tags.length;
    }
  }

  const uniqueConflictCompanyIds = new Set(conflicts.map((item) => item.company_id));
  const results = companyIds.map((companyId) => {
    const result = resultsByCompanyId.get(companyId);
    if (result) return result;
    return { company_id: companyId, tag_count: 0, tags: [] };
  });

  return {
    company_count: companyIds.length,
    rule_count: ruleCount,
    assignment_count: assignmentCount,
    conflicted_company_count: uniqueConflictCompanyIds.size,
    conflicts,
    results,
  };
}

async function applyIndustryTagMappings({ companyIds }) {
  const catalog = await ensureIndustryTagCatalog();
  const [allExistingTagRows] = await pool.query(
    `
      SELECT
        company_tag_name AS tagName,
        company_tag_subdimension_id AS subdimensionId
      FROM company_tag_library
    `,
  );
  const [allChainRows] = await pool.query(
    `
      SELECT chain_name AS tagName
      FROM chain_industry
      ORDER BY chain_id
    `,
  );
  const categoryDefinitions = await fetchIndustryCategoryDefinitions();
  const categoryTagNameById = buildIndustryCategoryTagNameMap(
    categoryDefinitions,
    allExistingTagRows,
    catalog.categorySubdimensionId,
    allChainRows.map((row) => row.tagName),
  );
  const [rawCategoryRows] = await pool.query(
    `
      SELECT DISTINCT
        m.company_id AS companyId,
        c.category_id AS categoryId
      FROM category_industry_company_map m
      JOIN category_industry c
        ON m.category_id = c.category_id
      WHERE m.company_id IN (?)
      ORDER BY m.company_id, c.category_id
    `,
    [companyIds],
  );
  const categoryTagNames = rawCategoryRows.map((row) => ({
    companyId: row.companyId,
    tagName: categoryTagNameById.get(row.categoryId),
  }));
  const uniqueCategoryTagNames = [...new Set(categoryTagNames.map((row) => row.tagName))];
  const [categoryTagRows] = uniqueCategoryTagNames.length > 0
    ? await pool.query(
        `
          SELECT company_tag_id AS companyTagId, company_tag_name AS companyTagName
          FROM company_tag_library
          WHERE company_tag_subdimension_id = ?
            AND company_tag_name IN (?)
        `,
        [catalog.categorySubdimensionId, uniqueCategoryTagNames],
      )
    : [[]];
  const categoryTagIdByName = new Map(categoryTagRows.map((row) => [row.companyTagName, row.companyTagId]));
  const categoryRows = [];
  const categorySeen = new Set();
  for (const row of categoryTagNames) {
    if (!row.tagName) continue;
    const companyTagId = categoryTagIdByName.get(row.tagName);
    if (!companyTagId) continue;
    const uniqueKey = `${row.companyId}::${companyTagId}`;
    if (categorySeen.has(uniqueKey)) continue;
    categorySeen.add(uniqueKey);
    categoryRows.push({
      companyId: row.companyId,
      companyTagId,
      companyTagName: row.tagName,
    });
  }
  const [chainRows] = await pool.query(
    `
      SELECT DISTINCT
        m.company_id AS companyId,
        l.company_tag_id AS companyTagId,
        l.company_tag_name AS companyTagName
      FROM category_industry_company_map m
      JOIN chain_industry_category_industry_map cmap
        ON m.category_id = cmap.category_id
      JOIN chain_industry ch
        ON cmap.chain_id = ch.chain_id
      JOIN company_tag_library l
        ON l.company_tag_subdimension_id = ?
       AND l.company_tag_name = ch.chain_name
      WHERE m.company_id IN (?)
      ORDER BY m.company_id, l.company_tag_id
    `,
    [catalog.chainSubdimensionId, companyIds],
  );

  await pool.query(
    `
      DELETE ctm
      FROM company_tag_map ctm
      JOIN company_tag_library l
        ON ctm.company_tag_id = l.company_tag_id
      JOIN company_tag_subdimension sd
        ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
      WHERE ctm.company_id IN (?)
        AND ctm.source = 2
        AND sd.company_tag_dimension_id = ?
    `,
    [companyIds, catalog.dimensionId],
  );

  const resultMap = new Map(
    companyIds.map((companyId) => [companyId, { company_id: companyId, tag_count: 0, tags: [] }]),
  );
  const inserts = [];
  const insertKeys = new Set();

  for (const row of chainRows) {
    const uniqueKey = `${row.companyId}::${row.companyTagId}`;
    if (insertKeys.has(uniqueKey)) continue;
    insertKeys.add(uniqueKey);
    inserts.push([row.companyId, row.companyTagId, 2, 0.88, null]);
    const result = resultMap.get(row.companyId);
    result.tags.push({
      company_tag_id: row.companyTagId,
      company_tag_name: row.companyTagName,
      company_tag_subdimension_name: INDUSTRY_CHAIN_SUBDIMENSION_NAME,
      company_tag_dimension_name: INDUSTRY_DIMENSION_NAME,
      rule_type: "industry_map",
      confidence: 0.88,
      evidence: "chain_industry_category_industry_map 命中产业链节点",
    });
  }

  for (const row of categoryRows) {
    const uniqueKey = `${row.companyId}::${row.companyTagId}`;
    if (insertKeys.has(uniqueKey)) continue;
    insertKeys.add(uniqueKey);
    inserts.push([row.companyId, row.companyTagId, 2, 0.93, null]);
    const result = resultMap.get(row.companyId);
    result.tags.push({
      company_tag_id: row.companyTagId,
      company_tag_name: row.companyTagName,
      company_tag_subdimension_name: INDUSTRY_CATEGORY_SUBDIMENSION_NAME,
      company_tag_dimension_name: INDUSTRY_DIMENSION_NAME,
      rule_type: "industry_map",
      confidence: 0.93,
      evidence: "category_industry_company_map 命中行业分类",
    });
  }

  if (inserts.length > 0) {
    await pool.query(
      `
        INSERT INTO company_tag_map (
          company_id,
          company_tag_id,
          source,
          confidence,
          user_id
        ) VALUES ?
        ON DUPLICATE KEY UPDATE
          source = VALUES(source),
          confidence = VALUES(confidence),
          user_id = VALUES(user_id),
          create_time = CURRENT_TIMESTAMP
      `,
      [inserts],
    );
  }

  const results = companyIds.map((companyId) => {
    const result = resultMap.get(companyId);
    result.tag_count = result.tags.length;
    return result;
  });

  return {
    company_count: companyIds.length,
    rule_count: inserts.length,
    assignment_count: results.reduce((sum, item) => sum + item.tag_count, 0),
    conflicted_company_count: 0,
    conflicts: [],
    results,
  };
}

async function runSelectedAutoTagEngines({ companyIds, dimensionIds }) {
  const catalog = await ensureIndustryTagCatalog();
  const industryDimensionId = catalog.dimensionId;
  const summaries = [];

  const baseDimensionIds = dimensionIds.filter((dimensionId) => dimensionId !== industryDimensionId);
  if (baseDimensionIds.length > 0) {
    summaries.push(await runAutoTagRuleScript({ companyIds, dimensionIds: baseDimensionIds }));
  }
  if (dimensionIds.includes(industryDimensionId)) {
    summaries.push(await applyIndustryTagMappings({ companyIds }));
  }

  if (summaries.length === 0) {
    return {
      company_count: companyIds.length,
      rule_count: 0,
      assignment_count: 0,
      conflicted_company_count: 0,
      conflicts: [],
      results: companyIds.map((companyId) => ({ company_id: companyId, tag_count: 0, tags: [] })),
    };
  }

  return mergeAutoTagSummaries(summaries, companyIds);
}

async function processAutoTagBatch(batchId) {
  const [batchRows] = await pool.query(
    `
      SELECT
        company_tag_batch_id AS batchId,
        dimension_ids AS dimensionIds
      FROM company_tag_batch
      WHERE company_tag_batch_id = ?
      LIMIT 1
    `,
    [batchId],
  );
  if (batchRows.length === 0) {
    return;
  }

  const [itemRows] = await pool.query(
    `
      SELECT company_id AS companyId
      FROM company_tag_batch_item
      WHERE company_tag_batch_id = ?
      ORDER BY company_id
    `,
    [batchId],
  );
  const companyIds = itemRows.map((row) => row.companyId);
  const dimensionIds = parseJsonValue(batchRows[0].dimensionIds, []) || [];

  await pool.query(
    `
      UPDATE company_tag_batch
      SET status = ?, started_at = CURRENT_TIMESTAMP, error_message = NULL
      WHERE company_tag_batch_id = ?
    `,
    [AUTO_TAG_BATCH_STATUS.RUNNING, batchId],
  );
  await pool.query(
    `
      UPDATE company_tag_batch_item
      SET status = ?, started_at = CURRENT_TIMESTAMP, error_message = NULL
      WHERE company_tag_batch_id = ?
    `,
    [AUTO_TAG_BATCH_ITEM_STATUS.PENDING, batchId],
  );

  try {
    const summary = await runSelectedAutoTagEngines({ companyIds, dimensionIds });
    const resultsByCompanyId = new Map((summary.results || []).map((item) => [item.company_id, item]));

    for (const companyId of companyIds) {
      const result = resultsByCompanyId.get(companyId) || { company_id: companyId, tag_count: 0, tags: [] };
      await pool.query(
        `
          UPDATE company_tag_batch_item
          SET
            status = ?,
            tag_count = ?,
            result_json = ?,
            error_message = NULL,
            finished_at = CURRENT_TIMESTAMP
          WHERE company_tag_batch_id = ? AND company_id = ?
        `,
        [
          AUTO_TAG_BATCH_ITEM_STATUS.SUCCESS,
          result.tag_count || 0,
          JSON.stringify(result),
          batchId,
          companyId,
        ],
      );
    }

    await pool.query(
      `
        UPDATE company_tag_batch
        SET
          status = ?,
          success_company_count = ?,
          failed_company_count = 0,
          summary_json = ?,
          finished_at = CURRENT_TIMESTAMP
        WHERE company_tag_batch_id = ?
      `,
      [
        AUTO_TAG_BATCH_STATUS.COMPLETED,
        companyIds.length,
        JSON.stringify(summary),
        batchId,
      ],
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    await pool.query(
      `
        UPDATE company_tag_batch_item
        SET
          status = ?,
          error_message = ?,
          finished_at = CURRENT_TIMESTAMP
        WHERE company_tag_batch_id = ? AND status = ?
      `,
      [
        AUTO_TAG_BATCH_ITEM_STATUS.FAILED,
        errorMessage,
        batchId,
        AUTO_TAG_BATCH_ITEM_STATUS.PENDING,
      ],
    );
    await pool.query(
      `
        UPDATE company_tag_batch
        SET
          status = ?,
          failed_company_count = requested_company_count,
          error_message = ?,
          finished_at = CURRENT_TIMESTAMP
        WHERE company_tag_batch_id = ?
      `,
      [AUTO_TAG_BATCH_STATUS.FAILED, errorMessage, batchId],
    );
  }
}

async function processSceneLlmBatch(batchId) {
  const batch = await fetchLlmBatchRow(batchId);
  if (!batch) {
    return;
  }

  await pool.query(
    `
      UPDATE company_tag_llm_batch
      SET status = ?, started_at = CURRENT_TIMESTAMP, error_message = NULL
      WHERE company_tag_llm_batch_id = ?
    `,
    [AUTO_TAG_LLM_BATCH_STATUS.RUNNING, batchId],
  );

  try {
    const [companyRows] = await pool.query(
      `
        SELECT company_id AS companyId
        FROM company_basic
        WHERE company_id IN (
          SELECT DISTINCT company_id
          FROM company_tag_llm_candidate
          WHERE company_tag_llm_batch_id = ?
        )
      `,
      [batchId],
    );

    let companyIds = companyRows.map((row) => row.companyId);
    if (companyIds.length === 0) {
      const [summaryOnlyRows] = await pool.query(
        `
          SELECT JSON_EXTRACT(summary_json, '$.company_ids') AS companyIdsJson
          FROM company_tag_llm_batch
          WHERE company_tag_llm_batch_id = ?
          LIMIT 1
        `,
        [batchId],
      );
      const companyIdsJson = summaryOnlyRows[0]?.companyIdsJson;
      if (companyIdsJson) {
        companyIds = parseJsonValue(companyIdsJson, []) || [];
      }
    }

    const [snapshotRows] = await pool.query(
      `
        SELECT summary_json AS summaryJson, requested_by_user_id AS requestedByUserId
        FROM company_tag_llm_batch
        WHERE company_tag_llm_batch_id = ?
        LIMIT 1
      `,
      [batchId],
    );
    const summarySnapshot = parseJsonValue(snapshotRows[0]?.summaryJson, {}) || {};
    const requestedCompanyIds = Array.isArray(summarySnapshot.company_ids)
      ? normalizeIntList(summarySnapshot.company_ids)
      : companyIds;
    const profiles = await fetchSceneLlmProfiles(requestedCompanyIds);
    const sceneTagOptions = await fetchSceneTagOptions();
    const existingSceneTagsByCompany = await fetchCurrentSceneTagsByCompany(requestedCompanyIds);
    const agentUserId = await resolveAgentUserId(snapshotRows[0]?.requestedByUserId);

    await pool.query(
      "DELETE FROM company_tag_llm_candidate WHERE company_tag_llm_batch_id = ?",
      [batchId],
    );

    const inserts = [];
    const results = [];
    let successCompanyCount = 0;
    let failedCompanyCount = 0;
    let mappedCount = 0;
    let unmappedCount = 0;
    let provider = batch.provider || "agent_chat";
    let modelName = batch.modelName || null;

    for (const profile of profiles) {
      try {
        const llmResult = await requestSceneLlmCandidates(
          profile,
          sceneTagOptions,
          agentUserId,
          existingSceneTagsByCompany.get(profile.companyId) || [],
        );
        const normalizedCandidates = [...llmResult.normalized.mapped, ...llmResult.normalized.unmapped];
        provider = llmResult.provider || provider;
        modelName = llmResult.modelName || modelName;
        for (const candidate of normalizedCandidates) {
          inserts.push([
            batchId,
            profile.companyId,
            candidate.companyTagId,
            candidate.candidateType,
            candidate.candidateName,
            candidate.normalizedName,
            candidate.status,
            candidate.confidence,
            candidate.reasonText,
            JSON.stringify({
              companyName: profile.companyName,
              industryBelong: profile.industryBelong,
              businessScope: profile.businessScope,
              existingSceneTags: existingSceneTagsByCompany.get(profile.companyId) || [],
            }),
            llmResult.prompt,
            llmResult.rawText,
            JSON.stringify(llmResult.normalized.raw),
            batch.requestedByUserId || null,
          ]);
        }

        mappedCount += llmResult.normalized.mapped.length;
        unmappedCount += llmResult.normalized.unmapped.length;
        successCompanyCount += 1;
        results.push({
          company_id: profile.companyId,
          mapped_count: llmResult.normalized.mapped.length,
          unmapped_count: llmResult.normalized.unmapped.length,
          summary: llmResult.normalized.summary,
        });
      } catch (error) {
        failedCompanyCount += 1;
        results.push({
          company_id: profile.companyId,
          mapped_count: 0,
          unmapped_count: 0,
          error_message: error.message,
        });
      }
    }

    if (inserts.length > 0) {
      await pool.query(
        `
          INSERT INTO company_tag_llm_candidate (
            company_tag_llm_batch_id,
            company_id,
            company_tag_id,
            candidate_type,
            candidate_name,
            normalized_name,
            status,
            confidence,
            reason_text,
            evidence_json,
            prompt_text,
            raw_response,
            response_json,
            created_by_user_id
          ) VALUES ?
        `,
        [inserts],
      );
    }

    await pool.query(
      `
        UPDATE company_tag_llm_batch
        SET
          status = ?,
          provider = ?,
          model_name = ?,
          success_company_count = ?,
          failed_company_count = ?,
          summary_json = ?,
          finished_at = CURRENT_TIMESTAMP
        WHERE company_tag_llm_batch_id = ?
      `,
      [
        AUTO_TAG_LLM_BATCH_STATUS.COMPLETED,
        provider,
        modelName,
        successCompanyCount,
        failedCompanyCount,
        JSON.stringify({
          company_ids: requestedCompanyIds,
          mapped_count: mappedCount,
          unmapped_count: unmappedCount,
          results,
        }),
        batchId,
      ],
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    await pool.query(
      `
        UPDATE company_tag_llm_batch
        SET
          status = ?,
          failed_company_count = requested_company_count,
          error_message = ?,
          finished_at = CURRENT_TIMESTAMP
        WHERE company_tag_llm_batch_id = ?
      `,
      [AUTO_TAG_LLM_BATCH_STATUS.FAILED, errorMessage, batchId],
    );
  }
}

async function runAutoTagRuleScript({ companyIds, dimensionIds }) {
  const reportPath = path.join(PROJECT_ROOT, "SQL", "tmp", `company-tag-auto-rule-run-${Date.now()}.md`);
  const args = [
    AUTO_TAG_RULE_SCRIPT,
    "--env-file",
    path.join(PROJECT_ROOT, ".env"),
    "--report",
    reportPath,
    "--apply",
    "--json-output",
  ];

  if (companyIds.length > 0) {
    args.push("--company-ids", companyIds.join(","));
  }
  if (dimensionIds.length > 0) {
    args.push("--dimension-ids", dimensionIds.join(","));
  }

  const { stdout } = await execFileAsync("python3", args, {
    cwd: PROJECT_ROOT,
    maxBuffer: 1024 * 1024 * 8,
  });

  const jsonText = stdout
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .find((line) => line.startsWith("{") && line.endsWith("}"));

  if (!jsonText) {
    throw new Error("自动打标脚本未返回可解析结果");
  }

  return JSON.parse(jsonText);
}

async function runImportAutoTagEvaluateScript({ records, dimensionIds }) {
  const inputPath = path.join(os.tmpdir(), `import-auto-tag-${Date.now()}-${crypto.randomBytes(4).toString("hex")}.json`);
  await fs.writeFile(
    inputPath,
    JSON.stringify({
      records,
      dimension_ids: dimensionIds,
    }),
    "utf-8",
  );

  try {
    const { stdout } = await execFileAsync("python3", [IMPORT_AUTO_TAG_EVALUATE_SCRIPT, "--input-json", inputPath], {
      cwd: PROJECT_ROOT,
      maxBuffer: 1024 * 1024 * 8,
    });
    const jsonText = stdout
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .find((line) => line.startsWith("{") && line.endsWith("}"));

    if (!jsonText) {
      throw new Error("导入前自动打标签脚本未返回可解析结果");
    }

    return JSON.parse(jsonText);
  } finally {
    await fs.unlink(inputPath).catch(() => {});
  }
}

async function fetchImportAutoTagRecordsByCompanyIds(companyIds) {
  if (!Array.isArray(companyIds) || companyIds.length === 0) {
    return [];
  }

  const [rows] = await pool.query(
    `
      SELECT
        b.company_id AS companyId,
        b.company_name AS company_name,
        b.credit_code AS credit_code,
        DATE_FORMAT(b.establish_date, '%Y-%m-%d') AS establish_date,
        b.register_capital AS register_capital,
        b.paid_capital AS paid_capital,
        b.employee_count AS employee_count,
        b.insured_count AS insured_count,
        b.contact_phone AS contact_phone,
        b.email_business AS email_business,
        b.register_address AS register_address,
        b.register_address_detail AS register_address_detail,
        b.business_scope AS business_scope,
        b.qualification_label AS qualification_label,
        b.industry_belong AS industry_belong,
        b.subdistrict AS subdistrict,
        b.is_micro_enterprise AS is_micro_enterprise,
        b.is_general_taxpayer AS is_general_taxpayer,
        b.has_recruitment AS has_recruitment,
        b.has_patent AS has_patent,
        b.has_work_copyright AS has_work_copyright,
        b.has_software_copyright AS has_software_copyright,
        b.is_high_tech_enterprise AS is_high_tech_enterprise,
        b.has_dishonest_execution AS has_dishonest_execution,
        b.has_chattel_mortgage AS has_chattel_mortgage,
        b.has_business_abnormal AS has_business_abnormal,
        b.has_legal_document AS has_legal_document,
        b.has_admin_penalty AS has_admin_penalty,
        b.has_bankruptcy_overlap AS has_bankruptcy_overlap,
        b.has_env_penalty AS has_env_penalty,
        b.has_equity_freeze AS has_equity_freeze,
        b.has_executed_person AS has_executed_person,
        COALESCE(c.branch_count, 0) AS branch_count,
        COALESCE(c.recruit_count, 0) AS recruit_count,
        COALESCE(c.patent_count, 0) AS patent_count,
        COALESCE(c.work_copyright_count, 0) AS work_copyright_count,
        COALESCE(c.software_copyright_count, 0) AS software_copyright_count,
        COALESCE(c.dishonest_execution_count, 0) AS dishonest_execution_count,
        COALESCE(c.chattel_mortgage_count, 0) AS chattel_mortgage_count,
        COALESCE(c.business_abnormal_count, 0) AS business_abnormal_count,
        COALESCE(c.legal_doc_all_count, 0) AS legal_doc_all_count,
        COALESCE(c.admin_penalty_count, 0) AS admin_penalty_count,
        COALESCE(c.bankruptcy_overlap_count, 0) AS bankruptcy_overlap_count,
        COALESCE(c.env_penalty_count, 0) AS env_penalty_count,
        COALESCE(c.equity_freeze_count, 0) AS equity_freeze_count,
        COALESCE(c.executed_person_count, 0) AS executed_person_count
      FROM company_basic b
      LEFT JOIN company_basic_count c
        ON b.company_id = c.company_id
      WHERE b.company_id IN (?)
      ORDER BY b.company_id
    `,
    [companyIds],
  );

  return rows.map((row) => ({
    ...row,
    company_name: normalizeText(row.company_name),
    credit_code: normalizeText(row.credit_code).toUpperCase(),
    establish_date: normalizeText(row.establish_date),
    contact_phone: normalizeText(row.contact_phone),
    email_business: normalizeText(row.email_business),
    register_address: normalizeText(row.register_address),
    register_address_detail: normalizeText(row.register_address_detail),
    business_scope: normalizeText(row.business_scope),
    qualification_label: normalizeText(row.qualification_label),
    industry_belong: normalizeText(row.industry_belong),
    subdistrict: normalizeText(row.subdistrict),
  }));
}

// ==========================================
// 1. 用户认证模块 (Auth)
// ==========================================

function normalizeText(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/\r/g, "").trim();
}

function isAdminRole(role) {
  return normalizeText(role).toUpperCase() === "ADMIN";
}

function requireAdmin(req, res, next) {
  if (!req.authUser) {
    return res.status(401).json({ success: false, message: "请先登录" });
  }
  if (!isAdminRole(req.authUser.role)) {
    return res.status(403).json({ success: false, message: "仅系统管理员可执行此操作" });
  }
  next();
}

function parseDateInput(value) {
  const text = normalizeText(value);
  if (!text) {
    return null;
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return text;
  }
  if (/^\d{4}\/\d{2}\/\d{2}$/.test(text)) {
    return text.replace(/\//g, "-");
  }
  const normalized = text.slice(0, 10).replace(/\//g, "-");
  if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
    return normalized;
  }
  return null;
}

function parseDecimalInput(value) {
  const text = normalizeText(value).replace(/,/g, "");
  if (!text) {
    return null;
  }
  const numeric = Number(text);
  return Number.isFinite(numeric) ? numeric : null;
}

function parseIntegerInput(value) {
  const text = normalizeText(value).replace(/,/g, "");
  if (!text) {
    return null;
  }
  const numeric = Number.parseInt(text, 10);
  return Number.isFinite(numeric) ? numeric : null;
}

function formatDateOutput(value) {
  if (!value) {
    return "";
  }
  if (value instanceof Date) {
    return value.toISOString().slice(0, 10);
  }
  return normalizeText(value).slice(0, 10);
}

function normalizeCsvHeader(value) {
  return normalizeText(value)
    .toLowerCase()
    .replace(/\uFEFF/g, "")
    .replace(/\s+/g, "_");
}

function parseCsvText(content) {
  const rows = [];
  let currentField = "";
  let currentRow = [];
  let inQuotes = false;

  for (let index = 0; index < content.length; index += 1) {
    const char = content[index];
    const nextChar = content[index + 1];

    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        currentField += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      currentRow.push(currentField);
      currentField = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && nextChar === "\n") {
        index += 1;
      }
      currentRow.push(currentField);
      rows.push(currentRow);
      currentField = "";
      currentRow = [];
      continue;
    }

    currentField += char;
  }

  if (currentField.length > 0 || currentRow.length > 0) {
    currentRow.push(currentField);
    rows.push(currentRow);
  }

  return rows.filter((row) => row.some((cell) => normalizeText(cell) !== ""));
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function buildCsvContent(rows) {
  return rows.map((row) => row.map((cell) => csvEscape(cell)).join(",")).join("\n");
}

const IMPORT_TEMPLATE_HEADERS = [
  "company_name",
  "credit_code",
];

function coerceImportCandidate(row, rowIndex) {
  return {
    rowIndex,
    companyName: normalizeText(row.company_name),
    creditCode: normalizeText(row.credit_code).toUpperCase(),
    establishDate: normalizeText(row.establish_date),
    registerCapital: normalizeText(row.register_capital),
    paidCapital: normalizeText(row.paid_capital),
    employeeCount: normalizeText(row.employee_count),
    insuredCount: normalizeText(row.insured_count),
    contactPhone: normalizeText(row.contact_phone),
    emailBusiness: normalizeText(row.email_business),
    registerAddress: normalizeText(row.register_address),
    registerAddressDetail: normalizeText(row.register_address_detail),
    businessScope: normalizeText(row.business_scope),
    qualificationLabel: normalizeText(row.qualification_label),
    industryBelong: normalizeText(row.industry_belong),
    subdistrict: normalizeText(row.subdistrict),
  };
}

function serializeImportCandidate(candidate) {
  return {
    row_index: candidate.rowIndex,
    company_name: candidate.companyName,
    credit_code: candidate.creditCode,
    establish_date: candidate.establishDate,
    register_capital: candidate.registerCapital,
    paid_capital: candidate.paidCapital,
    employee_count: candidate.employeeCount,
    insured_count: candidate.insuredCount,
    contact_phone: candidate.contactPhone,
    email_business: candidate.emailBusiness,
    register_address: candidate.registerAddress,
    register_address_detail: candidate.registerAddressDetail,
    business_scope: candidate.businessScope,
    qualification_label: candidate.qualificationLabel,
    industry_belong: candidate.industryBelong,
    subdistrict: candidate.subdistrict,
  };
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
  const nextSessionId = sessionId || crypto.randomUUID();
  try {
    const data = await agentRequest("/chat", {
      method: "POST",
      body: JSON.stringify({
        messages,
        sessionId: nextSessionId,
        userId: req.authUser.id,
      }),
    });
    res.json(data);
  } catch (_error) {
    try {
      const fallback = await buildDashscopeAssistantFallback(messages, nextSessionId);
      res.json(fallback);
    } catch (fallbackError) {
      res.json({
        success: false,
        message: `AGENT 与千问直连均不可用。AGENT: ${AGENT_API_URL}；错误：${fallbackError.message}`,
      });
    }
  }
});

app.post("/api/chat/stream", requireAuth, async (req, res) => {
  const { messages, sessionId } = req.body;
  const nextSessionId = sessionId || crypto.randomUUID();
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
        sessionId: nextSessionId,
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
    try {
      await writeDashscopeAssistantFallbackStream(res, messages, nextSessionId);
    } catch (fallbackError) {
      writeNdjson(res, [
        {
          type: "error",
          message: `AGENT 与千问直连均不可用。AGENT: ${error.message}；千问: ${fallbackError.message}`,
        },
      ]);
    }
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

// --- 系统管理：标签管理 ---

/**
 * 标签管理：获取企业列表及聚合标签
 */
app.get("/api/tags/companies", async (req, res) => {
  const { page = 1, pageSize = 10, keyword = "" } = req.query;
  const currentPage = toPositiveInt(page, 1);
  const currentPageSize = toPositiveInt(pageSize, 10);
  const offset = (currentPage - 1) * currentPageSize;
  try {
    let where = "WHERE 1=1";
    const params = [];
    const normalizedKeyword = normalizeText(keyword);
    if (normalizedKeyword) {
      where += " AND (company_name LIKE ? OR credit_code LIKE ?)";
      params.push(`%${normalizedKeyword}%`, `%${normalizedKeyword}%`);
    }

    const [totalRows] = await pool.query(
      `SELECT COUNT(*) AS total FROM company_basic ${where}`,
      params,
    );
    const [rows] = await pool.query(
      `
        SELECT
          company_id AS companyId,
          company_name AS companyName,
          credit_code AS creditCode,
          updated_at AS updateTime
        FROM company_basic
        ${where}
        ORDER BY updated_at DESC, company_id DESC
        LIMIT ? OFFSET ?
      `,
      [...params, currentPageSize, offset],
    );

    if (rows.length === 0) {
      return res.json({ success: true, data: { list: [], total: 0 } });
    }

    const tagRows = await fetchCompanyTags(rows.map((row) => row.companyId));
    const list = buildCompanyTagView(rows, tagRows);
    res.json({ success: true, data: { list, total: totalRows[0].total } });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

/**
 * 标签管理：添加标签
 */
app.post("/api/tags/add", async (req, res) => {
  const companyId = toPositiveInt(req.body.companyId, 0);
  const tagId = toPositiveInt(req.body.tagId, 0);
  const tagName = normalizeText(req.body.tagName);
  try {
    if (!companyId || (!tagId && !tagName)) {
      return res.status(400).json({ success: false, message: "缺少企业或标签参数" });
    }

    let resolvedTagId = tagId;
    if (!resolvedTagId) {
      const [tagRows] = await pool.query(
        "SELECT company_tag_id FROM company_tag_library WHERE company_tag_name = ? LIMIT 1",
        [tagName],
      );
      if (tagRows.length === 0) {
        return res.status(400).json({ success: false, message: "标签不存在" });
      }
      resolvedTagId = tagRows[0].company_tag_id;
    }

    await pool.query(
      `
        INSERT INTO company_tag_map (company_id, company_tag_id, source, confidence, user_id)
        VALUES (?, ?, 1, 1.00, NULL)
        ON DUPLICATE KEY UPDATE source = VALUES(source), confidence = VALUES(confidence), create_time = CURRENT_TIMESTAMP
      `,
      [companyId, resolvedTagId],
    );
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

/**
 * 标签管理：删除标签
 */
app.post("/api/tags/delete", async (req, res) => {
  const companyId = toPositiveInt(req.body.companyId, 0);
  const tagId = toPositiveInt(req.body.tagId, 0);
  const tagName = normalizeText(req.body.tagName);
  try {
    if (!companyId || (!tagId && !tagName)) {
      return res.status(400).json({ success: false, message: "缺少企业或标签参数" });
    }

    let resolvedTagId = tagId;
    if (!resolvedTagId) {
      const [tagRows] = await pool.query(
        "SELECT company_tag_id FROM company_tag_library WHERE company_tag_name = ? LIMIT 1",
        [tagName],
      );
      resolvedTagId = tagRows[0]?.company_tag_id || 0;
    }

    if (resolvedTagId) {
      await pool.query(
        "DELETE FROM company_tag_map WHERE company_id = ? AND company_tag_id = ?",
        [companyId, resolvedTagId],
      );
    }
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

/**
 * 标签管理：全部标签可选项
 */
app.get("/api/tags/library/options", async (_req, res) => {
  try {
    res.json({ success: true, data: await fetchTagLibraryOptions() });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

/**
 * 标签管理：维度统计
 */
app.get("/api/tags/dimensions/stats", async (req, res) => {
  try {
    await ensureIndustryTagCatalog();
    const [totalRows] = await pool.query("SELECT COUNT(*) AS total FROM company_basic");
    const [coveredRows] = await pool.query("SELECT COUNT(DISTINCT company_id) AS total FROM company_tag_map");
    const totalCompanies = totalRows[0].total || 1;
    const [rows] = await pool.query(
      `
        SELECT
          d.company_tag_dimension_id AS id,
          d.company_tag_dimension_name AS name,
          COUNT(DISTINCT l.company_tag_id) AS tagCount,
          COUNT(DISTINCT m.company_id) AS usedCount
        FROM company_tag_dimension d
        LEFT JOIN company_tag_subdimension sd
          ON d.company_tag_dimension_id = sd.company_tag_dimension_id
        LEFT JOIN company_tag_library l
          ON sd.company_tag_subdimension_id = l.company_tag_subdimension_id
        LEFT JOIN company_tag_map m
          ON l.company_tag_id = m.company_tag_id
        GROUP BY d.company_tag_dimension_id, d.company_tag_dimension_name, d.sort_order
        ORDER BY d.sort_order, d.company_tag_dimension_id
      `,
    );

    const data = rows.map((row) => {
      const meta = getTagDimensionMeta(row.name);
      return {
        ...row,
        key: meta.key,
        color: meta.color,
        coverage: Math.round((row.usedCount / totalCompanies) * 100),
      };
    });

    res.json({
      success: true,
      data: {
        dimensions: data,
        overview: {
          totalTags: data.reduce((sum, item) => sum + item.tagCount, 0),
          coveredEnterprises: coveredRows[0]?.total || 0,
          totalCompanies: totalRows[0].total || 0,
        },
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

/**
 * 标签管理：维度详情
 */
app.get("/api/tags/dimensions/:dimensionId/detail", async (req, res) => {
  const dimensionId = toPositiveInt(req.params.dimensionId, 0);
  const subdimensionId = toPositiveInt(req.query.subdimensionId, 0);
  const tagId = toPositiveInt(req.query.tagId, 0);
  const companyPage = Math.max(1, toPositiveInt(req.query.companyPage, 1));
  const companyPageSize = Math.max(1, toPositiveInt(req.query.companyPageSize, 10));
  const companyOffset = (companyPage - 1) * companyPageSize;
  const keyword = normalizeText(req.query.keyword);
  try {
    await ensureIndustryTagCatalog();
    if (!dimensionId) {
      return res.status(400).json({ success: false, message: "无效的维度 ID" });
    }

    const [dimensionRows] = await pool.query(
      `
        SELECT
          d.company_tag_dimension_id AS id,
          d.company_tag_dimension_name AS name,
          d.company_tag_dimension_des AS description,
          COUNT(DISTINCT l.company_tag_id) AS tagCount,
          COUNT(DISTINCT m.company_id) AS usedCount
        FROM company_tag_dimension d
        LEFT JOIN company_tag_subdimension sd
          ON d.company_tag_dimension_id = sd.company_tag_dimension_id
        LEFT JOIN company_tag_library l
          ON sd.company_tag_subdimension_id = l.company_tag_subdimension_id
        LEFT JOIN company_tag_map m
          ON l.company_tag_id = m.company_tag_id
        WHERE d.company_tag_dimension_id = ?
        GROUP BY d.company_tag_dimension_id, d.company_tag_dimension_name, d.company_tag_dimension_des
      `,
      [dimensionId],
    );

    if (dimensionRows.length === 0) {
      return res.status(404).json({ success: false, message: "未找到标签维度" });
    }

    const [totalCompanyRows] = await pool.query("SELECT COUNT(*) AS total FROM company_basic");
    const [subdimensionRows] = await pool.query(
      `
        SELECT
          sd.company_tag_subdimension_id AS id,
          sd.company_tag_subdimension_name AS name,
          COUNT(DISTINCT l.company_tag_id) AS tagCount,
          COUNT(DISTINCT m.company_id) AS usedCount
        FROM company_tag_subdimension sd
        LEFT JOIN company_tag_library l
          ON sd.company_tag_subdimension_id = l.company_tag_subdimension_id
        LEFT JOIN company_tag_map m
          ON l.company_tag_id = m.company_tag_id
        WHERE sd.company_tag_dimension_id = ?
        GROUP BY sd.company_tag_subdimension_id, sd.company_tag_subdimension_name, sd.sort_order
        ORDER BY sd.sort_order, sd.company_tag_subdimension_id
      `,
      [dimensionId],
    );
    const [tagRows] = await pool.query(
      `
        SELECT
          l.company_tag_id AS id,
          l.company_tag_name AS name,
          sd.company_tag_subdimension_id AS subdimensionId,
          sd.company_tag_subdimension_name AS subdimensionName,
          COUNT(DISTINCT m.company_id) AS usedCount
        FROM company_tag_library l
        JOIN company_tag_subdimension sd
          ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
        LEFT JOIN company_tag_map m
          ON l.company_tag_id = m.company_tag_id
        WHERE sd.company_tag_dimension_id = ?
        GROUP BY l.company_tag_id, l.company_tag_name, sd.company_tag_subdimension_id, sd.company_tag_subdimension_name, sd.sort_order, l.sort_order
        ORDER BY sd.sort_order, l.sort_order, l.company_tag_name
      `,
      [dimensionId],
    );
    const companyFilterConditions = ["sd.company_tag_dimension_id = ?"];
    const companyFilterParams = [dimensionId];
    if (subdimensionId) {
      companyFilterConditions.push("sd.company_tag_subdimension_id = ?");
      companyFilterParams.push(subdimensionId);
    }
    if (tagId) {
      companyFilterConditions.push("l.company_tag_id = ?");
      companyFilterParams.push(tagId);
    }
    if (keyword) {
      companyFilterConditions.push("(b.company_name LIKE ? OR b.credit_code LIKE ?)");
      companyFilterParams.push(`%${keyword}%`, `%${keyword}%`);
    }

    const [companyCountRows] = await pool.query(
      `
        SELECT COUNT(DISTINCT b.company_id) AS total
        FROM company_basic b
        JOIN company_tag_map m
          ON b.company_id = m.company_id
        JOIN company_tag_library l
          ON m.company_tag_id = l.company_tag_id
        JOIN company_tag_subdimension sd
          ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
        WHERE ${companyFilterConditions.join(" AND ")}
      `,
      companyFilterParams,
    );
    const [matchedCompanyRows] = await pool.query(
      `
        SELECT
          b.company_id AS companyId,
          b.company_name AS companyName,
          b.credit_code AS creditCode,
          MAX(m.create_time) AS lastMatchedUsed
        FROM company_basic b
        JOIN company_tag_map m
          ON b.company_id = m.company_id
        JOIN company_tag_library l
          ON m.company_tag_id = l.company_tag_id
        JOIN company_tag_subdimension sd
          ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
        WHERE ${companyFilterConditions.join(" AND ")}
        GROUP BY b.company_id, b.company_name, b.credit_code
        ORDER BY lastMatchedUsed DESC, b.company_id DESC
        LIMIT ? OFFSET ?
      `,
      [...companyFilterParams, companyPageSize, companyOffset],
    );
    const matchedCompanyIds = matchedCompanyRows.map((row) => row.companyId);
    let companyList = [];
    if (matchedCompanyIds.length > 0) {
      const companyTagConditions = ["sd.company_tag_dimension_id = ?", "b.company_id IN (?)"];
      const companyTagParams = [dimensionId, matchedCompanyIds];
      if (subdimensionId) {
        companyTagConditions.push("sd.company_tag_subdimension_id = ?");
        companyTagParams.push(subdimensionId);
      }
      const [companyTagRows] = await pool.query(
        `
          SELECT
            b.company_id AS companyId,
            COUNT(DISTINCT m.company_tag_id) AS tagCount,
            GROUP_CONCAT(DISTINCT l.company_tag_name ORDER BY l.company_tag_name SEPARATOR '||') AS tagNames,
            MAX(m.create_time) AS lastUsed
          FROM company_basic b
          JOIN company_tag_map m
            ON b.company_id = m.company_id
          JOIN company_tag_library l
            ON m.company_tag_id = l.company_tag_id
          JOIN company_tag_subdimension sd
            ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
          WHERE ${companyTagConditions.join(" AND ")}
          GROUP BY b.company_id
        `,
        companyTagParams,
      );
      const companyTagMap = new Map(companyTagRows.map((row) => [row.companyId, row]));
      companyList = matchedCompanyRows.map((row) => {
        const summary = companyTagMap.get(row.companyId);
        return {
          id: row.companyId,
          name: row.companyName,
          code: row.creditCode || String(row.companyId),
          tagCount: summary?.tagCount || 0,
          tags: summary?.tagNames ? summary.tagNames.split("||") : [],
          lastUsed: summary?.lastUsed || row.lastMatchedUsed,
        };
      });
    }

    const meta = getTagDimensionMeta(dimensionRows[0].name);
    const totalCompanies = totalCompanyRows[0]?.total || 0;
    const topTags = [...tagRows]
      .sort((left, right) => right.usedCount - left.usedCount || left.name.localeCompare(right.name, "zh-CN"))
      .slice(0, 8);
    const topSubdimension = [...subdimensionRows]
      .sort((left, right) => right.usedCount - left.usedCount || right.tagCount - left.tagCount)[0] || null;
    const industryHighlights = meta.key === "industry"
      ? {
          chain: subdimensionRows.find((row) => row.name === INDUSTRY_CHAIN_SUBDIMENSION_NAME) || null,
          category: subdimensionRows.find((row) => row.name === INDUSTRY_CATEGORY_SUBDIMENSION_NAME) || null,
        }
      : null;
    res.json({
      success: true,
      data: {
        dimension: {
          ...dimensionRows[0],
          key: meta.key,
          color: meta.color,
          description: dimensionRows[0].description || `${dimensionRows[0].name}标签管理`,
          coverage: totalCompanies > 0 ? Math.round((dimensionRows[0].usedCount / totalCompanies) * 100) : 0,
          totalCompanies,
        },
        subdimensions: subdimensionRows,
        tags: tagRows,
        highlights: {
          topSubdimension,
          topTags,
          industry: industryHighlights,
        },
        filters: {
          subdimensionId,
          tagId,
          keyword,
        },
        companies: {
          list: companyList,
          total: companyCountRows[0]?.total || 0,
          page: companyPage,
          pageSize: companyPageSize,
        },
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

/**
 * 自动打标：维度配置
 */
app.get("/api/auto-tag/import/template", async (_req, res) => {
  const rows = [
    IMPORT_TEMPLATE_HEADERS,
    ["示例科技有限公司", "91110105MA12345678"],
  ];
  const csvContent = buildCsvContent(rows);
  res.setHeader("Content-Type", "text/csv; charset=utf-8");
  res.setHeader("Content-Disposition", 'attachment; filename="auto-tag-import-template.csv"');
  res.send(`\uFEFF${csvContent}`);
});

app.post("/api/auto-tag/import/preview", async (req, res) => {
  const csvText = String(req.body?.csvText || "");
  if (!csvText.trim()) {
    return res.status(400).json({ success: false, message: "请提供 CSV 内容" });
  }

  try {
    const rows = parseCsvText(csvText);
    if (rows.length < 2) {
      return res.status(400).json({ success: false, message: "CSV 至少需要表头和一行数据" });
    }

    const headers = rows[0].map((value) => normalizeCsvHeader(value));
    const requiredHeaders = ["company_name", "credit_code"];
    const missingHeaders = requiredHeaders.filter((header) => !headers.includes(header));
    if (missingHeaders.length > 0) {
      return res.status(400).json({ success: false, message: `缺少必填列：${missingHeaders.join("、")}` });
    }

    const fileCreditCodeSeen = new Set();
    const fileCompanyNameSeen = new Set();
    const parsedRows = [];
    const invalidRows = [];

    for (let index = 1; index < rows.length; index += 1) {
      const cells = rows[index];
      const raw = {};
      headers.forEach((header, headerIndex) => {
        raw[header] = normalizeText(cells[headerIndex] || "");
      });

      const candidate = coerceImportCandidate(raw, index + 1);
      if (!candidate.companyName || !candidate.creditCode) {
        invalidRows.push({
          rowIndex: candidate.rowIndex,
          companyName: candidate.companyName,
          creditCode: candidate.creditCode,
          reason: "缺少企业名称或统一社会信用代码",
        });
        continue;
      }

      let duplicateReason = "";
      if (candidate.creditCode) {
        if (fileCreditCodeSeen.has(candidate.creditCode)) {
          duplicateReason = "上传文件内统一社会信用代码重复";
        } else {
          fileCreditCodeSeen.add(candidate.creditCode);
        }
      }

      const nameKey = candidate.companyName;
      if (!duplicateReason) {
        if (fileCompanyNameSeen.has(nameKey)) {
          duplicateReason = "上传文件内企业名称重复";
        } else {
          fileCompanyNameSeen.add(nameKey);
        }
      }

      parsedRows.push({
        ...candidate,
        duplicateReason,
      });
    }

    const creditCodes = parsedRows.map((item) => item.creditCode).filter(Boolean);
    const companyNames = parsedRows.map((item) => item.companyName).filter(Boolean);

    const [dbRows] = await pool.query(
      `
        SELECT
          b.company_id AS companyId,
          b.company_name AS companyName,
          b.credit_code AS creditCode,
          COUNT(DISTINCT m.company_tag_id) AS tagCount
        FROM company_basic b
        LEFT JOIN company_tag_map m
          ON b.company_id = m.company_id
        WHERE UPPER(b.credit_code) IN (?)
          OR b.company_name IN (?)
        GROUP BY b.company_id, b.company_name, b.credit_code
      `,
      [creditCodes.length > 0 ? creditCodes : [""], companyNames.length > 0 ? companyNames : [""]],
    );

    const dbByCreditCode = new Map();
    const dbByCompanyName = new Map();
    for (const row of dbRows) {
      if (row.creditCode) {
        dbByCreditCode.set(String(row.creditCode).toUpperCase(), row);
      }
      if (!dbByCompanyName.has(row.companyName)) {
        dbByCompanyName.set(row.companyName, []);
      }
      dbByCompanyName.get(row.companyName).push(row);
    }

    const existingCompanies = [];
    const duplicateCompanies = [];
    const newCompanies = [];

    for (const candidate of parsedRows) {
      const creditCodeMatch = candidate.creditCode ? dbByCreditCode.get(candidate.creditCode) : null;
      const companyNameMatches = dbByCompanyName.get(candidate.companyName) || [];

      if (candidate.duplicateReason) {
        duplicateCompanies.push({
          ...candidate,
          reason: candidate.duplicateReason,
        });
        continue;
      }

      if (!creditCodeMatch && companyNameMatches.length === 0) {
        invalidRows.push({
          rowIndex: candidate.rowIndex,
          companyName: candidate.companyName,
          creditCode: candidate.creditCode,
          reason: "企业尚未入库，当前自动打标签仅支持已导入但未打标的企业",
        });
        continue;
      }

      if (creditCodeMatch) {
        if (normalizeText(creditCodeMatch.companyName) === candidate.companyName) {
          const matched = {
            ...candidate,
            matchedCompanyId: creditCodeMatch.companyId,
            matchedCompanyName: creditCodeMatch.companyName,
            matchedCreditCode: creditCodeMatch.creditCode,
          };
          if (Number(creditCodeMatch.tagCount || 0) > 0) {
            existingCompanies.push({
              ...matched,
              reason: "企业已在库且已有标签",
            });
          } else {
            newCompanies.push({
              ...matched,
              reason: "企业已在库且尚未打标，可进入自动打标",
            });
          }
        } else {
          duplicateCompanies.push({
            ...candidate,
            reason: `统一社会信用代码已存在于企业“${creditCodeMatch.companyName}”`,
            matchedCompanyId: creditCodeMatch.companyId,
            matchedCompanyName: creditCodeMatch.companyName,
            matchedCreditCode: creditCodeMatch.creditCode,
          });
        }
        continue;
      }

      if (companyNameMatches.length > 0) {
        const exactCodeMatch = companyNameMatches.find((row) =>
          candidate.creditCode && normalizeText(row.creditCode).toUpperCase() === candidate.creditCode,
        );
        if (exactCodeMatch) {
          const matched = {
            ...candidate,
            matchedCompanyId: exactCodeMatch.companyId,
            matchedCompanyName: exactCodeMatch.companyName,
            matchedCreditCode: exactCodeMatch.creditCode,
          };
          if (Number(exactCodeMatch.tagCount || 0) > 0) {
            existingCompanies.push({
              ...matched,
              reason: "企业已在库且已有标签",
            });
          } else {
            newCompanies.push({
              ...matched,
              reason: "企业已在库且尚未打标，可进入自动打标",
            });
          }
        } else {
          const firstMatch = companyNameMatches[0];
          duplicateCompanies.push({
            ...candidate,
            reason: `企业名称已存在于库内企业“${firstMatch.companyName}”`,
            matchedCompanyId: firstMatch.companyId,
            matchedCompanyName: firstMatch.companyName,
            matchedCreditCode: firstMatch.creditCode,
          });
        }
        continue;
      }

      invalidRows.push({
        rowIndex: candidate.rowIndex,
        companyName: candidate.companyName,
        creditCode: candidate.creditCode,
        reason: "企业匹配结果不明确，无法自动打标",
      });
    }

    res.json({
      success: true,
      data: {
        headers,
        summary: {
          inputCount: parsedRows.length + invalidRows.length,
          existingCount: existingCompanies.length,
          duplicateCount: duplicateCompanies.length,
          newCount: newCompanies.length,
          invalidCount: invalidRows.length,
        },
        newCompanies,
        existingCompanies,
        duplicateCompanies,
        invalidRows,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.post("/api/auto-tag/import/run", async (req, res) => {
  const records = Array.isArray(req.body?.records) ? req.body.records : [];
  const dimensionIds = normalizeIntList(req.body?.dimensionIds);

  if (records.length === 0) {
    return res.status(400).json({ success: false, message: "请先提供待打标企业" });
  }
  if (dimensionIds.length === 0) {
    return res.status(400).json({ success: false, message: "请至少选择一个标签维度" });
  }

  try {
    const companyIds = normalizeIntList(records.map((item) => item?.matchedCompanyId));
    if (companyIds.length === 0) {
      return res.status(400).json({ success: false, message: "未找到可自动打标的已入库企业" });
    }

    const dbRecords = await fetchImportAutoTagRecordsByCompanyIds(companyIds);
    const dbRecordMap = new Map(dbRecords.map((item) => [item.companyId, item]));
    const evaluateRecords = records
      .map((item) => {
        const companyId = toPositiveInt(item?.matchedCompanyId, 0);
        const matched = dbRecordMap.get(companyId);
        if (!matched) {
          return null;
        }
        return {
          ...matched,
          row_index: toPositiveInt(item?.rowIndex, 0) || matched.companyId,
        };
      })
      .filter(Boolean);

    if (evaluateRecords.length === 0) {
      return res.status(400).json({ success: false, message: "未找到可用于自动打标的企业完整信息" });
    }

    const summary = await runImportAutoTagEvaluateScript({
      records: evaluateRecords,
      dimensionIds,
    });

    const sourceByCode = new Map(
      records
        .map((item) => {
          const key = normalizeText(item?.matchedCreditCode || item?.creditCode).toUpperCase();
          return key ? [key, item] : null;
        })
        .filter(Boolean),
    );

    const items = (summary.results || []).map((item, index) => {
      const source = sourceByCode.get(normalizeText(item.credit_code).toUpperCase()) || records[index] || {};
      const matchedCompanyId = toPositiveInt(source.matchedCompanyId, 0);
      const dimensions = emptyTagBuckets();
      const tags = (item.tags || []).map((tag) => {
        const meta = getTagDimensionMeta(tag.company_tag_dimension_name);
        if (dimensions[meta.key]) {
          dimensions[meta.key].push(tag.company_tag_name);
        }
        return {
          id: tag.company_tag_id,
          name: tag.company_tag_name,
          dimensionId: 0,
          dimensionName: tag.company_tag_dimension_name,
          subdimensionId: 0,
          subdimensionName: tag.company_tag_subdimension_name,
        };
      });

      return {
        batchItemId: index + 1,
        key: index + 1,
        companyId: matchedCompanyId || index + 1,
        name: source.matchedCompanyName || item.company_name,
        code: source.matchedCreditCode || item.credit_code || `企业-${index + 1}`,
        updateTime: null,
        tagCount: item.tag_count || tags.length,
        tags,
        dimensions,
        status: item.error_message ? AUTO_TAG_BATCH_ITEM_STATUS.FAILED : AUTO_TAG_BATCH_ITEM_STATUS.SUCCESS,
        errorMessage: item.error_message || "",
        result: {
          company_id: matchedCompanyId || index + 1,
          tag_count: item.tag_count || tags.length,
          tags: item.tags || [],
        },
      };
    });

    res.json({
      success: true,
      data: {
        summary: {
          companyCount: evaluateRecords.length,
          successCompanyCount: items.filter((item) => item.status === AUTO_TAG_BATCH_ITEM_STATUS.SUCCESS).length,
          failedCompanyCount: items.filter((item) => item.status === AUTO_TAG_BATCH_ITEM_STATUS.FAILED).length,
          assignmentCount: summary.assignment_count || 0,
        },
        items,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.get("/api/auto-tag/dimensions", async (_req, res) => {
  try {
    res.json({ success: true, data: await fetchTagDimensionList() });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

/**
 * 自动打标：企业候选列表
 */
app.get("/api/auto-tag/companies", async (req, res) => {
  const { page = 1, pageSize = 20, keyword = "" } = req.query;
  const currentPage = toPositiveInt(page, 1);
  const currentPageSize = toPositiveInt(pageSize, 20);
  const offset = (currentPage - 1) * currentPageSize;

  try {
    let where = "WHERE 1=1";
    const params = [];
    const normalizedKeyword = normalizeText(keyword);
    if (normalizedKeyword) {
      where += " AND (b.company_name LIKE ? OR b.credit_code LIKE ?)";
      params.push(`%${normalizedKeyword}%`, `%${normalizedKeyword}%`);
    }

    const [countRows] = await pool.query(
      `SELECT COUNT(*) AS total FROM company_basic b ${where}`,
      params,
    );
    const [rows] = await pool.query(
      `
        SELECT
          b.company_id AS companyId,
          b.company_name AS companyName,
          b.credit_code AS creditCode,
          b.establish_date AS establishDate,
          b.updated_at AS updateTime,
          COUNT(DISTINCT m.company_tag_id) AS tagCount
        FROM company_basic b
        LEFT JOIN company_tag_map m
          ON b.company_id = m.company_id
        ${where}
        GROUP BY b.company_id, b.company_name, b.credit_code, b.establish_date, b.updated_at
        ORDER BY b.updated_at DESC, b.company_id DESC
        LIMIT ? OFFSET ?
      `,
      [...params, currentPageSize, offset],
    );

    res.json({
      success: true,
      data: {
        list: rows.map((row) => ({
          key: row.companyId,
          companyId: row.companyId,
          name: row.companyName,
          code: row.creditCode || String(row.companyId),
          establishDate: row.establishDate,
          updateTime: row.updateTime,
          tagCount: row.tagCount,
        })),
        total: countRows[0]?.total || 0,
        page: currentPage,
        pageSize: currentPageSize,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

/**
 * 自动打标：上传名单解析
 */
app.post("/api/auto-tag/companies/resolve-identifiers", async (req, res) => {
  const identifiers = normalizeIdentifierList(req.body.identifiers);
  if (identifiers.length === 0) {
    return res.status(400).json({ success: false, message: "请提供至少一个企业标识" });
  }
  if (identifiers.length > 1000) {
    return res.status(400).json({ success: false, message: "单次最多解析 1000 个企业标识" });
  }

  try {
    const numericIds = identifiers
      .filter((item) => /^\d+$/.test(item))
      .map((item) => Number.parseInt(item, 10))
      .filter((item) => Number.isFinite(item) && item > 0);
    const creditCodes = identifiers.map((item) => item.toUpperCase());

    const [rows] = await pool.query(
      `
        SELECT
          company_id AS companyId,
          company_name AS companyName,
          credit_code AS creditCode
        FROM company_basic
        WHERE company_id IN (?)
          OR UPPER(credit_code) IN (?)
          OR company_name IN (?)
      `,
      [numericIds.length > 0 ? numericIds : [0], creditCodes, identifiers],
    );

    const companyById = new Map();
    const companyByCode = new Map();
    const companiesByName = new Map();
    for (const row of rows) {
      const candidate = {
        companyId: row.companyId,
        companyName: row.companyName,
        creditCode: row.creditCode || String(row.companyId),
      };
      companyById.set(String(row.companyId), candidate);
      if (row.creditCode) {
        companyByCode.set(String(row.creditCode).toUpperCase(), candidate);
      }
      const nameKey = normalizeText(row.companyName);
      if (!companiesByName.has(nameKey)) {
        companiesByName.set(nameKey, []);
      }
      companiesByName.get(nameKey).push(candidate);
    }

    const matchedEntries = [];
    const matchedCompanyIds = new Set();
    const unmatchedIdentifiers = [];
    const ambiguousIdentifiers = [];

    for (const identifier of identifiers) {
      const idMatch = companyById.get(identifier);
      if (idMatch) {
        matchedEntries.push({
          identifier,
          matchType: "company_id",
          ...idMatch,
        });
        matchedCompanyIds.add(idMatch.companyId);
        continue;
      }

      const codeMatch = companyByCode.get(identifier.toUpperCase());
      if (codeMatch) {
        matchedEntries.push({
          identifier,
          matchType: "credit_code",
          ...codeMatch,
        });
        matchedCompanyIds.add(codeMatch.companyId);
        continue;
      }

      const nameMatches = companiesByName.get(identifier) || [];
      if (nameMatches.length === 1) {
        matchedEntries.push({
          identifier,
          matchType: "company_name",
          ...nameMatches[0],
        });
        matchedCompanyIds.add(nameMatches[0].companyId);
        continue;
      }
      if (nameMatches.length > 1) {
        ambiguousIdentifiers.push({
          identifier,
          companyCount: nameMatches.length,
          companies: nameMatches,
        });
        continue;
      }

      unmatchedIdentifiers.push(identifier);
    }

    const matchedCompanies = await fetchCompanyCandidateListByIds([...matchedCompanyIds]);
    res.json({
      success: true,
      data: {
        identifiers,
        matchedEntries,
        matchedCompanies,
        unmatchedIdentifiers,
        ambiguousIdentifiers,
        summary: {
          inputCount: identifiers.length,
          matchedEntryCount: matchedEntries.length,
          matchedCompanyCount: matchedCompanies.length,
          unmatchedCount: unmatchedIdentifiers.length,
          ambiguousCount: ambiguousIdentifiers.length,
        },
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

/**
 * 自动打标：执行规则引擎
 */
app.post("/api/auto-tag/batches", async (req, res) => {
  const companyIds = normalizeIntList(req.body.companyIds);
  const dimensionIds = normalizeIntList(req.body.dimensionIds);
  const requestedByUserId = toPositiveInt(req.body.requestedByUserId, 0) || null;
  const batchName = normalizeText(req.body.batchName) || null;

  if (companyIds.length === 0) {
    return res.status(400).json({ success: false, message: "请至少选择一家企业" });
  }
  if (dimensionIds.length === 0) {
    return res.status(400).json({ success: false, message: "请至少选择一个标签维度" });
  }

  const [dimensionRows] = await pool.query(
    `
      SELECT
        company_tag_dimension_id AS id,
        company_tag_dimension_name AS name
      FROM company_tag_dimension
      WHERE company_tag_dimension_id IN (?)
      ORDER BY sort_order, company_tag_dimension_id
    `,
    [dimensionIds],
  );
  if (dimensionRows.length === 0) {
    return res.status(400).json({ success: false, message: "未找到可用标签维度" });
  }

  const [companyRows] = await pool.query(
    `
      SELECT company_id AS companyId
      FROM company_basic
      WHERE company_id IN (?)
      ORDER BY company_id
    `,
    [companyIds],
  );
  const resolvedCompanyIds = companyRows.map((row) => row.companyId);
  if (resolvedCompanyIds.length === 0) {
    return res.status(400).json({ success: false, message: "未找到可用企业" });
  }

  const connection = await pool.getConnection();
  try {
    await connection.beginTransaction();
    const batchCode = createBatchCode();
    const dimensionNames = dimensionRows.map((row) => row.name);
    const [insertResult] = await connection.query(
      `
        INSERT INTO company_tag_batch (
          batch_code,
          batch_name,
          status,
          requested_by_user_id,
          dimension_ids,
          dimension_names,
          requested_company_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
      `,
      [
        batchCode,
        batchName,
        AUTO_TAG_BATCH_STATUS.PENDING,
        requestedByUserId,
        JSON.stringify(dimensionIds),
        JSON.stringify(dimensionNames),
        resolvedCompanyIds.length,
      ],
    );

    const batchId = insertResult.insertId;
    const itemValues = resolvedCompanyIds.map((companyId) => [batchId, companyId, AUTO_TAG_BATCH_ITEM_STATUS.PENDING]);
    await connection.query(
      `
        INSERT INTO company_tag_batch_item (
          company_tag_batch_id,
          company_id,
          status
        ) VALUES ?
      `,
      [itemValues],
    );

    await connection.commit();
    setImmediate(() => {
      processAutoTagBatch(batchId).catch((error) => {
        console.error(`auto-tag batch ${batchId} failed`, error);
      });
    });

    const batch = await fetchBatchRow(batchId);
    res.json({ success: true, data: batch });
  } catch (error) {
    await connection.rollback();
    res.status(500).json({ success: false, message: error.message });
  } finally {
    connection.release();
  }
});

app.get("/api/auto-tag/batches", async (req, res) => {
  const page = Math.max(1, toPositiveInt(req.query.page, 1));
  const pageSize = Math.max(1, toPositiveInt(req.query.pageSize, 10));
  const offset = (page - 1) * pageSize;

  try {
    const [countRows] = await pool.query("SELECT COUNT(*) AS total FROM company_tag_batch");
    const [rows] = await pool.query(
      `
        SELECT
          company_tag_batch_id AS batchId,
          batch_code AS batchCode,
          batch_name AS batchName,
          status,
          requested_by_user_id AS requestedByUserId,
          dimension_ids AS dimensionIds,
          dimension_names AS dimensionNames,
          requested_company_count AS requestedCompanyCount,
          success_company_count AS successCompanyCount,
          failed_company_count AS failedCompanyCount,
          summary_json AS summaryJson,
          error_message AS errorMessage,
          started_at AS startedAt,
          finished_at AS finishedAt,
          created_at AS createdAt,
          updated_at AS updatedAt
        FROM company_tag_batch
        ORDER BY created_at DESC, company_tag_batch_id DESC
        LIMIT ? OFFSET ?
      `,
      [pageSize, offset],
    );

    res.json({
      success: true,
      data: {
        list: rows.map((row) => formatBatchRow(row)),
        total: countRows[0]?.total || 0,
        page,
        pageSize,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.get("/api/auto-tag/batches/:batchId", async (req, res) => {
  const batchId = toPositiveInt(req.params.batchId, 0);
  if (!batchId) {
    return res.status(400).json({ success: false, message: "无效的批次 ID" });
  }

  try {
    const batch = await fetchBatchRow(batchId);
    if (!batch) {
      return res.status(404).json({ success: false, message: "未找到批次" });
    }
    res.json({ success: true, data: batch });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.get("/api/auto-tag/batches/:batchId/progress", async (req, res) => {
  const batchId = toPositiveInt(req.params.batchId, 0);
  if (!batchId) {
    return res.status(400).json({ success: false, message: "无效的批次 ID" });
  }

  try {
    const batch = await fetchBatchRow(batchId);
    if (!batch) {
      return res.status(404).json({ success: false, message: "未找到批次" });
    }
    res.json({
      success: true,
      data: {
        batchId: batch.batchId,
        status: batch.status,
        requestedCompanyCount: batch.requestedCompanyCount,
        successCompanyCount: batch.successCompanyCount,
        failedCompanyCount: batch.failedCompanyCount,
        progressPercent: batch.requestedCompanyCount > 0
          ? Math.round(((batch.successCompanyCount + batch.failedCompanyCount) / batch.requestedCompanyCount) * 100)
          : 0,
        startedAt: batch.startedAt,
        finishedAt: batch.finishedAt,
        errorMessage: batch.errorMessage,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.get("/api/auto-tag/batches/:batchId/items", async (req, res) => {
  const batchId = toPositiveInt(req.params.batchId, 0);
  if (!batchId) {
    return res.status(400).json({ success: false, message: "无效的批次 ID" });
  }

  try {
    const batch = await fetchBatchRow(batchId);
    if (!batch) {
      return res.status(404).json({ success: false, message: "未找到批次" });
    }
    const data = await fetchBatchItemRows(batchId, req.query.page, req.query.pageSize);
    res.json({ success: true, data: { batch, ...data } });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.get("/api/auto-tag/batches/:batchId/export", async (req, res) => {
  const batchId = toPositiveInt(req.params.batchId, 0);
  if (!batchId) {
    return res.status(400).json({ success: false, message: "无效的批次 ID" });
  }

  try {
    const batch = await fetchBatchRow(batchId);
    if (!batch) {
      return res.status(404).json({ success: false, message: "未找到批次" });
    }
    const { list } = await fetchBatchItemRows(batchId, 1, 100000);
    const csvContent = buildBatchExportCsv(list);
    const batchCode = batch.batchCode || `batch_${batchId}`;
    res.setHeader("Content-Type", "text/csv; charset=utf-8");
    res.setHeader("Content-Disposition", `attachment; filename=\"${batchCode}.csv\"`);
    res.send(`\uFEFF${csvContent}`);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.post("/api/auto-tag/batches/:batchId/manual-save", async (req, res) => {
  const batchId = toPositiveInt(req.params.batchId, 0);
  const requestedChanges = Array.isArray(req.body?.companies) ? req.body.companies : [];
  if (!batchId) {
    return res.status(400).json({ success: false, message: "无效的批次 ID" });
  }

  const companies = requestedChanges
    .map((item) => ({
      companyId: toPositiveInt(item?.companyId, 0),
      addTagIds: normalizeIntList(item?.addTagIds),
      deleteTagIds: normalizeIntList(item?.deleteTagIds),
    }))
    .filter((item) => item.companyId > 0 && (item.addTagIds.length > 0 || item.deleteTagIds.length > 0));

  if (companies.length === 0) {
    return res.status(400).json({ success: false, message: "没有可保存的标签修改" });
  }

  const connection = await pool.getConnection();
  try {
    const [batchRows] = await connection.query(
      `
        SELECT company_tag_batch_id AS batchId
        FROM company_tag_batch
        WHERE company_tag_batch_id = ?
        LIMIT 1
      `,
      [batchId],
    );
    if (batchRows.length === 0) {
      return res.status(404).json({ success: false, message: "未找到批次" });
    }

    await connection.beginTransaction();

    for (const company of companies) {
      const [itemRows] = await connection.query(
        `
          SELECT company_tag_batch_item_id AS batchItemId
          FROM company_tag_batch_item
          WHERE company_tag_batch_id = ? AND company_id = ?
          LIMIT 1
        `,
        [batchId, company.companyId],
      );
      if (itemRows.length === 0) {
        throw new Error(`企业 ${company.companyId} 不在当前批次中`);
      }

      for (const tagId of company.addTagIds) {
        await connection.query(
          `
            INSERT INTO company_tag_map (company_id, company_tag_id, source, confidence, user_id)
            VALUES (?, ?, 1, 1, NULL)
            ON DUPLICATE KEY UPDATE
              source = VALUES(source),
              confidence = VALUES(confidence),
              user_id = VALUES(user_id),
              create_time = CURRENT_TIMESTAMP
          `,
          [company.companyId, tagId],
        );
      }

      if (company.deleteTagIds.length > 0) {
        await connection.query(
          `
            DELETE FROM company_tag_map
            WHERE company_id = ?
              AND company_tag_id IN (?)
          `,
          [company.companyId, company.deleteTagIds],
        );
      }

      const [tagRows] = await connection.query(
        `
          SELECT
            ctm.company_id AS companyId,
            l.company_tag_id AS companyTagId,
            l.company_tag_name AS tagName,
            sd.company_tag_subdimension_name AS subdimensionName,
            d.company_tag_dimension_name AS dimensionName
          FROM company_tag_map ctm
          JOIN company_tag_library l
            ON ctm.company_tag_id = l.company_tag_id
          JOIN company_tag_subdimension sd
            ON l.company_tag_subdimension_id = sd.company_tag_subdimension_id
          JOIN company_tag_dimension d
            ON sd.company_tag_dimension_id = d.company_tag_dimension_id
          WHERE ctm.company_id = ?
          ORDER BY d.sort_order, sd.sort_order, l.sort_order, l.company_tag_name
        `,
        [company.companyId],
      );
      const result = buildBatchResultFromTagRows(company.companyId, tagRows);

      await connection.query(
        `
          UPDATE company_tag_batch_item
          SET
            tag_count = ?,
            result_json = ?,
            finished_at = CURRENT_TIMESTAMP
          WHERE company_tag_batch_id = ? AND company_id = ?
        `,
        [result.tag_count, JSON.stringify(result), batchId, company.companyId],
      );
    }

    await connection.commit();

    const batch = await fetchBatchRow(batchId);
    const items = await fetchBatchItemRows(batchId, 1, 100000);
    res.json({
      success: true,
      data: {
        batch,
        items: items.list,
      },
    });
  } catch (error) {
    await connection.rollback();
    res.status(500).json({ success: false, message: error.message });
  } finally {
    connection.release();
  }
});

app.post("/api/auto-tag/llm-batches", async (req, res) => {
  const companyIds = normalizeIntList(req.body.companyIds);
  const requestedByUserId = toPositiveInt(req.body.requestedByUserId, 0) || null;
  const batchName = normalizeText(req.body.batchName) || null;
  if (companyIds.length === 0) {
    return res.status(400).json({ success: false, message: "请至少选择一家企业" });
  }

  try {
    const [dimensionRows] = await pool.query(
      `
        SELECT company_tag_dimension_id AS dimensionId
        FROM company_tag_dimension
        WHERE company_tag_dimension_name = ?
        LIMIT 1
      `,
      [SCENE_DIMENSION_NAME],
    );
    if (dimensionRows.length === 0) {
      return res.status(400).json({ success: false, message: "未找到应用场景维度" });
    }

    const [companyRows] = await pool.query(
      `
        SELECT company_id AS companyId
        FROM company_basic
        WHERE company_id IN (?)
        ORDER BY company_id
      `,
      [companyIds],
    );
    const resolvedCompanyIds = companyRows.map((row) => row.companyId);
    if (resolvedCompanyIds.length === 0) {
      return res.status(400).json({ success: false, message: "未找到可用企业" });
    }

    const [insertResult] = await pool.query(
      `
        INSERT INTO company_tag_llm_batch (
          batch_code,
          batch_name,
          status,
          provider,
          company_tag_dimension_id,
          requested_by_user_id,
          requested_company_count,
          summary_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `,
      [
        createLlmBatchCode(),
        batchName,
        AUTO_TAG_LLM_BATCH_STATUS.PENDING,
        "agent_chat",
        dimensionRows[0].dimensionId,
        requestedByUserId,
        resolvedCompanyIds.length,
        JSON.stringify({ company_ids: resolvedCompanyIds }),
      ],
    );

    const batch = await fetchLlmBatchRow(insertResult.insertId);
    setImmediate(() => {
      processSceneLlmBatch(insertResult.insertId).catch((error) => {
        console.error(`auto-tag llm batch ${insertResult.insertId} failed`, error);
      });
    });
    res.json({ success: true, data: batch });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.get("/api/auto-tag/llm-batches", async (req, res) => {
  const page = Math.max(1, toPositiveInt(req.query.page, 1));
  const pageSize = Math.max(1, toPositiveInt(req.query.pageSize, 10));
  const offset = (page - 1) * pageSize;
  try {
    const [countRows] = await pool.query("SELECT COUNT(*) AS total FROM company_tag_llm_batch");
    const [rows] = await pool.query(
      `
        SELECT
          company_tag_llm_batch_id AS batchId,
          batch_code AS batchCode,
          batch_name AS batchName,
          status,
          provider,
          model_name AS modelName,
          company_tag_dimension_id AS dimensionId,
          requested_by_user_id AS requestedByUserId,
          requested_company_count AS requestedCompanyCount,
          success_company_count AS successCompanyCount,
          failed_company_count AS failedCompanyCount,
          summary_json AS summaryJson,
          error_message AS errorMessage,
          started_at AS startedAt,
          finished_at AS finishedAt,
          created_at AS createdAt,
          updated_at AS updatedAt
        FROM company_tag_llm_batch
        ORDER BY created_at DESC, company_tag_llm_batch_id DESC
        LIMIT ? OFFSET ?
      `,
      [pageSize, offset],
    );
    res.json({
      success: true,
      data: {
        list: rows.map((row) => formatLlmBatchRow(row)),
        total: countRows[0]?.total || 0,
        page,
        pageSize,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.get("/api/auto-tag/llm-batches/:batchId", async (req, res) => {
  const batchId = toPositiveInt(req.params.batchId, 0);
  if (!batchId) {
    return res.status(400).json({ success: false, message: "无效的 LLM 批次 ID" });
  }
  try {
    const batch = await fetchLlmBatchRow(batchId);
    if (!batch) {
      return res.status(404).json({ success: false, message: "未找到 LLM 批次" });
    }
    res.json({ success: true, data: batch });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.get("/api/auto-tag/llm-batches/:batchId/candidates", async (req, res) => {
  const batchId = toPositiveInt(req.params.batchId, 0);
  if (!batchId) {
    return res.status(400).json({ success: false, message: "无效的 LLM 批次 ID" });
  }
  try {
    const batch = await fetchLlmBatchRow(batchId);
    if (!batch) {
      return res.status(404).json({ success: false, message: "未找到 LLM 批次" });
    }
    const data = await fetchLlmCandidateRows(batchId, req.query.page, req.query.pageSize);
    res.json({ success: true, data: { batch, ...data } });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.post("/api/auto-tag/llm-candidates/:candidateId/apply", async (req, res) => {
  const candidateId = toPositiveInt(req.params.candidateId, 0);
  const reviewedByUserId = toPositiveInt(req.body.reviewedByUserId, 0) || null;
  if (!candidateId) {
    return res.status(400).json({ success: false, message: "无效的候选 ID" });
  }

  const connection = await pool.getConnection();
  try {
    await connection.beginTransaction();
    const [rows] = await connection.query(
      `
        SELECT
          company_tag_llm_candidate_id AS candidateId,
          company_id AS companyId,
          company_tag_id AS companyTagId,
          status,
          candidate_type AS candidateType,
          confidence
        FROM company_tag_llm_candidate
        WHERE company_tag_llm_candidate_id = ?
        LIMIT 1
      `,
      [candidateId],
    );
    const candidate = rows[0];
    if (!candidate) {
      await connection.rollback();
      return res.status(404).json({ success: false, message: "未找到候选记录" });
    }
    if (candidate.candidateType !== AUTO_TAG_LLM_CANDIDATE_TYPE.MAPPED || !candidate.companyTagId) {
      await connection.rollback();
      return res.status(400).json({ success: false, message: "当前候选不能直接采纳为正式标签" });
    }

    await connection.query(
      `
        INSERT INTO company_tag_map (company_id, company_tag_id, source, confidence, user_id)
        VALUES (?, ?, 1, ?, ?)
        ON DUPLICATE KEY UPDATE
          source = VALUES(source),
          confidence = VALUES(confidence),
          user_id = VALUES(user_id),
          create_time = CURRENT_TIMESTAMP
      `,
      [candidate.companyId, candidate.companyTagId, candidate.confidence || 0.7, reviewedByUserId],
    );
    await connection.query(
      `
        UPDATE company_tag_llm_candidate
        SET
          status = ?,
          reviewed_by_user_id = ?,
          reviewed_at = CURRENT_TIMESTAMP,
          applied_at = CURRENT_TIMESTAMP
        WHERE company_tag_llm_candidate_id = ?
      `,
      [AUTO_TAG_LLM_CANDIDATE_STATUS.APPLIED, reviewedByUserId, candidateId],
    );
    await connection.commit();
    res.json({ success: true });
  } catch (error) {
    await connection.rollback();
    res.status(500).json({ success: false, message: error.message });
  } finally {
    connection.release();
  }
});

app.post("/api/auto-tag/llm-candidates/:candidateId/reject", async (req, res) => {
  const candidateId = toPositiveInt(req.params.candidateId, 0);
  const reviewedByUserId = toPositiveInt(req.body.reviewedByUserId, 0) || null;
  if (!candidateId) {
    return res.status(400).json({ success: false, message: "无效的候选 ID" });
  }
  try {
    const [result] = await pool.query(
      `
        UPDATE company_tag_llm_candidate
        SET
          status = ?,
          reviewed_by_user_id = ?,
          reviewed_at = CURRENT_TIMESTAMP
        WHERE company_tag_llm_candidate_id = ?
          AND status IN (?, ?)
      `,
      [
        AUTO_TAG_LLM_CANDIDATE_STATUS.REJECTED,
        reviewedByUserId,
        candidateId,
        AUTO_TAG_LLM_CANDIDATE_STATUS.PENDING,
        AUTO_TAG_LLM_CANDIDATE_STATUS.UNMAPPED,
      ],
    );
    if (!result.affectedRows) {
      return res.status(400).json({ success: false, message: "候选记录不存在或状态不可驳回" });
    }
    res.json({ success: true });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

app.post("/api/auto-tag/run", async (req, res) => {
  const companyIds = normalizeIntList(req.body.companyIds);
  const dimensionIds = normalizeIntList(req.body.dimensionIds);

  if (companyIds.length === 0) {
    return res.status(400).json({ success: false, message: "请至少选择一家企业" });
  }
  if (dimensionIds.length === 0) {
    return res.status(400).json({ success: false, message: "请至少选择一个标签维度" });
  }

  try {
    const summary = await runSelectedAutoTagEngines({ companyIds, dimensionIds });
    const [companyRows] = await pool.query(
      `
        SELECT
          company_id AS companyId,
          company_name AS companyName,
          credit_code AS creditCode,
          updated_at AS updateTime
        FROM company_basic
        WHERE company_id IN (?)
        ORDER BY company_name
      `,
      [companyIds],
    );
    const tagRows = await fetchCompanyTags(companyIds);
    const resultList = buildCompanyTagView(companyRows, tagRows);

    res.json({
      success: true,
      data: {
        summary,
        list: resultList,
      },
    });
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

export function startServer(port = PORT) {
  return app.listen(port, () => console.log(`Backend running at http://localhost:${port}`));
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  startServer();
}

export { app };
