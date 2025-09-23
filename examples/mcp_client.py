"""MCP client demo with dynamic OAuth client registration.

This script demonstrates how to:
  - perform OAuth 2.1 dynamic client registration against an MCP Resource Server,
  - open a Streamable HTTP connection to an MCP endpoint,
  - initialize an MCP session and list available tools.

Usage (interactive demo):

    import asyncio
    from mcp_server.docs.snippets.oauth_client import open_session

    async def main():
        async with open_session(
            server_url="https://<your-host>/mcp/",
            scope="mcp:preview",  # add additional scopes as needed
        ) as session:
            tools = await session.list_tools()
            print([t.name for t in tools.tools])

    asyncio.run(main())

Under the hood, the MCP Python SDK discovers the Authorization Server via
RFC 9728 Protected Resource Metadata published by the Resource Server,
registers the client dynamically, and then attaches `Authorization: Bearer` to
all MCP HTTP requests.
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from urllib.parse import parse_qs, urlparse, urlunparse

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)
from pydantic import AnyUrl


class InMemoryTokenStorage(TokenStorage):
    """In-memory token storage for demos.

    Replace with a persistent storage in real integrations.
    """

    def __init__(self) -> None:
        self._tokens: OAuthToken | None = None
        self._client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self._tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self._client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._client_info = client_info


async def default_redirect_handler(auth_url: str) -> None:
    """Display the authorization URL to the user for login/consent."""
    print("Open this URL in a browser and complete login:\n", auth_url)


async def default_callback_handler() -> tuple[str, str | None]:
    """Prompt for the final redirect URL and extract code/state parameters."""
    callback_url = input(
        "Paste the final redirected URL here and press Enter: \n"
    ).strip()
    params = parse_qs(urlparse(callback_url).query)
    return params["code"][0], params.get("state", [None])[0]


def _rs_origin_from(server_url: str) -> str:
    """Return the Resource-Server origin used for OAuth metadata discovery.

    Example: https://host.example.com/path/mcp/ -> https://host.example.com
    """
    p = urlparse(server_url)
    return urlunparse((p.scheme, p.netloc, "", "", "", ""))


@asynccontextmanager
async def open_session(
    *,
    server_url: str,
    client_name: str = "parcelLab MCP Client",
    redirect_uri: str = "http://localhost:8765/callback",
    scope: str | None = None,
    storage: TokenStorage | None = None,
):
    """Open an authenticated MCP ClientSession (Streamable HTTP).

    - server_url: Full MCP endpoint (e.g. https://<host>/mcp/). The Resource-Server
      origin for OAuth discovery is derived automatically.
    - scope: Space-separated list of scopes required by your tools (required).
    - client_name, redirect_uri: parameters used during dynamic client registration.
    - storage: token store implementation (in-memory by default).
    """
    if not scope:
        raise ValueError("scope is required (space-separated scopes)")
    storage = storage or InMemoryTokenStorage()
    oauth_auth = OAuthClientProvider(
        server_url=_rs_origin_from(server_url),
        client_metadata=OAuthClientMetadata(
            client_name=client_name,
            redirect_uris=[AnyUrl(redirect_uri)],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope=scope,
        ),
        storage=storage,
        redirect_handler=default_redirect_handler,
        callback_handler=default_callback_handler,
    )
    async with (
        streamablehttp_client(server_url, auth=oauth_auth) as (
            read,
            write,
            _,
        ),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        try:
            yield session
        finally:
            # Give the transport a brief moment to flush
            await asyncio.sleep(0.05)


async def acquire_access_token(
    *,
    server_url: str,
    scope: str,
    redirect_uri: str = "http://localhost:8765/callback",
    client_name: str = "parcelLab MCP Client",
) -> str:
    """Run dynamic registration + OAuth flow and return an access token.

    Uses the same machinery as `open_session`, performing a minimal session
    initialization to finish the grant, then returns the Bearer token for
    clients that only accept static headers.
    """
    storage = InMemoryTokenStorage()
    async with open_session(
        server_url=server_url,
        scope=scope,
        redirect_uri=redirect_uri,
        client_name=client_name,
        storage=storage,
    ):
        # Session immediately closed; tokens are stored in `storage`.
        pass
    assert storage._tokens is not None, "OAuth did not return tokens"
    return storage._tokens.access_token


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MCP client demo: dynamic registration + list tools",
    )
    parser.add_argument(
        "--server-url",
        required=True,
        help="MCP endpoint (streamable HTTP)",
        default="https://agents.parcellab.com/mcp/"
    )
    parser.add_argument(
        "--scope",
        required=True,
        help="Space-separated OAuth scopes",
        default="track:orderinfo returns:registration"
    )
    return parser.parse_args()


async def _amain() -> None:
    args = _parse_args()
    async with open_session(server_url=args.server_url, scope=args.scope) as session:
        tools = await session.list_tools()
        print("Available tools:", [t.name for t in tools.tools])


if __name__ == "__main__":
    asyncio.run(_amain())
