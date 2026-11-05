"""提示词模板：真实 LLM 供应商（openai_compat）使用；local_demo 供应商走抽取式逻辑，不经此文件。"""

QA_SYSTEM_PROMPT = """你是「开店筹备与运营验收 · 业务核对助手」，为青杉生活超市员工解答开店筹备与报销制度问题。
回答规则：
1. 只依据 <制度依据> 中的内容回答，禁止编造或使用外部知识。
2. 回答末尾以【出处】标注引用的文档名与章节。
3. 若 <制度依据> 不足以回答，明确说"现行制度库未找到直接依据"，建议联系管理员补充文档，不要猜测。
4. 简体中文，简洁专业，面向一线店长与筹备专员。"""

EXTRACT_SYSTEM_PROMPT = """你是报销单信息抽取器。从用户的报销诉求中抽取结构化字段，只输出一个 JSON 对象，不要输出其他内容。
字段：
- expense_type: 从 [设备采购费, 装修费, 押金, 差旅费, 培训费, 办公费, 日常费用] 中选择
- amount: 数字（人民币元），未提及填 0
- expense_date: YYYY-MM-DD，未提及填空字符串
- description: 一句话概括报销事由
- policy_refs: 制度依据数组，每项 {doc_title, section, excerpt}，从给定依据中挑选最相关项，无则空数组"""


def format_context(hits: list[dict]) -> str:
    lines = []
    for i, h in enumerate(hits, 1):
        lines.append(f"[{i}] 《{h['doc_title']}》 {h['section']}\n{h['excerpt']}")
    return "\n\n".join(lines) or "（无）"


def build_qa_messages(question: str, hits: list[dict], history: list[dict] | None = None) -> list[dict]:
    messages = [{"role": "system", "content": QA_SYSTEM_PROMPT}]
    for h in (history or [])[-6:]:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append(
        {
            "role": "user",
            "content": f"<制度依据>\n{format_context(hits)}\n</制度依据>\n\n问题：{question}",
        }
    )
    return messages


def build_extract_messages(text: str, hits: list[dict] | None = None) -> list[dict]:
    return [
        {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"<制度依据>\n{format_context(hits or [])}\n</制度依据>\n\n用户诉求：{text}",
        },
    ]
