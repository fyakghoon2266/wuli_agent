# app/tools/lifecycle.py
from langchain.tools import tool
from langchain_community.document_loaders import WebBaseLoader

# 定義官方 EOL 文件網址 (這是最準確的來源)
EOL_DOCS = {
    "aws": "https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html",
    "gcp": "https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions?hl=zh-tw",
    "azure": "https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/model-retirements?view=foundry-classic&tabs=text"
}

@tool("check_model_eol")
def check_model_eol(provider: str, model_name: str):
    """
    Use this tool to read the OFFICIAL documentation page to find the End-of-Life (EOL) date.
    This tool scrapes the content of the official cloud provider's lifecycle page.
    
    Args:
        provider (str): 'aws', 'gcp', or 'azure'.
        model_name (str): The exact model ID to look for.
    """
    provider_key = provider.lower()
    target_url = EOL_DOCS.get(provider_key)
    
    if not target_url:
        return f"❌ Wuli 不支援查詢 {provider}，目前僅支援: aws, gcp, azure"

    try:
        # 使用 WebBaseLoader 直接讀取網頁內容
        # 這會避開搜尋引擎的干擾，只看官方資料
        loader = WebBaseLoader(target_url)
        docs = loader.load()
        
        # 取得網頁純文字內容
        full_content = docs[0].page_content
        
        # 為了節省 Token 並讓 LLM 聚焦，我們可以做簡單的處理
        # 這裡直接回傳前 20,000 字 (通常表格都在前面)，或是回傳整頁讓長窗口模型處理
        # 建議回傳包含 "Table" 或 "Lifecycle" 的段落，這裡先回傳前 25k 字元通常夠用
        content_snippet = full_content[:25000]
        
        return f"""
        【來源網址】: {target_url}
        【網頁內容摘要】:
        {content_snippet}
        
        ----------------
        請在上面的內容中，尋找模型名稱 "{model_name}" 的 EOL 日期。
        注意：必須「完全符合」模型名稱或版本號，不要混淆 v1 和 v2。
        """

    except Exception as e:
        return f"❌ 讀取官方網頁失敗: {str(e)}"