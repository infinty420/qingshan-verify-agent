"""报销单结构化抽取（工具层）。

Demo 供应商：确定性规则抽取（正则 + 关键词映射）。
openai_compat 供应商：优先走 LLM JSON 模式，失败时回退到本规则。
"""
import re
from datetime import date

TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("押金", ["押金", "保证金"]),
    ("设备采购费", ["设备", "冷柜", "货架", "冰箱", "收银", "冷链", "厨具", "pos机"]),
    ("装修费", ["装修", "施工", "装饰", "门头", "水电改造", "电力增容"]),
    ("差旅费", ["差旅", "出差", "住宿", "高铁", "机票", "车票", "打车"]),
    ("培训费", ["培训"]),
    ("办公费", ["办公", "文具", "打印", "耗材"]),
]
_DEFAULT_TYPE = "日常费用"

_DATE_RE = re.compile(r"(\d{4})\s*[年/\-.]\s*(\d{1,2})\s*[月/\-.]\s*(\d{1,2})")


def extract_expense_type(text: str) -> str:
    for etype, kws in TYPE_KEYWORDS:
        if any(k in text for k in kws):
            return etype
    return _DEFAULT_TYPE


def extract_amount(text: str) -> float:
    m = re.search(r"(\d+(?:\.\d{1,2})?)\s*万(?:元|块)?", text)
    if m:
        return float(m.group(1)) * 10000
    m = re.search(r"[¥￥]\s*(\d+(?:\.\d{1,2})?)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d+(?:\.\d{1,2})?)\s*(?:元|块|圆)", text)
    if m:
        return float(m.group(1))
    return 0.0


def extract_date(text: str) -> str:
    m = _DATE_RE.search(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            pass
    return date.today().isoformat()


def extract_reimbursement(text: str, hits: list[dict] | None = None) -> dict:
    etype = extract_expense_type(text)
    refs = []
    for h in (hits or [])[:3]:
        if h.get("score", 0) >= 0.1:
            refs.append(
                {
                    "doc_title": h["doc_title"],
                    "section": h["section"],
                    "excerpt": h["excerpt"][:120],
                }
            )
    return {
        "expense_type": etype,
        "amount": extract_amount(text),
        "expense_date": extract_date(text),
        "description": (text or "").strip()[:200],
        "policy_refs": refs,
    }
