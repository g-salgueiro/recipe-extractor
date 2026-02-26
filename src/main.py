# src/main.py
"""
Entrypoint CLI do Recipe Extractor.

Uso:
    python -m src.main <URL>

Fluxo:
    1. `detect_source(url)` identifica a fonte (YouTube / Instagram / Web)
    2. O agente correspondente é instanciado e `extract(url)` é chamado
    3. O resultado é uma `list[RecipeModel]` — um post pode conter N receitas
    4. Para cada receita é salvo um par de arquivos:
         recipe_YYYYMMDD_HHMMSS.json       (única receita)
         recipe_YYYYMMDD_HHMMSS_1.json     (quando há múltiplas)
"""
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.agents.base import BaseAgent
from src.agents.instagram import InstagramAgent
from src.agents.web import WebAgent
from src.agents.youtube import YouTubeAgent
from src.models.recipe import RecipeModel
from src.router import UnsupportedSourceError, detect_source

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def run(url: str) -> list[RecipeModel]:
    """Roteia a URL para o agente correto e retorna as receitas extraídas."""
    source = detect_source(url)
    logger.info(f"Fonte detectada: {source}")
    agents: dict[str, type[BaseAgent]] = {
        "youtube": YouTubeAgent,
        "instagram": InstagramAgent,
        "web": WebAgent,
    }
    agent = agents[source]()
    return await agent.extract(url)


def save_outputs(recipes: list[RecipeModel], output_dir: Path = Path(".")) -> None:
    """Salva cada receita como JSON + Markdown no diretório especificado.

    Quando há múltiplas receitas, os arquivos recebem sufixo numérico
    (_1, _2, …) para evitar colisão de nomes.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    for i, recipe in enumerate(recipes):
        suffix = f"_{i + 1}" if len(recipes) > 1 else ""
        base_name = f"recipe_{timestamp}{suffix}"

        json_path = output_dir / f"{base_name}.json"
        json_path.write_text(recipe.model_dump_json(indent=2), encoding="utf-8")
        logger.info(f"JSON salvo: {json_path}")

        md_path = output_dir / f"{base_name}.md"
        md_path.write_text(recipe.to_markdown(), encoding="utf-8")
        logger.info(f"Markdown salvo: {md_path}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python -m src.main <URL>")
        sys.exit(1)

    url = sys.argv[1]
    try:
        recipes = asyncio.run(run(url))
        save_outputs(recipes)
        print(f"\n{len(recipes)} receita(s) extraída(s):")
        for recipe in recipes:
            print(f"  - {recipe.title} (confiança: {recipe.extraction_confidence:.0%}, "
                  f"ingredientes: {len(recipe.ingredients)}, passos: {len(recipe.steps)})")
    except UnsupportedSourceError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Falha na extração: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
