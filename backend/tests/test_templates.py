import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.resume import Resume
from app.services.storage_service import save_resume
from app.services.pdf_templates.registry import TemplateRegistry
from app.services.pdf_templates.executive import ExecutiveTemplate
from app.services.pdf_templates.ats import ATSTemplate
from app.services.pdf_templates.technical import TechnicalTemplate
from app.services.pdf_templates.modern import ModernTemplate
from app.services.pdf_templates.minimal import MinimalTemplate


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestTemplateRegistry:
    def test_all_templates_registered(self):
        names = TemplateRegistry.list_names()
        assert "executive" in names
        assert "ats" in names
        assert "technical" in names
        assert "modern" in names
        assert "minimal" in names

    def test_get_returns_correct_class(self):
        assert isinstance(TemplateRegistry.get("executive"), ExecutiveTemplate)
        assert isinstance(TemplateRegistry.get("ats"), ATSTemplate)
        assert isinstance(TemplateRegistry.get("technical"), TechnicalTemplate)
        assert isinstance(TemplateRegistry.get("modern"), ModernTemplate)
        assert isinstance(TemplateRegistry.get("minimal"), MinimalTemplate)

    def test_get_default(self):
        assert isinstance(TemplateRegistry.get_default(), ExecutiveTemplate)

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown template"):
            TemplateRegistry.get("nonexistent")

    def test_case_insensitive(self):
        assert isinstance(TemplateRegistry.get("EXECUTIVE"), ExecutiveTemplate)


class TestTemplateProperties:
    @pytest.mark.parametrize("name,cls", [
        ("executive", ExecutiveTemplate),
        ("ats", ATSTemplate),
        ("technical", TechnicalTemplate),
        ("modern", ModernTemplate),
        ("minimal", MinimalTemplate),
    ])
    def test_template_has_name(self, name, cls):
        t = cls()
        assert t.name == name

    def test_unique_names(self):
        names = [cls().name for cls in [ExecutiveTemplate, ATSTemplate, TechnicalTemplate, ModernTemplate, MinimalTemplate]]
        assert len(names) == len(set(names))


class TestEachTemplateRenders:
    @pytest.mark.parametrize("name", ["executive", "ats", "technical", "modern", "minimal"])
    def test_renders_without_error(self, name):
        resume = Resume(
            user_id="test",
            full_name="Test User",
            email="test@example.com",
            summary="A summary.",
            experience=[{"company": "Acme", "title": "Engineer", "current": False, "description": ["Did stuff."]}],
            education=[{"institution": "MIT", "degree": "BS", "achievements": []}],
            skills=[{"category": "Lang", "skills": ["Python"]}],
            projects=[{"name": "Proj", "technologies": []}],
            certifications=[{"name": "Cert"}],
        )
        template = TemplateRegistry.get(name)
        flowables = template.build_document(resume)
        assert len(flowables) > 0


@pytest.mark.asyncio
async def test_endpoint_with_template(client):
    resume_id = "pdf-template-test"
    save_resume(resume_id, Resume(user_id="test", full_name="Jane", email="j@e.com"))

    async with client as ac:
        resp = await ac.post(f"/api/v1/resume/{resume_id}/pdf", params={"template": "modern"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["template"] == "modern"


@pytest.mark.asyncio
async def test_endpoint_default_template(client):
    resume_id = "pdf-default-test"
    save_resume(resume_id, Resume(user_id="test", full_name="Jane", email="j@e.com"))

    async with client as ac:
        resp = await ac.post(f"/api/v1/resume/{resume_id}/pdf")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_endpoint_invalid_template(client):
    resume_id = "pdf-bad-test"
    save_resume(resume_id, Resume(user_id="test", full_name="Jane", email="j@e.com"))

    async with client as ac:
        resp = await ac.post(f"/api/v1/resume/{resume_id}/pdf", params={"template": "bogus"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_templates(client):
    async with client as ac:
        resp = await ac.get("/api/v1/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 5
    assert "executive" in data["data"]
