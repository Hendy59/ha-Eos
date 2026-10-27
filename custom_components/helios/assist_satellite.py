"""The clock as an Assist satellite: Home Assistant sees it as a voice satellite and can announce on it."""

from __future__ import annotations

from homeassistant.components.assist_pipeline import PipelineEvent
from homeassistant.components.assist_satellite import (
    AssistSatelliteAnnouncement,
    AssistSatelliteConfiguration,
    AssistSatelliteEntity,
    AssistSatelliteEntityFeature,
)
from homeassistant.components.assist_satellite.entity import AssistSatelliteState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HeliosEntity

# the clock's voice_state values that map onto an Assist satellite state; "error" has none and makes the entity unavailable
_VOICE_STATES = {
    "idle": AssistSatelliteState.IDLE,
    "listening": AssistSatelliteState.LISTENING,
    "processing": AssistSatelliteState.PROCESSING,
    "responding": AssistSatelliteState.RESPONDING,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([HeliosSatellite(hass.data[DOMAIN]["entries"][entry.entry_id])])


class HeliosSatellite(HeliosEntity, AssistSatelliteEntity):
    """One per clock. The voice state is the clock's own; announcements travel over the command channel like every other command."""

    _attr_translation_key = "satellite"
    _attr_supported_features = AssistSatelliteEntityFeature.ANNOUNCE

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "satellite")

    @property
    def value(self):
        return self.coordinator.value("voice_state")

    @property
    def available(self) -> bool:
        return self.coordinator.available and self.value is not None and self.value != "error"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Mirror the clock's voice state; the base class owns the state property and persists it through _set_state."""
        mapped = _VOICE_STATES.get(self.coordinator.value("voice_state"))
        if mapped is not None and mapped != self.state:
            self._set_state(mapped)  # writes the HA state itself
            return
        super()._handle_coordinator_update()

    @callback
    def async_get_configuration(self) -> AssistSatelliteConfiguration:
        """Wake words live in the EOS app; Home Assistant neither lists nor sets them."""
        return AssistSatelliteConfiguration(available_wake_words=[], active_wake_words=[], max_active_wake_words=0)

    async def async_set_configuration(self, config: AssistSatelliteConfiguration) -> None:
        """Nothing to push: the clock manages its own wake words in the app."""

    @callback
    def on_pipeline_event(self, event: PipelineEvent) -> None:
        """The clock runs its pipelines itself (the connection event hands it the pipeline id); no audio streams through Home Assistant."""

    async def async_announce(self, announcement: AssistSatelliteAnnouncement) -> None:
        """Play a resolved announcement (TTS stream or media URL) on the clock; confirmed or it fails, never retried."""
        await self.coordinator.async_command("announce.play", {"url": announcement.media_id})
