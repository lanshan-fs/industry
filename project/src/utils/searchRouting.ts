export type SearchScope =
  | "industry"
  | "company"
  | "person"
  | "risk"
  | "qualification"
  | "ecology";

type SearchOptions = {
  preferredScope?: SearchScope | "";
  exactPath?: string;
  exactScope?: SearchScope;
};

type SearchIntent = {
  scope?: SearchScope;
  keyword: string;
  path: string;
};

const CREDIT_CODE_PATTERN = /^[0-9A-Z]{18}$/;
const COMPANY_SUFFIXES = [
  "公司",
  "有限公司",
  "股份有限公司",
  "集团",
  "研究院",
  "研究所",
  "中心",
  "医院",
  "诊所",
  "事务所",
  "实验室",
  "杂志社",
];
export const INDUSTRY_HINTS = [
  "产业",
  "行业",
  "赛道",
  "产业链",
  "细分",
  "医药",
  "医疗",
  "器械",
  "中药",
  "创新药",
  "生物技术",
  "CXO",
  "医疗AI",
  "数字医疗",
  "医疗信息化",
  "高值耗材",
];
export const QUALIFICATION_HINTS = [
  "高新技术企业",
  "高新企业",
  "专精特新",
  "创新型企业",
  "GMP",
  "ISO9001",
  "ISO14001",
  "ISO45001",
  "医疗器械经营许可证",
  "医疗器械生产许可证",
  "医疗器械生产备案凭证",
  "药品生产许可证",
  "实验动物许可",
  "辐射安全许可证",
  "互联网药品信息服务资格证书",
  "医疗器械产品备案",
];
export const ECOLOGY_HINTS = ["科研院校", "行业协会", "投资基金", "孵化器", "专业园区", "概念验证"];
const LEADING_WORDS_PATTERN =
  /^(请帮我|帮我|我要|我想|查一下|查一查|查查|查询|搜索|搜一下|搜一搜|检索|找一下|找一找|找|看看|看下|查看)\s*/;
const TRAILING_SCORE_WORDS_PATTERN = /(的)?(评分|打分|评级|分数|得分)$/;
const PERSON_PATTERN = /(法人|法定代表人|负责人|创始人|董事长|总经理|CEO|CTO|院长)/;
const STREET_PATTERN = /([\u4e00-\u9fa5]{2,}(?:街道|地区|乡))/;

export const RISK_FILTERS: Array<{
  key: string;
  keywords: string[];
  fallbackKeyword: string;
}> = [
  { key: "riskDishonest", keywords: ["失信", "失信被执行"], fallbackKeyword: "失信被执行" },
  { key: "riskLimit", keywords: ["限高", "限制高消费", "高消费限制"], fallbackKeyword: "限制高消费" },
  { key: "riskAbnormal", keywords: ["经营异常"], fallbackKeyword: "经营异常" },
  { key: "riskLegal", keywords: ["法律文书", "司法案件", "诉讼", "裁判文书"], fallbackKeyword: "法律文书" },
  { key: "riskPenalty", keywords: ["行政处罚"], fallbackKeyword: "行政处罚" },
  { key: "riskEnv", keywords: ["环保处罚", "环境处罚"], fallbackKeyword: "环保处罚" },
  { key: "riskEquity", keywords: ["股权冻结"], fallbackKeyword: "股权冻结" },
  { key: "riskMortgage", keywords: ["动产抵押"], fallbackKeyword: "动产抵押" },
  { key: "riskBankruptcy", keywords: ["破产"], fallbackKeyword: "破产" },
  { key: "riskLiquidation", keywords: ["清算"], fallbackKeyword: "清算" },
  { key: "riskExecutor", keywords: ["被执行人", "执行案件"], fallbackKeyword: "被执行人" },
];

function normalizeQuery(rawQuery: string): string {
  return String(rawQuery || "")
    .replace(/\s+/g, " ")
    .replace(/[？?！!]+/g, "")
    .replace(LEADING_WORDS_PATTERN, "")
    .trim();
}

function stripScopePrefix(query: string): { scope?: SearchScope; keyword: string } {
  const trimmed = query.trim();
  const mappings: Array<[string, SearchScope]> = [
    ["行业", "industry"],
    ["产业", "industry"],
    ["企业", "company"],
    ["公司", "company"],
    ["负责人", "person"],
    ["法人", "person"],
    ["风险", "risk"],
    ["资质", "qualification"],
    ["生态", "ecology"],
  ];
  for (const [prefix, scope] of mappings) {
    if (trimmed.startsWith(`${prefix}:`) || trimmed.startsWith(`${prefix}：`)) {
      return { scope, keyword: trimmed.slice(2).trim() };
    }
  }
  return { keyword: trimmed };
}

function looksLikeCreditCode(keyword: string): boolean {
  return CREDIT_CODE_PATTERN.test(keyword.toUpperCase());
}

function looksLikeCompany(keyword: string): boolean {
  return COMPANY_SUFFIXES.some((suffix) => keyword.includes(suffix));
}

function looksLikeIndustry(keyword: string): boolean {
  return INDUSTRY_HINTS.some((hint) => keyword.includes(hint));
}

function extractStreetFilters(keyword: string): string[] {
  const streetPattern = new RegExp(STREET_PATTERN.source, "g");
  return Array.from(new Set(Array.from(keyword.matchAll(streetPattern)).map((match) => match[1]).filter(Boolean)));
}

