import re
import time
from github import Github, Auth
from langchain.tools import tool
from app.skills.base import SkillBase
from app.config import settings


COMPONENT_MAP = {
    "cognito": "cognito",
    "gateway": "gateway",
    "generic": "generic",
    "guardrail": "guardrail"
}


def get_next_error_id(repo, component: str) -> str:
    folder_path = f"error_docs/{component}"
    prefix = f"ERR-{component.upper()}-"
    max_id = 0

    try:
        contents = repo.get_contents(folder_path)
        for content_file in contents:
            if content_file.name.endswith(".md"):
                match = re.search(rf"{prefix}(\d+)\.md", content_file.name)
                if match:
                    num = int(match.group(1))
                    if num > max_id:
                        max_id = num
    except Exception:
        pass

    next_id = max_id + 1
    return f"{prefix}{next_id:04d}"


class ProposeErrorCardSkill(SkillBase):
    name = "propose_new_error_card"
    description = "透過 GitHub PR 新增 Error Card 至知識庫"
    permission = "admin"
    tags = ["git", "knowledge", "pr"]
    status_message = "📝 Wuli 正在撰寫新的 Error Card 並發 PR..."
    sop = (
        "### 📚 知識庫新增 SOP (嚴格觸發制 🔒)\n"
        "**【重要規則】請勿自動建立 Error Card！** "
        "只有在使用者**明確發出指令** (如 \"@Wuli 加入知識庫\", \"發 PR 更新文件\") 時才允許執行。\n"
        "**執行流程：**\n"
        "1. 聽到觸發關鍵字。\n"
        "2. 選擇分類 (cognito / gateway / guardrail / generic)。\n"
        "3. 撰寫符合 Markdown 格式的 `content_body`。\n"
        "4. 呼叫 `propose_new_error_card`。\n"
    )

    def as_tool(self):
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
                if component not in COMPONENT_MAP:
                    return f"❌ Invalid component. Must be one of {list(COMPONENT_MAP.keys())}"

                token = settings.GITHUB_TOKEN
                repo_name = settings.GITHUB_REPO_NAME
                base_branch = settings.BASE_BRANCH

                if not token or not repo_name:
                    return "❌ Missing GITHUB_TOKEN or GITHUB_REPO_NAME in .env"

                auth = Auth.Token(token)
                g = Github(auth=auth)
                repo = g.get_repo(repo_name)

                next_id_str = get_next_error_id(repo, component)
                filename = f"error_docs/{component}/{next_id_str}.md"

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

                new_branch_name = f"doc/wuli-add-{next_id_str}-{int(time.time())}"

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

        return propose_new_error_card
