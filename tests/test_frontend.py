"""The integration serves its own dashboard cards."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.wanas.frontend import CARDS_URL, async_register_cards


async def test_cards_are_skipped_without_the_frontend(hass: HomeAssistant) -> None:
    """A headless or test setup has no frontend; setup must not fail over it."""
    with patch("homeassistant.components.frontend.add_extra_js_url") as add_js:
        await async_register_cards(hass)
    add_js.assert_not_called()


async def test_cards_are_served_and_added_to_every_dashboard(hass: HomeAssistant) -> None:
    hass.http = MagicMock()
    hass.http.async_register_static_paths = AsyncMock()
    hass.config.components.add("frontend")

    with patch("homeassistant.components.frontend.add_extra_js_url") as add_js:
        await async_register_cards(hass)
        await async_register_cards(hass)  # a second entry must not register twice

    (config,) = hass.http.async_register_static_paths.call_args.args[0]
    assert config.url_path == CARDS_URL
    assert Path(config.path).is_file()
    assert config.cache_headers is False
    add_js.assert_called_once()
    url = add_js.call_args.args[1]
    assert url.startswith(f"{CARDS_URL}?v=")
