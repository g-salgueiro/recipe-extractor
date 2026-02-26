# tests/test_models.py
"""Testes unitários dos modelos Pydantic (Ingredient, RecipeContent, RecipeModel).

Verifica campos obrigatórios/opcionais, serialização JSON e a renderização
em Markdown via `to_markdown()`.
"""
from datetime import datetime
from src.models.recipe import Ingredient, RecipeContent, RecipeModel


def test_ingredient_all_fields():
    ing = Ingredient(quantity="2", unit="xícaras", name="farinha de trigo", notes="peneirada")
    assert ing.name == "farinha de trigo"
    assert ing.quantity == "2"


def test_ingredient_name_only():
    ing = Ingredient(name="sal a gosto")
    assert ing.quantity is None
    assert ing.unit is None
    assert ing.notes is None


def test_recipe_content_required_fields():
    content = RecipeContent(
        title="Bolo de Chocolate",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Misture tudo", "Asse por 40min"],
        extraction_confidence=0.95,
    )
    assert content.title == "Bolo de Chocolate"
    assert len(content.ingredients) == 1
    assert content.extraction_confidence == 0.95


def test_recipe_model_with_metadata():
    model = RecipeModel(
        title="Bolo",
        ingredients=[],
        steps=[],
        extraction_confidence=0.5,
        source_url="https://youtube.com/watch?v=abc",
        source_type="youtube",
    )
    assert model.source_type == "youtube"
    assert isinstance(model.extracted_at, datetime)


def test_recipe_model_json_serialization():
    model = RecipeModel(
        title="Bolo",
        ingredients=[Ingredient(name="farinha", quantity="2", unit="xícaras")],
        steps=["Passo 1"],
        extraction_confidence=0.9,
        source_url="https://example.com",
        source_type="web",
    )
    data = model.model_dump_json()
    assert "farinha" in data
    assert "Passo 1" in data


def test_to_markdown_contains_title_and_ingredients():
    model = RecipeModel(
        title="Bolo de Cenoura",
        ingredients=[Ingredient(name="cenoura", quantity="3", unit="unidades")],
        steps=["Bata no liquidificador", "Asse a 180 graus"],
        tips=["Não abra o forno antes de 30 min"],
        extraction_confidence=0.85,
        source_url="https://example.com",
        source_type="web",
    )
    md = model.to_markdown()
    assert "# Bolo de Cenoura" in md
    assert "cenoura" in md
    assert "Bata no liquidificador" in md
    assert "Não abra o forno" in md
