# 🖥 Debian01 Central Node: Data Ingestion & Visualization

Dieser Knoten ist das zentrale Herzstück der Homelab-Infrastruktur. Er empfängt Sensordaten per MQTT vom Broker auf dem Raspberry Pi, schreibt sie in eine Zeitreihendatenbank und stellt sie in Grafana bereit. Zusätzlich betreibt er den Monitoring-Stack (Prometheus, node-exporter, cAdvisor).

---

## 🏗 System-Architektur

Die Dienste sind auf drei Compose-Projekte verteilt. Projektübergreifend kommunizieren die Container über die veröffentlichten Host-Ports (`host.docker.internal` → `host-gateway`).

```
[Raspberry Pi / MQTT Broker]
         │
         │ MQTT (MQTT_HOST:MQTT_PORT)
         │ Topic: homelab/pi5/dht22/metrics
         ▼
┌────────────────────────────────────────────────┐
│                Debian01 (Host)                 │
│                                                │
│  ┌──────────────────────────────────┐          │
│  │   mqtt-influx-subscriber         │          │
│  │   Python · paho-mqtt             │          │
│  │   Validiert & schreibt Daten     │          │
│  └──────────────┬───────────────────┘          │
│                 │ HTTP host.docker.internal    │
│                 ▼                              │
│  ┌──────────────────────────────────┐          │
│  │   InfluxDB 2 (Port 8086)         │          │
│  │   Bucket: sensors / Org: homelab │          │
│  └──────────────┬───────────────────┘          │
│                 │ Datasource (manuell)         │
│                 ▼                              │
│  ┌──────────────────────────────────┐          │
│  │   Grafana (Port 3000)            │          │
│  │   Dashboards                     │          │
│  └──────────────▲───────────────────┘          │
│                 │ Datasource (provisioniert)   │
│  ┌──────────────┴───────────────────┐          │
│  │   Prometheus (Port 9090)         │          │
│  │   scrapt: node-exporter (9100),  │          │
│  │   cAdvisor (8080), InfluxDB,     │          │
│  │   Pi node-exporter               │          │
│  └──────────────────────────────────┘          │
└────────────────────────────────────────────────┘
```

| Komponente | Details |
| :--- | :--- |
| **Runtime** | Docker Engine & Docker Compose Plugin (`docker compose`) |
| **Basis-Image Subscriber** | `python:3.13-slim` |
| **Messaging** | Paho-MQTT (Subscriber-Client) |
| **Storage** | InfluxDB 2 (`influxdb:2`) |
| **Visualization** | Grafana (`grafana/grafana:latest`) |
| **Monitoring** | Prometheus `v2.53.0`, node-exporter `v1.8.1`, cAdvisor `v0.49.1` |

### Dienste-Übersicht

| Compose-Ordner | Container | Image:Tag | Port (Host:Container) | Zweck |
| :--- | :--- | :--- | :--- | :--- |
| `docker/influxdb/` | `influxdb` | `influxdb:2` | `8086:8086` | Zeitreihenspeicher für Sensordaten |
| `docker/influxdb/` | `grafana` | `grafana/grafana:latest` | `3000:3000` | Dashboards |
| `docker/mqtt-influx-subscriber/` | `mqtt-influx-subscriber` | lokaler Build (`python:3.13-slim`) | – | MQTT → InfluxDB Bridge |
| `docker/monitoring/` | `prometheus` | `prom/prometheus:v2.53.0` | `9090:9090` | Metriken sammeln & speichern |
| `docker/monitoring/` | `node-exporter` | `prom/node-exporter:v1.8.1` | `9100:9100` | Host-Metriken von debian01 |
| `docker/monitoring/` | `cadvisor` | `gcr.io/cadvisor/cadvisor:v0.49.1` | `8080:8080` | Container-Metriken von debian01 |

Alle Ports sind ohne Bind-Adresse veröffentlicht, also auf allen Interfaces (`0.0.0.0`) erreichbar. Alle Container laufen mit `restart: unless-stopped`.

---

## 📦 Dienste im Detail

### 1. InfluxDB + Grafana (`docker/influxdb/`)

Beide Dienste sind in einer gemeinsamen `docker-compose.yml` zusammengefasst und teilen das Default-Netzwerk des Compose-Projekts.

**InfluxDB** wird beim ersten Start automatisch initialisiert (`DOCKER_INFLUXDB_INIT_MODE: setup`). Alle Zugangsdaten werden ausschließlich über Umgebungsvariablen gesetzt – niemals im Klartext in der Compose-Datei.

- Volumes: `influxdb-data` → `/var/lib/influxdb2`, `influxdb-config` → `/etc/influxdb2`

**Grafana** läuft auf Port `3000`. Über Provisioning werden beim Start automatisch eingerichtet:

- **Datasource** `Prometheus` (UID `homelab-prometheus`) → `http://host.docker.internal:9090` (`provisioning/datasources/datasources.yaml`)
- **Dashboard-Provider** `homelab` → Ordner `Homelab`, lädt alle Dashboards aus `./dashboards` (`provisioning/dashboards/dashboards.yaml`)
- **Dashboard** `Prometheus Stats` (`dashboards/prometheus-stats.json`)

