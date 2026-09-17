from typing import Any
from .base import BaseWhatsAppProvider
from .evolution import EvolutionWhatsAppProvider
from .meta_cloud import MetaCloudWhatsAppProvider
from .custom_api import CustomApiWhatsAppProvider


def get_whatsapp_provider(provider_type: str, config: dict[str, Any]) -> BaseWhatsAppProvider:
    """
    Factory para instanciar o provedor WhatsApp selecionado.
    Suporta: 'evolution', 'meta_cloud', 'zapi', 'custom'.
    """
    p_type = provider_type.lower()
    if p_type == "evolution":
        return EvolutionWhatsAppProvider(config)
    elif p_type == "meta_cloud":
        return MetaCloudWhatsAppProvider(config)
    elif p_type in ["zapi", "custom"]:
        return CustomApiWhatsAppProvider(config)
    else:
        raise ValueError(f"Provedor WhatsApp '{provider_type}' não suportado.")
