class AIError(Exception):
    """Base exception for all AI-related errors."""


class AIServiceUnavailable(AIError):  # noqa: N818  keep public name referenced across AI services
    """Raised when the AI service cannot be reached after retries."""


class AIResponseError(AIError):
    """Raised when the AI returns an invalid or unparseable response."""


class ResponseTruncated(AIResponseError):  # noqa: N818  crosses every AI service boundary
    """Raised when the provider stopped generating because it hit its token cap.

    Distinct from a malformed response on purpose. A truncated body is valid
    text that happens to stop mid-structure, so it fails JSON parsing for a
    reason that says nothing about the response's quality — and it is fixable,
    by asking for a bigger ``num_predict``. Folding it into
    :class:`AIServiceUnavailable` would report a healthy local model as an
    outage, and folding it into a generic parse failure would retry the same
    cap and get the same cut-off response.

    The concrete failure this prevents, measured on the real V4.1 resume: the
    certifications chunk needs up to 2157 output tokens, the cap was 2000, and
    every truncated response was converted into a clean empty chunk. The
    section vanished, along with the three genuine credentials in it, and the
    parse still reported success.
    """

    def __init__(
        self,
        message: str,
        *,
        tokens: int | None = None,
        num_predict: int | None = None,
        section: str | None = None,
    ) -> None:
        super().__init__(message)
        # Tokens actually generated before the cut, and the cap that cut it.
        self.tokens = tokens
        self.num_predict = num_predict
        # Filled in by the chunk parser, which knows which section this was.
        self.section = section

    def describe(self) -> str:
        """One line naming the cap that was hit, for logs and error messages."""
        parts = []
        if self.section:
            parts.append(f"section={self.section}")
        if self.tokens is not None and self.num_predict is not None:
            parts.append(f"stopped at {self.tokens}/{self.num_predict} tokens")
        elif self.tokens is not None:
            parts.append(f"{self.tokens} tokens")
        return f"{super().__str__()} ({', '.join(parts)})" if parts else str(self)


class AIMockFallback(AIError):  # noqa: N818  keep public name referenced across AI services
    """Raised internally when falling back to mock data."""
