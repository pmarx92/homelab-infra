# 🖥 Debian01 Central Node: Data Ingestion & Visualization

Dieser Knoten ist das zentrale Herzstück der Homelab-Infrastruktur. Er empfängt Sensordaten vom Raspberry Pi Edge Node via MQTT, schreibt sie in eine Zeitreihendatenbank und stellt sie in einem Echtzeit-Dashboard bereit.

---

## 🏗 System-Architektur

Drei containerisierte Dienste arbeiten als Pipeline zusammen:

```
[Raspberry Pi / MQTT Broker]
         │
         │ MQTT (Port 1883)
         ▼
┌─────────────────────────────────────────┐
│            Debian01 (Host)              │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │   mqtt-influx-subscriber         │   │
│  │   Python · paho-mqtt             │   │
│  │   Validiert & schreibt Daten     │   │
│  └──────────────┬───────────────────┘   │
│                 │ HTTP (host-internal)  │
│                 ▼                       │
│  ┌──────────────────────────────────┐   │
│  │   InfluxDB 2.x  (Port 8086)      │   │
│  │   Zeitreihenspeicher             │   │
│  │   Bucket: sensors / Org: homelab │   │
│  └──────────────┬───────────────────┘   │
│                 │ Datasource            │
│                 ▼                       │
│  ┌──────────────────────────────────┐   │
│  │   Grafana  (Port 3000)           │   │
│  │   Echtzeit-Dashboard             │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

| Komponente | Details |
| :--- | :--- |
| **Betriebssystem** | Debian 13 (Trixie) |
| **Runtime** | Docker Engine & Docker Compose |
| **Basis-Image** | `python:3.13-slim` |
| **Messaging** | Paho-MQTT (Subscriber-Client) |
| **Storage** | InfluxDB 2.7 |
| **Visualization** | Grafana (latest) |

---

## 📦 Dienste im Detail

### 1. InfluxDB + Grafana (`docker/influxdb/`)

Beide Dienste sind in einer gemeinsamen `docker-compose.yml` zusammengefasst und teilen ein internes Docker-Netzwerk.

**InfluxDB** wird beim ersten Start automatisch initialisiert (`DOCKER_INFLUXDB_INIT_MODE: setup`). Alle Zugangsdaten werden ausschließlich über Umgebungsvariablen gesetzt – niemals im Klartext in der Compose-Datei.

**Grafana** läuft auf Port `3000` und nutzt InfluxDB als Datasource. Die Verbindung wird manuell über die UI oder per provisioning konfiguriert.

<img width="1600" height="493" alt="image" src="https://github.com/user-attachments/assets/d12e2e3a-a3c4-4593-987d-e8a4d19d2020" />


### 2. MQTT-InfluxDB-Subscriber (`docker/mqtt-influx-subscriber/`)

Ein schlanker Python-Service, der:
- sich als MQTT-Client mit dem Broker auf dem Pi verbindet
- eingehende JSON-Payloads (`temperature`, `humidity`, `host`, `sensor`) validiert
- die Daten als InfluxDB `Point` mit Tags und Fields in den Bucket `sensors` schreibt
- einen Healthcheck-Timestamp unter `/health/status` aktualisiert – der Container wird neu gestartet, wenn länger als 60 Sekunden keine Daten ankommen

---

## 🔧 Konfiguration & Secrets

Alle sensiblen Werte werden über eine `.env`-Datei gesetzt, die **niemals** ins Repository gepusht wird (`.gitignore` gesichert).

**Benötigte `.env`-Variablen:**

```env
# InfluxDB
INFLUXDB_USERNAME=<admin-user>
INFLUXDB_PASSWORD=<sicheres-passwort>
INFLUXDB_ORG=homelab
INFLUXDB_BUCKET=sensors
INFLUXDB_ADMIN_TOKEN=<langer-random-token>

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=<sicheres-passwort>

