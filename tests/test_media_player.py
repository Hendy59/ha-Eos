"""The clock as a media player: state, volume and play_media travel over the command channel."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.helios import async_setup, identity
from custom_components.helios import media_player as media_player_module
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


def player_entity_id(hass: HomeAssistant) -> str:
    ids = hass.states.async_entity_ids("media_player")
    assert len(ids) == 1
    return ids[0]


async def test_state_and_volume_follow_the_clock(hass: HomeAssistant):
    entry = await setup(hass)
    coordinator = hass.data[DOMAIN]["entries"][entry.entry_id]
    entity_id = player_entity_id(hass)
    assert hass.states.get(entity_id).state == "unavailable", "no state snapshot yet"
    coordinator.set_state({"volume_percent": 40, "music_state": "playing", "voice_state": "idle"})
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "playing" and state.attributes["volume_level"] == 0.4
    assert state.attributes["supported_features"] & MediaPlayerEntityFeature.PLAY_MEDIA, "the clock is a playback target"
    coordinator.set_state({"volume_percent": 40, "music_state": "paused", "voice_state": "idle"})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "paused"


async def test_play_media_sends_announce_play_with_the_url(hass: HomeAssistant):
    entry = await setup(hass)
    coordinator = hass.data[DOMAIN]["entries"][entry.entry_id]
    coordinator.set_state({"volume_percent": 40, "music_state": "idle"})
    await hass.async_block_till_done()
    with patch.object(coordinator, "async_command", new=AsyncMock()) as command:
        await hass.services.async_call(
            "media_player",
            "play_media",
            {"entity_id": player_entity_id(hass), "media_content_type": "music", "media_content_id": "https://media.example.com/song.mp3"},
            blocking=True,
        )
    command.assert_awaited_once_with("announce.play", {"url": "https://media.example.com/song.mp3"})


async def test_play_media_resolves_media_source_urls(hass: HomeAssistant, monkeypatch):
    entry = await setup(hass)
    coordinator = hass.data[DOMAIN]["entries"][entry.entry_id]
    coordinator.set_state({"volume_percent": 40})
    await hass.async_block_till_done()
    monkeypatch.setattr(media_player_module, "async_resolve_media", AsyncMock(return_value=SimpleNamespace(url="https://media.example.com/resolved.mp3")))
    with patch.object(coordinator, "async_command", new=AsyncMock()) as command:
        await hass.services.async_call(
            "media_player",
            "play_media",
            {"entity_id": player_entity_id(hass), "media_content_type": "music", "media_content_id": "media-source://media_source/song.mp3"},
            blocking=True,
        )
    command.assert_awaited_once_with("announce.play", {"url": "https://media.example.com/resolved.mp3"})


async def test_play_media_refuses_urls_the_clock_cannot_play(hass: HomeAssistant):
    entry = await setup(hass)
    coordinator = hass.data[DOMAIN]["entries"][entry.entry_id]
    coordinator.set_state({"volume_percent": 40})
    await hass.async_block_till_done()
    with patch.object(coordinator, "async_command", new=AsyncMock()) as command, pytest.raises(HomeAssistantError, match="http"):
        await hass.services.async_call(
            "media_player",
            "play_media",
            {"entity_id": player_entity_id(hass), "media_content_type": "music", "media_content_id": "ftp://media.example.com/song.mp3"},
            blocking=True,
        )
    command.assert_not_awaited()
