"""The clock as an Assist satellite: registered per clock, the voice state mirrored, announce sent over the command channel."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.assist_satellite.const import DATA_COMPONENT
from homeassistant.components.assist_satellite.entity import AssistSatelliteState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.helios import async_setup, identity
from custom_components.helios.const import DOMAIN

INSTALLATION = "0f3c1b2a-9d8e-4c7b-a6f5-1e2d3c4b5a69"


async def setup(hass: HomeAssistant) -> MockConfigEntry:
    assert await async_setup_component(hass, "http", {})
    assert await async_setup(hass, {})
    user_id, _token = await identity.async_create_identity(hass, INSTALLATION)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=INSTALLATION, data={"installation_id": INSTALLATION, "user_id": user_id, "app_version": "0.19.0", "version_code": 33, "music_assistant": None})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    return entry


def satellite_entity_id(hass: HomeAssistant) -> str:
    ids = hass.states.async_entity_ids("assist_satellite")
    assert len(ids) == 1
    return ids[0]


async def test_satellite_is_registered_on_the_clock_device_with_a_stable_unique_id(hass: HomeAssistant):
    await setup(hass)
    entity_id = satellite_entity_id(hass)
    entity_entry = er.async_get(hass).async_get(entity_id)
    assert entity_entry is not None
    assert entity_entry.platform == DOMAIN and entity_entry.domain == "assist_satellite"
    assert entity_entry.unique_id == f"{INSTALLATION}_satellite"
    device = dr.async_get(hass).async_get(entity_entry.device_id)
    assert device is not None and device.identifiers == {(DOMAIN, INSTALLATION)}


async def test_satellite_state_mirrors_the_clock_voice_state(hass: HomeAssistant):
    entry = await setup(hass)
    coordinator = hass.data[DOMAIN]["entries"][entry.entry_id]
    entity_id = satellite_entity_id(hass)
    assert hass.states.get(entity_id).state == "unavailable", "no voice state yet"
    for voice_state in ("idle", "listening", "processing", "responding", "idle"):
        coordinator.set_state({"voice_state": voice_state})
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == voice_state, voice_state
    coordinator.set_state({"voice_state": "error"})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "unavailable", "the clock's error state has no satellite state"


async def test_announce_sends_announce_play_with_the_resolved_url(hass: HomeAssistant):
    entry = await setup(hass)
    coordinator = hass.data[DOMAIN]["entries"][entry.entry_id]
    coordinator.set_state({"voice_state": "idle"})
    await hass.async_block_till_done()
    entity_id = satellite_entity_id(hass)
    with patch.object(coordinator, "async_command", new=AsyncMock()) as command:
        await hass.services.async_call(
            "assist_satellite",
            "announce",
            {"entity_id": entity_id, "media_id": "https://media.example.com/bell.mp3", "preannounce": False},
            blocking=True,
        )
    command.assert_awaited_once_with("announce.play", {"url": "https://media.example.com/bell.mp3"})
    assert hass.states.get(entity_id).state == "idle", "announce leaves the satellite idle again"


async def test_configuration_is_empty_and_pipeline_events_are_ignored(hass: HomeAssistant):
    await setup(hass)
    entity = hass.data[DATA_COMPONENT].get_entity(satellite_entity_id(hass))
    config = entity.async_get_configuration()
    assert config.available_wake_words == [] and config.active_wake_words == [] and config.max_active_wake_words == 0
    await entity.async_set_configuration(config)  # no-op: wake words live in the EOS app
    entity.on_pipeline_event(None)  # the clock runs its pipelines itself
    assert entity.state == AssistSatelliteState.IDLE
