from app.services.pdf_templates.base import BaseTemplate


class MinimalTemplate(BaseTemplate):
    name = "minimal"
    accent_color = "#333333"
    dark_color = "#111111"
    gray_color = "#666666"
    show_section_lines = False

    def _build_styles(self):
        styles = super()._build_styles()
        styles["Name"].fontSize = 18
        styles["Name"].spaceAfter = 8
        styles["ContactRow"].fontSize = 8
        styles["ContactRow"].spaceAfter = 1
        styles["LinkRow"].fontSize = 7
        styles["LinkRow"].spaceAfter = 1
        styles["SectionTitle"].fontSize = 10
        styles["SectionTitle"].spaceBefore = 10
        styles["SectionTitle"].spaceAfter = 3
        styles["ItemTitle"].fontSize = 9
        styles["ItemTitle"].spaceBefore = 4
        styles["ItemSubtitle"].fontSize = 8
        styles["ItemSubtitle"].spaceAfter = 1
        styles["BulletItem"].fontSize = 8
        styles["BulletItem"].leading = 12
        styles["BulletItem"].spaceAfter = 0
        styles["BulletItem"].leftIndent = 10
        styles["Summary"].fontSize = 8.5
        styles["Summary"].leading = 13
        styles["Summary"].spaceAfter = 2
        styles["SkillItem"].fontSize = 8
        styles["SkillItem"].spaceAfter = 1
        return styles
