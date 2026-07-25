"""Thin wrapper around the Composio SDK so the rest of the package
doesn't have to know about toolkit versions or auth-link plumbing."""
from __future__ import annotations

from typing import Any

from composio import Composio

from .config import Config


class ComposioClient:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.client = Composio(api_key=cfg.composio_api_key)

    def list_connected(self) -> list[dict[str, Any]]:
        resp = self.client.connected_accounts.list()
        items = getattr(resp, "items", None) or []
        out: list[dict[str, Any]] = []
        for a in items:
            out.append({
                "id": getattr(a, "id", None),
                "toolkit": getattr(a, "toolkit", None),
                "status": getattr(a, "status", None),
                "user_id": getattr(a, "user_id", None),
            })
        return out

    def is_connected(self, toolkit: str) -> bool:
        toolkit = toolkit.lower()
        for a in self.list_connected():
            tk = a.get("toolkit")
            slug = tk.get("slug") if isinstance(tk, dict) else getattr(tk, "slug", None) or tk
            if str(slug).lower() == toolkit and str(a.get("status", "")).upper() == "ACTIVE":
                return True
        return False

    def authorize(self, toolkit: str) -> str:
        """Return a redirect URL the user opens once to connect the toolkit."""
        result = self.client.toolkits.authorize(user_id=self.cfg.user_id, toolkit=toolkit)
        # SDK returns either a string URL or an object with redirect_url
        url = getattr(result, "redirect_url", None) or getattr(result, "url", None) or result
        return str(url)

    def execute(self, slug: str, args: dict[str, Any], *, version: str | None = None) -> Any:
        kwargs: dict[str, Any] = {"user_id": self.cfg.user_id}
        # Composio rejects "latest" for manual execution — it needs a concrete
        # pinned version. When we don't have one, skip the version check so the
        # toolkit's current version is used automatically.
        if version and version.lower() != "latest":
            kwargs["version"] = version
        else:
            kwargs["dangerously_skip_version_check"] = True
        return self.client.tools.execute(slug, args, **kwargs)

    @staticmethod
    def unwrap(resp: Any) -> Any:
        """ToolExecutionResponse → its .data payload (or pass-through dict)."""
        if hasattr(resp, "data"):
            return resp.data
        if isinstance(resp, dict) and "data" in resp:
            return resp["data"]
        return resp
