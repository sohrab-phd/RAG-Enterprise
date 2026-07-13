"""BGE-M3 provider unit tests."""

import pytest

from rag_enterprise.indexing.exceptions import ModelUnavailableError
from rag_enterprise.indexing.providers import BgeM3EmbeddingProvider


@pytest.mark.asyncio
async def test_deterministic_embed_texts_and_query() -> None:
    provider = BgeM3EmbeddingProvider(mode="deterministic", dimensions=1024)

    vectors = await provider.embed_texts(["سلام دنیا", "hello world"])
    query = await provider.embed_query("سلام دنیا")

    assert provider.model_key == "BAAI/bge-m3"
    assert provider.dimensions == 1024
    assert len(vectors) == 2
    assert len(vectors[0]) == 1024
    assert len(query) == 1024
    assert abs(sum(v * v for v in vectors[0]) - 1.0) < 1e-6
    # Query and document paths differ intentionally for retrieval asymmetry.
    assert query != vectors[0]


@pytest.mark.asyncio
async def test_flag_mode_without_package_raises() -> None:
    provider = BgeM3EmbeddingProvider(mode="flag")
    with pytest.raises(ModelUnavailableError):
        await provider.embed_texts(["test"])
