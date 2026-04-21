from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

class OllamaAI:
    def __init__(self, model_name=None):
        self.llm = Ollama(model=model_name or OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

    def generate_answer(self, question: str, context: str, chat_history: str = ""):
        """Sinh câu trả lời có kèm lịch sử hội thoại gần nhất để AI không bị quên."""
        template = """Bạn là một chuyên gia về hệ thống văn bản hành chính Việt Nam.
Hãy dựa vào NGỮ CẢNH TRÍCH XUẤT và LỊCH SỬ HỘI THOẠI để trả lời chính xác, chuyên nghiệp bằng tiếng Việt.
Nếu trong ngữ cảnh không có thông tin, hãy nói "Tôi không tìm thấy thông tin này trong văn bản đã nạp."

NGỮ CẢNH TRÍCH XUẤT:
{context}

LỊCH SỬ HỘI THOẠI GẦN ĐÂY:
{chat_history}

CÂU HỎI MỚI NHẤT: {question}

TRẢ LỜI:"""
        prompt = PromptTemplate.from_template(template)
        formatted = prompt.format(context=context, question=question, chat_history=chat_history or "(Chưa có lịch sử)")
        return self.llm.invoke(formatted)
