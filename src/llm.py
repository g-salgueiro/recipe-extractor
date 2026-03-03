# src/llm.py
"""
Camada de integração com o LLM via Pydantic AI + OpenRouter.

Responsabilidades:
- Criar e gerenciar o agente Pydantic AI (lazy singleton para evitar falha
  na importação quando a API key ainda não está configurada)
- Expor `extract_recipe_from_text` e `extract_recipe_from_images`, que recebem
  conteúdo bruto e devolvem `list[RecipeModel]`
- Suportar múltiplas receitas por extração: o output type do agente é
  `RecipeCollection`, e cada elemento é promovido a `RecipeModel` com os
  metadados da fonte
"""
import os

from dotenv import load_dotenv
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIChatModel as OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.models.recipe import RecipeCollection, RecipeContent, RecipeModel

load_dotenv()

_SYSTEM_PROMPT = """Você é um especialista em extração de receitas culinárias.
Dado um texto (ou imagem), extraia TODAS as receitas presentes e retorne em formato estruturado.

Regras:
- O conteúdo pode vir de múltiplas fontes (legenda, descrição, transcrição). Cruze as informações para obter a receita mais completa possível — por exemplo, use quantidades exatas da descrição e instruções detalhadas da legenda.
- O conteúdo pode conter UMA ou MÚLTIPLAS receitas — extraia todas sem exceção
- Para cada receita, extraia TODOS os ingredientes com quantidades e unidades exatas. Formato de cada ingrediente:
  - quantity: a quantidade na unidade de medida principal, tal qual a fonte disponibilizou (ex: "1/4 xícara", "2 colheres de sopa", "1 pedaço")
  - unit: null (a unidade já faz parte de quantity)
  - name: o nome do ingrediente com conectivos gramaticais corretos (ex: "de shoyu", "de gengibre", "de farinha de trigo")
  - notes: quantidade alternativa em outra unidade e/ou forma de apresentação, separados por vírgula (ex: "60g", "4g, fresco e ralado", "8g, ralados ou esmagados")
  - Revise a gramática: não omita preposições como "de" entre quantidade e ingrediente. Ex: "1 pedaço de gengibre", NÃO "1 pedaço gengibre".
- Extraia as instruções passo a passo de cada receita
- Coloque dicas, variações e observações do chef em "tips" da receita correspondente. IMPORTANTE: capture TODAS as dicas mencionadas, incluindo:
  - Técnicas de preparo de ingredientes (como desossar frango, limpar carne, cortar legumes, remover pele, tirar excesso de gordura)
  - Preferências e recomendações do chef (ex: "prefira sobrecoxa ao invés de peito para um resultado mais suculento")
  - Substituições possíveis de ingredientes
  - Observações sobre tempo/temperatura
  - NÃO suprima nenhuma dica presente no conteúdo original, mesmo que pareça genérica
- Se uma informação estiver ausente, use null
- Defina extraction_confidence entre 0.0 e 1.0 indicando a clareza de cada receita
- Se não encontrar nenhuma receita, retorne uma lista vazia em "recipes"
- Responda sempre em português"""

_MAX_TEXT_LENGTH = 24_000  # ~6k tokens


def create_recipe_agent() -> Agent:
    """Instancia o agente Pydantic AI apontando para o OpenRouter.

    O modelo e a API key são lidos de variáveis de ambiente para evitar
    valores hard-coded. O output_type `RecipeCollection` força o LLM a
    sempre retornar uma lista estruturada de receitas.
    """
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
        output_type=RecipeCollection,
        system_prompt=_SYSTEM_PROMPT,
    )


# Lazy singleton: criado apenas na primeira chamada, evitando falha de
# importação quando OPENROUTER_API_KEY ainda não está no ambiente.
_agent: Agent | None = None


def _get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = create_recipe_agent()
    return _agent


def _to_recipe_models(
    collection: RecipeCollection,
    source_url: str,
    source_type: str,
) -> list[RecipeModel]:
    """Converte `RecipeCollection` em `list[RecipeModel]` injetando os metadados da fonte."""
    return [
        RecipeModel(**content.model_dump(), source_url=source_url, source_type=source_type)
        for content in collection.recipes
    ]


async def extract_recipe_from_text(
    text: str,
    source_url: str,
    source_type: str,
) -> list[RecipeModel]:
    """Extrai todas as receitas de um texto.

    O texto é truncado em `_MAX_TEXT_LENGTH` antes de ser enviado ao LLM
    para manter o custo de tokens sob controle.
    """
    truncated = text[:_MAX_TEXT_LENGTH]
    result = await _get_agent().run(f"Extraia as receitas do seguinte conteúdo:\n\n{truncated}")
    return _to_recipe_models(result.output, source_url, source_type)


async def extract_recipe_from_images(
    images: list[bytes],
    caption: str,
    source_url: str,
    source_type: str,
) -> list[RecipeModel]:
    """Extrai todas as receitas de uma lista de imagens, usando a caption como contexto.

    Cada imagem é enviada como `BinaryContent` junto com a caption do post,
    aproveitando a capacidade de visão do modelo.
    """
    parts: list = [f"Caption do post: {caption}\n\nExtraia as receitas das imagens abaixo:"]
    for img_bytes in images:
        parts.append(BinaryContent(data=img_bytes, media_type="image/jpeg"))
    result = await _get_agent().run(parts)
    return _to_recipe_models(result.output, source_url, source_type)
