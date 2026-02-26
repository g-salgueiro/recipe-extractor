# Recipe Extractor

CLI que extrai receitas culinárias de vídeos do YouTube, posts do Instagram e páginas web, estruturando o conteúdo em JSON e Markdown via LLM.

## Arquitetura

```
URL → SourceRouter → Agent (YouTube | Instagram | Web)
                         ↓
                    Extractor (texto / imagens / áudio)
                         ↓
                    LLM (OpenRouter / gpt-4o)
                         ↓
                  list[RecipeModel] → JSON + Markdown
```

Cada fonte tem um agente especializado que decide como extrair o conteúdo antes de enviar ao LLM. O LLM retorna sempre uma **lista** de receitas — um único post pode conter múltiplas.

### Agentes e estratégias de extração

| Fonte | Estratégia primária | Fallback 1 | Fallback 2 |
|---|---|---|---|
| **YouTube** | API de legendas | Descrição do vídeo | Whisper (transcrição) |
| **Instagram (foto)** | instaloader (caption) | Caption curta → visão LLM | og:description (sem auth) |
| **Instagram (vídeo)** | instaloader → `is_video` → yt-dlp + Whisper | og:description + yt-dlp + Whisper | og:description |
| **Web** | httpx + parse HTML | Playwright (JS rendering) | — |

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

49 testes unitários, todos com mocks — sem chamadas reais à API ou rede.

## Estrutura do projeto

```
src/
  models/recipe.py          # Pydantic models: Ingredient, RecipeContent, RecipeCollection, RecipeModel
  router.py                 # Detecção de fonte por URL (YouTube / Instagram / Web)
  llm.py                    # Agente LLM: extração de texto e imagens, suporte a múltiplas receitas
  main.py                   # Entrypoint CLI
  agents/
    base.py                 # Interface abstrata BaseAgent
    youtube.py              # YouTubeAgent
    instagram.py            # InstagramAgent
    web.py                  # WebAgent
  extractors/
    youtube_transcript.py   # Extração de texto de vídeos YouTube (3 estratégias)
    instagram_loader.py     # Extração de posts Instagram (caption / imagens / vídeo)
    web_scraper.py          # Scraping web (httpx → Playwright)
tests/
  test_models.py
  test_router.py
  test_llm.py
  test_main.py
  test_youtube_agent.py / test_youtube_extractor.py
  test_instagram_agent.py / test_instagram_extractor.py
  test_web_agent.py / test_web_scraper.py
docs/
  plans/                    # Design doc e plano de implementação original
  known-issues.md           # Issues conhecidos e pendentes
```

## Issues conhecidos

Ver [`docs/known-issues.md`](docs/known-issues.md).
