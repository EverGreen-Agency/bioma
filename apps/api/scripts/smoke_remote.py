import os

import httpx


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} não configurado.")
    return value


def main() -> None:
    base_url = required_env("BIOMA_API_BASE_URL").rstrip("/")
    email = required_env("BIOMA_SMOKE_EMAIL")
    password = required_env("BIOMA_SMOKE_PASSWORD")
    cookie_name = os.getenv("BIOMA_SESSION_COOKIE_NAME", "bioma_session").strip() or "bioma_session"

    with httpx.Client(base_url=base_url, timeout=20, follow_redirects=True) as client:
        health = client.get("/health")
        health.raise_for_status()
        ready = client.get("/health/ready")
        ready.raise_for_status()

        login = client.post("/auth/login", json={"email": email, "password": password})
        login.raise_for_status()
        assert client.cookies.get(cookie_name), "cookie de sessão não foi recebido"

        me = client.get("/auth/me")
        me.raise_for_status()
        assert me.json()["email"].lower() == email.lower()

        clients = client.get("/clients")
        clients.raise_for_status()

        logout = client.post("/auth/logout")
        logout.raise_for_status()
        assert client.get("/auth/me").status_code == 401

    print("remote smoke ok")


if __name__ == "__main__":
    main()
