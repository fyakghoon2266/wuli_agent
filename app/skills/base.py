"""
Skills 基礎架構：所有 Skill 的抽象基底類別。

每個 Skill 自帶 metadata（名稱、描述、權限、SOP、狀態訊息），
未來新增 Skill 只需繼承 SkillBase 並實作 as_tool()，
放入 app/skills/ 資料夾即可被自動發現。
"""
from abc import ABC, abstractmethod
from langchain.tools import BaseTool


class SkillBase(ABC):
    """
    所有 Skill 的抽象基底類別。

    子類別必須定義以下類別屬性：
        name (str):            Skill 名稱，對應 LangChain tool name
        description (str):     一行描述，給人看的
        permission (str):      "user" 表示所有人可用，"admin" 表示僅管理員
        tags (list[str]):      分類標籤，用於未來篩選
        sop (str):             注入 system prompt 的使用策略說明
        status_message (str):  Agent 呼叫此 tool 時，顯示給使用者的狀態文字
    """

    name: str = ""
    description: str = ""
    permission: str = "user"      # "user" | "admin"
    tags: list = []
    sop: str = ""                 # 會自動注入到 system prompt
    status_message: str = ""      # 呼叫時顯示的提示訊息

    @abstractmethod
    def as_tool(self) -> BaseTool:
        """回傳 LangChain Tool 物件"""
        ...
