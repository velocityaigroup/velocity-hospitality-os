"""Pytest configuration — pin the whole suite to the deterministic offline backend.

`velocity_hos.config.settings` is a frozen dataclass built from environment
variables at import time. That makes the test suite inherit whatever backend the
developer's shell happens to have exported — so running the tests in the same
PowerShell window used for a live open-weights demo sends every test to the
gateway. The suite then takes fifteen minutes, fails on transient 502s, and
fails again on phrasing differences between the offline stub and a real model.

None of that is a defect in the code under test, but it is indistinguishable
from one at a glance, which is worse. This module runs before any test imports
`velocity_hos`, so pinning the environment here makes the suite hermetic:
offline, deterministic, no network, no credentials, identical on a laptop and in
CI. Tests that need a different backend monkeypatch it explicitly.
"""
import os

# Force the offline, deterministic backend.
os.environ["VHOS_LLM_BACKEND"] = "local"
os.environ["VHOS_EMBED_BACKEND"] = "local"

# Drop anything that could point a backend at a real endpoint or real credentials.
for _leaked in (
    "VHOS_OPENWEIGHTS_URL",
    "VHOS_OPENWEIGHTS_MODEL",
    "VHOS_OPENWEIGHTS_EMBED_MODEL",
    "VHOS_OPENWEIGHTS_API_KEY",
    "BEDROCK_MODEL_ID",
    "BEDROCK_EMBED_MODEL_ID",
):
    os.environ.pop(_leaked, None)
