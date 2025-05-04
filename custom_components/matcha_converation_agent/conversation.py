from typing import Literal, Any

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from homeassistant.components import conversation, assist_pipeline
from homeassistant.const import CONF_URL, MATCH_ALL, CONF_LLM_HASS_API, Platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.llm import ToolInput, Tool
from homeassistant.loader import async_get_loaded_integration
from homeassistant.helpers import aiohttp_client, intent, device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .client import MatchaClient
from .const import DOMAIN, LOGGER, DATA_AGENT, CONF_PROMPT, CONF_AGENT_NAME


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> bool:
    """Set up this integration using UI."""
    agent = MatchaAgent(hass, entry)
    #conversation.async_set_agent(hass, entry, agent)
    async_add_entities([agent])
    return True



class MatchaAgent(conversation.ConversationEntity, conversation.AbstractConversationAgent):
    """MatchaAgent conversation agent."""

    _attr_has_entity_name = True
    _attr_name = None
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self.history: dict[str, list[dict]] = {}
        base_url = entry.data.get(CONF_URL)
        self.client = MatchaClient(base_url, aiohttp_client.async_get_clientsession(hass))

        if self.entry.options.get(CONF_LLM_HASS_API):
            self._attr_supported_features = (
                conversation.ConversationEntityFeature.CONTROL
            )
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = device_registry.DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="S&M Labs",
            model="Matcha Server",
            entry_type=device_registry.DeviceEntryType.SERVICE,
        )


    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL


    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle options update."""
        # Reload as we update device info + entity name + supported features
        await hass.config_entries.async_reload(entry.entry_id)

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        assist_pipeline.async_migrate_engine(
            self.hass, "conversation", self.entry.entry_id, self.entity_id
        )
        conversation.async_set_agent(self.hass, self.entry, self)
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._async_entry_update_listener)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

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
        if chat_log.llm_api:
            tools = [
                _convert_tool(tool)  # TODO format the tools as your LLM expects
                for tool in chat_log.llm_api.tools
            ]

        messages = [
            _convert_content(user_input, content) for content in chat_log.content
        ]

        # Interact with LLM and pass tools
        for _iteration in range(10):
            response = await self.client.agent_chat(
                self.entry.data.get(CONF_AGENT_NAME),
                  {
                      "messages": messages,
                      "tools": tools,
                  })


            # Process tool calls
            tool_calls = None
            if response["tool_call_requests"] and len(response["tool_call_requests"]) > 0:
                tool_calls = [chat_log.llm_api.async_call_tool(ToolInput(x["name"], x["arguments"], x["id"])) for x in response["tool_call_requests"]]

            messages.extend(
                [
                    _convert_content(user_input, content)
                    async for content in chat_log.async_add_assistant_content(
                        conversation.AssistantContent(user_input.agent_id, response["content"], tool_calls )
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

def _convert_tool(tool: Tool) -> dict[str, Any]:
    return {
        "name": tool.name,
        "type": "function",
        "description": tool.description,
        "parameters": tool.parameters,
        "strict": True,
    }