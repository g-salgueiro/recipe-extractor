# Design: Mesclagem de Múltiplas Fontes

**Data:** 2026-03-02
**Status:** Aprovado

## Problema

Os extractors usam uma cascata excludente: retornam na primeira estratégia que funciona, descartando fontes complementares. Exemplo: vídeo do YouTube com legenda (instruções + dicas de técnica) E descrição (quantidades exatas + info nutricional) — hoje só a legenda é usada.

Além disso, o prompt do LLM não enfatiza captura de dicas de técnica culinária (desossar, limpar, cortar), que são perdidas mesmo quando presentes no texto.

## Solução

### 1. Extractors retornam `dict[str, str]`

Cada extractor coleta **todas** as fontes disponíveis (não para na primeira) e retorna um dicionário nomeado.

**YouTubeExtractor.extract_sources(url) -> dict[str, str]:**
- `titulo`: título do vídeo (via yt-dlp metadata)
- `descricao`: descrição do vídeo (se > 100 chars)
- `legenda`: legendas via YouTube Transcript API
- `transcricao_whisper`: só se legenda E descrição falharem (é caro)
- Metadata (título + descrição) vem de uma única chamada yt-dlp

**InstagramExtractor.extract(url) -> {"sources": dict[str, str], "images": list[bytes]}:**
- `caption`: caption do post (via instaloader ou og:description)
- `og_description`: sempre tentado como fonte adicional
- `transcricao_audio`: se for vídeo, via yt-dlp + Whisper

**WebScraper.scrape_sources(url) -> dict[str, str]:**
- `conteudo_pagina`: texto extraído do HTML (httpx → Playwright)
- `json_ld_recipe`: dados Recipe de JSON-LD/schema.org se disponível

### 2. Agents formatam seções rotuladas

Helper compartilhado em `src/agents/base.py`:

```python
def format_sources(sources: dict[str, str]) -> str:
    sections = []
    for label, content in sources.items():
        readable = label.replace("_", " ").title()
        sections.append(f"## {readable}\n{content}")
    return "\n\n".join(sections)
```

Cada agent usa `format_sources()` antes de chamar `extract_recipe_from_text()`.

### 3. Prompt do LLM melhorado

Dois ajustes ao `_SYSTEM_PROMPT`:

1. **Cruzamento de fontes:** "O conteúdo pode vir de múltiplas fontes (legenda, descrição, transcrição). Cruze as informações para obter a receita mais completa possível — por exemplo, use quantidades da descrição e instruções da legenda."

2. **Técnicas culinárias:** "Dicas incluem técnicas de preparo de ingredientes (como desossar, limpar, cortar), substituições possíveis, e observações do chef sobre tempo/temperatura."

### 4. _MAX_TEXT_LENGTH: 12k → 24k

Acomoda múltiplas fontes concatenadas sem truncar conteúdo útil (~6k tokens).

### 5. Web: extração de JSON-LD/schema.org

Função `_extract_json_ld_recipe(html)` que busca `<script type="application/ld+json">` com `@type: "Recipe"` e retorna o JSON formatado como string.

## Escopo de testes

- Adaptar os 49 testes existentes para a nova interface
- Adicionar testes para: multi-source collection, format_sources, JSON-LD extraction
- Testar que Whisper só é acionado como último recurso
