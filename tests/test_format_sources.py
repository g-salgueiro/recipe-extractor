from src.agents.base import format_sources


def test_format_sources_single_source():
    result = format_sources({"legenda": "Texto da legenda"})
    assert "## Legenda" in result
    assert "Texto da legenda" in result


def test_format_sources_multiple_sources():
    sources = {
        "titulo": "Bolo de Chocolate",
        "descricao": "Ingredientes: farinha, açúcar",
        "legenda": "Hoje vou ensinar a fazer bolo",
    }
    result = format_sources(sources)
    assert "## Titulo" in result
    assert "## Descricao" in result
    assert "## Legenda" in result
    assert result.index("## Titulo") < result.index("## Descricao") < result.index("## Legenda")


def test_format_sources_empty_dict():
    result = format_sources({})
    assert result == ""


def test_format_sources_replaces_underscores():
    result = format_sources({"transcricao_whisper": "Texto"})
    assert "## Transcricao Whisper" in result
