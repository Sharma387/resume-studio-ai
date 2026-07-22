from pydantic import BaseModel, Field


class JobDescription(BaseModel):
    resume_id: str = Field(..., min_length=1, description="ID of the resume to match against")
    job_title: str | None = Field(None, description="Optional job title for display")
    description: str = Field(..., min_length=10, description="Full job description text")


class SkillMatch(BaseModel):
    skill: str = Field(..., min_length=1, description="Skill name")
    required: bool = Field(default=True, description="Whether the job requires this skill")
    matched: bool = Field(default=False, description="Whether the resume contains this skill")
    category: str | None = Field(None, description="Skill category (e.g. Languages, Frontend)")


class Recommendation(BaseModel):
    section: str = Field(..., min_length=1, description="Resume section to improve")
    priority: str = Field(default="medium", pattern=r"^(high|medium|low)$")
    message: str = Field(..., min_length=10, description="What to improve")
    suggestion: str | None = Field(None, description="How to implement the improvement")


class MatchResult(BaseModel):
    id: str = Field(..., min_length=1, description="Unique match ID")
    resume_id: str = Field(..., min_length=1)
    job_title: str | None = None
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall ATS match score 0-100")
    skill_matches: list[SkillMatch] = []
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    recommendations: list[Recommendation] = []
    summary: str | None = Field(None, description="Brief summary of the match analysis")
    created_at: str | None = None
