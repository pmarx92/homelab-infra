# Multi-Node Homelab Infrastructure

[![Architecture](https://img.shields.io/badge/Architecture-Hybrid%20Edge-blue)](#)
[![Stack](https://img.shields.io/badge/Stack-Docker%20|%20MQTT%20|%20InfluxDB%20|%20Grafana-orange)](#)
[![Python](https://img.shields.io/badge/Python-3.13-blue)](#)

Dieses Repository dokumentiert den Aufbau und die Automatisierung meiner privaten Infrastruktur. Es dient als Proof of Concept für ein hybrides Monitoring-System, das Sensordaten von einem Edge-Device (Raspberry Pi 5) an einen zentralen Server (debian01) übermittelt, dort persistiert und visualisiert. Zusätzlich werden beide Hosts über Prometheus überwacht.

---

## 🏗 System-Architektur

```
┌─────────────────────────────┐          ┌──────────────────────────────────────┐
│   Edge Layer                │          │   Central Services                   │
│   Raspberry Pi 5            │          │   debian01                           │
│                             │          │                                      │
│  ┌───────────────────────┐  │          │  ┌────────────────────────────────┐  │
│  │  DHT22 Publisher      │  │          │  │  mqtt-influx-subscriber        │  │
│  │  Python · GPIO Pin 12 │  │          │  │  Python · Paho-MQTT            │  │
│  │  10s Publish-Intervall│  │          │  │  Validierung & Ingestion       │  │
│  └───────────┬───────────┘  │          │  └──────▲────────┬────────────────┘  │
│              ▼              │          │         │        │ HTTP              │
│  ┌───────────────────────┐  │  MQTT    │         │        ▼                   │
│  │  Mosquitto Broker     │──┼──────────┼─────────┘  ┌─────────────────────┐   │
│  │  eclipse-mosquitto:2  │  │  :1883   │            │ InfluxDB 2 · 8086   │   │
│  │  Auth: Password-File  │  │          │            │ Bucket: sensors     │   │
│  └───────────────────────┘  │          │            └──────────┬──────────┘   │
│                             │          │                       ▼              │
│  ┌───────────────────────┐  │  Scrape  │  ┌──────────────┐  ┌─────────────┐   │
│  │  node-exporter · 9100 │◀─┼──────────┼──│ Prometheus   │─▶│ Grafana     │   │
│  └───────────────────────┘  │          │  │ 9090         │  │ 3000        │   │
│                             │          │  └──────┬───────┘  └─────────────┘   │
└─────────────────────────────┘          │         ▼ Scrape                     │
                                         │  node-exporter · cAdvisor            │
                                         └──────────────────────────────────────┘
```

Das Setup ist in zwei logische Ebenen unterteilt:

**Edge Layer (Raspberry Pi 5)** erfasst Umgebungsdaten via GPIO, stellt einen lokalen MQTT-Broker als Kommunikationsschnittstelle bereit und liefert Host-Metriken über einen node-exporter. Alle Dienste laufen containerisiert unter Docker Compose.

**Central Services (debian01)** empfangen die MQTT-Nachrichten, validieren und persistieren sie in InfluxDB und stellen sie über Grafana bereit. Prometheus sammelt Metriken von debian01 selbst, von InfluxDB und vom node-exporter auf dem Pi.

**Datenfluss:** DHT22 → Publisher (Pi) → MQTT-Broker (Pi) → Subscriber (debian01) → InfluxDB → Grafana; parallel Monitoring über Prometheus → Grafana.

### Übersicht

| Host | Rolle | OS / Architektur | Dienste | Details |
| :--- | :--- | :--- | :--- | :--- |
| **debian01** | Central Node | nicht im Repo festgelegt | `influxdb`, `grafana`, `mqtt-influx-subscriber`, `prometheus`, `node-exporter`, `cadvisor` | [debian01/README.md](debian01/README.md) |
| **Raspberry Pi 5** | Edge Node | nicht im Repo festgelegt | `mqtt-broker`, `dht22-publisher`, `node-exporter` | [raspberry_pi/README.md](raspberry_pi/README.md) |

---

## 🛠 Tech Stack

| Bereich | Technologien |
| :--- | :--- |
| **Runtime** | Docker Engine, Docker Compose |
| **Sprache** | Python 3.13 |
| **Bibliotheken** | adafruit-circuitpython-dht, Paho-MQTT, InfluxDB-Client |
| **Messaging** | MQTT · Eclipse Mosquitto 2 |
| **Storage** | InfluxDB 2 |
| **Visualization** | Grafana |
| **Monitoring** | Prometheus, node-exporter, cAdvisor |

---

## 🗂 Verzeichnisstruktur

```
homelab-infra/
├── README.md          # Diese Datei
├── .github/           # CI-Workflow (GitHub Actions)
├── debian01/          # Central Node – Compose-Projekte unter docker/
└── raspberry_pi/      # Edge Node – Compose-Projekte unter docker/
```

Der Aufbau der einzelnen Compose-Ordner ist in den Host-READMEs beschrieben.

---

## 📐 Konventionen

- **Ein Compose-Projekt pro Ordner:** `<host>/docker/<projekt>/docker-compose.yml`
- **Secrets pro Ordner:** Wo Zugangsdaten benötigt werden, liegt eine `.env` neben der jeweiligen `docker-compose.yml`. Sie ist per `.gitignore` ausgeschlossen und liegt nicht im Repo. Welche Ordner eine `.env` brauchen, steht in den Host-READMEs.
- **Restart-Policy:** Alle Container laufen mit `restart: unless-stopped`.
- **Image-Tags:** Nur die Monitoring-Images (Prometheus, node-exporter, cAdvisor) sind auf exakte Versionen gepinnt. InfluxDB und Mosquitto nutzen Major-Tags (`:2`), Grafana `:latest`, die eigenen Images bauen auf `python:3.13-slim` auf.

---

## 🚀 Quickstart

Die Schritt-für-Schritt-Anleitungen inklusive `.env`-Variablen und Befehlen stehen in den node-spezifischen READMEs. Empfohlene Reihenfolge:

1. **Raspberry Pi:** MQTT-Broker, danach DHT22-Publisher → [raspberry_pi/README.md](raspberry_pi/README.md)
2. **debian01:** InfluxDB & Grafana, danach der Subscriber → [debian01/README.md](debian01/README.md)
3. **Monitoring:** node-exporter auf dem Pi und Monitoring-Stack auf debian01 (unabhängig von der Sensor-Pipeline)

---

## 🔒 Security by Design

- **Kein anonymer MQTT-Zugriff:** `allow_anonymous false` + Passwortdatei auf dem Broker
- **Keine Secrets im Repo:** Alle Passwörter und Tokens ausschließlich über `.env`-Dateien (via `.gitignore` geschützt)
- **Docker Healthchecks:** Der Subscriber wird als `unhealthy` markiert, wenn länger als 60 Sekunden keine Daten verarbeitet wurden; der Publisher prüft die Erreichbarkeit des Brokers

---

## ✅ CI

Es gibt einen GitHub-Actions-Workflow: `.github/workflows/ci.yml`.

- **Trigger:** Push auf `main` und `feature/**`, Pull Requests auf `main`
- **debian01:** `docker compose config` für `influxdb` und `mqtt-influx-subscriber`, dazu `pull` und `up -d` für `influxdb` sowie `build` für den Subscriber
- **Raspberry Pi:** `docker compose config` für `dht22_sensor` und `mosquitto`

Die Monitoring-Compose-Projekte (`debian01/docker/monitoring`, `raspberry_pi/docker/node-exporter`) werden in der CI nicht geprüft.

---

## 📖 Weiterführende Dokumentation

- [Raspberry Pi Edge Node →](raspberry_pi/README.md)
- [Debian01 Central Node →](debian01/README.md)
