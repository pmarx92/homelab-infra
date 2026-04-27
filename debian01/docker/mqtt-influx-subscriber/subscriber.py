import json
import logging
import os
import time

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, UTC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger(__name__)

# MQTT
MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT"))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = os.getenv("MQTT_TOPIC")

# INFLUX
INFLUX_URL = os.getenv("INFLUX_URL")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET")

# Influx Client
influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

write_api = influx_client.write_api(write_options=SYNCHRONOUS)


def on_connect(client, userdata, flags, reason_code, properties):
    logger.info("Connected to MQTT Broker: %s", reason_code)
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode("utf-8"))

        logger.info("MQTT: %s", payload)

        point = (
            Point("dht22")
            .tag("host", payload.get("host", "unknown"))
            .tag("sensor", payload.get("sensor", "dht22"))
            .field("temperature", float(payload["temperature"]))
            .field("humidity", float(payload["humidity"]))
        )

        write_api.write(
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG,
            record=point
        )

        logger.info("→ Written to InfluxDB")
        update_health()

    except Exception as error:
        logger.exception("Error: %s", error)


def connect_with_retry(client):
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            return
        except Exception as error:
           logger.exception("MQTT connection failed: %s", error)
           time.sleep(5)


def update_health():
    with open("/health/status", "w") as f:
        f.write(datetime.now(UTC).isoformat())



client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

client.on_connect = on_connect
client.on_message = on_message

connect_with_retry(client)
client.loop_forever()
