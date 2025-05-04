"""
Custom integration to integrate matcha_conversation_agent with Home Assistant.

For more details about this integration, please refer to
https://github.com/marcushill/matcha_conversation_agent
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Any

from homeassistant.components import conversation, assist_pipeline
from homeassistant.const import CONF_URL, MATCH_ALL, CONF_LLM_HASS_API, Platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.llm import ToolInput
from homeassistant.loader import async_get_loaded_integration
from homeassistant.helpers import aiohttp_client, intent, device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .client import MatchaClient
from .const import DOMAIN, LOGGER, DATA_AGENT, CONF_PROMPT, CONF_AGENT_NAME

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS = (Platform.CONVERSATION, )

# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    data = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    # conversation.async_set_agent(hass, entry, agent)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True




async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    hass.data[DOMAIN].pop(entry.entry_id)
    # conversation.async_unset_agent(hass, entry)
    await hass.config_entries.async_unload_platforms( entry, PLATFORMS)
    return True


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


hass_to_match_roles = {
    # System, User, Assistant, Function, Tool, Developer
    "system": "System",
    "user": "User",
    "assistant": "Assistant",
    "tool_result": "Tool"
}
matcha_to_has_roles = {v: k for k, v in hass_to_match_roles.items()}

def _convert_content(user_input: conversation.ConversationInput, content: conversation.Content) -> dict[str, Any]:
    # Switch over all possible content types
    result = {
        "role": hass_to_match_roles[content.role],
        "content": content.content
    }

    if result["role"] == "User":
        result["user_name"] = user_input.context.user_id
    else:
        result["user_name"] = user_input.agent_id

    if result["role"] == "Tool":
        result["tool_call_result"] = {
            "id": content.tool_call_id,
            "name": content.tool_name,
            "result": content.tool_result
        }

    return result
