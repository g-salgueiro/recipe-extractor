# Changelog

## [Unreleased] — Post-implementação (2026-02-26)

Correções e melhorias realizadas durante smoke tests após a implementação inicial.

### Corrigido

#### `src/llm.py` — Event loop conflict + suporte a múltiplas receitas

**Bug:** `extract_recipe_from_text` e `extract_recipe_from_images` usavam `agent.run_sync()` internamente via `asyncio.run()`, que falha quando já existe um event loop ativo (e.g. quando chamado de dentro de `asyncio.run(run(url))` em `main.py`).
**Fix:** Funções tornadas `async` com `await agent.run()`.

**Bug:** O schema enviado ao LLM era `RecipeContent` (uma única receita). Posts com múltiplas receitas resultavam em apenas 1 sendo retornada — o modelo não tinha como devolver uma lista.
**Fix:** Output type alterado para `RecipeCollection(recipes: list[RecipeContent])`. System prompt atualizado para instruir o modelo a extrair **todas** as receitas presentes.

#### `src/extractors/instagram_loader.py` — Três bugs

**Bug 1 — Regex sem `re.DOTALL`:** A função `_fetch_og_description` usava `(.*?)` sem a flag `re.DOTALL`. O `og:description` do Instagram contém quebras de linha literais no atributo HTML, então o `.` parava no primeiro `\n`, retornando string vazia.
**Fix:** Adicionada flag `re.DOTALL` e `html.unescape()` no resultado.

**Bug 2 — Vídeos sem fallback de transcrição:** Quando instaloader falhava (403) e `og:description` não tinha receita (apenas legenda descritiva), o LLM recebia texto sem conteúdo e retornava lista vazia. Posts de vídeo cujas receitas estão no áudio não eram processados.
**Fix:** Adicionado `_transcribe_video()` usando yt-dlp + Whisper como terceiro fallback após falha do instaloader.

**Bug 3 — `post.is_video` ignorado:** Mesmo quando instaloader tinha sucesso técnico (retornando a legenda do post), posts de vídeo com legenda descritiva (sem receita) não acionavam a transcrição. O código tratava vídeo e foto da mesma forma.
**Fix:** Em `_extract_via_instaloader`, verificação de `post.is_video`: se verdadeiro, aciona `_transcribe_video()` e combina com a legenda.

#### Dependência de sistema

**ffmpeg** não estava instalado, causando falha no pós-processamento do yt-dlp (`FFmpegExtractAudio`).
**Fix:** `brew install ffmpeg`.

### Adicionado

- `RecipeCollection` em `src/models/recipe.py` — wrapper para lista de receitas
- `_to_recipe_models()` em `src/llm.py` — converte `RecipeCollection` em `list[RecipeModel]`
- `_transcribe_video()` em `InstagramExtractor` — yt-dlp + Whisper síncrono (já roda em thread)
- `save_outputs()` em `main.py` agora salva um par JSON+MD por receita, com sufixo `_1`, `_2`...
- Testes: `test_extract_recipe_from_text_returns_multiple_recipes`, `test_save_outputs_creates_separate_files_for_multiple_recipes`, `test_extract_transcribes_video_when_post_is_video`, e dois testes de fallback do extractor Instagram

### Issues identificados mas não corrigidos

- **Comentário do owner:** receitas publicadas no primeiro comentário do post (não na legenda) não são detectadas. Ver [`docs/known-issues.md`](docs/known-issues.md).
