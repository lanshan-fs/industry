from __future__ import annotations


ECOLOGY_RULES: dict[str, list[str]] = {
    "科研院校": ["研究院", "研究所", "大学", "学院", "实验室", "医院"],
    "行业协会": ["协会", "学会", "联合会", "促进会"],
    "投资基金": ["基金", "投资", "资本", "创投", "股权"],
    "孵化器": ["孵化器", "孵化", "众创空间", "加速器"],
    "专业园区": ["园区", "产业园", "科技园", "基地"],
    "概念验证": ["概念验证", "中试", "验证平台", "成果转化"],
}


def ecology_keywords(label: str) -> list[str]:
    normalized = str(label or "").replace("\r", "").strip()
    if not normalized:
        return []
    return ECOLOGY_RULES.get(normalized, [normalized])
