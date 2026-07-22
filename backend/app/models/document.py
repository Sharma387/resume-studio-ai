from pydantic import BaseModel, Field


class ExtractionResult:
    """Internal DTO between extractors and the Document model."""

    def __init__(self, content: str, page_count: int = 0):
        self.content = content
        self.page_count = page_count


class Document(BaseModel):
    id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    file_type: str = Field(..., pattern=r"^(pdf|docx|txt)$")
    document_type: str = Field(default="unknown", pattern=r"^(resume|job_description|cover_letter|unknown)$")
    mime_type: str = ""
    page_count: int = 0
    word_count: int = 0
    character_count: int = 0
    language: str | None = None
    encoding: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    content: str = ""
    metadata: dict = {}
