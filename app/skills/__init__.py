"""
Skills Auto-Discovery 模組。

自動掃描 app/skills/ 下所有 SkillBase 子類別，
依照使用者權限 (admin/user) 動態組裝工具清單與 SOP。
"""
import importlib
import pkgutil
from typing import List, Dict

from app.skills.base import SkillBase
from app.utils.logging import get_logger

logger = get_logger(__name__)

# 快取：避免每次 request 都重新掃描
_skill_registry: List[SkillBase] = []


def _scan_skills() -> List[SkillBase]:
    """
    掃描 app/skills/ 下所有模組，
    找出所有繼承 SkillBase 的具體類別並實例化。
    """
    global _skill_registry
    if _skill_registry:
        return _skill_registry

    import app.skills as skills_pkg

    for importer, modname, ispkg in pkgutil.iter_modules(skills_pkg.__path__):
        if modname == "base":
            continue
        try:
            module = importlib.import_module(f"app.skills.{modname}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, SkillBase)
                    and attr is not SkillBase
                    and attr.name  # 確保有設定 name
                ):
                    _skill_registry.append(attr())
                    logger.info(f"  📦 已載入 Skill: {attr.name} (permission={attr.permission})")
        except Exception as e:
            logger.warning(f"  ⚠️ 載入 Skill 模組 '{modname}' 失敗: {e}")

    logger.info(f"✅ Skills Auto-Discovery 完成，共載入 {len(_skill_registry)} 個 Skills")
    return _skill_registry


def discover_skills(is_admin: bool = False) -> List:
    """
    根據權限等級，回傳可用的 LangChain Tool 清單。

    對於 search_litellm_logs 這個特殊 skill，
    admin 和 user 各有不同的版本（同 name 不同 class），
    需要依權限挑選正確的版本。

    Args:
        is_admin: 是否為管理員

    Returns:
        List[BaseTool]: LangChain Tool 物件清單
    """
    all_skills = _scan_skills()
    tools = []
    seen_names = set()

    for skill in all_skills:
        # admin 可用所有 skill
        # user 只能用 permission == "user" 的 skill
        if not is_admin and skill.permission == "admin":
            continue

        # 處理同名 skill 衝突 (如 search_litellm_logs 有 admin/user 版本)
        if skill.name in seen_names:
            continue
        seen_names.add(skill.name)

        tools.append(skill.as_tool())

    return tools


def get_all_sops(is_admin: bool = False) -> str:
    """
    收集所有可用 skills 的 SOP，組合成 system prompt 的一部分。

    Args:
        is_admin: 是否為管理員

    Returns:
        str: 組合後的 SOP 文字
    """
    all_skills = _scan_skills()
    sop_parts = []
    seen_names = set()

    for skill in all_skills:
        if not is_admin and skill.permission == "admin":
            continue

        if skill.name in seen_names:
            continue
        seen_names.add(skill.name)

        if skill.sop and skill.sop.strip():
            sop_parts.append(skill.sop.strip())

    return "\n\n".join(sop_parts)


def get_status_messages() -> Dict[str, str]:
    """
    回傳所有 skill 的 tool_name → status_message 對照表，
    供 main.py 動態顯示呼叫狀態。

    Returns:
        Dict[str, str]: {tool_name: status_message}
    """
    all_skills = _scan_skills()
    mapping = {}
    for skill in all_skills:
        if skill.status_message:
            mapping[skill.name] = skill.status_message
    return mapping
