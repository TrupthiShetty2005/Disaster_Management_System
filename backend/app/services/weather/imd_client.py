"""IMD official API client. Requires an IMD-issued JWT / API credential."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.providers import ProviderUnavailableError
from app.services.weather.models import ProviderAlert


class ImdClient:
    """Calls https://api.imd.gov.in — does not invent IMD products."""

    name = "imd"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key if api_key is not None else settings.imd_api_key
        self.base_url = (base_url or settings.imd_api_base_url).rstrip("/")
        self.station_id = settings.imd_station_id

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _headers(self) -> dict[str, str]:
        token = (self.api_key or "").strip()
        return {
            "Authorization": f"Bearer {token}",
            "X-API-KEY": token,
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        if not self.configured:
            raise ProviderUnavailableError(
                self.name,
                "IMD_API_KEY not configured. Register at https://api.imd.gov.in and set the JWT/token.",
            )
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = httpx.get(url, params=params or {}, headers=self._headers(), timeout=20.0)
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(self.name, f"Request failed: {exc}") from exc
        if response.status_code in {401, 403}:
            raise ProviderUnavailableError(
                self.name,
                "IMD rejected credentials (401/403). Obtain a valid token from the IMD API portal.",
            )
        if response.status_code != 200:
            raise ProviderUnavailableError(
                self.name, f"HTTP {response.status_code}: {response.text[:200]}"
            )
        return response.json()

    def district_warnings(self) -> list[ProviderAlert]:
        data = self._get("districtwarning")
        items = data if isinstance(data, list) else (data.get("data") or data.get("items") or [])
        if not isinstance(items, list):
            raise ProviderUnavailableError(self.name, "Unexpected districtwarning payload shape.")
        alerts: list[ProviderAlert] = []
        for row in items[:20]:
            if not isinstance(row, dict):
                continue
            title = str(row.get("warning") or row.get("title") or row.get("event") or "IMD warning")
            message = str(row.get("message") or row.get("description") or row.get("detail") or title)
            severity = str(row.get("severity") or row.get("color") or "warning").lower()
            if severity in {"red", "orange"}:
                severity = "critical" if severity == "red" else "warning"
            loc = str(row.get("district") or row.get("area") or "India")
            alerts.append(
                ProviderAlert(
                    title=f"IMD: {title}"[:240],
                    severity=severity if severity in {"info", "watch", "warning", "critical"} else "warning",
                    category="imd",
                    message=message[:2000],
                    issued_at=datetime.now(timezone.utc),
                    location_name=loc,
                )
            )
        return alerts

    def current_wx(self) -> dict:
        return self._get("current_wx", {"id": self.station_id})

    def status(self) -> dict:
        if not self.configured:
            return {
                "provider": self.name,
                "configured": False,
                "available": False,
                "note": "IMD_API_KEY missing - official IMD data unavailable (no fake IMD data used).",
            }
        try:
            self._get("current_wx", {"id": self.station_id})
            return {"provider": self.name, "configured": True, "available": True, "note": "IMD API reachable."}
        except ProviderUnavailableError as exc:
            return {
                "provider": self.name,
                "configured": True,
                "available": False,
                "note": exc.message,
            }
