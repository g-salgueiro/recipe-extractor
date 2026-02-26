# Design: MVP Extrator de Receitas Culinárias

**Data:** 2026-02-26
**Status:** Aprovado
**Autor:** Gabriel Salgueiro + Claude

---

## Visão Geral

MVP funcional (sem UI) para extração de receitas culinárias a partir de links de YouTube, Instagram e sites web genéricos. Agentes especializados por fonte coletam texto/imagem e um agente LLM (Pydantic AI + OpenRouter) extrai os dados estruturados.

---

## Decisões Técnicas

| Componente | Decisão |
|-----------|---------|
| LLM backend | OpenRouter (OpenAI-compatible API) |
| Modelo padrão | `openai/gpt-4o` (configurável via `.env`) |
| Framework de agentes | Pydantic AI |
| YouTube transcript | `youtube-transcript-api` → fallback `whisper` |
| Instagram scraping | `instaloader` |
| Web scraping | `httpx` + BeautifulSoup → fallback Playwright |
| Saída | JSON (Pydantic) + Markdown |
| Interface | CLI (`python -m src.main <url>`) |

---

## Arquitetura

### Estrutura de Pastas

```
recipes/
├── src/
│   ├── agents/
│   │   ├── base.py          # BaseAgent (interface comum)
│   │   ├── youtube.py       # YouTubeAgent
│   │   ├── instagram.py     # InstagramAgent
│   │   └── web.py           # WebAgent
│   ├── extractors/
│   │   ├── youtube_transcript.py  # yt-transcript → whisper fallback
│   │   ├── instagram_loader.py    # instaloader wrapper
│   │   └── web_scraper.py         # httpx → playwright fallback
│   ├── models/
│   │   └── recipe.py        # RecipeModel (Pydantic)
│   ├── router.py            # SourceRouter (detecta fonte por URL)
│   ├── llm.py               # Configuração OpenRouter + Pydantic AI
│   └── main.py              # Ponto de entrada CLI
├── tests/
│   ├── test_youtube.py
│   ├── test_instagram.py
│   └── test_web.py
├── .env.example
├── pyproject.toml
└── README.md
```

### Fluxo Principal

```
URL (CLI)
  → SourceRouter.detect(url)
  → Agent.extract(url)
      → Extractor (coleta texto/imagem com fallbacks)
      → PydanticAI LLM Agent (extração estruturada)
  → RecipeModel
      → recipe_<timestamp>.json
      → recipe_<timestamp>.md
```

---

## Modelo de Dados

```python
class Ingredient(BaseModel):
    quantity: str | None       # "2 xícaras"
    unit: str | None           # "xícara", "g", "ml"
    name: str                  # "farinha de trigo"
    notes: str | None          # "peneirada", "em temperatura ambiente"

class RecipeModel(BaseModel):
    title: str
    source_url: str
    source_type: Literal["youtube", "instagram", "web"]
    servings: str | None
    prep_time: str | None
    cook_time: str | None
    ingredients: list[Ingredient]
    steps: list[str]
    tips: list[str]
    extraction_confidence: float  # 0.0 a 1.0
    extracted_at: datetime
```

---

## Estratégias de Extração por Fonte

### YouTube

| Prioridade | Estratégia | Condição |
|-----------|-----------|---------|
| 1 | `youtube-transcript-api` | Legenda/transcript disponível |
| 2 | Descrição do vídeo | Transcript indisponível |
| 3 | Whisper (áudio via yt-dlp) | Nenhuma das anteriores |

### Instagram

| Tipo de post | Prioridade 1 | Prioridade 2 |
|-------------|-------------|-------------|
| Qualquer | Caption (texto da legenda) | — |
| Foto(s) sem receita na caption | Vision LLM (imagem → extração) | — |
| Reel/vídeo | Caption | Áudio (fase 2, não MVP) |

> **Nota:** Posts de foto podem conter receitas visualmente (cards, prints). O `InstagramAgent` detecta se a caption é insuficiente e aciona o LLM com visão enviando as imagens do post.

### Web Genérico

| Prioridade | Estratégia | Condição |
|-----------|-----------|---------|
| 1 | `httpx` + BeautifulSoup | HTML estático |
| 2 | Playwright (headless) | Site renderiza via JavaScript |

---

## Tratamento de Erros

- **SourceRouter:** URL não reconhecida → `UnsupportedSourceError`
- **Extractors:** cada fallback loga warning; todos falham → `ExtractionError` com log das tentativas
- **LLM Agent:** extração incerta → `extraction_confidence` baixo + aviso em `tips`
- **Sem retry automático no MVP** — erros sobem ao `main.py` com contexto claro

---

## Configuração (`.env`)

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o
INSTAGRAM_USERNAME=
INSTAGRAM_PASSWORD=
WHISPER_MODEL_SIZE=base
```

---

## Interface CLI

```bash
# YouTube
python -m src.main "https://youtube.com/watch?v=..."

# Instagram (post, reel ou foto)
python -m src.main "https://instagram.com/p/..."

# Site web
python -m src.main "https://www.tudogostoso.com.br/receita/..."

# Saída gerada:
# recipe_<timestamp>.json
# recipe_<timestamp>.md
```

---

## Fora do Escopo (MVP)

- Interface web ou API REST
- Banco de dados / persistência
- Autenticação de usuário
- Extração de áudio de Reels do Instagram
- Suporte a TikTok, Pinterest, etc.
- Cache de resultados
