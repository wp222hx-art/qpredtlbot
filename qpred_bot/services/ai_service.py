"""
AI 智能问答服务 (自主 RAG 增强)

升级亮点:
1. 多供应商兼容: OpenAI / DeepSeek / OpenRouter / Anthropic / 任意 OpenAI 兼容端点
2. 真 RAG 检索: 关键词 + RapidFuzz 模糊匹配 + 实时平台数据注入
3. 推理模型友好: 支持 o1 / deepseek-reasoner 等推理模型 (自动切换参数)
4. 兜底降级: API 不可用时, 仍能基于 FAQ 给出有效回答
"""
import json
import os
from typing import Optional, Tuple, List, Dict
from openai import AsyncOpenAI
from config import config
from logger_config import logger

try:
    from rapidfuzz import fuzz
    HAS_FUZZ = True
except Exception:
    HAS_FUZZ = False


SYSTEM_PROMPT = """你是 QPred (qpred.io) 官方 AI 客服助手 —— 群组里的专业运营官 + 客服 + 销售。

【平台核心信息】
- QPred 是全球首个双币预测平台 (USDT + JYC 双币体系)
- 当前数据: TVL $2M, 用户 11.7万, 活跃市场 2,305+, 累计派发 $8.5M
- JYC 基准价 $0.7723, 流通市值 $37.7M, 持币地址 8,392
- 核心价值: 预测赚钱 · 推广赚钱 · 质押赚钱 (三重引擎)
- 官网: https://www.qpred.io

【回答风格】
- 专业、简洁、鼓舞人心, 适合在 Telegram 群里阅读 (不超过 500 字)
- 涉及金额 / 数据必须以"知识库参考"或"平台实时数据"为准
- 推广 / 成交类问题主动引导到官网或 /ref /predict /price 命令
- 不确定的问题引导用户使用 /help 联系人工客服
- 结尾可以加 1-2 个 emoji, 避免生硬

【禁止行为】
- 禁止承诺具体收益数字 / 投资建议
- 禁止讨论竞争对手
- 禁止泄露内部信息或编造数据
- 不要使用 Markdown 表格 (Telegram 不支持)
"""


# 推理模型 (使用这些时 temperature/system 参数需要兼容处理)
REASONING_MODELS = {"o1", "o1-mini", "o1-preview", "o3-mini", "deepseek-reasoner"}


