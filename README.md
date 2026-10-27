# EOS - Home Assistant integration for the Lenovo Smart Clock 2

Home Assistant side of [EOS](https://github.com/SychPL/helios), an Android
app that turns a Lenovo Smart Clock 2 into a Home Assistant dashboard and voice
satellite. The clock connects to Home Assistant over its own WebSocket
connection; this integration registers the device and its entities, pairs the
clock with a six-digit code and hands it everything it needs to run.

No pip dependencies, push only (`iot_class: local_push`).

## What you get

| Entity | Source on the clock |
| --- | --- |
| `sensor` App version (diagnostic) | the EOS APK version |
| `sensor` Voice state | idle / listening / processing / responding / error |
| `sensor` Dock version (diagnostic) | firmware of the charging dock |
| `binary_sensor` Dock connected | the OEM dock listener |
| `binary_sensor` Phone charging | Qi charging listener; unavailable without a dock |
| `light` Dock lamp | on/off read from the OEM service, brightness 1-10 |
| `number` Device volume | `STREAM_MUSIC` 0-100 %, polled every 3 s |
| `media_player` Clock speaker | the same device volume as a player (`volume_set` / `volume_step` only), so Assist understands "louder" in the clock's area; music itself is a separate Music Assistant player |
| `assist_satellite` Satellite | the clock registered as a voice satellite: its voice state (idle / listening / processing / responding) and `announce` playback of a TTS or media URL on the clock |

The satellite entity is how Home Assistant sees the clock as a voice device: it
appears in the voice assistant settings and accepts
`assist_satellite.announce`. Home Assistant resolves the announcement to a
signed TTS stream or media URL and the clock plays it (`announce.play`, like
every command confirmed or failed, never retried; an EOS app that does not
know the command fails the service call).

The device carries the clock's stable installation id, so the area you assign in
Home Assistant becomes the room context of every voice command (the `device_id`
passed to `assist_pipeline/run`).

## Install

1. HACS -> Integrations -> three-dot menu -> **Custom repositories** -> add this
   repository's URL, category *Integration*.
2. Install **EOS** and restart Home Assistant.
3. On the clock (EOS 0.9.0 or newer): hold EOS -> **Paruj z HA** (Pair
   with HA) -> pick your Home Assistant from the mDNS list or type its address.
4. Settings -> Devices and services -> **Add integration** -> EOS. Home
   Assistant shows a six-digit code valid for five minutes. Leave that dialog
   open - it is what finishes the pairing.
5. On the clock tap **Dalej** (Next) and type the code. The clock receives its
   own Home Assistant token, and if the Music Assistant integration is present,
   music access too.
6. Assign the device to an area.

Pairing the same clock again refreshes the existing entry: a new user and token,
and the old ones are removed only once the new pairing succeeded.

## Security model

This integration creates a Home Assistant user and mints a token from an
endpoint that is **not authenticated**, so it is worth stating exactly what that
means before you install it.

- **What is created.** On a successful pairing the integration creates one Home
  Assistant user per clock: system-generated, **not an administrator**,
  `local_only` (it cannot be used from outside your LAN), in the plain users
  group. Its token is a system token with a ten-year expiry. That token is the
  only credential the clock ever holds; you never paste a long-lived admin token
  into the device.
- **Who may pair.** `POST /api/helios/pair` is unauthenticated because a clock
  that has never been paired has no credential to authenticate with. It only
  accepts a six-digit code that **you** generated in the Home Assistant UI
  moments earlier and that is valid for five minutes. Five wrong codes from one
  address block that address for five minutes. Error responses are uniform and
  reveal nothing; neither the code nor the token is ever logged.
- **What the clock can do with it.** The device channel accepts connections from
  that user only, and the command allowlist is closed: `lamp.turn_on`,
  `lamp.turn_off`, `lamp.set_brightness`, `audio.set_device_volume`,
  `music.play`, `music.pause`, `music.stop`, `announce.play`. Home
  Assistant waits up to 10 s for a confirmation and never retries.
- **Removal cleans up.** Deleting the config entry deletes the clock's user, its
  Music Assistant token and its stored background image. The clock notices,
  stops reconnecting and asks to be paired again.
- **Music Assistant credentials.** The integration reads the address and token
  of the core `music_assistant` config entry in order to mint a separate token
  for the clock (it shows up in Music Assistant's own token list). This is a
  deliberate cross-integration read of another entry's data; if you would rather
  it did not, leave Music Assistant out and the clock simply runs without music.
  When Music Assistant runs as an add-on it refuses to mint a usable token at
  all, and you paste one yourself in the options - see below.

## Protocol

The WebSocket channel (`helios/connect`, `helios/state`, `helios/result`), the
pairing exchange (`GET`/`POST /api/helios/pair`) and the `connection` event are
described in **[docs/PROTOCOL.md](docs/PROTOCOL.md)**.

## Behaviour

- Entities stay unavailable until the clock sends its first snapshot;
  a dropped socket marks them `unavailable` with no extra heartbeats.
- Commands are confirmed or they fail: a second command for the same resource
  while the first is in flight gets `busy`.
- Music Assistant as an add-on authenticates Home Assistant as a system user,
  and Music Assistant refuses such tokens on its LAN web server. Paste a token
  once in Settings -> Devices and services -> EOS -> Configure -> *Music
  Assistant token for the clock*. It is stored as given, never verified, never
  revoked, and changing it refreshes music on the clock's next connect.
  A clock paired later takes the token already pasted for another clock, so it
  plays music from the start. A clock left without music while Music Assistant
  runs shows up in Settings -> Repairs.

## Clock appearance

Settings -> Devices and services -> EOS -> the clock -> **Configure**: theme
(warm graphite / night blue), background (theme colour, keep the current photo,
or upload a new JPEG/PNG up to 10 MB), dimming 35-80 % and a focus point, plus
the Sendspin, diagnostics and Music Assistant overrides.

An uploaded photo is normalised in Home Assistant (EXIF orientation applied,
metadata stripped, transparency flattened, bounded to 1600x960, JPEG under
2 MB) and stored privately in `config/helios/<entry_id>/`. The clock fetches it
with an authenticated `GET /api/helios/appearance/<entry_id>/<image_id>`, which
serves only the current image and only to that clock's user or an administrator.

## Dashboard editor

The sidebar entry **EOS** (administrators only) is a visual editor for the
clock's layout: a 4x3 canvas, pages, one form per card. Click an empty cell to
add a card, click a card to edit or delete it. Entity and icon pickers are Home
Assistant's own (`ha-form`); if they fail to load the panel falls back to plain
inputs with a datalist of your entities. The editor validates with the clock's
own rules and wording, so a layout it accepts is a layout the clock accepts.

The editor has one tab per paired clock, named after its Home Assistant device,
and each tab edits the dashboard that clock shows. Every clock starts on the
shared `helios-clock`; **Own dashboard** on a tab copies the current document
into a new hidden dashboard (`helios-<clock name>`) and switches that clock to
it on the spot, without a restart. The path is stored with the clock's config
entry and sent to the app in the `connection` event.

The card list includes **Energy (PV, house, battery)** (`energy`, EOS 0.14 or newer on the clock): PV
production and house load on top, the battery charge large under it; without a battery sensor the
production / load pair is the value.

**Thermostat** (`climate`, EOS 0.16 or newer): the measured temperature large, the setpoint under it; on the
clock a tap opens the full control panel (setpoint, mode, preset, fan, swing).

**Readings (1–3 entities)** (`entities`): one to three ordered rows, each with an entity and an optional short
label. Select the entities in the card's list editor; any HA entity domain is accepted. Numeric states use at most
one decimal place and their HA units; a missing, unknown or unavailable value shows `—` without hiding the other
rows. The card displays values only. Its title defaults to `Odczyty`, and its header icon to
`mdi:format-list-bulleted`. Update the clock to EOS 0.19 or newer before saving this card; older clocks reject the
document and retain their previous layout. The dashboard schema stays at version 6. Drag list entries by their
handles to change the display order.

**Alerts** (`alerts`, EOS 0.17 or newer): every warning in one 1x1, 1x2 or 2x1 tile - the count and the newest
few; on the clock a tap slides in the full list with "active since" times and an optional "turn off lights" button.
Each source is a text entity plus a condition (`when`); an optional stand-in card (`empty`: energy, climate, weather,
clock or tile) takes the tile's place while everything is known and nothing applies.

It edits the `helios` section of a storage-mode dashboard through the frontend's
`lovelace/config` and `lovelace/config/save` commands; everything else in that
dashboard is left untouched. Before saving it re-reads the dashboard and
refuses to overwrite a version changed elsewhere in the meantime. A document in
schema 2-5 loads as one page and is upgraded to schema 6 on the first save -
that needs EOS 0.12 on the clock; an older clock rejects the new document
and keeps its previous layout. The JavaScript is public (no secrets in it); the
only mutation path is `lovelace/config/save`, which Home Assistant gates to
administrators.
# EOS — Home Assistant Integration for Lenovo Smart Clock 2

EOS is a custom [Home Assistant](https://www.home-assistant.io/) integration for the [Helios/EOS Android app](https://github.com/SychPL/helios). It turns a Lenovo Smart Clock 2 into a Home Assistant dashboard and voice satellite.

The clock communicates with Home Assistant through a local WebSocket connection. The integration handles pairing, device registration, entities, voice commands, dashboard configuration, appearance settings, and optional Music Assistant support.

> **Status:** This integration is designed for local use with Home Assistant and is distributed through HACS as a custom repository.

## Features

- Local push communication over WebSocket
- Six-digit pairing code generated by Home Assistant
- Home Assistant device and area registration
- Voice-state and diagnostic sensors
- Dock and charging binary sensors
- Dock lamp control with brightness support
- Device volume control, media-player support (volume, transport, play_media) and an Assist voice satellite with announcements
- EOS dashboard editor in the Home Assistant sidebar
- Per-clock dashboards and shared dashboards
- Custom themes, backgrounds, dimming, and focus-point settings
- Automatic Music Assistant integration (token minted and pushed to the clock, also when Music Assistant starts later)
- Support for dashboard cards including:
  - Energy
  - Thermostat
  - Readings
  - Alerts

The integration has no additional Python runtime dependencies.

## Entities

| Platform | Entity | Description |
| --- | --- | --- |
| `sensor` | App version | EOS application version on the clock |
| `sensor` | Voice state | Idle, listening, processing, responding, or error |
| `sensor` | Dock version | Charging-dock firmware version |
| `binary_sensor` | Dock connected | Whether the OEM dock is connected |
| `binary_sensor` | Phone charging | Qi charging status; requires a dock |
| `light` | Dock lamp | On/off control and brightness from 1–10 |
| `number` | Device volume | `STREAM_MUSIC` volume from 0–100% |
| `media_player` | Clock speaker | Volume, transport and play_media (TTS, media, Music Assistant streams) for Home Assistant Assist and the media browser |
| `assist_satellite` | Satellite | Voice satellite: mirrors the clock's voice state and accepts announcements |

Entities remain unavailable until the clock sends its first state snapshot. If the WebSocket connection is lost, the integration marks the entities unavailable.

## Requirements

- Home Assistant
- A Lenovo Smart Clock 2
- The EOS/Helios Android app installed on the clock
- EOS 0.9.0 or newer for pairing
- HACS, or manual installation as a custom integration

Some dashboard cards require newer EOS versions:

- Energy: EOS 0.14 or newer
- Thermostat: EOS 0.16 or newer
- Alerts: EOS 0.17 or newer
- Readings: EOS 0.19 or newer

## Installation with HACS

1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Open the three-dot menu and select **Custom repositories**.
4. Add this repository URL:

   `https://github.com/Hendy59/ha-Eos`

5. Select **Integration** as the category.
6. Install **EOS**.
7. Restart Home Assistant.

## Pairing the Clock

1. On the clock, open EOS and select **Pair with HA** (`Paruj z HA`).
2. Select Home Assistant from the mDNS list or enter its address manually.
3. In Home Assistant, open **Settings → Devices & services**.
4. Select **Add integration** and choose **EOS**.
5. Home Assistant displays a six-digit pairing code valid for five minutes.
6. On the clock, tap **Next** (`Dalej`) and enter the code.
7. Assign the new device to an area.

The device's assigned Home Assistant area is used as the room context for voice commands. Pairing the same clock again refreshes its existing credentials after the new pairing succeeds.

## Security

The pairing endpoint is intentionally unauthenticated because a new clock does not yet have credentials. It accepts only a short-lived six-digit code generated in the Home Assistant interface.

After pairing, the integration creates a dedicated Home Assistant user for the clock:

- The user is not an administrator.
- The user is restricted to the local network.
- The clock receives its own long-lived system token.
- The token is not an administrator token.
- The device connection accepts only the commands required by the clock.
- Pairing codes expire after five minutes.
- Repeated invalid attempts are rate-limited.
- Pairing codes and tokens are not written to the logs.

Removing the EOS config entry also removes the clock user, Music Assistant token, and stored background image associated with that device.

For the complete protocol and security details, see [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Dashboard Editor

The **EOS** sidebar panel is available to Home Assistant administrators. It provides a visual editor for the clock layout:

- 4×3 dashboard canvas
- Multiple pages
- Entity and icon selectors
- Add, edit, move, and delete cards
- Shared dashboards or a separate dashboard for each clock
- Validation using the same rules as the EOS application

The editor modifies only the `helios` section of a storage-mode Lovelace dashboard. Other dashboard content is preserved.

## Appearance Configuration

Open **Settings → Devices & services → EOS → Configure** to change:

- Theme
- Background image
- Dimming level
- Image focus point
- Sendspin settings
- Diagnostics
- Music Assistant options

Uploaded images are processed locally by Home Assistant. EXIF orientation is applied, metadata is removed, transparency is flattened, and the image is resized before being stored privately.

## Music Assistant

Music Assistant support is optional and automatic. When a Music Assistant integration is loaded, EOS mints a separate token for the clock and pushes the Music Assistant address, token and Sendspin address to it. This also happens when Music Assistant starts later (an add-on that boots after Home Assistant) or is installed while a clock is already connected: the clock then connects to Music Assistant on its own and appears there as a player.

The clock is also a media player in Home Assistant: `media_player.play_media` plays TTS, media files and Music Assistant streams on it.

If Music Assistant runs as an add-on and cannot issue a usable token automatically, provide a token through:

**Settings → Devices & services → EOS → Configure → Music Assistant token for the clock**

The token is stored as provided and is sent to the clock when it connects.

## Protocol Documentation

The WebSocket channels, pairing exchange, connection event, and command flow are documented in [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Development

Install the test dependencies:

```bash
pip install -r requirements_test.txt
```

Run the Python tests:

```bash
python -m pytest tests
```

Run the JavaScript panel tests:

```bash
node --test tests/panel/schema.test.mjs
```

The project uses Python 3.14 for development. GitHub Actions runs the Home Assistant and HACS validation checks, Python tests, JavaScript tests, and an import check.

Translations are stored in:

- `strings.json` — English
- `translations/pl.json` — Polish

The Polish README is available as [README.pl.md](README.pl.md).

## License

This project is licensed under the **MIT License**.

Copyright © 2026 Mateusz Sych.

See the complete license text in [LICENSE](LICENSE).
