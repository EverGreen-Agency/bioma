from typing import Any
import httpx
from .base import BaseWhatsAppProvider


class EvolutionWhatsAppProvider(BaseWhatsAppProvider):
    """
    Provedor Evolution API v2 (baseado em Baileys).
    Conecta a instâncias auto-hospedadas ou gerenciadas via HTTP REST.
    """

    def send_text_message(self, to_number: str, text: str) -> dict[str, Any]:
        if not self.api_url or not self.api_token or not self.instance_name:
            return {
                "status": "simulated",
                "provider": "evolution",
                "to": to_number,
                "message": text,
                "detail": "Modo simulação local EverGreen (Evolution API)",
            }

        endpoint = f"{self.api_url.rstrip('/')}/message/sendText/{self.instance_name}"
        headers = {"apikey": self.api_token, "Content-Type": "application/json"}
        payload = {"number": to_number, "text": text}

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return {"status": "sent", "provider": "evolution", "data": response.json()}
        except Exception as e:
            return {"status": "failed", "provider": "evolution", "error": str(e)}

    def send_template_message(self, to_number: str, template_name: str, variables: list[str]) -> dict[str, Any]:
        formatted_text = f"[{template_name}] " + " ".join(variables)
        return self.send_text_message(to_number, formatted_text)

    def check_health(self) -> dict[str, Any]:
        if not self.api_url or not self.instance_name:
            return {"status": "simulation_online", "provider": "evolution"}

        endpoint = f"{self.api_url.rstrip('/')}/instance/connectionState/{self.instance_name}"
        headers = {"apikey": self.api_token}
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.get(endpoint, headers=headers)
                return {"status": "connected" if res.status_code == 200 else "error", "data": res.json()}
        except Exception as e:
            return {"status": "offline", "error": str(e)}