# MQTT (Subscriber)
MQTT_HOST=<IP-des-Raspberry-Pi>
MQTT_USER=<mqtt-username>
MQTT_PASSWORD=<mqtt-passwort>
```

> **Hinweis:** Die `.env`-Datei im gleichen Verzeichnis wie die jeweilige `docker-compose.yml` ablegen. Docker Compose liest sie automatisch ein.

---

## 🚀 Deployment

### Voraussetzungen

- Docker Engine ≥ 24.x und Docker Compose Plugin installiert
- Raspberry Pi Node läuft und MQTT-Broker ist erreichbar
- `.env`-Datei in beiden Service-Verzeichnissen angelegt

### 1. Startsequenz

Die Dienste werden in folgender Reihenfolge gestartet, da der Subscriber InfluxDB benötigt:

**Schritt 1 – InfluxDB & Grafana starten:**

```bash
cd docker/influxdb
docker compose up -d
```

InfluxDB initialisiert sich beim ersten Start selbstständig. Der Prozess dauert ca. 10–20 Sekunden. Status prüfen:

```bash
docker logs influxdb --follow
```

**Schritt 2 – Subscriber starten:**

```bash
cd docker/mqtt-influx-subscriber
docker compose up -d --build
```

### 2. Status prüfen

```bash
# Alle laufenden Container anzeigen
docker ps

# Subscriber-Logs verfolgen
docker logs mqtt-influx-subscriber --follow

# Healthcheck-Status des Subscribers prüfen
docker inspect --format='{{.State.Health.Status}}' mqtt-influx-subscriber
```

### 3. Grafana aufrufen

Grafana ist unter `http://<debian01-IP>:3000` erreichbar. Beim ersten Login:

1. Mit den in `.env` gesetzten Credentials anmelden
2. Datasource hinzufügen: **InfluxDB** → URL `http://influxdb:8086` → Token aus `.env` eintragen → Org `homelab` → Bucket `sensors`
3. Dashboard importieren oder manuell erstellen

---

## 🔒 Sicherheitshinweise

- **Grafana-Passwort:** Das Default-Passwort `admin` muss durch einen starken Wert in der `.env` ersetzt werden.
- **InfluxDB-Port:** Port `8086` ist aktuell auf `0.0.0.0` gebunden. Bei reinem lokalen Betrieb empfiehlt sich die Einschränkung auf `127.0.0.1:8086`.
- **MQTT-Verbindung:** Läuft aktuell unverschlüsselt auf Port `1883`. Für erhöhte Sicherheit: Migration auf Port `8883` mit TLS-Zertifikaten.
- **SSH-Zugriff:** Ausschließlich via Ed25519-Keys, passwortbasierter Login ist deaktiviert.

---

## 🐛 Troubleshooting

**Subscriber verbindet sich nicht mit MQTT:**
- IP-Adresse des Pi in der `.env` korrekt gesetzt?
- Ist der Mosquitto-Broker auf dem Pi gestartet? (`docker ps` auf dem Pi ausführen)
- Firewall-Regel für Port `1883` auf dem Pi vorhanden?

**Keine Daten in InfluxDB:**
- Subscriber-Logs prüfen: `docker logs mqtt-influx-subscriber`
- InfluxDB-Token stimmt überein mit dem in der `.env`?
- Bucket `sensors` und Org `homelab` existieren in InfluxDB?

**Grafana zeigt keine Daten:**
- Datasource-Verbindung in Grafana testen (Settings → Data Sources → Test)
- Zeitraum im Dashboard-Filter auf die letzten 15 Minuten setzen
- Measurement-Name im Query: `dht22`, Fields: `temperature`, `humidity`

---

## 🗂 Verzeichnisstruktur

```
debian01/
├── docs/
│   └── README.md          # Diese Datei
└── docker/
    ├── influxdb/
    │   └── docker-compose.yml   # InfluxDB + Grafana
    └── mqtt-influx-subscriber/
        ├── Dockerfile
        ├── docker-compose.yml
        ├── subscriber.py        # MQTT → InfluxDB Bridge
        └── requirements.txt
```
