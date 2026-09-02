# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
"""Perplexity Sonar — shared real-time web retrieval helper (sonar-pro by default).

Used by: Jarvis SONAR search (routes/agent.py), Medical News Sentinel live feed
(routes/news.py) and the Morning Briefing health headlines. The API key lives ONLY in
backend/.env (PERPLEXITY_API_KEY); a blank key makes every caller degrade gracefully."""
import asyncio
import json
import logging
import os
import re
from typing import Optional

import httpx

logger = logging.getLogger("guardian")

PPLX_URL = "https://api.perplexity.ai/v1/sonar"
SONAR_PRO = "sonar-pro"
SONAR_REASONING_PRO = "sonar-reasoning-pro"


def pplx_key() -> str:
    return os.environ.get("PERPLEXITY_API_KEY", "").strip()


def pplx_enabled() -> bool:
    return bool(pplx_key())


def strip_think(text: str) -> str:
    """Reasoning models emit hidden <think> blocks — never expose them (also unclosed ones)."""
    t = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    t = re.sub(r"<think>.*\Z", "", t, flags=re.S)
    return t.strip()


def strip_cite_marks(text: str) -> str:
    """Display cleanup: remove inline [1][2] citation markers and markdown bold/italic asterisks."""
    t = re.sub(r"\s*\[\d+\]", "", text or "")
    return t.replace("**", "").replace("__", "").strip()


def parse_json(content: str):
    """Best-effort JSON extraction from a model reply (structured output or fenced/inline JSON)."""
    if not content:
        return None
    c = strip_think(content)
    try:
        return json.loads(c)
    except ValueError:
        pass
    m = re.search(r"```(?:json)?\s*(.*?)```", c, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except ValueError:
            pass
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = c.find(opener), c.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(c[i:j + 1])
            except ValueError:
                continue
    return None


async def sonar(messages: list, *, model: str = SONAR_PRO, recency: Optional[str] = None,
                context_size: str = "medium", max_tokens: int = 1500, temperature: float = 0.2,
                json_schema: Optional[dict] = None, timeout: float = 60.0) -> Optional[dict]:
    """One Sonar call. Returns {content, citations, search_results, usage} or None when the key
    is missing / the upstream call fails (callers fall back to offline data)."""
    key = pplx_key()
    if not key:
        return None
    payload = {
        "model": model,
        "messages": messages,
        "search_mode": "web",
        "web_search_options": {"search_context_size": context_size},
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    if recency:
        payload["search_recency_filter"] = recency   # top-level, not inside web_search_options
    if json_schema:
        payload["response_format"] = {"type": "json_schema", "json_schema": {"schema": json_schema}}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
            r = await client.post(PPLX_URL, json=payload, headers={
                "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            if r.status_code == 429:   # burst rate limit — one short retry, then give up gracefully
                await asyncio.sleep(2.5)
                r = await client.post(PPLX_URL, json=payload, headers={
                    "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            r.raise_for_status()
            data = r.json()
        content = strip_think(data["choices"][0]["message"]["content"])
        search_results = data.get("search_results") or []
        citations = data.get("citations") or [s["url"] for s in search_results if s.get("url")]
        return {"content": content, "citations": citations, "search_results": search_results,
                "usage": data.get("usage") or {}, "id": data.get("id")}
    except httpx.HTTPStatusError as e:
        logger.error(f"perplexity {model} http {e.response.status_code}: {e.response.text[:300]}")
    except Exception as e:
        logger.error(f"perplexity {model} error: {e}")
    return None
