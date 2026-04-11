import React, { useEffect, useMemo, useState } from "react";
import { Space, Tag, Typography } from "antd";
import { useNavigate } from "react-router-dom";

import {
  ECOLOGY_HINTS,
  QUALIFICATION_HINTS,
  RISK_FILTERS,
  resolveSearchTarget,
  type SearchScope,
} from "../../utils/searchRouting";
import {
  fetchDashboardOverview,
  fetchMetaAll,
  peekDashboardOverview,
  peekMetaAll,
} from "../../utils/apiCache";

const { Text } = Typography;

type IndustryNode = {
  title?: string;
  isStage?: boolean;
  children?: IndustryNode[];
};

type SearchCatalog = {
  industries: Array<{ label: string; path: string; hot: boolean }>;
  hotIndustries: string[];
  hotEnterprises: string[];
};

type SuggestionOption = {
  value: string;
  label: React.JSX.Element;
  exactPath?: string;
  exactScope: SearchScope;
  rank: number;
};

const DEFAULT_CATALOG: SearchCatalog = {
  industries: [],
  hotIndustries: [],
  hotEnterprises: [],
};

function normalizeText(value: string) {
  return String(value || "").trim().toLowerCase();
}

function flattenIndustryTree(nodes: IndustryNode[], parents: string[] = []) {
  const result: Array<{ label: string; path: string }> = [];
  for (const node of nodes || []) {
    const title = String(node.title || "").trim();
    if (!title) {
      continue;
    }
    const nextParents = node.isStage ? parents : [...parents, title];
    if (!node.isStage) {
      result.push({
        label: title,
        path: nextParents.join(" / "),
      });
    }
    result.push(...flattenIndustryTree(node.children || [], nextParents));
  }
  return result;
}

function scoreMatch(query: string, text: string) {
  const normalizedQuery = normalizeText(query);
  const normalizedText = normalizeText(text);
  if (!normalizedQuery || !normalizedText) {
    return 0;
  }
  if (normalizedText === normalizedQuery) {
    return 120;
  }
  if (normalizedText.startsWith(normalizedQuery)) {
    return 100;
  }
  if (normalizedText.includes(normalizedQuery)) {
    return 80;
  }
  return 0;
}

function suggestionLabel(scopeLabel: string, value: string, description?: string) {
  return (
    <Space direction="vertical" size={0} style={{ lineHeight: 1.25 }}>
      <Space size={8}>
        <Tag color="blue" bordered={false} style={{ margin: 0 }}>
          {scopeLabel}
        </Tag>
        <Text>{value}</Text>
      </Space>
      {description ? (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {description}
        </Text>
      ) : null}
    </Space>
  );
}

function buildIndustryOptions(query: string, catalog: SearchCatalog) {
  return catalog.industries
    .map((item) => {
      const rank = Math.max(scoreMatch(query, item.label), scoreMatch(query, item.path)) + (item.hot ? 15 : 0);
      return {
        value: item.label,
        label: suggestionLabel("行业", item.label, item.path),
        exactPath: `/industry-portrait/industry-profile?industryName=${encodeURIComponent(item.label)}`,
        exactScope: "industry" as const,
        rank,
      };
    })
    .filter((item) => item.rank > 0)
    .sort((a, b) => b.rank - a.rank || a.value.localeCompare(b.value, "zh-CN"))
    .slice(0, 8);
}

function buildCompanyOptions(query: string, catalog: SearchCatalog) {
  return catalog.hotEnterprises
    .map((name) => ({
      value: name,
      label: suggestionLabel("企业", name),
      exactScope: "company" as const,
      rank: scoreMatch(query, name),
    }))
    .filter((item) => item.rank > 0)
    .sort((a, b) => b.rank - a.rank || a.value.localeCompare(b.value, "zh-CN"))
    .slice(0, 5);
}

function buildTextOptions(query: string, values: string[], scope: SearchScope, scopeLabel: string) {
  return values
    .map((value) => ({
      value,
      label: suggestionLabel(scopeLabel, value),
      exactScope: scope,
      rank: scoreMatch(query, value),
    }))
    .filter((item) => item.rank > 0)
    .sort((a, b) => b.rank - a.rank || a.value.localeCompare(b.value, "zh-CN"))
    .slice(0, 6);
}

