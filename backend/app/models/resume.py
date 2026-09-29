from pydantic import BaseModel, EmailStr, Field, HttpUrl, model_validator


class Education(BaseModel):
    institution: str = Field(..., min_length=1, description="School or university name")
    degree: str = Field(..., min_length=1, description="Degree earned")
    field: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    gpa: float | None = Field(None, ge=0.0, le=4.0)
    achievements: list[str] = []


class Experience(BaseModel):
    company: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    current: bool = False
    description: list[str] = []


class Project(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None
    url: HttpUrl | None = None
    technologies: list[str] = []


class Skill(BaseModel):
    category: str = Field(..., min_length=1)
    skills: list[str] = []


class Certification(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    issuer: str | None = None
    date: str | None = None
    url: HttpUrl | None = None
    category: str | None = Field(default=None, min_length=1)
    values: list[str] = []

    @model_validator(mode="after")
    def require_name_or_category(self) -> "Certification":
        if not self.name and not self.category:
            raise ValueError("certification must define name or category")
        return self


class Award(BaseModel):
    name: str = Field(..., min_length=1)
    issuer: str | None = None
    date: str | None = None
    description: str | None = None


class Language(BaseModel):
    name: str = Field(..., min_length=1)
    proficiency: str | None = None


class Resume(BaseModel):
    user_id: str
    full_name: str = Field(..., min_length=1)
    email: EmailStr
    phone: str | None = None
    location: str | None = None
    linkedin: HttpUrl | None = None
    github: HttpUrl | None = None
    website: HttpUrl | None = None
    professional_title: str | None = None
    summary: str | None = None
    education: list[Education] = []
    experience: list[Experience] = []
    projects: list[Project] = []
    skills: list[Skill] = []
    certifications: list[Certification] = []
    awards: list[Award] = []
    languages: list[Language] = []

    @model_validator(mode="before")
    @classmethod
    def normalize_empty_urls(cls, data: dict) -> dict:
        """Convert absent URLs to None for ``HttpUrl | None`` fields before validation.

        Also prefixes URLs that are missing a scheme (LLM output often drops
        ``https://``, e.g. ``linkedin.com/in/jane``) so they validate.

        Models often answer "unknown" fields with prose placeholders rather than
        null — "Not specified", "N/A", "none". Those are not URLs, but
        prefixing them yields ``https://Not specified``, which fails
        ``HttpUrl`` and takes the whole record down with it: a section full of
        certifications that happened to carry a placeholder URL was dropped
        entirely. Treat them as absent.
        """
        placeholders = {"", "n/a", "na", "none", "null", "nil", "not specified", "not available", "not applicable", "unknown", "not given", "not provided", "-", "--", "tbd"}

        def _normalize(value):
            if not isinstance(value, str):
                return value
            value = value.strip()
            if value.lower() in placeholders:
                return None
            if "://" not in value:
                return "https://" + value
            return value

        def _blank(value):
            """Drop prose placeholders a model used in place of a null."""
            return None if isinstance(value, str) and value.strip().lower() in placeholders else value

        # Top-level URL fields
        for field in ("linkedin", "github", "website"):
            if field in data:
                data[field] = _normalize(data[field])
        # Project.url
        for item in data.get("projects", []):
            if isinstance(item, dict) and "url" in item:
                item["url"] = _normalize(item["url"])
        for item in data.get("certifications", []):
            if not isinstance(item, dict):
                continue
            if "url" in item:
                item["url"] = _normalize(item["url"])
            # A placeholder issuer/date is not metadata: it would render as
            # "PRINCE2 Practitioner · Not specified · Not specified" and, worse,
            # make the entry look like a standalone card instead of a member of
            # its category group.
            for field in ("issuer", "date"):
                if field in item:
                    item[field] = _blank(item[field])
        return data
