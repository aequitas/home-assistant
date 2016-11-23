"""
Support for Tellstick switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.tellstick/
"""
from homeassistant.components.tellstick import (
    ATTR_DISCOVER_CONFIG, ATTR_DISCOVER_DEVICES, DEFAULT_SIGNAL_REPETITIONS,
    DOMAIN, TellstickDevice)
from homeassistant.helpers.entity import ToggleEntity
import voluptuous as vol

PLATFORM_SCHEMA = vol.Schema({vol.Required("platform"): DOMAIN})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup Tellstick switches."""
    if (discovery_info is None or
            discovery_info[ATTR_DISCOVER_DEVICES] is None):
        return

    # Allow platform level override, fallback to module config
    signal_repetitions = discovery_info.get(ATTR_DISCOVER_CONFIG,
                                            DEFAULT_SIGNAL_REPETITIONS)

    add_devices(TellstickSwitch(tellcore_id, signal_repetitions)
                for tellcore_id in discovery_info[ATTR_DISCOVER_DEVICES])


class TellstickSwitch(TellstickDevice, ToggleEntity):
    """Representation of a Tellstick switch."""

    def _parse_ha_data(self, kwargs):
        """Turn the value from HA into something useful."""
        return None

    def _parse_tellcore_data(self, tellcore_data):
        """Turn the value recieved from tellcore into something useful."""
        return None

    def _update_model(self, new_state, data):
        """Update the device entity state to match the arguments."""
        self._state = new_state

    def _send_tellstick_command(self):
        """Let tellcore update the device to match the current state."""
        if self._state:
            self._tellcore_device.turn_on()
        else:
            self._tellcore_device.turn_off()

    @property
    def force_update(self) -> bool:
        """Will trigger anytime the state property is updated."""
        return True
