from custom_components.helios import async_setup
from custom_components.helios.const import DOMAIN


async def test_setup_registers_both_views_once(hass):
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "http", {})  # the bare hass fixture has no http app
    assert await async_setup(hass, {})
    assert await async_setup(hass, {})
    routes = [(r.method, r.resource.canonical) for r in hass.http.app.router.routes()]  # HA registers routes without names
    assert routes.count(("GET", "/api/helios/appearance/{entry_id}/{image_id}")) == 1
    assert routes.count(("GET", "/api/helios/pair")) == 1 and routes.count(("POST", "/api/helios/pair")) == 1
    assert hass.data[DOMAIN]["views_registered"] is True


def _clock_entry(app_version):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    return MockConfigEntry(domain=DOMAIN, data={"installation_id": "0f3c1b2a-9d8e-4c7b-a6f5-1e2d3c4b5a69", "user_id": "u", "app_version": app_version, "version_code": 29})


async def test_app_update_issue_when_github_release_is_newer(hass, aioclient_mock):
    from homeassistant.helpers import issue_registry as ir
    from homeassistant.setup import async_setup_component

    from custom_components.helios import const

    _clock_entry("0.9.1").add_to_hass(hass)
    aioclient_mock.get(const.LATEST_APP_RELEASE_API, json={"tag_name": "v0.20.0"})
    assert await async_setup_component(hass, "http", {})
    assert await async_setup(hass, {})
    await hass.async_block_till_done()
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "app_update")
    assert issue is not None and issue.translation_key == "app_update"
    assert issue.translation_placeholders == {"latest": "0.20.0", "current": "0.9.1"}
    assert issue.learn_more_url == const.APP_RELEASES_URL


async def test_no_app_update_issue_when_clocks_run_the_latest(hass, aioclient_mock):
    from homeassistant.helpers import issue_registry as ir
    from homeassistant.setup import async_setup_component

    from custom_components.helios import const

    _clock_entry("0.20.0").add_to_hass(hass)
    aioclient_mock.get(const.LATEST_APP_RELEASE_API, json={"tag_name": "v0.20.0"})
    assert await async_setup_component(hass, "http", {})
    assert await async_setup(hass, {})
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, "app_update") is None


async def test_app_update_check_skips_the_request_until_a_clock_reported(hass, aioclient_mock):
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "http", {})
    assert await async_setup(hass, {})
    await hass.async_block_till_done()
    assert not aioclient_mock.mock_calls


async def test_app_update_check_survives_github_errors(hass, aioclient_mock):
    from homeassistant.helpers import issue_registry as ir
    from homeassistant.setup import async_setup_component

    from custom_components.helios import const

    _clock_entry("0.9.1").add_to_hass(hass)
    aioclient_mock.get(const.LATEST_APP_RELEASE_API, exc=OSError("offline"))
    assert await async_setup_component(hass, "http", {})
    assert await async_setup(hass, {})
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, "app_update") is None
