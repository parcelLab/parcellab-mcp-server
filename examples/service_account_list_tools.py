"""List parcelLab MCP tools using service account credentials.

This example is intended for customers who received:
  - PARCELLAB_CLIENT
  - PARCELLAB_SECRET

It performs a client-credentials token exchange, connects to the MCP endpoint,
and prints the tools available to that service account.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
TOKEN_URL = "https://auth.parcellab.com/realms/parcellab/protocol/openid-connect/token"
MCP_URL = "https://agents.parcellab.com/mcp/"
SCOPE = "track:orderinfo returns:registration"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values

async def fetch_access_token(client_id: str, client_secret: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "scope": SCOPE,
            },
            auth=(client_id, client_secret),
        )
        response.raise_for_status()
        payload = response.json()
        return payload["access_token"]


async def list_tools(access_token: str) -> None:
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {access_token}"},
        follow_redirects=True,
        timeout=30,
    ) as http_client:
        async with streamable_http_client(MCP_URL, http_client=http_client) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()

    print("Available tools:")
    for tool in tools.tools:
        print(f"- {tool.name}")


async def main() -> None:
    env = load_env(ENV_FILE)
    client_id = env["PARCELLAB_CLIENT"]
    client_secret = env["PARCELLAB_SECRET"]

    access_token = await fetch_access_token(client_id, client_secret)
    await list_tools(access_token)


if __name__ == "__main__":
    asyncio.run(main())
