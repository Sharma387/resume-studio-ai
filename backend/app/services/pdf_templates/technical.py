from app.services.pdf_templates.base import BaseTemplate


class TechnicalTemplate(BaseTemplate):
    name = "technical"
    accent_color = "#6c5ce7"
    font_name = "Courier"
    font_bold = "Courier-Bold"

    def _build_styles(self):
        styles = super()._build_styles()
        styles["Name"].fontSize = 20
        styles["SectionTitle"].fontSize = 11
        styles["SectionTitle"].spaceBefore = 14
        styles["BulletItem"].fontSize = 8.5
        styles["BulletItem"].leading = 13
        return styles