class AIService:
    """
    自主 RAG 客服:
        1. 入参问题 → 检索 FAQ + 平台实时数据
        2. 拼装 prompt → 调用最强推理模型
        3. 失败时回退到本地 FAQ 命中答案
    """

    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.faq_data: List[Dict] = []
        if config.ENABLE_AI and config.OPENAI_API_KEY:
            kwargs = {"api_key": config.OPENAI_API_KEY}
            if config.OPENAI_BASE_URL:
                kwargs["base_url"] = config.OPENAI_BASE_URL
            self.client = AsyncOpenAI(**kwargs)
            logger.info(
                f"✅ AI client ready | provider={config.AI_PROVIDER} "
                f"| model={config.OPENAI_MODEL} | base={config.OPENAI_BASE_URL}"
            )
        self._load_faq()

    # -------------------- FAQ 加载 / 检索 --------------------

    def _load_faq(self):
        faq_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "knowledge_base", "faq.json"
        )
        try:
            with open(faq_path, "r", encoding="utf-8") as f:
                self.faq_data = json.load(f)
            logger.info(f"✅ Loaded {len(self.faq_data)} FAQs")
        except Exception as e:
            logger.error(f"Load FAQ failed: {e}")
            self.faq_data = []

    def search_faq(self, question: str) -> Tuple[Optional[dict], float]:
        """
        关键词 + 模糊匹配 FAQ
        返回: (best_faq, score)  score >= 2 视为高度匹配
        """
        if not self.faq_data:
            return None, 0.0

        question_lower = question.lower()
        best_match = None
        best_score = 0.0

        for faq in self.faq_data:
            score = 0.0
            # 1. 关键词命中 (权重最大)
            for keyword in faq.get("keywords", []):
                if keyword.lower() in question_lower:
                    score += 2.0

            # 2. 问题文本相似度 (RapidFuzz)
            if HAS_FUZZ:
                ratio = fuzz.partial_ratio(
                    question_lower, faq.get("question", "").lower()
                )
                # 70 分以上才计权重
                if ratio >= 70:
                    score += ratio / 100.0  # 0.7 ~ 1.0
            else:
                # 退化方案: 字符交集
                q_text = faq.get("question", "").lower()
                common = set(question_lower) & set(q_text)
                score += len(common) / max(len(q_text), 1)

            if score > best_score:
                best_score = score
                best_match = faq

        return best_match, best_score

    def topk_faq(self, question: str, k: int = 3) -> List[Dict]:
        """检索 top-k 最相关 FAQ 用于 RAG 上下文注入"""
        if not self.faq_data:
            return []
        scored = []
        ql = question.lower()
        for faq in self.faq_data:
            s = 0.0
            for kw in faq.get("keywords", []):
                if kw.lower() in ql:
                    s += 2.0
            if HAS_FUZZ:
                s += fuzz.partial_ratio(ql, faq.get("question", "").lower()) / 100.0
            scored.append((s, faq))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:k]]

    # -------------------- 主问答入口 --------------------

    async def answer(self, question: str, extra_context: str = "") -> str:
        """
        主问答入口
        Args:
            question: 用户原始问题
            extra_context: 可选的额外上下文 (例如平台实时价格 / 热门市场)
        """
        if not question or not question.strip():
            return "请输入您的问题, 例如: 如何质押 JYC?"

        # Step 1: 高度命中 → 直接返回 FAQ 答案 (省 token, 秒回)
        faq, score = self.search_faq(question)
        if faq and score >= 3.0:
            logger.info(f"FAQ exact hit | q={question[:30]} | score={score:.2f}")
            return faq["answer"] + "\n\n💡 输入 /help 联系人工客服"

        # Step 2: AI 推理 (RAG)
        if not self.client:
            if faq:
                return faq["answer"] + "\n\n💡 输入 /help 联系人工客服"
            return (
                "🤖 AI 服务暂未开启\n"
                "请访问 /faq 查看常见问题, 或 /help 联系人工客服"
            )

        try:
            # 组装 RAG 上下文: top-3 FAQ + 实时数据
            context_blocks = []
            if config.ENABLE_RAG:
                topk = self.topk_faq(question, k=3)
                if topk:
                    context_blocks.append(
                        "【知识库参考】\n" + "\n\n".join(
                            f"Q{i+1}: {f['question']}\nA{i+1}: {f['answer']}"
                            for i, f in enumerate(topk)
                        )
                    )
            if extra_context:
                context_blocks.append("【平台实时数据】\n" + extra_context)

            user_payload = (
                ("\n\n".join(context_blocks) + "\n\n") if context_blocks else ""
            ) + f"【用户问题】{question}\n\n请用中文专业、简洁地回答。"

            model = config.OPENAI_MODEL
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ]

            # 推理模型不支持 system + temperature
            kwargs = {"model": model, "messages": messages}
            if model in REASONING_MODELS or model.startswith("o1") or model.startswith("o3"):
                # 推理模型: system → 合并到 user, 去掉 temperature
                kwargs["messages"] = [{
                    "role": "user",
                    "content": SYSTEM_PROMPT + "\n\n" + user_payload
                }]
                # OpenAI o1 系列使用 max_completion_tokens
                kwargs["max_completion_tokens"] = 800
            else:
                kwargs["temperature"] = 0.3
                kwargs["max_tokens"] = 600

            resp = await self.client.chat.completions.create(**kwargs)
            answer = resp.choices[0].message.content or ""
            answer = answer.strip()
            logger.info(f"AI answered | model={model} | q={question[:30]}")
            return answer + "\n\n💡 输入 /help 联系人工客服"

        except Exception as e:
            logger.error(f"AI error: {e}")
            # 失败兜底: 用 FAQ 模糊命中答案
            if faq:
                return (
                    "🤖 AI 暂时繁忙, 为您找到最相关的 FAQ:\n\n"
                    + faq["answer"]
                    + "\n\n💡 输入 /help 联系人工客服"
                )
            return (
                "🤖 AI 暂时繁忙, 请稍后重试\n"
                "或输入 /faq 查看常见问题, /help 联系客服"
            )


ai_service = AIService()
