"""MQTT client factory shared by all services."""

from __future__ import annotations

import uuid

import paho.mqtt.client as mqtt


def create_client(client_name: str) -> mqtt.Client:
    """Create a paho MQTT client with a readable unique client id."""
    # Unique ids avoid collisions when multiple copies of a service run while experimenting.
    client_id = f"sensor-platform-{client_name}-{uuid.uuid4().hex[:8]}"
    return mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
    )
