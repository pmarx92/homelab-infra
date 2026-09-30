import json
import os
import time

import adafruit_dht
import board
import paho.mqtt.client as mqtt

# =========================
# Konfiguration
# =========================
def require_env(name: str) -> str:
    """Variablen lesen, sonst mit Meldung abbrechen."""
    value = os.getenv(name)
    if not value:
        sys.exit(f"Fehlende Umgebungsvariable: {name}")
    return value


def int_env(name: str, default: str) -> int:
    """Int lesen, bei ungültigem Wert mit Meldung abbrechen."""
    raw = os.getenv(name, default)
    try:
        return int(raw)
    except ValueError:
        sys.exit(f"Ungültiger Wert für {name}: {raw!r} (erwartet: Ganzzahl)")


# Pflicht: umgebungsabhängig oder geheim
MQTT_HOST = require_env("MQTT_HOST")
MQTT_USER = require_env("MQTT_USER")
MQTT_PASSWORD = require_env("MQTT_PASSWORD")

# Optional: überall gleich, nicht geheim
MQTT_PORT = int_env("MQTT_PORT", "1883")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "homelab/pi5/dht22/metrics")
PUBLISH_INTERVAL = int_env("PUBLISH_INTERVAL", "10")

# =========================
# SENSOR SETUP
# =========================
dht_device = adafruit_dht.DHT22(board.D12)

# =========================
# MQTT SETUP
# =========================
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

def connect_mqtt():
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_start()
            print(f"Connected to MQTT Broker at {MQTT_HOST}:{MQTT_PORT}")
            return
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            time.sleep(5)

#PUBLISH FUNCTION
# =========================
def publish_data(temperature, humidity):
    payload = {
        "temperature": temperature,
        "humidity": humidity,
        "host": "pi5",
        "sensor": "dht22"
    }

    result = client.publish(
        MQTT_TOPIC,
        json.dumps(payload),
        qos=1
    )

    result.wait_for_publish()
    if result.rc == 0:
        print(f"Published: {payload}")
    else:
        print("Failed to publish message")

# =========================
# MAIN LOOP
# =========================
def main():
    connect_mqtt()

    while True:
        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity

            if temperature is not None and humidity is not None:
                publish_data(temperature, humidity)
            else:
                print("Sensor returned None")

        except RuntimeError as error:
            # typisch beim DHT22 (Timing issues)
            print(f"DHT22 read error: {error}")

        except Exception as error:
            print(f"Unexpected error: {error}")

        time.sleep(PUBLISH_INTERVAL)


if __name__ == "__main__":
    main()
