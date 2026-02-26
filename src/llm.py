# src/llm.py
import os

from dotenv import load_dotenv
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIChatModel as OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.models.recipe import RecipeContent, RecipeModel

load_dotenv()

_SYSTEM_PROMPT = """Você é um especialista em extração de receitas culinárias.
Dado um texto (ou imagem) de uma receita, extraia todas as informações e retorne em formato estruturado.

Regras:
- Extraia TODOS os ingredientes com quantidades e unidades exatas
- Extraia as instruções passo a passo
- Coloque dicas, variações e observações do chef em "tips"
- Se uma informação estiver ausente, use null
- Defina extraction_confidence entre 0.0 e 1.0 indicando a clareza da receita
- Se não encontrar receita, use extraction_confidence=0.0 e listas vazias
- Responda sempre em português"""

_MAX_TEXT_LENGTH = 12_000  # ~3k tokens


def create_recipe_agent() -> Agent:
    provider = OpenAIProvider(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    )
    model = OpenAIModel(
        model_name=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o"),
        provider=provider,
    )
    return Agent(
        model=model,
        output_type=RecipeContent,
        system_prompt=_SYSTEM_PROMPT,
    )


# Lazy singleton: avoids startup failure if API key is missing at import time
_agent: Agent | None = None


def _get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = create_recipe_agent()
    return _agent


def extract_recipe_from_text(
    text: str,
    source_url: str,
    source_type: str,
) -> RecipeModel:
    truncated = text[:_MAX_TEXT_LENGTH]
    result = _get_agent().run_sync(f"Extraia a receita do seguinte conteúdo:\n\n{truncated}")
    content = result.data
    return RecipeModel(
        **content.model_dump(),
        source_url=source_url,
        source_type=source_type,
    )


def extract_recipe_from_images(
    images: list[bytes],
    caption: str,
    source_url: str,
    source_type: str,
) -> RecipeModel:
    parts: list = [f"Caption do post: {caption}\n\nExtraia a receita das imagens abaixo:"]
    for img_bytes in images:
        parts.append(BinaryContent(data=img_bytes, media_type="image/jpeg"))
    result = _get_agent().run_sync(parts)
    content = result.data
    return RecipeModel(
        **content.model_dump(),
        source_url=source_url,
        source_type=source_type,
    )
