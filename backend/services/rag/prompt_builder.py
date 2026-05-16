from langchain_core.prompts import PromptTemplate


class PromptBuilder:
    RAG_ANSWER_TEMPLATE = """Bạn là một chuyên gia về hệ thống văn bản hành chính Việt Nam.
Hãy dựa vào NGỮ CẢNH TRÍCH XUẤT và LỊCH SỬ HỘI THOẠI để trả lời chính xác, chuyên nghiệp bằng tiếng Việt.
Nếu trong ngữ cảnh không có thông tin, hãy nói "Tôi không tìm thấy thông tin này trong văn bản đã nạp."

NGỮ CẢNH TRÍCH XUẤT:
{context}

LỊCH SỬ HỘI THOẠI GẦN ĐÂY:
{chat_history}

CÂU HỎI MỚI NHẤT: {question}

TRẢ LỜI:"""

    def __init__(self, answer_template: str | None = None):
        self.answer_template = answer_template or self.RAG_ANSWER_TEMPLATE

    def build_answer_prompt(self, question: str, context: str, chat_history: str = "") -> str:
        prompt = PromptTemplate.from_template(self.answer_template)
        return prompt.format(
            context=context,
            question=question,
            chat_history=chat_history or "(Chưa có lịch sử)",
        )

