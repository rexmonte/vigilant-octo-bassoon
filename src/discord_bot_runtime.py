"""Discord runtime for ACE chat with provider/model fallback routing."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import discord
import requests
from anthropic import Anthropic
from dotenv import load_dotenv

from src.discord_interface import send_discord_alert
from src.model_router import load_config

LOGGER = logging.getLogger("ace_discord_bot")


@dataclass(frozen=True)
class Candidate:
    provider: str
    model: str


@dataclass
class BotRuntimeConfig:
    token: str
    anthropic_key: str
    local_openai_base_url: str
    alert_webhook: str
    role: str
    timeout: int
    respond_in_all_channels: bool
    allowed_channels: set[int]


class ModelCallError(RuntimeError):
    pass


def _parse_allowed_channels(value: str) -> set[int]:
    out: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            out.add(int(item))
        except ValueError:
            LOGGER.warning("Skipping invalid channel ID in ACE_ALLOWED_CHANNEL_IDS: %s", item)
    return out


def load_runtime_config() -> BotRuntimeConfig:
    load_dotenv(dotenv_path=".env")
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise ModelCallError("Missing DISCORD_BOT_TOKEN")

    role = os.getenv("DEFAULT_LLM_ROLE", "ace").strip() or "ace"
    timeout = int(os.getenv("INFERENCE_TIMEOUT", "60"))

    return BotRuntimeConfig(
        token=token,
        anthropic_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        local_openai_base_url=os.getenv("LOCAL_OPENAI_BASE_URL", "http://localhost:11434/v1").strip(),
        alert_webhook=os.getenv("DISCORD_ALERT_WEBHOOK", "").strip(),
        role=role,
        timeout=timeout,
        respond_in_all_channels=os.getenv("ACE_RESPOND_IN_ALL_CHANNELS", "false").lower() == "true",
        allowed_channels=_parse_allowed_channels(os.getenv("ACE_ALLOWED_CHANNEL_IDS", "")),
    )


def role_candidates(role: str) -> List[Candidate]:
    config = load_config()
    role_cfg = config.get("roles", {}).get(role)
    if not role_cfg:
        raise ModelCallError(f"Unknown role '{role}' in config/providers.json")

    candidates: List[Candidate] = []
    primary = role_cfg.get("primary", {})
    if primary.get("provider") and primary.get("model"):
        candidates.append(Candidate(provider=primary["provider"], model=primary["model"]))

    for fb in role_cfg.get("fallbacks", []):
        if fb.get("provider") and fb.get("model"):
            candidates.append(Candidate(provider=fb["provider"], model=fb["model"]))

    if not candidates:
        raise ModelCallError(f"Role '{role}' has no provider/model candidates")
    return candidates


def _extract_anthropic_text(response) -> str:
    chunks: List[str] = []
    for block in getattr(response, "content", []):
        text = getattr(block, "text", None)
        if text:
            chunks.append(text)
    joined = "\n".join(chunks).strip()
    return joined or "(No content returned.)"


def call_anthropic(model: str, prompt: str, cfg: BotRuntimeConfig) -> str:
    if not cfg.anthropic_key:
        raise ModelCallError("ANTHROPIC_API_KEY is not set")

    client = Anthropic(api_key=cfg.anthropic_key)
    response = client.messages.create(
        model=model,
        max_tokens=700,
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_anthropic_text(response)


def call_ollama(model: str, prompt: str, cfg: BotRuntimeConfig) -> str:
    endpoint = cfg.local_openai_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    response = requests.post(endpoint, json=payload, timeout=cfg.timeout)
    if response.status_code >= 400:
        raise ModelCallError(f"Ollama request failed: HTTP {response.status_code} {response.text[:200]}")

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        raise ModelCallError(f"Unexpected Ollama response shape: {data}") from exc


def invoke_candidate(candidate: Candidate, prompt: str, cfg: BotRuntimeConfig) -> str:
    if candidate.provider == "anthropic":
        return call_anthropic(candidate.model, prompt, cfg)
    if candidate.provider == "ollama":
        return call_ollama(candidate.model, prompt, cfg)
    raise ModelCallError(f"Unsupported provider in runtime: {candidate.provider}")


def complete_with_fallback(prompt: str, cfg: BotRuntimeConfig) -> Tuple[str, Candidate]:
    errors: List[str] = []
    for candidate in role_candidates(cfg.role):
        try:
            answer = invoke_candidate(candidate, prompt, cfg)
            LOGGER.info("Selected %s/%s", candidate.provider, candidate.model)
            return answer, candidate
        except Exception as exc:  # noqa: BLE001
            error = f"{candidate.provider}/{candidate.model}: {exc}"
            LOGGER.warning("Candidate failed: %s", error)
            errors.append(error)

    send_discord_alert(
        cfg.alert_webhook,
        title="Open Fall Triggered",
        description="All ACE role providers failed during Discord request.",
        details={"errors": errors, "role": cfg.role},
    )
    raise ModelCallError("All fallback candidates failed. Check provider credentials and connectivity.")


def _should_respond(message: discord.Message, bot_user_id: int, cfg: BotRuntimeConfig) -> bool:
    if cfg.respond_in_all_channels:
        return True
    if cfg.allowed_channels and message.channel.id in cfg.allowed_channels:
        return True
    return message.content.startswith(f"<@{bot_user_id}>") or message.content.startswith(f"<@!{bot_user_id}>")


def _clean_prompt(content: str, bot_user_id: int) -> str:
    prompt = content.replace(f"<@{bot_user_id}>", "").replace(f"<@!{bot_user_id}>", "").strip()
    return prompt or "Hello ACE. Please share your current status."


def _chunk_message(text: str, size: int = 1900) -> Iterable[str]:
    for i in range(0, len(text), size):
        yield text[i : i + size]


async def run_discord_bot() -> None:
    cfg = load_runtime_config()

    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.messages = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        LOGGER.info("ACE Discord bot is online as %s", client.user)

    @client.event
    async def on_message(message: discord.Message) -> None:
        if message.author.bot or client.user is None:
            return

        if not _should_respond(message, client.user.id, cfg):
            return

        prompt = _clean_prompt(message.content, client.user.id)
        async with message.channel.typing():
            try:
                answer, selected = await asyncio.to_thread(complete_with_fallback, prompt, cfg)
                banner = f"_model: {selected.provider}/{selected.model}_\n"
                for part in _chunk_message(banner + answer):
                    await message.channel.send(part)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Request handling failed")
                await message.channel.send(
                    "I couldn't complete that request right now. "
                    "Please check provider credentials and try again."
                )
                send_discord_alert(
                    cfg.alert_webhook,
                    title="ACE Discord Request Failed",
                    description=str(exc),
                    details={"channel_id": message.channel.id, "author": str(message.author)},
                )

    await client.start(cfg.token)


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    try:
        asyncio.run(run_discord_bot())
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped by user")
        return 0
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Fatal startup error")
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
