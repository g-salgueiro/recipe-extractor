import pytest


@pytest.fixture
def sample_recipe_text():
    return """
    Bolo de Chocolate

    Ingredientes:
    - 2 xícaras de farinha de trigo
    - 1 xícara de açúcar
    - 1/2 xícara de cacau em pó
    - 3 ovos
    - 1 xícara de leite
    - 1/2 xícara de óleo

    Modo de preparo:
    1. Misture os ingredientes secos
    2. Adicione os ovos, leite e óleo
    3. Leve ao forno a 180 graus por 40 minutos

    Dica: use cacau 70% para um sabor mais intenso
    """
