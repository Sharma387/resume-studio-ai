from pathlib import Path

import pytest

from app.services.prompt_service import PromptService


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "resume_parser_system.md").write_text("System: {schema}")
    (d / "resume_parser_user.md").write_text("User: {text}")
    return d


def test_loads_system_prompt(prompts_dir: Path):
    svc = PromptService(prompts_dir)
    system, user = svc.build_prompt("my text", "my schema")
    assert "System:" in system
    assert "my schema" in system


def test_loads_user_prompt(prompts_dir: Path):
    svc = PromptService(prompts_dir)
    system, user = svc.build_prompt("my text", "my schema")
    assert "User:" in user
    assert "my text" in user


def test_injects_schema(prompts_dir: Path):
    svc = PromptService(prompts_dir)
    system, _ = svc.build_prompt("text", '{"type": "object"}')
    assert '{"type": "object"}' in system


def test_real_prompt_files():
    svc = PromptService()
    system, user = svc.build_prompt("sample resume text", "{}")
    assert len(system) > 50
    assert len(user) > 10
    assert "sample resume text" in user
    assert "{}" in user
