from __future__ import annotations

from typing import Any, Mapping

import myhome.object
import voluptuous as vol
from myhome._gen.model.object_value_shutter import ObjectValueShutter

import homeassistant.helpers.config_validation as cv
from homeassistant.components.cover import CoverEntity, CoverEntityFeature, CoverDeviceClass, PLATFORM_SCHEMA, STATE_CLOSING, STATE_OPENING
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

PARALLEL_UPDATES = 10

OPTIONAL_COVER_SENSOR_STATE_ATTRIBUTES = [
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
    blinds = [
        MyHomeServerBlind(server_serial, blind)
        for blind in await hub.blinds()
    ]

    if len(blinds) > 0:
        async_add_entities(blinds)

    return True


class MyHomeServerBlind(CoverEntity):
    def __init__(self, server_serial: str, thermostat: myhome.object.Shutter):
        self._blind = thermostat
        self._server_serial = server_serial
        self._value: ObjectValueShutter | None = None

    @property
    def device_class(self):
        return CoverDeviceClass.BLIND
    
    @property
    def supported_features(self) -> int:
        return CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    
    @property
    def native_value(self):
        return self._value.temperature if self._value is not None else None

    
    @property
    def unique_id(self) -> str | None:
        return "%s_%d_temp" % (self._server_serial, self._blind.id)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        extra_state_attributes = {}

        for attribute_name in OPTIONAL_COVER_SENSOR_STATE_ATTRIBUTES:
            if attribute_name in self._blind.object_info:
                extra_state_attributes[attribute_name] = self._blind.object_info[attribute_name]
        return extra_state_attributes
    
    @property
    def device_info(self) -> DeviceInfo | None:
        device_info = {
            "identifiers": {(DOMAIN, self._blind.id)},
            "name": self.name,
        }

        if self._blind.room and self._blind.zone:
            device_info["suggested_area"] = self._blind.zone.name + " / " + self._blind.room.name.replace(
                self._blind.zone.name, '').strip()

        return device_info

    @property
    def state(self) -> str | None:
        if self._value is not None:
            if self._value.move == 'DOWN':
                return STATE_CLOSING
            if self._value.move == 'UP':
                return STATE_OPENING
        return None
    
    @property
    def name(self) -> str | None:
        return self._blind.name
    
    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        return await self._blind.move_up()

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        return await self._blind.move_down()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        return await self._blind.move_stop()

    async def async_update(self):
        self._value = await self._blind.get_value()
