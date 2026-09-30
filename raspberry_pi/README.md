# 🍓 Raspberry Pi Edge Node: Sensorik & Messaging

Dieser Knoten fungiert als dedizierte Edge-Schnittstelle innerhalb meiner Homelab-Infrastruktur. Seine Hauptaufgabe ist das Erfassen von Umgebungsdaten via GPIO und das Bereitstellen eines lokalen MQTT-Brokers zur Entkoppelung der Datenströme. Zusätzlich stellt er Host-Metriken über einen node-exporter bereit.

---

## 🏗 System-Architektur

Die Software-Infrastruktur ist vollständig dockerisiert und auf drei Compose-Projekte verteilt. Der Publisher erreicht den Broker über den veröffentlichten Host-Port (`host.docker.internal` → `host-gateway`):

```
┌─────────────────────────────────────────────────────┐
│   Raspberry Pi 5 (Host)                             │
│                                                     │
│  ┌─────────────────────┐    JSON via MQTT (QoS 1)   │
│  │  dht22-publisher    │──────────────────────────┐ │
│  │  Python 3.13-slim   │  Topic:                  │ │
│  │  GPIO Pin 12        │  homelab/pi5/dht22/      │ │
│  │  Intervall: 10s     │  metrics                 │ │
│  └─────────────────────┘                          │ │
│                                                   ▼ │
│  ┌──────────────────────────────────────────────┐   │
│  │  mqtt-broker (Mosquitto)  · Port 1883        │   │
│  │  eclipse-mosquitto:2                         │   │
│  │  allow_anonymous false · Password-File Auth  │   │
│  └──────────────────────────────────────────────┘   │
│                              │                      │
│  ┌──────────────────────────────────────────────┐   │
│  │  node-exporter · Port 9100                   │   │
│  │  prom/node-exporter:v1.8.1                   │   │
│  └──────────────────────────────────────────────┘   │
│                              │                      │
└──────────────────────────────┼──────────────────────┘
                               │ MQTT → Debian01 (mqtt-influx-subscriber)
                               ▼ Scrape :9100 ← Debian01 (Prometheus)
```

| Komponente | Details |
| :--- | :--- |
| **Hardware** | Raspberry Pi 5 |
| **Runtime** | Docker Engine & Docker Compose Plugin (`docker compose`) |
| **Basis-Image Publisher** | `python:3.13-slim` (lokal auf dem Pi gebaut) |
| **Broker** | Eclipse Mosquitto 2 (`eclipse-mosquitto:2`) |
| **Monitoring** | node-exporter (`prom/node-exporter:v1.8.1`) |
| **Sensor** | DHT22 · GPIO Pin 12 (`board.D12`) |
| **Publish-Intervall** | 10 Sekunden |

### Dienste-Übersicht

| Compose-Ordner | Container | Image:Tag | Port (Host:Container) | Zweck |
| :--- | :--- | :--- | :--- | :--- |
| `docker/mosquitto/` | `mqtt-broker` | `eclipse-mosquitto:2` | `1883:1883` | MQTT-Broker |
| `docker/dht22_sensor/` | `dht22-publisher` | lokaler Build (`python:3.13-slim`) | – | DHT22 auslesen & per MQTT publizieren |
| `docker/node-exporter/` | `node-exporter` | `prom/node-exporter:v1.8.1` | `9100:9100` | Host-Metriken für Prometheus auf debian01 |

Die Ports sind ohne Bind-Adresse veröffentlicht, also auf allen Interfaces (`0.0.0.0`) erreichbar. Alle Container laufen mit `restart: unless-stopped`.

**Build:** Es gibt keine Multi-Arch-/`buildx`-Konfiguration. Das Publisher-Image wird direkt auf dem Pi per `docker compose up -d --build` gebaut. Mosquitto und node-exporter werden als fertige Images gezogen.

---

## 🔌 Hardware

- Raspberry Pi 5
- DHT22-Sensor, Signal an **GPIO 12** (im Code `board.D12`), VCC an 3.3V oder 5V, GND an GND

---

## 🛰 DHT22 Publisher (`docker/dht22_sensor/`)

