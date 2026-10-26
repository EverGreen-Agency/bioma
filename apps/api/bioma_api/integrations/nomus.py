"""Cliente de integração com a API REST do Nomus ERP."""

from __future__ import annotations

import logging
import re
from typing import Any
import httpx

logger = logging.getLogger(__name__)

DEFAULT_NOMUS_BASE_URL = "https://univetoptic.nomus.com.br/univetoptic/rest"
DEFAULT_UNIVET_KEY = "aW50ZWdyYWRvcmVycDpocHFCTVdLUHZ3TUhqNFI="


class NomusError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def parse_ptbr_float(val: Any) -> float:
    """Converte valores no formato pt-BR ('16.800,00', '0,10', 1500) para float."""
    if val is None or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    clean = val_str.replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except ValueError:
        return 0.0


def normalize_phone(phone: str | None) -> str | None:
    """Normaliza número de telefone para formato E.164 (+55...)."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return None
    digits = digits.lstrip("0")
    if len(digits) in (10, 11):  # DDD + número (Brasil)
        digits = "55" + digits
    if len(digits) >= 12 and not digits.startswith("55"):
        digits = "55" + digits
    return f"+{digits}"


class NomusClient:
    def __init__(self, key: str = DEFAULT_UNIVET_KEY, base_url: str = DEFAULT_NOMUS_BASE_URL, timeout: float = 30.0):
        self.key = key.strip() if key else DEFAULT_UNIVET_KEY
        self.base_url = base_url.rstrip("/") if base_url else DEFAULT_NOMUS_BASE_URL
        self.headers = {
            "Authorization": f"Basic {self.key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self.timeout = timeout

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = f"{self.base_url}{endpoint}"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.request(method, url, headers=self.headers, **kwargs)
            if resp.status_code >= 400:
                logger.error("Nomus API error: %d %s", resp.status_code, resp.text)
                raise NomusError(f"Nomus API retornou {resp.status_code}: {resp.text}", status_code=resp.status_code)
            if resp.status_code == 204 or not resp.text.strip():
                return [] if method.upper() == "GET" else {}
            return resp.json()

    def get_pedidos(self, pagina: int = 1) -> list[dict[str, Any]]:
        """Busca pedidos paginados (50 registros por página)."""
        data = self._request("GET", f"/pedidos?pagina={pagina}")
        return data if isinstance(data, list) else []

    def get_all_pedidos(self, max_pages: int = 5) -> list[dict[str, Any]]:
        """Busca pedidos recentes até o limite de páginas."""
        all_pedidos = []
        for p in range(1, max_pages + 1):
            batch = self.get_pedidos(p)
            if not batch:
                break
            all_pedidos.extend(batch)
            if len(batch) < 50:
                break
        return all_pedidos

    def get_clientes(self, pagina: int = 1) -> list[dict[str, Any]]:
        data = self._request("GET", f"/clientes?pagina={pagina}")
        return data if isinstance(data, list) else []

    def get_cliente(self, client_id: int) -> dict[str, Any]:
        data = self._request("GET", f"/clientes/{client_id}")
        return data if isinstance(data, dict) else {}

    def get_representantes(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/representantes")
        return data if isinstance(data, list) else []

    def get_vendedores(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/vendedores")
        return data if isinstance(data, list) else []

    def get_nfes(self, pagina: int = 1) -> list[dict[str, Any]]:
        data = self._request("GET", f"/nfes?pagina={pagina}")
        return data if isinstance(data, list) else []
