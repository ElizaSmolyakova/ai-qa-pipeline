from pathlib import Path


def load_skill(skill_name: str) -> str:
    skill_path = Path("skills") / skill_name / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Скилл не найден: {skill_path}")
    return skill_path.read_text(encoding="utf-8")
