"""Azure-hosted LLM clients (OpenAI + Foundry) for clause verification."""

from llm.settings import LLMSettings
from llm.verifier import Anomaly, build_verifier, verify

__all__ = ["Anomaly", "LLMSettings", "__version__", "build_verifier", "verify"]
__version__ = "0.1.0"
