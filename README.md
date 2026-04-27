# Multi-Node Homelab Infrastructure

[![Architecture](https://img.shields.io/badge/Architecture-Hybrid%20Edge-blue)](#)
[![Stack](https://img.shields.io/badge/Stack-Docker%20|%20MQTT%20|%20InfluxDB%20|%20Grafana-orange)](#)
[![Python](https://img.shields.io/badge/Python-3.13-blue)](#)

Dieses Repository dokumentiert den Aufbau und die Automatisierung meiner privaten Infrastruktur. Es dient als Proof of Concept für ein hybrides Monitoring-System, das Sensordaten von einem Edge-Device (Raspberry Pi 5) sicher an einen zentralen Server (Debian 13) übermittelt, dort persistiert und visualisiert.

---

## 🏗 System-Architektur

```
┌─────────────────────────────┐          ┌──────────────────────────────────────┐
│   Edge Layer                │          │   Central Services                   │
│   Raspberry Pi 5            │          │   Debian 13 (Trixie)                 │
│                             │          │                                      │
│  ┌───────────────────────┐  │          │  ┌────────────────────────────────┐  │
│  │  DHT22 Publisher      │  │  MQTT    │  │  mqtt-influx-subscriber        │  │
│  │  Python · GPIO Pin 12 │──┼──────────┼─▶│  Python · Paho-MQTT            │  │
│  │  10s Publish-Intervall│  │  :1883   │  │  Validierung & Ingestion       │  │
│  └───────────────────────┘  │          │  └───────────────┬────────────────┘  │
│                             │          │                  │ HTTP              │
│  ┌───────────────────────┐  │          │                  ▼                   │
│  │  Mosquitto Broker     │  │          │  ┌────────────────────────────────┐  │
│  │  eclipse-mosquitto:2  │  │          │  │  InfluxDB 2.x  · Port 8086     │  │
│  │  Auth: Password-File  │  │          │  │  Bucket: sensors               │  │
│  └───────────────────────┘  │          │  └───────────────┬────────────────┘  │
└─────────────────────────────┘          │                  │ Datasource        │
                                         │                  ▼                   │
                                         │  ┌────────────────────────────────┐  │
                                         │  │  Grafana  · Port 3000          │  │
                                         │  │  Echtzeit-Dashboard            │  │
                                         │  └────────────────────────────────┘  │
                                         └──────────────────────────────────────┘
```

Das Setup ist in zwei logische Ebenen unterteilt:

**Edge Layer (Raspberry Pi 5)** erfasst Umgebungsdaten via GPIO und stellt einen lokalen MQTT-Broker als Kommunikationsschnittstelle bereit. Alle Dienste laufen containerisiert unter Docker Compose.

**Central Services (Debian 13)** empfangen die MQTT-Nachrichten, validieren und persistieren sie in InfluxDB und stellen sie über Grafana als Echtzeit-Dashboard bereit.

---

## 🛠 Tech Stack

| Bereich | Technologien |
| :--- | :--- |
| **OS** | Debian 13 (Trixie), Raspberry Pi OS Lite (64-bit) |
| **Runtime** | Docker Engine, Docker Compose |
| **Sprache** | Python 3.13 |
| **Bibliotheken** | adafruit-circuitpython-dht, Paho-MQTT, InfluxDB-Client |
| **Messaging** | MQTT · Eclipse Mosquitto 2 |
| **Storage** | InfluxDB 2.7 |
| **Visualization** | Grafana |

---

## 🗂 Verzeichnisstruktur

```
homelab-infra/
├── README.md                          # Diese Datei
│
├── raspberry_pi/                      # Edge Node
│   ├── docs/
│   │   └── README.md                 # Setup-Dokumentation Pi
│   └── docker/
│       ├── mosquitto/                 # MQTT Broker
│       │   ├── config/mosquitto.conf
│       │   └── docker-compose.yml
│       └── dht22_sensor/             # Sensor-Publisher
│           ├── Dockerfile
│           ├── docker-compose.yml
│           ├── mqtt_publisher.py
│           ├── humidity.py            # Flask-Endpunkt (experimentell)
│           └── requirements.txt
│
└── debian01/                          # Central Node
    ├── docs/
    │   └── README.md                 # Setup-Dokumentation Debian
    └── docker/
        ├── influxdb/                  # InfluxDB + Grafana
        │   └── docker-compose.yml
        └── mqtt-influx-subscriber/   # MQTT → InfluxDB Bridge
            ├── Dockerfile
            ├── docker-compose.yml
            ├── subscriber.py
            └── requirements.txt
```

---

## 🚀 Quickstart

Eine vollständige Schritt-für-Schritt-Anleitung zum Deployment findet sich in den node-spezifischen READMEs. Kurzübersicht:

**1. Raspberry Pi – Broker & Publisher starten:**

```bash
# MQTT-Broker
cd raspberry_pi/docker/mosquitto
docker compose up -d

# DHT22-Publisher (.env mit MQTT_PASSWORD anlegen)
cd ../dht22_sensor
echo "MQTT_PASSWORD=<passwort>" > .env
docker compose up -d --build
```

**2. Debian01 – Datenbank, Dashboard & Subscriber starten:**

```bash
# InfluxDB + Grafana (.env anlegen, siehe debian01/docs/README.md)
cd debian01/docker/influxdb
docker compose up -d

# MQTT → InfluxDB Subscriber
cd ../mqtt-influx-subscriber
docker compose up -d --build
```

---

## 🔒 Security by Design

- **Kein anonymer MQTT-Zugriff:** `allow_anonymous false` + Passwortdatei auf dem Broker
- **Keine Secrets im Repo:** Alle Passwörter und Tokens ausschließlich über `.env`-Dateien (via `.gitignore` geschützt)
- **SSH Key-only:** Ed25519-Keys auf beiden Nodes, passwortbasierter Login deaktiviert
- **Docker Healthcheck:** Subscriber-Container startet automatisch neu, wenn >60 Sekunden keine Daten ankommen

---

## 📈 Roadmap

- [x] Containerisierung der Sensor-Pipeline (Mosquitto, DHT22-Publisher, Subscriber)
- [x] Docker Healthcheck für den MQTT-InfluxDB-Subscriber
- [x] Secrets-Management via `.env` + `.gitignore`
- [ ] GitHub Actions CI: Dockerfile-Linting (hadolint), Python-Tests
- [ ] Image-Tags pinnen für reproduzierbare Builds
- [ ] MQTT über TLS (Port 8883) absichern
- [ ] Orchestrierung mit k3s / Lightweight Kubernetes
- [ ] Infrastructure as Code mit Terraform / OpenTofu

---

## 📖 Weiterführende Dokumentation

- [Raspberry Pi Edge Node →](raspberry_pi/docs/README.md)
- [Debian01 Central Node →](debian01/docs/README.md)
