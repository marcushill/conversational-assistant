"""
Custom integration to integrate matcha_conversation_agent with Home Assistant.

For more details about this integration, please refer to
https://github.com/marcushill/matcha_conversation_agent
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Literal, Any

from homeassistant.components import conversation
from homeassistant.const import  CONF_URL, MATCH_ALL, CONF_LLM_HASS_API
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_loaded_integration
from homeassistant.config_entries import ConfigEntry
from .blueprint_api import IntegrationBlueprintApiClient
from .const import DOMAIN, LOGGER, DATA_AGENT, CONF_PROMPT, CONF_AGENT_NAME
from .coordinator import BlueprintDataUpdateCoordinator
from .data import IntegrationBlueprintData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    data = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    agent = MatchaAgent(hass, entry)
    data[DATA_AGENT] = agent

    conversation.async_set_agent(hass, entry, agent)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    hass.data[DOMAIN].pop(entry.entry_id)
    # TODO: Remove the conversation agent


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

class MatchaAgent(conversation.AbstractConversationAgent, conversation.ConversationEntity):
    """MatchaAgent conversation agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.history: dict[str, list[dict]] = {}
        base_url = entry.data.get(CONF_URL)



    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

  async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Call the API."""

        try:
            await chat_log.async_update_llm_data(
                DOMAIN,
                user_input,
                self.entry.options.get(CONF_LLM_HASS_API),
                self.entry.options.get(CONF_PROMPT),
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        tools: list[dict[str, Any]] | None = None
        # if chat_log.llm_api:
        #     tools = [
        #         _format_tool(tool)  # TODO format the tools as your LLM expects
        #         for tool in chat_log.llm_api.tools
        #     ]

        # messages = [
        #     m
        #     for content in chat_log.content
        #     for m in _convert_content(content)  # TODO format messages
        # ]

        # Interact with LLM and pass tools
        request = user_input.text
        for _iteration in range(10):
            response = ... # Send request to LLM and get streaming response

            messages.extend(
                [
                    _convert_content(content)  # TODO format messages
                    async for content in chat_log.async_add_delta_content_stream(
                        user_input.agent_id, _transform_stream(response)  # TODO call tools and stream responses
                    )
                ]
            )

            if not chat_log.unresponded_tool_results:
                break

        # Send the final response to the user
        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(chat_log.content[-1].content or "")
        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=chat_log.conversation_id,
            continue_conversation=chat_log.continue_conversation,
        )