from abc import ABC, abstractmethod
from typing import Any


class BaseWhatsAppProvider(ABC):
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.api_url = config.get("api_url")
        self.api_token = config.get("api_token")
        self.instance_name = config.get("instance_name")

    @abstractmethod
    def send_text_message(self, to_number: str, text: str) -> dict[str, Any]:
        """Envia mensagem de texto via provedor."""
        pass

    @abstractmethod
    def send_template_message(self, to_number: str, template_name: str, variables: list[str]) -> dict[str, Any]:
        """Envia mensagem baseada em modelo pré-aprovado."""
        pass

    @abstractmethod
    def check_health(self) -> dict[str, Any]:
        """Verifica conectividade e estado da instância."""
        pass
