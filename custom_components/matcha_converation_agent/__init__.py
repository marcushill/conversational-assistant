"""
Custom integration to integrate matcha_conversation_agent with Home Assistant.

For more details about this integration, please refer to
https://github.com/marcushill/matcha_conversation_agent
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform

from .client import MatchaClient
from .const import CONF_AGENT_NAME, CONF_PROMPT, DATA_AGENT, DOMAIN, LOGGER

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

