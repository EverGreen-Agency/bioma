from typing import Any
import httpx
from .base import BaseWhatsAppProvider


class CustomApiWhatsAppProvider(BaseWhatsAppProvider):
    """
    Provedor Genérico / Z-API para integrações não oficiais customizadas.
    Suporta Webhooks e rotas HTTP configuráveis por cliente.
    """

    def send_text_message(self, to_number: str, text: str) -> dict[str, Any]:
        if not self.api_url:
            return {
                "status": "simulated",
                "provider": "custom",
                "to": to_number,
                "message": text,
                "detail": "Modo simulação local Z-API / Custom Provider",
            }

        headers = {"Authorization": f"Bearer {self.api_token}"} if self.api_token else {}
        payload = {"phone": to_number, "message": text}

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                return {"status": "sent", "provider": "custom", "data": response.json()}
        except Exception as e:
            return {"status": "failed", "provider": "custom", "error": str(e)}

    def send_template_message(self, to_number: str, template_name: str, variables: list[str]) -> dict[str, Any]:
        text = f"[{template_name}] " + " ".join(variables)
        return self.send_text_message(to_number, text)

    def check_health(self) -> dict[str, Any]:
        return {"status": "online", "provider": "custom", "url": self.api_url}
