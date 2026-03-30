import requests
from bs4 import BeautifulSoup
from langchain.tools import tool
from app.skills.base import SkillBase

EOL_DOCS = {
    "aws": "https://docs.aws.amazon.com/bedrock/latest/userguide/model-lifecycle.html",
    "gcp": "https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions?hl=zh-tw",
    "azure": "https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/model-retirements?view=foundry-classic&tabs=text"
}


def extract_markdown_table(table) -> str:
    extracted_data = []

    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    if headers:
        extracted_data.append("| " + " | ".join(headers) + " |")
        extracted_data.append("|" + "|".join(["---"] * len(headers)) + "|")

    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if cells:
            cell_texts = [cell.get_text(separator=' ', strip=True) for cell in cells]
            extracted_data.append("| " + " | ".join(cell_texts) + " |")

    return "\n".join(extracted_data) + "\n\n"


def parse_aws_bedrock_tables(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_data = []

    target_sections = [
        ("【Legacy 版本 (即將下架/過渡期)】", "versions-for-legacy"),
        ("【End-of-Life 版本 (已完全下架)】", "versions-for-eol")
    ]

    for section_title, section_id in target_sections:
        heading = soup.find(id=section_id)
        if not heading:
            continue
        table = heading.find_next('table')
        if not table:
            continue
        extracted_data.append(f"### {section_title} ###\n")
        extracted_data.append(extract_markdown_table(table))

    return "".join(extracted_data) if extracted_data else "警告：無法從 AWS 官方網頁解析出 Legacy 或 EOL 表格。"


def parse_gcp_vertex_tables(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_data = []

    heading = soup.find(id="retired-models")
    if not heading:
        heading = soup.find(id="deprecated-models")

    if heading:
        table = heading.find_next('table')
        if table:
            extracted_data.append("### 【GCP 已淘汰的模型 (Retired Models)】 ###\n")
            extracted_data.append(extract_markdown_table(table))
            return "".join(extracted_data)

    tables = soup.find_all('table')
    for table in tables:
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        header_text = "".join(headers)
        if "退役" in header_text or "淘汰" in header_text or "eol" in header_text or "retired" in header_text:
            extracted_data.append("### 【GCP 已淘汰的模型 (Fallback 解析)】 ###\n")
            extracted_data.append(extract_markdown_table(table))

    return "".join(extracted_data) if extracted_data else "警告：無法從 GCP 官方網頁解析出淘汰模型表格。"


def parse_azure_openai_tables(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_data = []

    current_models_heading = soup.find(id="current-models")
    if current_models_heading:
        extracted_data.append("### 【Azure: Current Models (包含即將退休的日期)】 ###\n")
        tab_group = current_models_heading.find_next('div', class_='tabGroup')
        if tab_group:
            tables = tab_group.find_all('table')
            for table in tables:
                extracted_data.append(extract_markdown_table(table))
        else:
            table = current_models_heading.find_next('table')
            if table:
                extracted_data.append(extract_markdown_table(table))

    fine_tuned_heading = soup.find(id="fine-tuned-models")
    if fine_tuned_heading:
        extracted_data.append("### 【Azure: Fine-tuned Models】 ###\n")
        table = fine_tuned_heading.find_next('table')
        if table:
            extracted_data.append(extract_markdown_table(table))

    return "".join(extracted_data) if extracted_data else "警告：無法從 Azure 官方網頁解析出模型表格。"


class CheckModelEolSkill(SkillBase):
    name = "check_model_eol"
    description = "查詢雲端模型的 EOL (End of Life) 狀態"
    permission = "user"
    tags = ["lifecycle", "eol", "model"]
    status_message = "📅 Wuli 正在查詢模型生命週期..."
    sop = ""

    def as_tool(self):
        @tool("check_model_eol")
        def check_model_eol(provider: str, model_name: str):
            """
            查詢官方文件尋找模型的 EOL (End of Life) 日期。

            Args:
                provider (str): 'aws', 'gcp', or 'azure'.
                model_name (str): 要尋找的模型名稱 (例如 "Claude 3.5 Sonnet", "gpt-4o")。
            """
            provider_key = provider.lower()
            target_url = EOL_DOCS.get(provider_key)

            if not target_url:
                return f"❌ Wuli 不支援查詢 {provider}，目前僅支援: aws, gcp, azure"

            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(target_url, headers=headers, timeout=15)
                response.raise_for_status()

                if provider_key == "aws":
                    structured_content = parse_aws_bedrock_tables(response.text)
                elif provider_key == "gcp":
                    structured_content = parse_gcp_vertex_tables(response.text)
                elif provider_key == "azure":
                    structured_content = parse_azure_openai_tables(response.text)
                else:
                    return "❌ 不支援的 Provider。"

                return f"""
        【來源網址】: {target_url}

        以下是從官方網頁擷取出來的模型生命週期清單：

        {structured_content}

        ----------------
        【判斷任務】
        請在上述清單中，尋找 '{model_name}' 的相關資訊。

        1. 如果你有在清單中找到該模型，請仔細閱讀其「Retirement Date」或「淘汰日期」。
           - 如果日期已經過去，或是即將到來，請提供該日期並標記 "STATUS: EXPIRING"。
           - 注意：如果日期寫著「No retirement scheduled」或是留空，請回答 "目前無淘汰計畫，STATUS: SAFE"。
           - 如果有標註「No earlier than (不早於) xxx」，請將這個資訊完整告訴使用者。
        2. 如果你沒有在清單中找到該模型，請回答 "未在清單中發現，STATUS: SAFE"。

        注意：必須「完全符合」模型名稱或版本號。
        """

            except requests.exceptions.RequestException as e:
                return f"❌ 無法連線至官方網頁: {str(e)}"
            except Exception as e:
                return f"❌ 解析官方網頁時發生錯誤: {str(e)}"

        return check_model_eol
