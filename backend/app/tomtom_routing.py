from __future__ import annotations

import os
import httpx

TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY", "")
TOMTOM_ROUTING_URL = "https://api.tomtom.com/routing/1/calculateRoute"


class TomTomRoutingError(Exception):
    """Raised when the TomTom Routing API call fails or returns no route."""


async def get_route_with_geometry(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> dict:
    """
    Call TomTom's calculateRoute endpoint with live traffic enabled.

    Returns:
        {
            "distance_km": float,
            "duration_minutes": int,
            "traffic_delay_minutes": int,
            "route_geometry": [{"latitude": float, "longitude": float}, ...],
        }

    Raises:
        TomTomRoutingError on missing API key, request failure, or empty
        route results.
    """
    if not TOMTOM_API_KEY:
        raise TomTomRoutingError("TOMTOM_API_KEY environment variable is not set.")

    url = f"{TOMTOM_ROUTING_URL}/{origin_lat},{origin_lng}:{dest_lat},{dest_lng}/json"
    params = {
        "key": TOMTOM_API_KEY,
        "traffic": "true",
        "routeType": "fastest",
        "travelMode": "car",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise TomTomRoutingError(f"TomTom routing request failed: {exc}") from exc

    routes = data.get("routes") or []
    if not routes:
        raise TomTomRoutingError("TomTom returned no routes for the given origin/destination.")

    route = routes[0]
    summary = route.get("summary", {})

    geometry: list[dict[str, float]] = []
    for leg in route.get("legs", []):
        for point in leg.get("points", []):
            geometry.append({
                "latitude": point["latitude"],
                "longitude": point["longitude"],
            })

    if not geometry:
        raise TomTomRoutingError("TomTom route contained no geometry points.")

    return {
        "distance_km": round(summary.get("lengthInMeters", 0) / 1000, 2),
        "duration_minutes": round(summary.get("travelTimeInSeconds", 0) / 60),
        "traffic_delay_minutes": round(summary.get("trafficDelayInSeconds", 0) / 60),
        "route_geometry": geometry,
    }


def classify_congestion(distance_km: float, duration_minutes: float, traffic_delay_minutes: int) -> dict:
    """
    Derive a simple congestion level/percentage from TomTom's traffic delay.

    This is a placeholder heuristic -- swap with D2STGNN-derived congestion
    once the event-aware fusion output is wired into this endpoint.
    """
    free_flow_minutes = max(duration_minutes - traffic_delay_minutes, 1)
    delay_ratio = traffic_delay_minutes / free_flow_minutes

    if delay_ratio >= 0.5:
        level = "Heavy"
    elif delay_ratio >= 0.15:
        level = "Moderate"
    else:
        level = "Low"

    percentage = min(round(delay_ratio * 100, 1), 100.0)
    return {"level": level, "percentage": percentage}
