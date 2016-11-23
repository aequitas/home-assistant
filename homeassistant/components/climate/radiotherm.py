"""
Support for Radio Thermostat wifi-enabled home thermostats.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/climate.radiotherm/
"""
import datetime
import logging

from homeassistant.components.climate import (
    PLATFORM_SCHEMA, STATE_AUTO, STATE_COOL, STATE_HEAT, STATE_IDLE, STATE_OFF,
    ClimateDevice)
from homeassistant.const import ATTR_TEMPERATURE, CONF_HOST, TEMP_FAHRENHEIT
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

REQUIREMENTS = ['radiotherm==1.2']

_LOGGER = logging.getLogger(__name__)

ATTR_FAN = 'fan'
ATTR_MODE = 'mode'

CONF_HOLD_TEMP = 'hold_temp'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_HOST): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_HOLD_TEMP, default=False): cv.boolean,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Radio Thermostat."""
    import radiotherm

    hosts = []
    if CONF_HOST in config:
        hosts = config[CONF_HOST]
    else:
        hosts.append(radiotherm.discover.discover_address())

    if hosts is None:
        _LOGGER.error("No Radiotherm Thermostats detected")
        return False

    hold_temp = config.get(CONF_HOLD_TEMP)
    tstats = []

    for host in hosts:
        try:
            tstat = radiotherm.get_thermostat(host)
            tstats.append(RadioThermostat(tstat, hold_temp))
        except OSError:
            _LOGGER.exception("Unable to connect to Radio Thermostat: %s",
                              host)

    add_devices(tstats)


class RadioThermostat(ClimateDevice):
    """Representation of a Radio Thermostat."""

    def __init__(self, device, hold_temp):
        """Initialize the thermostat."""
        self.device = device
        self.set_time()
        self._target_temperature = None
        self._current_temperature = None
        self._current_operation = STATE_IDLE
        self._name = None
        self._fmode = None
        self._tmode = None
        self.hold_temp = hold_temp
        self.update()
        self._operation_list = [STATE_AUTO, STATE_COOL, STATE_HEAT, STATE_OFF]

    @property
    def name(self):
        """Return the name of the Radio Thermostat."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_FAHRENHEIT

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        return {
            ATTR_FAN: self._fmode,
            ATTR_MODE: self._tmode,
        }

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def current_operation(self):
        """Return the current operation. head, cool idle."""
        return self._current_operation

    @property
    def operation_list(self):
        """Return the operation modes list."""
        return self._operation_list

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    def update(self):
        """Update the data from the thermostat."""
        self._current_temperature = self.device.temp['raw']
        self._name = self.device.name['raw']
        self._fmode = self.device.fmode['human']
        self._tmode = self.device.tmode['human']

        if self._tmode == 'Cool':
            self._target_temperature = self.device.t_cool['raw']
            self._current_operation = STATE_COOL
        elif self._tmode == 'Heat':
            self._target_temperature = self.device.t_heat['raw']
            self._current_operation = STATE_HEAT
        else:
            self._current_operation = STATE_IDLE

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        if self._current_operation == STATE_COOL:
            self.device.t_cool = round(temperature * 2.0) / 2.0
        elif self._current_operation == STATE_HEAT:
            self.device.t_heat = round(temperature * 2.0) / 2.0
        if self.hold_temp:
            self.device.hold = 1
        else:
            self.device.hold = 0

    def set_time(self):
        """Set device time."""
        now = datetime.datetime.now()
        self.device.time = {
            'day': now.weekday(),
            'hour': now.hour,
            'minute': now.minute
        }

    def set_operation_mode(self, operation_mode):
        """Set operation mode (auto, cool, heat, off)."""
        if operation_mode == STATE_OFF:
            self.device.tmode = 0
        elif operation_mode == STATE_AUTO:
            self.device.tmode = 3
        elif operation_mode == STATE_COOL:
            self.device.t_cool = round(self._target_temperature * 2.0) / 2.0
        elif operation_mode == STATE_HEAT:
            self.device.t_heat = round(self._target_temperature * 2.0) / 2.0
