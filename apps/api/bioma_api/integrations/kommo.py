import httpx
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class KommoError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

class KommoClient:
    def __init__(self, subdomain: str, access_token: str):
        self.subdomain = subdomain
        self.access_token = access_token
        self.base_url = f"https://{subdomain}.kommo.com"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            if response.status_code >= 400:
                logger.error(f"Kommo API error: {response.status_code} {response.text}")
                raise KommoError(
                    f"API returned {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )
            
            # Kommo can return 204 No Content for empty lists sometimes
            if response.status_code == 204:
                return {}
            return response.json()

    async def get_pipelines(self) -> List[Dict[str, Any]]:
        """Fetch all pipelines and their statuses (stages)."""
        data = await self._request("GET", "/api/v4/leads/pipelines")
        if "_embedded" in data and "pipelines" in data["_embedded"]:
            return data["_embedded"]["pipelines"]
        return []

    async def get_leads(self, limit: int = 250, page: int = 1) -> List[Dict[str, Any]]:
        """Fetch leads for the account. Supports pagination."""
        params = {"limit": limit, "page": page}
        data = await self._request("GET", "/api/v4/leads", params=params)
        if "_embedded" in data and "leads" in data["_embedded"]:
            return data["_embedded"]["leads"]
        return []

    async def get_all_leads(self) -> List[Dict[str, Any]]:
        """Iterate through pagination and fetch all leads."""
        all_leads = []
        page = 1
        while True:
            leads = await self.get_leads(limit=250, page=page)
            if not leads:
                break
            all_leads.extend(leads)
            # If we received less than the limit, we're at the end
            if len(leads) < 250:
                break
            page += 1
        return all_leads

    # Helper method to refresh tokens if needed (typically done via a separate auth flow)
    @staticmethod
    async def exchange_token(client_id: str, client_secret: str, code: str, redirect_uri: str, subdomain: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        url = f"https://{subdomain}.kommo.com/oauth2/access_token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def refresh_token(client_id: str, client_secret: str, refresh_token: str, redirect_uri: str, subdomain: str) -> Dict[str, Any]:
        """Get a new access token using a refresh token."""
        url = f"https://{subdomain}.kommo.com/oauth2/access_token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "redirect_uri": redirect_uri
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
