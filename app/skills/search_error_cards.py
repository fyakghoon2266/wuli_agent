from langchain.tools import tool
from app.skills.base import SkillBase
from app.rag.retriever import retrieve_cards


class SearchErrorCardsSkill(SkillBase):
    name = "search_error_cards"
    description = "搜尋維運手冊與錯誤知識庫 (Error Cards)"
    permission = "user"
    tags = ["rag", "knowledge"]
    status_message = "🐾 Wuli 正在翻閱維運手冊..."
    sop = (
        "3. **靜態排查與架構知識 (Static Knowledge)**：\n"
        "   - 當問題屬於「Error 700 是什麼意思」、「Gateway 是怎麼運作的」、"
        "「護欄有哪些微服務」這類定義性或架構性問題時。\n"
        "   - 請使用 `search_error_cards` 查詢維運手冊與架構知識庫。\n"
    )

    def as_tool(self):
        @tool
        def search_error_cards(query: str):
            """
            這是一個「維運手冊/錯誤卡片搜尋工具」。
            當使用者詢問關於系統錯誤代碼 (Error Code)、Log 內容、GAIA 平台架構、
            護欄 (Guardrails)、Proxy 設定、Token 認證、504 Timeout、407 Error
            或任何系統異常排查時，**必須**使用此工具來查詢內部文件。

            輸入 query 應該是使用者遇到的錯誤訊息或問題關鍵字。
            """
            hits = retrieve_cards(query, k=3)

            if not hits:
                return "搜尋維運手冊後，沒有發現直接相關的說明。"

            context_blocks = []
            for idx, (card_id, content) in enumerate(hits, start=1):
                context_blocks.append(f"[Result {idx}: {card_id}]\n{content}")

            return "\n\n".join(context_blocks)

        return search_error_cards