Die Sensor-Logik läuft in einem eigenen Container (`dht22-publisher`). Das Python-Skript `mqtt_publisher.py` liest den DHT22-Sensor aus und publiziert die Messwerte als JSON-Payload auf das Topic `homelab/pi5/dht22/metrics`.

**Technische Besonderheiten:**

- **Hardware-Zugriff:** `privileged: true` im Docker Compose ermöglicht den direkten Zugriff auf GPIO. Es werden keine einzelnen `devices` gemountet.
- **lg-Bibliothek:** Wird im Dockerfile aus dem Quellcode gebaut (`git clone joan2937/lg`), da sie als C-Extension die GPIO-Kommunikation auf dem Pi 5 ermöglicht. Zusätzlich werden `gpiod` (apt) und die Pakete aus `requirements.txt` (`adafruit-circuitpython-dht`, `rpi-lgpio`, `flask`, `paho-mqtt`) installiert.
- **Netzwerk:** Der Publisher erreicht den Mosquitto-Broker über `host.docker.internal`, das via `extra_hosts: host-gateway` auf die Host-IP gemappt wird.
- **Zuverlässigkeit:** Nachrichten werden mit QoS 1 publiziert; der Publisher wartet jeweils auf die Bestätigung (`wait_for_publish`).
- **Fehlertoleranz:** Kein Container-Absturz bei Lesefehlern – die Schleife läuft nach `PUBLISH_INTERVAL` weiter:
  - `RuntimeError` (typische Timing-Issues des DHT22) → Log `DHT22 read error: …`
  - Sensor liefert `None` → Log `Sensor returned None`
  - Sonstige Exceptions → Log `Unexpected error: …`
- **Reconnect-Logik:** `connect_mqtt()` wiederholt den Verbindungsversuch mit 5-Sekunden-Pause bis der Broker erreichbar ist.
- **Healthcheck** (im `Dockerfile`, Intervall 30s, Timeout 5s, Start-Period 20s, 3 Retries): prüft per TCP-Verbindung, ob `MQTT_HOST:MQTT_PORT` erreichbar ist.

`MQTT_HOST` (`host.docker.internal`), `MQTT_TOPIC` und `PUBLISH_INTERVAL` (`10`) sind fest in der `docker-compose.yml` gesetzt.

---

## 📨 MQTT-Nachrichtenformat

**Topic:** `homelab/pi5/dht22/metrics` · **QoS:** 1

```json
{
  "temperature": <float>,
  "humidity": <float>,
  "host": "pi5",
  "sensor": "dht22"
}
```

Abnehmer ist der `mqtt-influx-subscriber` auf debian01.

---

## 📡 Mosquitto (`docker/mosquitto/`)

Konfiguration aus `config/mosquitto.conf`:

| Einstellung | Wert |
| :--- | :--- |
| Listener | `1883` |
| `allow_anonymous` | `false` |
| `password_file` | `/etc/mosquitto/credentials` |
| Persistenz | `persistence true`, `/mosquitto/data/` |
| Logging | `log_dest stdout` |

Mounts:

| Host | Container | Modus |
| :--- | :--- | :--- |
| `./config/mosquitto.conf` | `/mosquitto/config/mosquitto.conf` | ro |
| `/etc/mosquitto/credentials` | `/etc/mosquitto/credentials` | ro |
| `./data` | `/mosquitto/data` | rw |
| `./log` | `/mosquitto/log` | rw |

Da `log_dest stdout` gesetzt ist, landen die Logs in `docker logs mqtt-broker`, nicht in `./log`.

---

## 📊 node-exporter (`docker/node-exporter/`)

Stellt Host-Metriken des Pi auf Port `9100` bereit. `/proc`, `/sys` und `/` des Hosts werden read-only eingebunden. Abnehmer ist Prometheus auf debian01.

---

## 🔧 Konfiguration & Secrets

Alle sensiblen Werte werden über eine `.env`-Datei gesetzt, die **niemals** ins Repository gepusht wird (`.gitignore` gesichert). Die `.env`-Datei liegt im gleichen Verzeichnis wie die jeweilige `docker-compose.yml`.

**Benötigte `.env`-Variablen pro Compose-Ordner:**

| Compose-Ordner | Variablen |
| :--- | :--- |
| `docker/dht22_sensor/` | `MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD` |
| `docker/mosquitto/` | – (keine) |
| `docker/node-exporter/` | – (keine) |

