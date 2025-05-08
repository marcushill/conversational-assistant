"""Adds config flow for Matcha Conversation Agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_LLM_HASS_API, CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import aiohttp_client, llm, selector
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)
from slugify import slugify

from . import MatchaClient
from .const import CONF_AGENT_NAME, DOMAIN

if TYPE_CHECKING:
    from types import MappingProxyType

    from aiohttp import ClientSession
    from homeassistant.config_entries import ConfigFlowResult
    from homeassistant.data_entry_flow import FlowResult

async def _validate_base_url(user_input: dict | None, session: ClientSession) -> bool:
    if user_input is None:
        return False

    base_url : str = user_input.get(CONF_URL)
    if base_url == "":
        return False

    client = MatchaClient(base_url, session)
    await client.agent_list()

    return True


async def _validate_agent(user_input: dict | None, client: MatchaClient) -> bool:
    if user_input is None:
        return False

    agent_name = user_input.get(CONF_AGENT_NAME)
    if agent_name == "":
        return False

    try:
        agents = await client.agent_list()
        return any(True for agent in agents if agent["name"] == agent_name)
    except Exception:
        return False

class MatchaFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Matcha Conversation Agent."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.base_url = None

    @staticmethod
    @callback
    def async_get_options_flow(
            config_entry: Any,
    ) -> OptionsFlowHandler:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                if await _validate_base_url(user_input, aiohttp_client.async_get_clientsession(self.hass)):
                    self.base_url = user_input[CONF_URL]
                    return await self.async_step_choose_agent()
            except Exception as e:
                _errors= {CONF_URL: str(e)}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL,
                        default=(user_input or {}).get(CONF_URL, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )


    async def async_step_choose_agent(self,
                                      user_input: dict | None = None,
                                      ) -> ConfigFlowResult:
        """Handle a flow after the user has selected a base URL."""
        _errors = {}
        session = aiohttp_client.async_get_clientsession(self.hass)
        matcha_client = MatchaClient(self.base_url, session)
        if user_input is not None and await _validate_agent(user_input, matcha_client):
                agent_title = f"Matcha Agent {user_input[CONF_AGENT_NAME]}"
                unique_id = slugify("-".join([self.base_url, "agents", user_input[CONF_AGENT_NAME]]))
                await self.async_set_unique_id(unique_id=unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=agent_title,
                    data={
                        CONF_URL: self.base_url,
                        CONF_AGENT_NAME: user_input[CONF_AGENT_NAME],
                    },
                )
        agents = await matcha_client.agent_list()
        agent_names = [agent["name"] for agent in agents]
        return self.async_show_form(
            step_id="choose_agent",
            last_step=True,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_AGENT_NAME,
                        description={"suggested_value": agent_names[0]},
                    ): SelectSelector(SelectSelectorConfig(options=[
                        SelectOptionDict(
                                value=agent_name,
                                label=agent_name,
                            ) for agent_name in agent_names
                        ], multiple=False)),
                },
            ),
            errors=_errors,
        )
class OptionsFlowHandler(config_entries.OptionsFlow):
    """
    OptionsFlowHandler for Matcha Conversation Agent.
    This handles the options flow for the Matcha Conversation Agent allowing selection of valid tools.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                async_get_options_schema(self.hass, self.config_entry.options), self.config_entry.options
            ),
        )

@callback
def async_get_options_schema(
        hass: HomeAssistant,
        options: MappingProxyType[str, Any],
) -> vol.Schema:
    """Return the options schema."""
    apis: list[SelectOptionDict] = [
        SelectOptionDict(
            label=api.name,
            value=api.id,
        )
        for api in llm.async_get_apis(hass)
    ]

    return vol.Schema(
        {
            vol.Optional(
                CONF_LLM_HASS_API,
                description={"suggested_value": options.get(CONF_LLM_HASS_API)},
            ): SelectSelector(SelectSelectorConfig(options=apis, multiple=True)),
        }
    )
