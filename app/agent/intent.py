"""意图路由：qa（制度问答）| reimbursement（发起报销）。"""
import re

REIMB_WORDS = ["报销", "垫付", "付款申请", "申请付款", "费用申请"]
QUESTION_WORDS = [
    "上限", "标准", "流程", "怎么", "如何", "多少", "要求", "规定", "时限",
    "比例", "能否", "可以吗", "是什么", "范围", "条件", "需要什么", "哪些", "什么", "吗", "呢",
]
ACTION_WORDS = ["我要", "帮我", "我想", "申请", "请给我", "麻烦", "请帮"]
_AMOUNT_RE = re.compile(r"\d{2,}\s*(?:元|块|圆|万)|[¥￥]\s*\d")


def detect_intent(text: str) -> str:
    t = (text or "").strip()
    if not any(w in t for w in REIMB_WORDS):
        return "qa"
    has_amount = bool(_AMOUNT_RE.search(t))
    if has_amount and any(w in t for w in ACTION_WORDS):
        return "reimbursement"
    if any(q in t for q in QUESTION_WORDS):
        return "qa"
    return "reimbursement"