Eine InfluxDB-Datasource wird **nicht** provisioniert und muss manuell angelegt werden (siehe [Grafana aufrufen](#3-grafana-aufrufen)).

- Volumes: `grafana-data` → `/var/lib/grafana`, `./provisioning` → `/etc/grafana/provisioning` (ro), `./dashboards` → `/var/lib/grafana/dashboards` (ro)
- `extra_hosts`: `host.docker.internal:host-gateway` (für den Zugriff auf Prometheus)

<img width="1600" height="493" alt="image" src="https://github.com/user-attachments/assets/d12e2e3a-a3c4-4593-987d-e8a4d19d2020" />


### 2. MQTT-InfluxDB-Subscriber (`docker/mqtt-influx-subscriber/`)

Ein schlanker Python-Service (`subscriber.py`, Abhängigkeiten: `paho-mqtt`, `influxdb-client`), der:
- sich als MQTT-Client mit dem Broker auf dem Pi verbindet (bei Fehlschlag erneuter Versuch alle 5 Sekunden)
- das Topic `homelab/pi5/dht22/metrics` abonniert
- eingehende JSON-Payloads (`temperature`, `humidity`, `host`, `sensor`) verarbeitet
- die Daten als InfluxDB `Point` in Org `homelab`, Bucket `sensors` schreibt:
  - Measurement: `dht22`
  - Tags: `host` (Default `unknown`), `sensor` (Default `dht22`)
  - Fields: `temperature`, `humidity` (float)
- InfluxDB über `http://host.docker.internal:8086` erreicht (`extra_hosts: host.docker.internal:host-gateway`)

Topic, InfluxDB-URL, Org und Bucket sind fest in der `docker-compose.yml` hinterlegt.

**Healthcheck** (im `Dockerfile`, Intervall 30s, Timeout 5s, 3 Retries): Nach jedem erfolgreichen Schreibvorgang wird `/health/status` aktualisiert. Ist die Datei älter als 60 Sekunden, wird der Container als `unhealthy` markiert.

### 3. Monitoring (`docker/monitoring/`)

**Prometheus** (`prom/prometheus:v2.53.0`):
- Konfiguration: `prometheus.yml` (read-only gemountet), Daten im Volume `prometheus-data`
- Retention: `30d` (`--storage.tsdb.retention.time=30d`)
- Lifecycle-API aktiv (`--web.enable-lifecycle`) → Konfiguration per HTTP neu ladbar
- `extra_hosts`: `host.docker.internal:host-gateway` (für das Scraping von InfluxDB)

**node-exporter** (`prom/node-exporter:v1.8.1`): liest `/proc`, `/sys` und `/` des Hosts read-only.

**cAdvisor** (`gcr.io/cadvisor/cadvisor:v0.49.1`): läuft `privileged` und liest u. a. `/var/lib/docker` und `/var/run` read-only.

---

## 🔧 Konfiguration & Secrets

Alle sensiblen Werte werden über eine `.env`-Datei gesetzt, die **niemals** ins Repository gepusht wird (`.gitignore` gesichert). Die `.env`-Datei liegt im gleichen Verzeichnis wie die jeweilige `docker-compose.yml`; Docker Compose liest sie automatisch ein.

**Benötigte `.env`-Variablen pro Compose-Ordner:**

| Compose-Ordner | Variablen |
| :--- | :--- |
| `docker/influxdb/` | `INFLUXDB_USERNAME`, `INFLUXDB_PASSWORD`, `INFLUXDB_ORG`, `INFLUXDB_BUCKET`, `INFLUXDB_ADMIN_TOKEN`, `GF_SECURITY_USERNAME`, `GF_SECURITY_PASSWORD` |
| `docker/mqtt-influx-subscriber/` | `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD`, `INFLUXDB_ADMIN_TOKEN` |
| `docker/monitoring/` | – (keine) |

> **Hinweis:** Der Subscriber schreibt fest in Org `homelab` und Bucket `sensors`. `INFLUXDB_ORG` und `INFLUXDB_BUCKET` müssen dazu passen, `INFLUXDB_ADMIN_TOKEN` muss in beiden `.env`-Dateien identisch sein.

---

## 🚀 Deployment

### Voraussetzungen

- Docker Engine und Docker Compose Plugin installiert
- MQTT-Broker auf dem Raspberry Pi ist erreichbar
- `.env`-Datei in `docker/influxdb/` und `docker/mqtt-influx-subscriber/` angelegt

### 1. Startsequenz

Der Subscriber benötigt InfluxDB, daher wird `docker/influxdb/` zuerst gestartet. Der Monitoring-Stack ist davon unabhängig; die in Grafana provisionierte Prometheus-Datasource liefert erst Daten, wenn er läuft.

**Schritt 1 – InfluxDB & Grafana starten:**

```bash
cd docker/influxdb
docker compose up -d
```

InfluxDB initialisiert sich beim ersten Start selbstständig. Status prüfen:

```bash
docker logs influxdb --follow
```

**Schritt 2 – Subscriber starten:**

```bash
cd docker/mqtt-influx-subscriber
docker compose up -d --build
```

**Schritt 3 – Monitoring starten:**

```bash
cd docker/monitoring
docker compose up -d
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

1. Mit `GF_SECURITY_USERNAME` / `GF_SECURITY_PASSWORD` aus der `.env` anmelden
2. Datasource hinzufügen: **InfluxDB** → URL `http://influxdb:8086` → Token (`INFLUXDB_ADMIN_TOKEN`) eintragen → Org `homelab` → Bucket `sensors`
3. Die Prometheus-Datasource und das Dashboard `Prometheus Stats` (Ordner `Homelab`) sind bereits provisioniert

### 4. Stoppen

```bash
cd docker/mqtt-influx-subscriber && docker compose down
cd ../monitoring && docker compose down
cd ../influxdb && docker compose down
```

Die Named Volumes (`influxdb-data`, `influxdb-config`, `grafana-data`, `prometheus-data`) bleiben dabei erhalten.

---

## 📈 Monitoring

Globales Scrape- und Evaluation-Intervall: `15s`.

| Job | Target | Label `instance` |
| :--- | :--- | :--- |
| `prometheus` | `localhost:9090` | – |
| `node-debian01` | `node-exporter:9100` | `debian01` |
| `cadvisor-debian01` | `cadvisor:8080` | `debian01` |
| `node-pi5` | node-exporter auf dem Raspberry Pi, Port `9100` | `pi5` |
| `influxdb` | `host.docker.internal:8086` (`/metrics`) | – |

Nach Änderungen an `prometheus.yml` die Konfiguration ohne Neustart neu laden:

```bash
curl -X POST http://localhost:9090/-/reload
```

---

## 🔒 Sicherheitshinweise

- **Grafana-Zugang:** Admin-User und -Passwort werden ausschließlich über `GF_SECURITY_USERNAME` / `GF_SECURITY_PASSWORD` aus der `.env` gesetzt.
- **Ports:** Alle veröffentlichten Ports (`8086`, `3000`, `9090`, `9100`, `8080`) sind auf `0.0.0.0` gebunden.
- **MQTT-Verbindung:** Der Subscriber verbindet sich ohne TLS, nur mit Benutzername/Passwort.
- **cAdvisor:** Läuft als `privileged` Container.

---

## 🐛 Troubleshooting

**Subscriber verbindet sich nicht mit MQTT:**
- `MQTT_HOST` und `MQTT_PORT` in der `.env` korrekt gesetzt?
- `MQTT_USER` / `MQTT_PASSWORD` korrekt?
- Logs zeigen `MQTT connection failed`? → Broker nicht erreichbar, der Subscriber versucht es alle 5 Sekunden erneut.

**Keine Daten in InfluxDB:**
- Subscriber-Logs prüfen: `docker logs mqtt-influx-subscriber`
- `INFLUXDB_ADMIN_TOKEN` im Subscriber identisch mit dem der InfluxDB?
- Bucket `sensors` und Org `homelab` existieren in InfluxDB?

**Grafana zeigt keine Daten:**
- Datasource-Verbindung in Grafana testen (Settings → Data Sources → Test)
- Zeitraum im Dashboard-Filter auf die letzten 15 Minuten setzen
- Measurement-Name im Query: `dht22`, Fields: `temperature`, `humidity`
- Prometheus-Dashboard leer? → Läuft der Monitoring-Stack (`docker/monitoring/`)?

---

## ✅ CI

Die GitHub-Actions-Pipeline (`.github/workflows/ci.yml`) läuft bei Pushes auf `main` und `feature/**` sowie bei Pull Requests auf `main`. Für debian01 wird geprüft:

- `docker/influxdb/docker-compose.yml`: `config` (Validierung), `pull`, `up -d`
- `docker/mqtt-influx-subscriber/docker-compose.yml`: `config` (Validierung), `build`

`docker/monitoring/` wird in der CI nicht geprüft.

---

## 🗂 Verzeichnisstruktur

```
debian01/
├── README.md                        # Diese Datei
└── docker/
    ├── influxdb/
    │   ├── docker-compose.yml       # InfluxDB + Grafana
    │   ├── dashboards/
    │   │   └── prometheus-stats.json
    │   └── provisioning/
    │       ├── dashboards/dashboards.yaml
    │       └── datasources/datasources.yaml
    ├── monitoring/
    │   ├── docker-compose.yml       # Prometheus, node-exporter, cAdvisor
    │   └── prometheus.yml           # Scrape-Konfiguration
    └── mqtt-influx-subscriber/
        ├── Dockerfile
        ├── docker-compose.yml
        ├── subscriber.py            # MQTT → InfluxDB Bridge
        └── requirements.txt
```
