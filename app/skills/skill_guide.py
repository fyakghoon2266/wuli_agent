"""
.md Skill Prompt Loader

掃描 app/skill_prompts/ 下的所有 .md 檔，解析 YAML frontmatter，
註冊為一個 lookup_skill_guide 工具讓 Wuli 可以動態查閱 SOP。

未來任何人只要在 app/skill_prompts/ 放一個 .md 檔，
重啟後 Wuli 就能自動發現並使用。
"""
import os
import yaml
from typing import Dict, List

from langchain.tools import tool
from app.skills.base import SkillBase
from app.utils.logging import get_logger

logger = get_logger(__name__)

SKILL_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "skill_prompts")

# 快取：{skill_name: {description, triggers, content}}
_skill_prompt_registry: Dict[str, dict] = {}


def _parse_md_skill(filepath: str) -> dict:
    """
    解析一個 .md skill 檔案，回傳 frontmatter + body。
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    if not raw.startswith("---"):
        return {}

    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}

    try:
        meta = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        logger.warning(f"⚠️ 解析 YAML frontmatter 失敗 ({filepath}): {e}")
        return {}

    if not meta or not meta.get("name"):
        return {}

    return {
        "name": meta["name"],
        "description": meta.get("description", ""),
        "triggers": meta.get("triggers", []),
        "content": parts[2].strip(),
    }


def scan_skill_prompts() -> Dict[str, dict]:
    """
    掃描 app/skill_prompts/ 資料夾，載入所有 .md skill。
    跳過以 _ 開頭的檔案（模板/說明）。
    """
    global _skill_prompt_registry

    if _skill_prompt_registry:
        return _skill_prompt_registry

    if not os.path.isdir(SKILL_PROMPTS_DIR):
        logger.warning(f"⚠️ skill_prompts 資料夾不存在: {SKILL_PROMPTS_DIR}")
        return _skill_prompt_registry

    for filename in sorted(os.listdir(SKILL_PROMPTS_DIR)):
        if filename.startswith("_") or not filename.endswith(".md"):
            continue

        filepath = os.path.join(SKILL_PROMPTS_DIR, filename)
        parsed = _parse_md_skill(filepath)

        if parsed:
            _skill_prompt_registry[parsed["name"]] = parsed
            logger.info(f"  📄 已載入 Skill Prompt: {parsed['name']} ({filename})")

    logger.info(f"✅ Skill Prompts 掃描完成，共載入 {len(_skill_prompt_registry)} 個 .md SOP")
    return _skill_prompt_registry


def build_skill_catalog() -> str:
    """
    產生一份簡短的技能目錄，注入到 system prompt 中。
    格式：每個 skill 一行，包含名稱、描述、觸發關鍵字。
    """
    registry = scan_skill_prompts()

    if not registry:
        return ""

    lines = []
    for name, info in registry.items():
        triggers = ", ".join(info["triggers"][:5]) if info["triggers"] else "無特定觸發詞"
        lines.append(f"  - `{name}`: {info['description']} (觸發詞: {triggers})")

    catalog = (
        "### 📖 可查閱的 SOP 指南\n"
        "當使用者的問題符合以下情境時，請使用 `lookup_skill_guide` 工具查詢完整 SOP，"
        "然後按照 SOP 的步驟執行：\n"
    )
    catalog += "\n".join(lines)

    return catalog


class SkillGuideSkill(SkillBase):
    name = "lookup_skill_guide"
    description = "查閱 .md 格式的 SOP 排查指南"
    permission = "user"
    tags = ["sop", "guide", "knowledge"]
    status_message = "📖 Wuli 正在查閱排查指南..."
    sop = ""  # SOP 目錄由 build_skill_catalog() 動態注入，不走這裡

    def as_tool(self):
        @tool("lookup_skill_guide")
        def lookup_skill_guide(skill_name: str) -> str:
            """
            查閱指定的 SOP 排查指南。

            使用時機：當使用者的問題符合某個已知的排查情境時，
            先用此工具取得完整的 SOP 步驟，再按步驟使用其他工具執行排查。

            Args:
                skill_name: SOP 名稱，例如 "troubleshoot_504", "troubleshoot_blocked"。
                            如果不確定名稱，可以傳入 "list" 查看所有可用的 SOP。
            """
            registry = scan_skill_prompts()

            # 特殊指令：列出所有可用的 SOP
            if skill_name.lower().strip() in ("list", "all", "目錄"):
                if not registry:
                    return "📭 目前沒有任何 .md SOP 指南。"
                lines = []
                for name, info in registry.items():
                    lines.append(f"- **{name}**: {info['description']}")
                return "📖 可用的 SOP 指南：\n" + "\n".join(lines)

            # 精確名稱匹配
            if skill_name in registry:
                info = registry[skill_name]
                return (
                    f"📖 SOP 指南：{info['name']}\n"
                    f"說明：{info['description']}\n"
                    f"{'=' * 50}\n\n"
                    f"{info['content']}"
                )

            # 模糊匹配：用觸發詞搜尋
            query_lower = skill_name.lower()
            for name, info in registry.items():
                for trigger in info.get("triggers", []):
                    if trigger.lower() in query_lower or query_lower in trigger.lower():
                        return (
                            f"📖 SOP 指南：{info['name']} (透過關鍵字 '{trigger}' 匹配)\n"
                            f"說明：{info['description']}\n"
                            f"{'=' * 50}\n\n"
                            f"{info['content']}"
                        )

            # 都找不到
            available = ", ".join(registry.keys()) if registry else "（目前無任何 SOP）"
            return (
                f"📭 找不到名為 '{skill_name}' 的 SOP 指南。\n"
                f"可用的 SOP：{available}\n"
                f"提示：你也可以傳入 'list' 查看完整目錄。"
            )

        return lookup_skill_guide