### MQTT-Passwortdatei

Der Broker erlaubt keine anonymen Verbindungen. Die Zugangsdaten liegen auf dem Pi-Host unter `/etc/mosquitto/credentials` und werden schreibgeschützt in den Container gemountet.

```bash
# Passwortdatei anlegen (auf dem Pi-Host, nicht im Container)
sudo mosquitto_passwd -c /etc/mosquitto/credentials <username>
```

`MQTT_USER` / `MQTT_PASSWORD` in der `.env` des Publishers müssen zu einem Eintrag in dieser Datei passen.

---

## 🚀 Deployment

### Voraussetzungen

- Docker Engine und Docker Compose Plugin installiert
- DHT22-Sensor an GPIO Pin 12 angeschlossen
- MQTT-Passwortdatei unter `/etc/mosquitto/credentials` angelegt (siehe oben)
- `.env`-Datei im `docker/dht22_sensor/`-Verzeichnis vorhanden

### Startsequenz

Der DHT22-Publisher benötigt den Broker – daher in dieser Reihenfolge starten. Der node-exporter ist unabhängig.

**Schritt 1 – MQTT-Broker starten:**

```bash
cd docker/mosquitto
docker compose up -d
```

Status prüfen:

```bash
docker logs mqtt-broker --follow
```

**Schritt 2 – DHT22-Publisher starten:**

```bash
cd ../dht22_sensor
docker compose up -d --build
```

Status prüfen:

```bash
docker logs dht22-publisher --follow
```

Erwartete Ausgabe (etwa alle 10 Sekunden):

```
Connected to MQTT Broker at host.docker.internal:<MQTT_PORT>
Published: {'temperature': <float>, 'humidity': <float>, 'host': 'pi5', 'sensor': 'dht22'}
```

**Schritt 3 – node-exporter starten:**

```bash
cd ../node-exporter
docker compose up -d
```

### Alle laufenden Container anzeigen

```bash
docker ps

# Healthcheck-Status des Publishers prüfen
docker inspect --format='{{.State.Health.Status}}' dht22-publisher
```

### Stoppen

```bash
cd docker/dht22_sensor && docker compose down
cd ../mosquitto && docker compose down
cd ../node-exporter && docker compose down
```

---

## 🐛 Troubleshooting

**Publisher verbindet sich nicht mit dem Broker:**
- Läuft Mosquitto? → `docker ps` und `docker logs mqtt-broker`
- Sind `MQTT_PORT`, `MQTT_USER` und `MQTT_PASSWORD` in der `.env` korrekt gesetzt und passend zur Passwortdatei?
- Log zeigt `MQTT connection failed: …`? → Der Publisher versucht es alle 5 Sekunden erneut.

**Sensor liefert keine Werte:**
- Log zeigt `Sensor returned None` oder `DHT22 read error`? → Einzelne Fehler sind typische DHT22-Timing-Issues und nicht kritisch
- Verkabelung prüfen: Signal an GPIO 12, VCC an 3.3V oder 5V, GND an GND

**Container startet nicht (GPIO-Fehler):**
- Prüfen ob `privileged: true` in der `docker-compose.yml` gesetzt ist

---

## ✅ CI

Die GitHub-Actions-Pipeline (`.github/workflows/ci.yml`) läuft bei Pushes auf `main` und `feature/**` sowie bei Pull Requests auf `main`. Für den Pi wird geprüft:

- `docker/dht22_sensor/docker-compose.yml`: `config` (Validierung)
- `docker/mosquitto/docker-compose.yml`: `config` (Validierung)

Es werden keine Pi-Images gebaut; `docker/node-exporter/` wird in der CI nicht geprüft.

---

## 🗂 Verzeichnisstruktur

```
raspberry_pi/
├── README.md                      # Diese Datei
└── docker/
    ├── mosquitto/
    │   ├── config/
    │   │   └── mosquitto.conf     # Broker-Konfiguration
    │   └── docker-compose.yml
    ├── dht22_sensor/
    │   ├── Dockerfile
    │   ├── docker-compose.yml
    │   ├── mqtt_publisher.py      # Sensor → MQTT
    │   └── requirements.txt
    └── node-exporter/
        └── docker-compose.yml
```
