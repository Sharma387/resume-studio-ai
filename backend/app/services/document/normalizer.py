import re


class TextNormalizer:
    """Normalize extracted text — whitespace, deduplication, encoding."""

    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""

        lines = text.split("\n")
        cleaned: list[str] = []
        prev_blank = False

        for line in lines:
            stripped = line.strip()
            if stripped == "":
                if not prev_blank:
                    cleaned.append("")
                    prev_blank = True
            else:
                cleaned.append(stripped)
                prev_blank = False

        result = "\n".join(cleaned)
        result = re.sub(r" +", " ", result)
        return result.strip()