export function useSmartSearch(inputValue: string, preferredScope: SearchScope | "" = "") {
  const navigate = useNavigate();
  const [catalog, setCatalog] = useState<SearchCatalog>(() => {
    const metaJson = peekMetaAll<any>();
    const overviewJson = peekDashboardOverview<any>();
    if (!metaJson && !overviewJson) {
      return DEFAULT_CATALOG;
    }

    const tree = metaJson?.success ? metaJson.data?.industryTree || [] : [];
    const flattened = flattenIndustryTree(tree);
    const hotIndustries = overviewJson?.success ? overviewJson.data?.hotSearches?.industries || [] : [];
    const hotEnterprises = overviewJson?.success ? overviewJson.data?.hotSearches?.enterprises || [] : [];
    const dedupedIndustryMap = new Map<string, { label: string; path: string; hot: boolean }>();

    flattened.forEach((item: { label: string; path: string }) => {
      const existing = dedupedIndustryMap.get(item.label);
      if (!existing || existing.path.length < item.path.length) {
        dedupedIndustryMap.set(item.label, {
          label: item.label,
          path: item.path,
          hot: hotIndustries.includes(item.label),
        });
      }
    });

    hotIndustries.forEach((label: string) => {
      const existing = dedupedIndustryMap.get(label);
      dedupedIndustryMap.set(label, {
        label,
        path: existing?.path || label,
        hot: true,
      });
    });

    return {
      industries: Array.from(dedupedIndustryMap.values()),
      hotIndustries,
      hotEnterprises,
    };
  });

  useEffect(() => {
    let cancelled = false;
    const loadCatalog = async () => {
      try {
        const [metaJson, overviewJson] = await Promise.all([
          fetchMetaAll<any>(),
          fetchDashboardOverview<any>(),
        ]);
        if (cancelled) {
          return;
        }
        const tree = metaJson?.success ? metaJson.data?.industryTree || [] : [];
        const flattened = flattenIndustryTree(tree);
        const hotIndustries = overviewJson?.success ? overviewJson.data?.hotSearches?.industries || [] : [];
        const hotEnterprises = overviewJson?.success ? overviewJson.data?.hotSearches?.enterprises || [] : [];
        const dedupedIndustryMap = new Map<string, { label: string; path: string; hot: boolean }>();
        flattened.forEach((item: { label: string; path: string }) => {
          const existing = dedupedIndustryMap.get(item.label);
          if (!existing || existing.path.length < item.path.length) {
            dedupedIndustryMap.set(item.label, {
              label: item.label,
              path: item.path,
              hot: hotIndustries.includes(item.label),
            });
          }
        });
        hotIndustries.forEach((label: string) => {
          const existing = dedupedIndustryMap.get(label);
          dedupedIndustryMap.set(label, {
            label,
            path: existing?.path || label,
            hot: true,
          });
        });
        setCatalog({
          industries: Array.from(dedupedIndustryMap.values()),
          hotIndustries,
          hotEnterprises,
        });
      } catch {
        if (!cancelled) {
          setCatalog(DEFAULT_CATALOG);
        }
      }
    };
    void loadCatalog();
    return () => {
      cancelled = true;
    };
  }, []);

  const options = useMemo(() => {
    const query = String(inputValue || "").trim();
    if (!query) {
      return [];
    }
    const industryOptions = buildIndustryOptions(query, catalog);
    const companyOptions = buildCompanyOptions(query, catalog);
    const qualificationOptions = buildTextOptions(query, QUALIFICATION_HINTS, "qualification", "资质");
    const riskOptions = buildTextOptions(
      query,
      Array.from(new Set(RISK_FILTERS.flatMap((item) => item.keywords))),
      "risk",
      "风险",
    );
    const ecologyOptions = buildTextOptions(query, ECOLOGY_HINTS, "ecology", "生态");

    const byScope: Record<string, SuggestionOption[]> = {
      industry: industryOptions,
      company: companyOptions,
      qualification: qualificationOptions,
      risk: riskOptions,
      ecology: ecologyOptions,
    };

    if (preferredScope) {
      return byScope[preferredScope] || [];
    }

    return [
      ...industryOptions,
      ...qualificationOptions,
      ...riskOptions,
      ...companyOptions,
      ...ecologyOptions,
    ]
      .sort((a, b) => b.rank - a.rank || a.value.localeCompare(b.value, "zh-CN"))
      .slice(0, 10);
  }, [catalog, inputValue, preferredScope]);

  const handleResolvedSearch = (rawQuery: string, option?: { exactPath?: string; exactScope?: SearchScope }) => {
    const target = resolveSearchTarget(rawQuery, {
      preferredScope,
      exactPath: option?.exactPath,
      exactScope: option?.exactScope,
    });
    if (!target.path) {
      return false;
    }
    navigate(target.path);
    return true;
  };

  return {
    options,
    handleResolvedSearch,
  };
}
