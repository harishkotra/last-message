import os
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    lm_studio_endpoint: str = field(
        default_factory=lambda: os.getenv("LM_STUDIO_ENDPOINT", "http://localhost:1234/v1/chat/completions")
    )
    lm_studio_model: str = field(default_factory=lambda: os.getenv("LM_STUDIO_MODEL", "gemma-3-12b-it"))
    openrouter_endpoint: str = field(
        default_factory=lambda: os.getenv("OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions")
    )
    openrouter_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "google/gemma-3-12b-it:free"))


def get_openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "")
