from langchain_core.prompts import PromptTemplate


class PromptBuilder:
    RAG_ANSWER_TEMPLATE = """Bạn là trợ lý tra cứu văn bản hành chính Việt Nam. Hãy trả lời câu hỏi dựa trên ngữ cảnh trích xuất.

NGỮ CẢNH TRÍCH XUẤT:
{context}

CÂU HỎI: {question}

NGUYÊN TẮC:
1. Chỉ dùng thông tin trong NGỮ CẢNH TRÍCH XUẤT.
2. Nếu ngữ cảnh có nội dung liên quan, hãy trả lời trực tiếp, ngắn gọn và có thể tổng hợp các ý chính.
3. Khi có nhãn nguồn trong ngữ cảnh như [Điều 1], [Điều 2], hãy trích dẫn nhãn đó ở cuối ý liên quan.
4. Chỉ trả lời "Tôi không tìm thấy thông tin này trong văn bản đã nạp." khi ngữ cảnh không có nội dung liên quan đến câu hỏi.
5. Không lặp lại cùng một câu trả lời nhiều lần.

TRẢ LỜI:"""

    REWRITE_QUERY_TEMPLATE = """Viết lại CÂU HỎI TIẾP THEO thành một câu hỏi độc lập để dùng cho tìm kiếm tài liệu.

YÊU CẦU:
- Nếu câu hỏi đã đầy đủ ý nghĩa hoặc là chủ đề mới, giữ nguyên câu hỏi.
- Chỉ dùng lịch sử để làm rõ đại từ/cụm như "văn bản này", "thông tư này", "đối tượng đó".
- Không trả lời câu hỏi.
- Chỉ trả về một câu hỏi duy nhất, không giải thích.

LỊCH SỬ:
{chat_history}

CÂU HỎI TIẾP THEO: {question}

CÂU HỎI ĐỘC LẬP:"""

    def __init__(self, answer_template: str | None = None):
        self.answer_template = answer_template or self.RAG_ANSWER_TEMPLATE

    def build_answer_prompt(self, question: str, context: str, chat_history: str = "") -> str:
        prompt = PromptTemplate.from_template(self.answer_template)
        return prompt.format(
            context=context,
            question=question,
        )

    def build_rewrite_prompt(self, question: str, chat_history: str = "") -> str:
        prompt = PromptTemplate.from_template(self.REWRITE_QUERY_TEMPLATE)
        return prompt.format(
            question=question,
            chat_history=chat_history or "(Chưa có lịch sử)",
        )
