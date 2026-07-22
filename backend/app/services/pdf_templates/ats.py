from app.services.pdf_templates.base import BaseTemplate


class ATSTemplate(BaseTemplate):
    name = "ats"
    accent_color = "#333333"
    dark_color = "#222222"
    gray_color = "#555555"
    show_section_lines = False

    def _build_styles(self):
        styles = super()._build_styles()
        styles["SectionTitle"].fontSize = 11
        styles["SectionTitle"].spaceBefore = 12
        styles["SectionTitle"].spaceAfter = 4
        styles["ItemTitle"].fontSize = 9.5
        styles["ItemTitle"].spaceBefore = 4
        styles["BulletItem"].fontSize = 8.5
        styles["BulletItem"].leading = 13
        styles["BulletItem"].leftIndent = 10
        return styles
