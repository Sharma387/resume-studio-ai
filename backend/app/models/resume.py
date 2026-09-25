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
        """Convert empty strings to None for HttpUrl | None fields before validation.

        Also prefixes URLs that are missing a scheme (LLM output often drops
        ``https://``, e.g. ``linkedin.com/in/jane``) so they validate.
        """
        def _normalize(value):
            if not isinstance(value, str):
                return value
            value = value.strip()
            if not value:
                return None
            if "://" not in value:
                return "https://" + value
            return value

        # Top-level URL fields
        for field in ("linkedin", "github", "website"):
            if field in data:
                data[field] = _normalize(data[field])
        # Project.url
        for item in data.get("projects", []):
            if isinstance(item, dict) and "url" in item:
                item["url"] = _normalize(item["url"])
        # Certification.url
        for item in data.get("certifications", []):
            if isinstance(item, dict) and "url" in item:
                item["url"] = _normalize(item["url"])
        return data
