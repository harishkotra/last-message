import json
from typing import Dict

import requests

from utils.config import ModelConfig, get_openrouter_api_key


class InferenceError(Exception):
    pass


def _post_chat_completion(endpoint: str, body: Dict, headers: Dict | None = None, timeout: int = 60) -> str:
    response = requests.post(endpoint, json=body, headers=headers or {}, timeout=timeout)
    if response.status_code >= 400:
        raise InferenceError(f"Inference failed ({response.status_code}): {response.text[:500]}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise InferenceError(f"Unexpected model response: {json.dumps(data)[:500]}") from exc


def run_lm_studio_multimodal_inference(
    system_prompt: str,
    user_text: str,
    image_data_url: str,
    model_config: ModelConfig,
    temperature: float = 0.2,
) -> str:
    payload = {
        "model": model_config.lm_studio_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
    }
    return _post_chat_completion(model_config.lm_studio_endpoint, payload)


def run_openrouter_multimodal_inference(
    system_prompt: str,
    user_text: str,
    image_data_url: str,
    model_config: ModelConfig,
    temperature: float = 0.2,
) -> str:
    api_key = get_openrouter_api_key()
    if not api_key:
        raise InferenceError("OPENROUTER_API_KEY is not set.")

    payload = {
        "model": model_config.openrouter_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://last-message.local",
        "X-Title": "Last Message",
    }
    return _post_chat_completion(model_config.openrouter_endpoint, payload, headers=headers)


def run_lm_studio_inference(
    system_prompt: str,
    user_prompt: str,
    model_config: ModelConfig,
    temperature: float = 0.2,
) -> str:
    payload = {
        "model": model_config.lm_studio_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    return _post_chat_completion(model_config.lm_studio_endpoint, payload)


def run_openrouter_inference(
    system_prompt: str,
    user_prompt: str,
    model_config: ModelConfig,
    temperature: float = 0.2,
) -> str:
    api_key = get_openrouter_api_key()
    if not api_key:
        raise InferenceError("OPENROUTER_API_KEY is not set.")

    payload = {
        "model": model_config.openrouter_model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://last-message.local",
        "X-Title": "Last Message",
    }
    return _post_chat_completion(model_config.openrouter_endpoint, payload, headers=headers)
