from app.services.pdf_templates.base import BaseTemplate
from app.services.pdf_templates.executive import ExecutiveTemplate
from app.services.pdf_templates.ats import ATSTemplate
from app.services.pdf_templates.technical import TechnicalTemplate
from app.services.pdf_templates.modern import ModernTemplate
from app.services.pdf_templates.minimal import MinimalTemplate


class TemplateRegistry:
    _templates: dict[str, type[BaseTemplate]] = {}

    @classmethod
    def register(cls, template_class: type[BaseTemplate]) -> None:
        instance = template_class()
        cls._templates[instance.name] = template_class

    @classmethod
    def get(cls, name: str) -> BaseTemplate:
        name = name.lower()
        if name not in cls._templates:
            raise ValueError(
                f"Unknown template '{name}'. Available: {', '.join(sorted(cls._templates))}"
            )
        return cls._templates[name]()

    @classmethod
    def list_names(cls) -> list[str]:
        return sorted(cls._templates)

    @classmethod
    def get_default(cls) -> BaseTemplate:
        return cls.get("executive")


TemplateRegistry.register(ExecutiveTemplate)
TemplateRegistry.register(ATSTemplate)
TemplateRegistry.register(TechnicalTemplate)
TemplateRegistry.register(ModernTemplate)
TemplateRegistry.register(MinimalTemplate)
