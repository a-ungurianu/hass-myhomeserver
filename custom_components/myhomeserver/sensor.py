from __future__ import annotations

from typing import Any, Mapping

import myhome.object
import voluptuous as vol
from myhome._gen.model.object_value_thermostat import ObjectValueThermostat

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, TEMP_CELSIUS, DEVICE_CLASS_TEMPERATURE, STATE_CLASS_MEASUREMENT
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

PARALLEL_UPDATES = 10

OPTIONAL_TEMP_SENSOR_STATE_ATTRIBUTES = [
    "protocol_name",
    "protocol_config",
    "id_room",
    "id_zone",
]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_USERNAME, default="admin"): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }
)


async def async_setup_entry(
        hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up MyHomeSERVER lights from a config entry."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    server_serial = await hub.get_server_serial()
    thermostats = [
        MyHomeServerThermostatTemp(server_serial, thermostat)
        for thermostat in await hub.thermostats()
    ]

    if len(thermostats) > 0:
        async_add_entities(thermostats)

    return True


class MyHomeServerThermostatTemp(SensorEntity):
    def __init__(self, server_serial: str, thermostat: myhome.object.Thermostat):
        self._thermostat = thermostat
        self._server_serial = server_serial
        self._value: ObjectValueThermostat | None = None

    @property
    def device_class(self):
        return DEVICE_CLASS_TEMPERATURE
    
    @property
    def native_unit_of_measurement(self) -> str | None:
        return TEMP_CELSIUS

    @property
    def state_class(self):
        return STATE_CLASS_MEASUREMENT
    
    @property
    def native_value(self):
        return self._value.temperature if self._value is not None else None

    
    @property
    def unique_id(self) -> str | None:
        return "%s_%d_temp" % (self._server_serial, self._thermostat.id)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        extra_state_attributes = {}

        for attribute_name in OPTIONAL_TEMP_SENSOR_STATE_ATTRIBUTES:
            if attribute_name in self._thermostat.object_info:
                extra_state_attributes[attribute_name] = self._thermostat.object_info[attribute_name]
        return extra_state_attributes
    
    @property
    def device_info(self) -> DeviceInfo | None:
        device_info = {
            "identifiers": {(DOMAIN, self._thermostat.id)},
            "name": self.name,
        }

        if self._thermostat.room and self._thermostat.zone:
            device_info["suggested_area"] = self._thermostat.zone.name + " / " + self._thermostat.room.name.replace(
                self._thermostat.zone.name, '').strip()

        return device_info

    
    @property
    def name(self) -> str | None:
        return self._thermostat.name
    
    async def async_update(self):
        self._value = await self._thermostat.get_value()
