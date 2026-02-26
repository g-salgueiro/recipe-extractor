# src/main.py
import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.agents.instagram import InstagramAgent
from src.agents.web import WebAgent
from src.agents.youtube import YouTubeAgent
from src.models.recipe import RecipeModel
from src.router import UnsupportedSourceError, detect_source

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_AGENTS = {
    "youtube": YouTubeAgent,
    "instagram": InstagramAgent,
    "web": WebAgent,
}


async def run(url: str) -> RecipeModel:
    source = detect_source(url)
    logger.info(f"Fonte detectada: {source} — {url}")
    agent_class = {
        "youtube": YouTubeAgent,
        "instagram": InstagramAgent,
        "web": WebAgent,
    }[source]
    agent = agent_class()
    return await agent.extract(url)


def save_outputs(recipe: RecipeModel, output_dir: Path = Path(".")) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = f"recipe_{timestamp}"

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
        recipe = asyncio.run(run(url))
        save_outputs(recipe)
        print(f"\nReceita extraída: {recipe.title}")
        print(f"  Confiança: {recipe.extraction_confidence:.0%}")
        print(f"  Ingredientes: {len(recipe.ingredients)}")
        print(f"  Passos: {len(recipe.steps)}")
    except UnsupportedSourceError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Falha na extração: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
