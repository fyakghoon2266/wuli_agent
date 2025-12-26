# app/tools/search.py
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

# 1. 準備搜尋引擎實體
_tavily_engine = TavilySearchResults(max_results=3)

# 2. 直接定義工具，並用 @tool 裝飾
# 注意：這裡我把 Python 函式名稱直接取名為 get_search_tool
# 這樣你在 llm_factory 引入時，變數名稱就叫 get_search_tool，而且它就是工具本人！
@tool("web_search_technical_solution")
def get_search_tool(query: str):
    """
    ONLY use this tool when internal tools (error cards, logs) return NO results.
    Useful for finding solutions to NEW technical errors, LiteLLM version issues,
    or AWS/K8s configurations that are not yet in the internal database.
    DO NOT use this for general coding requests, logic puzzles, or non-technical chat.
    The query must be specific to the error encountered.
    """
    # 呼叫 Tavily
    return _tavily_engine.invoke(query)
