import logging
import os
from typing import Optional

import requests
from dotenv import load_dotenv

from models import ModelConfig


load_dotenv()
logger = logging.getLogger(__name__)


class NetworkError(Exception):
    pass


def send_prompt(model: ModelConfig, prompt: str, timeout: int = 20) -> str:
    api_key = os.getenv(model.api_key_env)
    if not api_key:
        raise NetworkError(f"Missing API key in env: {model.api_key_env}")

    logger.info(
        "Sending prompt to model=%s url=%s prompt_len=%s",
        model.name,
        model.api_url,
        len(prompt),
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"prompt": prompt}

    try:
        response = requests.post(
            model.api_url, json=payload, headers=headers, timeout=timeout
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Network error for model=%s: %s", model.name, exc)
        raise NetworkError(str(exc)) from exc

    data: Optional[dict] = None
    try:
        data = response.json()
    except ValueError:
        data = None

    if data and "text" in data:
        return str(data["text"])
    if data and "response" in data:
        return str(data["response"])
    if data and "choices" in data and data["choices"]:
        return str(data["choices"][0].get("text", "")).strip()

    return response.text.strip()
