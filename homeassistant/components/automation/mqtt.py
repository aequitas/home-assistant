"""
Offer MQTT listening automation rules.

For more details about this automation rule, please refer to the documentation
at https://home-assistant.io/components/automation/#mqtt-trigger
"""
import homeassistant.components.mqtt as mqtt
from homeassistant.const import CONF_PAYLOAD, CONF_PLATFORM
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

DEPENDENCIES = ['mqtt']

CONF_TOPIC = 'topic'

TRIGGER_SCHEMA = vol.Schema({
    vol.Required(CONF_PLATFORM): mqtt.DOMAIN,
    vol.Required(CONF_TOPIC): mqtt.valid_subscribe_topic,
    vol.Optional(CONF_PAYLOAD): cv.string,
})


def async_trigger(hass, config, action):
    """Listen for state changes based on configuration."""
    topic = config.get(CONF_TOPIC)
    payload = config.get(CONF_PAYLOAD)

    @callback
    def mqtt_automation_listener(msg_topic, msg_payload, qos):
        """Listen for MQTT messages."""
        if payload is None or payload == msg_payload:
            hass.async_run_job(action, {
                'trigger': {
                    'platform': 'mqtt',
                    'topic': msg_topic,
                    'payload': msg_payload,
                    'qos': qos,
                }
            })

    return mqtt.async_subscribe(hass, topic, mqtt_automation_listener)
