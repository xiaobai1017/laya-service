from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any


MODEL_ALIASES = {
    "jev-latest": "router",
    "laya": "english",
    "laya-english": "english",
    "laya-multilingual": "multilingual",
    "laya-typed-decisions": "typed-decisions",
}


def _import_laya():
    """Import installed Laya, falling back to the checked-out upstream source."""
    try:
        import laya
        return laya
    except ModuleNotFoundError as exc:
        if exc.name != "laya":
            raise
        local_root = Path(__file__).resolve().parents[1] / "laya-upstream"
        if not (local_root / "laya" / "__init__.py").exists():
            raise RuntimeError(
                "Laya is not installed. Run `uv pip install -e laya-upstream` "
                "or clone the upstream repository into laya-upstream."
            ) from exc
        sys.path.insert(0, str(local_root))
        import laya
        return laya


class ModelManager:
    def __init__(self, settings):
        self.settings = settings
        self._router: Any = None
        self._agents: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    @property
    def ready(self) -> bool:
        return self._router is not None or bool(self._agents)

    async def startup(self) -> None:
        if self.settings.preload:
            await self._ensure_router()

    async def _ensure_router(self):
        if self._router is None:
            async with self._lock:
                if self._router is None:
                    laya = _import_laya()
                    self._router = laya.Router(
                        device=self._device(),
                        token=self.settings.hf_token,
                        preload=True,
                    )
        return self._router

    def _device(self):
        # `auto` is a service-level value; Laya expects None for automatic selection.
        return None if self.settings.device in (None, "", "auto") else self.settings.device

    async def predict(self, state, questions, model: str) -> dict[str, Any]:
        target = MODEL_ALIASES.get(model)
        if target is None:
            raise ValueError(f"unsupported model: {model}")
        if target == "router":
            router = await self._ensure_router()
            return await asyncio.to_thread(router.predict, state, questions)
        if target not in self._agents:
            async with self._lock:
                if target not in self._agents:
                    laya = _import_laya()
                    subfolder = None if target == "english" else target
                    self._agents[target] = laya.load(
                        "convaiinnovations/laya", device=self._device(),
                        token=self.settings.hf_token, subfolder=subfolder,
                    )
        agent = self._agents[target]
        return await asyncio.to_thread(agent.system_one, state, questions)

    def models(self) -> list[dict[str, str]]:
        return [{"id": alias, "implementation": impl} for alias, impl in MODEL_ALIASES.items()]
