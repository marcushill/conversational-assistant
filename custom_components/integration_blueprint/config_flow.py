"""Adds config flow for Matcha Conversation Agent."""

from __future__ import annotations

import urllib.parse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_URL
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from slugify import slugify

from .blueprint_api import (
    IntegrationBlueprintApiClient,
    IntegrationBlueprintApiClientAuthenticationError,
    IntegrationBlueprintApiClientCommunicationError,
    IntegrationBlueprintApiClientError,
)
from .const import DOMAIN, LOGGER, CONFIG_AGENT_NAME


async def validate_basic_info(user_input: dict | None) -> bool:
    # TODO: Make a way to validate that the URL and agent are valid.
    if user_input is None:
        return False

    if user_input.get(CONF_URL) == "":
        return False

    if user_input.get(CONFIG_AGENT_NAME) == "":
        return False

    return True


class MatchaFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Matcha Conversation Agent."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            if await validate_basic_info(user_input):
                agent_title = f"Matcha Agent {user_input[CONFIG_AGENT_NAME]}"
                unique_id = slugify(urllib.parse.urljoin(user_input[CONF_URL], "agents", user_input[CONFIG_AGENT_NAME]))
                await self.async_set_unique_id(unique_id=unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=agent_title,
                    data=user_input,
                )
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
                    vol.Required(CONFIG_AGENT_NAME): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )
