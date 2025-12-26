# app/tools/git_ops.py
import re
import time
from github import Github, Auth # 需確保安裝 pip install PyGithub
from langchain.tools import tool
from app.config import settings


# 定義你的目錄結構對應
COMPONENT_MAP = {
    "cognito": "cognito",
    "gateway": "gateway",
    "generic": "generic",
    "guardrail": "guardrail"
}

def get_next_error_id(repo, component: str) -> str:
    """
    自動計算下一個錯誤編號。
    例如：error_docs/cognito/ 下有 ERR-COGNITO-0002.md -> 回傳 ERR-COGNITO-0003.md
    """
    folder_path = f"error_docs/{component}"
    prefix = f"ERR-{component.upper()}-"
    max_id = 0
    
    try:
        # 列出目錄下所有檔案
        contents = repo.get_contents(folder_path)
        for content_file in contents:
            if content_file.name.endswith(".md"):
                # 使用 Regex 解析檔名中的數字
                # 檔名格式: ERR-COGNITO-0001.md
                match = re.search(rf"{prefix}(\d+)\.md", content_file.name)
                if match:
                    num = int(match.group(1))
                    if num > max_id:
                        max_id = num
    except Exception:
        # 如果目錄不存在或是空的，就從 0 開始
        pass
    
    # 下一個號碼
    next_id = max_id + 1
    # 格式化為 4 位數，例如 0003
    return f"{prefix}{next_id:04d}"

@tool("propose_new_error_card")
def propose_new_error_card(component: str, content_body: str, title: str, tags: str):
    """
    Use this tool to propose a NEW error card to the knowledge base with AUTO-NUMBERING.
    
    Args:
        component (str): One of ["cognito", "gateway", "generic", "guardrail"].
        content_body (str): The markdown body content (excluding the YAML header). 
                            Start directly with "# 標題".
        title (str): The title for the Pull Request.
        tags (str): Comma-separated tags, e.g., "404, connection, timeout".
    """
    try:
        # 1. 檢查 Component 是否合法
        if component not in COMPONENT_MAP:
            return f"❌ Invalid component. Must be one of {list(COMPONENT_MAP.keys())}"

        # 2. 讀取環境變數
        token = settings.GITHUB_TOKEN
        repo_name = settings.GITHUB_REPO_NAME
        base_branch = settings.BASE_BRANCH
        
        if not token or not repo_name:
            return "❌ Missing GITHUB_TOKEN or GITHUB_REPO_NAME in .env"

        auth = Auth.Token(token)
        g = Github(auth=auth)
        repo = g.get_repo(repo_name)
        
        # 3. 自動計算下一個 ID 和檔名
        # 例如: "ERR-COGNITO-0003"
        next_id_str = get_next_error_id(repo, component)
        filename = f"error_docs/{component}/{next_id_str}.md"
        
        # 4. 組合完整的檔案內容 (YAML Header + Body)
        # 這裡幫你自動填好 YAML，Wuli 只要專注寫內容
        full_file_content = f"""---
                            id: {next_id_str}
                            component: {component}
                            category: error
                            tags: [{', '.join([f'"{t.strip()}"' for t in tags.split(',')])}]
                            patterns:
                            - "{title}"
                            ---

                            {content_body}
                            """

        # 5. 準備新的臨時分支
        new_branch_name = f"doc/wuli-add-{next_id_str}-{int(time.time())}"
        
        # 6. 切分支與發 PR (同之前的邏輯)
        source_branch = repo.get_branch(base_branch)
        repo.create_git_ref(ref=f"refs/heads/{new_branch_name}", sha=source_branch.commit.sha)
        
        repo.create_file(
            path=filename,
            message=f"Add {next_id_str} by Wuli Agent",
            content=full_file_content,
            branch=new_branch_name
        )

        pr_body = f"""
        ## 🤖 Wuli Auto-Generated Card
        
        - **ID**: `{next_id_str}`
        - **Component**: `{component}`
        - **File**: `{filename}`
        
        Auto-numbered and formatted. Please review. 🐾
        """
        
        pr = repo.create_pull(
            title=f"[Wuli] New Error Card: {next_id_str}",
            body=pr_body,
            head=new_branch_name,
            base=base_branch
        )
        
        return f"✅ 成功！已自動編號為 `{next_id_str}` 並發出 PR：{pr.html_url}"

    except Exception as e:
        return f"❌ GitHub Operation Failed: {str(e)}"