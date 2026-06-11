from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import ANALYST_DIRS, GLOBAL_SPECS_ROOT, PROJECT_ROOT


@dataclass(frozen=True)
class AnalystNode:
    key: str
    folder: str
    title: str

    @property
    def path(self) -> Path:
        return PROJECT_ROOT / self.folder


ANALYSTS = {
    key: AnalystNode(key=key, folder=folder, title=folder)
    for key, folder in ANALYST_DIRS.items()
}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def load_global_context() -> str:
    parts = [
        ("全局工作流与分析师联动协议", GLOBAL_SPECS_ROOT / "00_Global_Workflow_and_Analyst_Interlock.md"),
        ("系统目标与最终输出", GLOBAL_SPECS_ROOT / "00_System_Objective_and_Final_Output.md"),
    ]
    return "\n\n".join(
        f"## {title}\n{read_text(path)}" for title, path in parts if path.exists()
    )


def load_analyst_context(node: AnalystNode) -> str:
    base = node.path
    files = [
        ("角色画像", base / "analyst_profile.md"),
        ("分析师指令", base / "instructions.md"),
        ("工作流", base / "workflow.md"),
        ("输入规范", base / "input_schema.md"),
        ("输出规范", base / "output_schema.md"),
        ("知识清单", base / "knowledge" / "checklist.md"),
        ("方法论", base / "knowledge" / "methodology.md"),
        ("信息源地图", base / "knowledge" / "source_map.md"),
    ]
    sections = []
    for title, path in files:
        content = read_text(path)
        if content:
            sections.append(f"## {title}\n{content}")
    return "\n\n".join(sections)
