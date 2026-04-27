import json
import os
import time

import adafruit_dht
import board
import paho.mqtt.client as mqtt

# =========================
# CONFIG
# =========================
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER = os.getenv("MQTT_USER", "techpm")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "homelab/pi5/dht22/metrics")

PUBLISH_INTERVAL = int(os.getenv("PUBLISH_INTERVAL", "10"))

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
