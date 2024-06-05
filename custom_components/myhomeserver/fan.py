from __future__ import annotations

from typing import Any, Mapping, Optional

import myhome.object
import voluptuous as vol
from myhome._gen.model.object_value_fancoil import ObjectValueFancoil

import homeassistant.helpers.config_validation as cv

from homeassistant.components.fan import FanEntity, FanEntityFeature, PLATFORM_SCHEMA

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

from homeassistant.util.percentage import ordered_list_item_to_percentage, percentage_to_ordered_list_item

PARALLEL_UPDATES = 10

OPTIONAL_FAN_STATE_ATTRIBUTES = [
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
    """Set up MyHomeSERVER fans from a config entry."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    server_serial = await hub.get_server_serial()
    fans = [
        MyHomeServerFanCoil(server_serial, fan)
        for fan in await hub.fans()
    ]

    if len(fans) > 0:
        async_add_entities(fans)

    return True

ORDERED_NAMED_FAN_SPEEDS = [1, 2, 3]  # off is not included


def myhomeserver_to_hass_brightness(value: int):
    """Convert MyHomeSERVER brightness (0..100) to hass format (0..255)"""
    return int((value / 100.0) * 255)


def hass_to_myhomeserver_brightness(value: int):
    """Convert hass brightness (0..100) to MyHomeSERVER format (0..255)"""
    return int((value / 255.0) * 100)

class MyHomeServerFanCoil(FanEntity):
    def __init__(self, server_serial: str, fan: myhome.object.Fancoil):
        self._fan = fan
        self._server_serial = server_serial
        self._value: ObjectValueFancoil | None = None
    
    @property
    def name(self) -> str | None:
        return self._fan.name

    @property
    def supported_features(self) -> int:
        return FanEntityFeature.SET_SPEED

    @property
    def unique_id(self) -> str | None:
        return "%s_%d" % (self._server_serial, self._fan.id)

    @property
    def device_info(self) -> DeviceInfo | None:
        device_info = {
            "identifiers": {(DOMAIN, self._fan.id)},
            "name": self.name,
        }

        if self._fan.room and self._fan.zone:
            device_info["suggested_area"] = self._fan.zone.name + " / " + self._fan.room.name.replace(
                self._fan.zone.name, '').strip()

        return device_info

    
    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        extra_state_attributes = {}

        for attribute_name in OPTIONAL_FAN_STATE_ATTRIBUTES:
            if attribute_name in self._fan.object_info:
                extra_state_attributes[attribute_name] = self._fan.object_info[attribute_name]
        return extra_state_attributes
    
    @property
    def is_on(self) -> bool:
        return self._value is not None and self._value.power

    @property
    def percentage(self) -> Optional[int]:
        """Return the current speed percentage."""
        return ordered_list_item_to_percentage(ORDERED_NAMED_FAN_SPEEDS, int(self._value.fan)) if self._value is not None else None

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        fan_strength = percentage_to_ordered_list_item(ORDERED_NAMED_FAN_SPEEDS, percentage)
        await self._fan.set_fan_speed(float(fan_strength))

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return len(ORDERED_NAMED_FAN_SPEEDS)

    async def async_turn_on(self, percentage: Optional[int] = None, **kwargs: Any) -> None:
        if percentage:
            await self.async_set_percentage(percentage)
        else:
            await self._fan.switch_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._fan.switch_off()

    async def async_update(self):
        self._value = await self._fan.get_value()

