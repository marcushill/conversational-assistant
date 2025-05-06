import urllib.parse
from typing import Any

import aiohttp


class MatchaClient:
    """Client for the Matcha API."""

    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self.session = session
        self.base_url = base_url

    async def agent_chat(self, agent_id: str, body: dict[str, Any]) -> dict[str, Any]:
        result = await self.session.post(urllib.parse.urljoin(self.base_url, "agents/") + agent_id + "/chat", json=body)
        return await result.json()
