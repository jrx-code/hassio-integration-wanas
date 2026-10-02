"""Serve the Wanas dashboard cards from the integration itself.

One HACS install then brings both the integration and its cards: the JavaScript is
served from this package and added to every dashboard, with no resource to add by hand.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARDS_FILE = "wanas-cards.js"
CARDS_URL = f"/{DOMAIN}_static/{CARDS_FILE}"
_REGISTERED = f"{DOMAIN}_cards_registered"


async def async_register_cards(hass: HomeAssistant) -> None:
    """Register the card module once per Home Assistant run.

    Frontend and HTTP are after_dependencies, not dependencies: a test harness or a
    headless install without them still sets the integration up, just without cards.
    """
    if hass.data.get(_REGISTERED):
        return
    if hass.http is None or "frontend" not in hass.config.components:
        _LOGGER.debug("Frontend not loaded, Wanas cards not registered")
        return

    # Imported here so the module loads in setups without the frontend component.
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415
    from homeassistant.components.http import StaticPathConfig  # noqa: PLC0415

    path = Path(__file__).parent / "www" / CARDS_FILE
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARDS_URL, str(path), cache_headers=False)]
    )
    # The version in the query string makes browsers fetch the new file after an update.
    integration = await async_get_integration(hass, DOMAIN)
    add_extra_js_url(hass, f"{CARDS_URL}?v={integration.version}")
    hass.data[_REGISTERED] = True
