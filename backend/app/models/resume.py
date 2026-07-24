from pydantic import BaseModel, EmailStr, HttpUrl, Field, model_validator


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
    name: str = Field(..., min_length=1)
    issuer: str | None = None
    date: str | None = None
    url: HttpUrl | None = None


class Resume(BaseModel):
    user_id: str
    full_name: str = Field(..., min_length=1)
    email: EmailStr
    phone: str | None = None
    location: str | None = None
    linkedin: HttpUrl | None = None
    github: HttpUrl | None = None
    website: HttpUrl | None = None
    summary: str | None = None
    education: list[Education] = []
    experience: list[Experience] = []
    projects: list[Project] = []
    skills: list[Skill] = []
    certifications: list[Certification] = []

    @model_validator(mode="before")
    @classmethod
    def normalize_empty_urls(cls, data: dict) -> dict:
        """Convert empty strings to None for HttpUrl | None fields before validation."""
        # Top-level URL fields
        for field in ("linkedin", "github", "website"):
            if field in data and data[field] == "":
                data[field] = None
        # Project.url
        for item in data.get("projects", []):
            if isinstance(item, dict) and "url" in item and item["url"] == "":
                item["url"] = None
        # Certification.url
        for item in data.get("certifications", []):
            if isinstance(item, dict) and "url" in item and item["url"] == "":
                item["url"] = None
        return data
