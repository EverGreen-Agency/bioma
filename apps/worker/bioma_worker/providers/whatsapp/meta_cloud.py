from typing import Any
import httpx
from .base import BaseWhatsAppProvider


class MetaCloudWhatsAppProvider(BaseWhatsAppProvider):
    """
    Provedor Meta Cloud API Oficial (WhatsApp Business Platform).
    Utiliza Graph API v19.0 para envio oficial de mensagens e templates.
    """

    def send_text_message(self, to_number: str, text: str) -> dict[str, Any]:
        phone_number_id = self.config.get("phone_number_id") or self.instance_name
        if not self.api_token or not phone_number_id:
            return {
                "status": "simulated",
                "provider": "meta_cloud",
                "to": to_number,
                "message": text,
                "detail": "Modo simulação local EverGreen (Meta Cloud API Oficial)",
            }

        endpoint = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return {"status": "sent", "provider": "meta_cloud", "data": response.json()}
        except Exception as e:
            return {"status": "failed", "provider": "meta_cloud", "error": str(e)}

    def send_template_message(self, to_number: str, template_name: str, variables: list[str]) -> dict[str, Any]:
        phone_number_id = self.config.get("phone_number_id") or self.instance_name
        if not self.api_token or not phone_number_id:
            return {
                "status": "simulated",
                "provider": "meta_cloud",
                "to": to_number,
                "template": template_name,
                "detail": "Modo simulação local de Template Meta Cloud API",
            }

        endpoint = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        components = []
        if variables:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": v} for v in variables]
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "pt_BR"},
                "components": components,
            },
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return {"status": "sent", "provider": "meta_cloud", "data": response.json()}
        except Exception as e:
            return {"status": "failed", "provider": "meta_cloud", "error": str(e)}

    def check_health(self) -> dict[str, Any]:
        return {"status": "online", "provider": "meta_cloud", "mode": "official_graph_api"}
