# Known Issues

## [OPEN] Instagram: receita em comentário do owner não é extraída

**Data identificada:** 2026-02-26
**Severidade:** Média
**Reprodução:** `https://www.instagram.com/p/DTzEP2lEo88/`

### Descrição

Em posts do Instagram onde o owner publica a receita no **primeiro comentário** (ou comentário pinado), o sistema não extrai esse comentário — vai direto para a transcrição do vídeo via Whisper.

A cascata atual para posts de vídeo:
1. instaloader → caption do post
2. yt-dlp + Whisper → transcrição do áudio

A cascata **esperada**:
1. instaloader → caption do post
2. **Comentário do owner** ← passo ausente
3. yt-dlp + Whisper → transcrição do áudio (fallback)

### Causa raiz

- `instaloader` consegue acessar comentários via `Post.get_comments()`, mas exige autenticação para posts com muitos comentários.
- `yt-dlp` (sem auth) retornou apenas 8 de 44 comentários neste post, e o comentário do owner não estava nesse subconjunto.
- Não há scraping de comentários no HTML público da página (Instagram não os embute no HTML).

### Impacto

- Receita extraída do áudio do vídeo (via Whisper) em vez do comentário estruturado.
- A receita resultante pode ter menos precisão nas quantidades (o host nem sempre menciona medidas exatas no vídeo).
- Confiança 80% vs esperado ~95% se viesse do comentário.

### Solução proposta

Quando instaloader estiver autenticado (`INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD` configurados no `.env`):

1. Após obter o `Post`, iterar em `post.get_comments()`
2. Identificar comentário do owner: `comment.owner.username == post.owner_username`
3. Se encontrado e tiver conteúdo suficiente (> 100 chars), usar como fonte primária
4. Só acionar yt-dlp + Whisper se o comentário do owner não existir ou for curto demais

**Pré-requisito:** credenciais do Instagram no `.env` — sem auth, a API de comentários é bloqueada para posts populares.
