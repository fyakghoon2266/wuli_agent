# app/tools/lifecycle.py
from langchain.tools import tool
from langchain_tavily import TavilySearch

# 定義官方 EOL 文件網址 (這是你剛剛提供的)
EOL_DOCS = {
    "aws": "https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html",
    "gcp": "https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions?hl=zh-tw",
    "azure": "https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/model-retirements?view=foundry-classic&tabs=text"
}

@tool("check_model_eol")
def check_model_eol(provider: str, model_name: str):
    """
    Use this tool to find the End-of-Life (EOL) or retirement date for a specific AI model.
    
    Args:
        provider (str): The cloud provider. Must be one of 'aws', 'gcp', or 'azure'.
        model_name (str): The name of the model to check (e.g., 'claude-v2', 'gpt-3.5-turbo', 'gemini-1.0').
    """
    provider_key = provider.lower()
    
    # 1. 檢查是否有對應的官方文件
    target_url = EOL_DOCS.get(provider_key)
    
    if not target_url:
        return f"❌ 目前 Wuli 只支援查詢 AWS, GCP, Azure 的 EOL 資訊。無法查詢: {provider}"

    # 2. 組裝搜尋 query，強制 Tavily 去看該網址
    # 技巧：使用 'site:...' 語法或直接在 prompt 裡告訴 Tavily 網址
    query = f"Check the End of Life (EOL) or retirement date for model '{model_name}' from this page: {target_url}"
    
    try:
        # 初始化 Tavily 工具 (k=3 代表抓取最相關的 3 個片段)
        # 注意：這需要你的 .env 裡有 TAVILY_API_KEY
        search_tool = TavilySearch(k=3)
        
        # 執行搜尋
        results = search_tool.invoke({"query": query})
        
        # 3. 回傳搜尋到的原始片段給 LLM 閱讀
        return f"🔍 正在查詢 {provider.upper()} 官方文件...\n找到的相關資訊如下：\n{results}"

    except Exception as e:
        return f"❌ 查詢失敗: {str(e)}"