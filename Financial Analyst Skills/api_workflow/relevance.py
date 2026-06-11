from __future__ import annotations

import re


FINANCE_KEYWORDS = {
    "股票",
    "股价",
    "估值",
    "财报",
    "年报",
    "季报",
    "公司",
    "上市",
    "港股",
    "美股",
    "a股",
    "A股",
    "中概股",
    "买入",
    "卖出",
    "持有",
    "减仓",
    "风险",
    "DCF",
    "市盈率",
    "PE",
    "PB",
    "EPS",
    "利润",
    "收入",
    "现金流",
    "行业",
    "基本面",
    "技术面",
    "催化剂",
}


UNRELATED_KEYWORDS = {
    "天气",
    "菜谱",
    "做饭",
    "小说",
    "诗",
    "情书",
    "翻译",
    "旅游",
    "减肥",
    "健身",
    "数学题",
    "代码报错",
    "游戏",
}


TICKER_PATTERNS = [
    r"\b[A-Z]{1,5}\b",
    r"\b\d{6}\.(SH|SZ|BJ)\b",
    r"\b\d{5}\.HK\b",
    r"\b\d{4,6}\b",
]


def is_stock_analysis_related(user_input: str) -> bool:
    text = user_input.strip()
    if not text:
        return False

    keyword_hit = any(keyword in text for keyword in FINANCE_KEYWORDS)
    ticker_hit = any(re.search(pattern, text) for pattern in TICKER_PATTERNS)
    unrelated_hit = any(keyword in text for keyword in UNRELATED_KEYWORDS)

    if keyword_hit:
        return True
    if ticker_hit and not unrelated_hit:
        return True
    return False


def refusal_response(user_input: str) -> dict:
    return {
        "status": "refused",
        "reason": "输入内容与股票、上市公司、估值、财务分析或投资风险分析无关。",
        "user_input": user_input,
        "message": "本工作流只处理股票分析、上市公司研究、估值、财务质量、风险反证和投资决策相关问题。请提供公司名称/股票代码/市场/分析目标后再运行。",
    }