function parseRiskFilters(keyword: string, params: URLSearchParams) {
  const matchedKeywords: string[] = [];
  for (const item of RISK_FILTERS) {
    if (item.keywords.some((riskKeyword) => keyword.includes(riskKeyword))) {
      params.set(item.key, "1");
      matchedKeywords.push(item.fallbackKeyword);
    }
  }
  return matchedKeywords;
}

function routeToIndustryClass(
  keyword: string,
  scope: SearchScope,
  options: {
    exactQualification?: string;
    exactEcology?: string;
    highTech?: boolean;
  } = {},
): SearchIntent {
  const params = new URLSearchParams();
  params.set("searchScope", scope);

  const streets = extractStreetFilters(keyword);
  for (const street of streets) {
    params.append("street", street);
  }

  if (options.highTech) {
    params.set("highTechStatus", "1");
  }
  if (options.exactQualification) {
    params.append("qualification", options.exactQualification);
  }
  if (options.exactEcology) {
    params.append("ecology", options.exactEcology);
  }

  const matchedRiskKeywords = parseRiskFilters(keyword, params);
  const cleanKeyword = keyword
    .replace(PERSON_PATTERN, "")
    .replace(TRAILING_SCORE_WORDS_PATTERN, "")
    .trim();

  const fallbackKeyword =
    cleanKeyword ||
    options.exactQualification ||
    options.exactEcology ||
    matchedRiskKeywords.join(" ") ||
    streets.join(" ");

  if (fallbackKeyword) {
    params.set("keyword", fallbackKeyword);
  }

  return {
    scope,
    keyword: fallbackKeyword,
    path: `/industry-class?${params.toString()}`,
  };
}

function resolveCompanyRoute(keyword: string): SearchIntent {
  const cleaned = keyword.replace(TRAILING_SCORE_WORDS_PATTERN, "").trim();
  const scoreIntent = /(评分|打分|评级|分数|得分)/.test(keyword);
  if (scoreIntent) {
    const key = looksLikeCreditCode(cleaned) ? "id" : "keyword";
    return {
      scope: "company",
      keyword: cleaned,
      path: `/enterprise-score?${key}=${encodeURIComponent(cleaned)}`,
    };
  }
  return {
    scope: "company",
    keyword: cleaned,
    path: `/industry-class?keyword=${encodeURIComponent(cleaned)}&searchScope=company`,
  };
}

function resolveIndustryRoute(keyword: string): SearchIntent {
  const cleaned = keyword.replace(/(行业|产业|赛道|产业链|细分领域)/g, "").trim() || keyword;
  return routeToIndustryClass(cleaned, "industry");
}

export function resolveSearchTarget(rawQuery: string, options: SearchOptions = {}): SearchIntent {
  const normalized = normalizeQuery(rawQuery);
  const scoped = stripScopePrefix(normalized);
  const scope = options.exactScope || scoped.scope || (options.preferredScope || undefined);
  const keyword = scoped.keyword.trim();

  if (!keyword) {
    return { scope, keyword: "", path: "" };
  }
  if (options.exactPath) {
    return {
      scope,
      keyword,
      path: options.exactPath,
    };
  }

  if (scope === "company") {
    return resolveCompanyRoute(keyword);
  }
  if (scope === "industry") {
    return resolveIndustryRoute(keyword);
  }
  if (scope === "person") {
    return routeToIndustryClass(keyword, "person");
  }
  if (scope === "risk") {
    return routeToIndustryClass(keyword, "risk");
  }
  if (scope === "qualification") {
    const matchedQualification = QUALIFICATION_HINTS.find((hint) => keyword.includes(hint));
    const highTech = keyword.includes("高新");
    return routeToIndustryClass(keyword, "qualification", {
      exactQualification: matchedQualification,
      highTech,
    });
  }
  if (scope === "ecology") {
    const matchedEcology = ECOLOGY_HINTS.find((hint) => keyword.includes(hint));
    return routeToIndustryClass(keyword, "ecology", { exactEcology: matchedEcology });
  }

  if (looksLikeCreditCode(keyword) || looksLikeCompany(keyword)) {
    return resolveCompanyRoute(keyword);
  }
  if (PERSON_PATTERN.test(keyword)) {
    return routeToIndustryClass(keyword, "person");
  }
  if (RISK_FILTERS.some((item) => item.keywords.some((riskKeyword) => keyword.includes(riskKeyword)))) {
    return routeToIndustryClass(keyword, "risk");
  }
  if (QUALIFICATION_HINTS.some((hint) => keyword.includes(hint))) {
    return routeToIndustryClass(keyword, "qualification", {
      exactQualification: QUALIFICATION_HINTS.find((hint) => keyword.includes(hint)),
      highTech: keyword.includes("高新"),
    });
  }
  if (ECOLOGY_HINTS.some((hint) => keyword.includes(hint))) {
    return routeToIndustryClass(keyword, "ecology", {
      exactEcology: ECOLOGY_HINTS.find((hint) => keyword.includes(hint)),
    });
  }
  if (looksLikeIndustry(keyword)) {
    return resolveIndustryRoute(keyword);
  }

  return routeToIndustryClass(keyword, "industry");
}
