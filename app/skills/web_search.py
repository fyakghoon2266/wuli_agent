from langchain.tools import tool
from langchain_tavily import TavilySearch
from app.skills.base import SkillBase


class WebSearchSkill(SkillBase):
    name = "web_search_technical_solution"
    description = "使用 Tavily 搜尋外部技術解答"
    permission = "user"
    tags = ["search", "web", "fallback"]
    status_message = "🌐 內部查無資料，Wuli 正在搜尋外部網站解答中..."
    sop = ""  # 搜尋時機已在邊界規則中定義

    def as_tool(self):
        _tavily_engine = TavilySearch(max_results=3)

        @tool("web_search_technical_solution")
        def get_search_tool(query: str):
            """
            ONLY use this tool when internal tools (error cards, logs) return NO results.
            Useful for finding solutions to NEW technical errors, LiteLLM version issues,
            or AWS/K8s configurations that are not yet in the internal database.
            DO NOT use this for general coding requests, logic puzzles, or non-technical chat.
            The query must be specific to the error encountered.
            """
            return _tavily_engine.invoke(query)

        return get_search_tool
