# src/models/recipe.py
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    quantity: str | None = None
    unit: str | None = None
    name: str
    notes: str | None = None


class RecipeContent(BaseModel):
    """Fields extracted by the LLM."""
    title: str
    servings: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    ingredients: list[Ingredient]
    steps: list[str]
    tips: list[str] = Field(default_factory=list)
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class RecipeModel(RecipeContent):
    """Full model with source metadata."""
    source_url: str
    source_type: Literal["youtube", "instagram", "web"]
    extracted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            "",
            f"**Fonte:** {self.source_url}",
        ]
        if self.servings:
            lines.append(f"**Porções:** {self.servings}")
        if self.prep_time:
            lines.append(f"**Tempo de preparo:** {self.prep_time}")
        if self.cook_time:
            lines.append(f"**Tempo de cozimento:** {self.cook_time}")

        lines += ["", "## Ingredientes", ""]
        for ing in self.ingredients:
            parts = [p for p in [ing.quantity, ing.unit, ing.name] if p]
            line = " ".join(parts)
            if ing.notes:
                line += f" ({ing.notes})"
            lines.append(f"- {line}")

        lines += ["", "## Modo de Preparo", ""]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. {step}")

        if self.tips:
            lines += ["", "## Dicas", ""]
            for tip in self.tips:
                lines.append(f"- {tip}")

        lines += [
            "",
            "---",
            f"*Confiança na extração: {self.extraction_confidence:.0%}*",
        ]
        return "\n".join(lines)
