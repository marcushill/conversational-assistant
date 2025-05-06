"""Constants for matcha_conversation_agent."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "matcha_conversation_agent"
ATTRIBUTION = "Data provided by http://jsonplaceholder.typicode.com/"
CONF_AGENT_NAME = "agent_name"
CONF_PROMPT = "prompt"
DATA_AGENT = "agent_obj"
