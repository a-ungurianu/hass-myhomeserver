from __future__ import annotations

from typing import Any, Mapping

import myhome.object
import voluptuous as vol
from myhome._gen.model.object_value_thermostat import ObjectValueThermostat

import homeassistant.helpers.config_validation as cv
from homeassistant.components.climate import ClimateEntity, TEMP_CELSIUS, PLATFORM_SCHEMA, SUPPORT_TARGET_TEMPERATURE
from homeassistant.components.climate.const import CURRENT_HVAC_HEAT, CURRENT_HVAC_OFF, HVAC_MODE_HEAT, HVAC_MODE_OFF
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

PARALLEL_UPDATES = 10

OPTIONAL_CLIMATE_STATE_ATTRIBUTES = [
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
        MyHomeServerThermostat(server_serial, thermostat)
        for thermostat in await hub.thermostats()
    ]

    if len(thermostats) > 0:
        async_add_entities(thermostats)

    return True


class MyHomeServerThermostat(ClimateEntity):
    def __init__(self, server_serial: str, thermostat: myhome.object.Thermostat):
        self._thermostat = thermostat
        self._server_serial = server_serial
        self._value: ObjectValueThermostat | None = None
    
    @property
    def temperature_unit(self) -> str | None:
        return TEMP_CELSIUS

    
    @property
    def current_temperature(self):
        return self._value.temperature if self._value is not None else None

    @property
    def target_temperature(self):
        return self._value.setpoint if self._value is not None and self._value.mode == "HOT" else None
    
    async def async_set_temperature(self, temperature=None, **kwargs) -> None:
        await self._thermostat.set_temperature(float(temperature))

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        await self._thermostat.set_mode("HOT" if hvac_mode == HVAC_MODE_HEAT else "OFF")

    @property
    def hvac_modes(self) -> list[str]:
        return [HVAC_MODE_HEAT, HVAC_MODE_OFF]

    @property
    def hvac_mode(self) -> str:
        return HVAC_MODE_HEAT

    @property
    def max_temp(self) -> float:
        return 25.0

    @property
    def min_temp(self) -> float:
        return 16.0

    @property
    def hvac_action(self) -> str | None:
        if self._value is not None:
            if self._value.mode == "HOT":
                return CURRENT_HVAC_HEAT
        return CURRENT_HVAC_OFF

    @property
    def supported_features(self) -> int:
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def unique_id(self) -> str | None:
        return "%s_%d_temp" % (self._server_serial, self._thermostat.id)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        extra_state_attributes = {}

        for attribute_name in OPTIONAL_CLIMATE_STATE_ATTRIBUTES:
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
