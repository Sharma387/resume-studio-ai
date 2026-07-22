from app.services.pdf_templates.base import BaseTemplate


class ModernTemplate(BaseTemplate):
    name = "modern"
    accent_color = "#00b894"
    dark_color = "#2d3436"
    gray_color = "#636e72"
    section_divider = "▸ {title}"

    def _build_styles(self):
        styles = super()._build_styles()
        styles["Name"].fontSize = 26
        styles["Name"].spaceAfter = 16
        styles["ContactRow"].fontSize = 9.5
        styles["SectionTitle"].fontSize = 14
        styles["SectionTitle"].spaceBefore = 22
        styles["SectionTitle"].spaceAfter = 8
        styles["ItemTitle"].fontSize = 11
        styles["ItemTitle"].spaceBefore = 10
        styles["BulletItem"].fontSize = 9.5
        styles["BulletItem"].leading = 16
        styles["BulletItem"].leftIndent = 16
        styles["Summary"].fontSize = 10
        styles["Summary"].leading = 17
        return styles
