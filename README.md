# Recipe Extractor

CLI que extrai receitas culinárias de vídeos do YouTube, posts do Instagram e páginas web, estruturando o conteúdo em JSON e Markdown via LLM.

## Arquitetura

```
URL → SourceRouter → Agent (YouTube | Instagram | Web)
                         ↓
                    Extractor → dict[str, str] (múltiplas fontes nomeadas)
                         ↓
                    format_sources() → seções rotuladas "## Fonte\nconteúdo"
                         ↓
                    LLM (cruza fontes) → RecipeCollection
                         ↓
                  list[RecipeModel] → JSON + Markdown
```

Cada fonte tem um agente especializado que coleta **todas** as fontes disponíveis (não apenas a primeira) e as envia como seções rotuladas ao LLM, que cruza as informações para montar a receita mais completa possível. O LLM retorna sempre uma **lista** de receitas — um único post pode conter múltiplas.

### Fontes coletadas por extractor

| Extractor | Fontes coletadas |
|---|---|
| **YouTube** | título + descrição (se > 100 chars) + legenda (Transcript API) + Whisper (só se sem legenda e sem descrição) |
| **Instagram (foto)** | caption (instaloader) + og:description (sempre) + imagens (se caption curta → visão LLM) |
| **Instagram (vídeo)** | caption + og:description + transcrição de áudio (yt-dlp + Whisper) |
| **Web** | conteúdo da página (httpx → Playwright) + JSON-LD/schema.org Recipe (se disponível) |

## Instalação

```bash
# Dependências do sistema
brew install ffmpeg   # necessário para Whisper + yt-dlp

# Dependências Python
pip install -e ".[dev]"

# Playwright (para sites com JS pesado)
playwright install chromium
```

## Configuração

Copie `.env.example` para `.env` e preencha:

```
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=openai/gpt-4o   # qualquer modelo compatível com OpenAI
INSTAGRAM_USERNAME=               # opcional — melhora acesso a posts privados
INSTAGRAM_PASSWORD=               # opcional
WHISPER_MODEL_SIZE=base           # tiny | base | small | medium | large
```

## Uso

```bash
python -m src.main <URL>
```

Exemplos:

```bash
python -m src.main "https://www.youtube.com/watch?v=..."
python -m src.main "https://www.instagram.com/p/..."
python -m src.main "https://www.tudogostoso.com.br/receita/..."
```

Saída gerada no diretório corrente:
- `recipe_YYYYMMDD_HHMMSS.json` — dados estruturados
- `recipe_YYYYMMDD_HHMMSS.md` — formato legível

Quando a fonte contém múltiplas receitas, são gerados arquivos numerados:
`recipe_..._1.json`, `recipe_..._2.json`, etc.

## Testes

```bash
pytest
```

67 testes unitários, todos com mocks — sem chamadas reais à API ou rede.

## Estrutura do projeto

```
src/
  models/recipe.py          # Pydantic models: Ingredient, RecipeContent, RecipeCollection, RecipeModel
  router.py                 # Detecção de fonte por URL (YouTube / Instagram / Web)
  llm.py                    # Agente LLM: extração de texto e imagens, cruzamento de fontes
  main.py                   # Entrypoint CLI
  agents/
    base.py                 # Interface abstrata BaseAgent + format_sources()
    youtube.py              # YouTubeAgent
    instagram.py            # InstagramAgent
    web.py                  # WebAgent
  extractors/
    youtube_transcript.py   # Multi-source: título + descrição + legenda + Whisper
    instagram_loader.py     # Multi-source: caption + og:description + transcrição
    web_scraper.py          # Multi-source: conteúdo HTML + JSON-LD/schema.org
tests/
  test_models.py
  test_router.py
  test_llm.py
  test_main.py
  test_format_sources.py
  test_youtube_agent.py / test_youtube_extractor.py
  test_instagram_agent.py / test_instagram_extractor.py
  test_web_agent.py / test_web_scraper.py
docs/
  plans/                    # Design docs e planos de implementação
  known-issues.md           # Issues conhecidos e pendentes
```

## Issues conhecidos

Ver [`docs/known-issues.md`](docs/known-issues.md).
