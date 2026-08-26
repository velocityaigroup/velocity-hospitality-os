"""The suite must run offline and deterministically, whatever the shell exports.

If this fails, tests/conftest.py is not being loaded before velocity_hos.config
is imported, and every other test result in this run is suspect.
"""
from velocity_hos.config import settings
from velocity_hos.llm import get_embeddings, get_llm
from velocity_hos.llm.local import LocalEmbeddings, LocalLLM


def test_backend_is_pinned_to_local():
    assert settings.llm_backend == "local"
    assert settings.embed_backend == "local"


def test_factories_return_the_offline_implementations():
    assert isinstance(get_llm(), LocalLLM)
    assert isinstance(get_embeddings(), LocalEmbeddings)


def test_no_live_endpoint_credentials_are_in_scope():
    assert settings.openweights_api_key is None
