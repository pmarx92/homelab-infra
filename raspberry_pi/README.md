# 🍓 Raspberry Pi Edge Node: Sensorik & Messaging

Dieser Knoten fungiert als dedizierte Edge-Schnittstelle innerhalb meiner Homelab-Infrastruktur. Seine Hauptaufgabe ist das Erfassen von Umgebungsdaten via GPIO und das Bereitstellen eines lokalen MQTT-Brokers zur Entkoppelung der Datenströme.

---

## 🏗 System-Architektur

Die Software-Infrastruktur ist vollständig dockerisiert. Zwei Container laufen parallel und kommunizieren über das Host-Netzwerk:

```
┌─────────────────────────────────────────────────────┐
│   Raspberry Pi 5 (Host)                             │
│                                                     │
│  ┌─────────────────────┐    JSON via MQTT (QoS 1)   │
│  │  dht22-publisher    │──────────────────────────┐ │
│  │  Python 3.13-slim   │  Topic:                  │ │
│  │  GPIO Pin 12        │  homelab/pi5/dht22/       │ │
│  │  Intervall: 10s     │  metrics                 │ │
│  └─────────────────────┘                          │ │
│                                                   ▼ │
│  ┌──────────────────────────────────────────────┐   │
│  │  mqtt-broker (Mosquitto)  · Port 1883        │   │
│  │  eclipse-mosquitto:2                         │   │
│  │  allow_anonymous false · Password-File Auth  │   │
│  └──────────────────────────────────────────────┘   │
│                              │                      │
└──────────────────────────────┼──────────────────────┘
                               │ MQTT → Debian01
                               ▼ (mqtt-influx-subscriber)
```

| Komponente | Details |
| :--- | :--- |
| **Betriebssystem** | Raspberry Pi OS Lite (64-bit) |
| **Runtime** | Docker Engine & Docker Compose |
| **Basis-Image** | `python:3.13-slim` |
| **Broker** | Eclipse Mosquitto 2 |
| **Sensor** | Adafruit DHT22 · GPIO Pin 12 |
| **Publish-Intervall** | 10 Sekunden |

---

## 🛰 DHT22 Publisher

Die Sensor-Logik läuft in einem eigenen Container. Das Python-Skript `mqtt_publisher.py` liest den DHT22-Sensor aus und publiziert die Messwerte als JSON-Payload:

```json
{
  "temperature": 22.5,
  "humidity": 58.3,
  "host": "pi5",
  "sensor": "dht22"
}
```

**Technische Besonderheiten:**

- **Hardware-Zugriff:** `privileged: true` im Docker Compose ermöglicht den direkten Zugriff auf GPIO.
- **lg-Bibliothek:** Wird im Dockerfile aus dem Quellcode gebaut (`git clone joan2937/lg`), da sie als C-Extension die GPIO-Kommunikation auf dem Pi 5 ermöglicht.
- **Netzwerk:** Der Publisher erreicht den Mosquitto-Broker über `host.docker.internal`, das via `extra_hosts: host-gateway` auf die Host-IP gemappt wird.
- **Fehlertoleranz:** `RuntimeError` (typische Timing-Issues des DHT22) werden abgefangen – kein Container-Absturz bei kurzzeitigen Lesefehlern.
- **Reconnect-Logik:** `connect_mqtt()` wiederholt den Verbindungsversuch mit 5-Sekunden-Pause bis der Broker erreichbar ist.

> **Hinweis:** `humidity.py` ist ein experimenteller Flask-Endpunkt (`/metrics`, `/health`), der die Sensordaten per HTTP statt MQTT bereitstellt. Er ist aktuell **nicht** im Dockerfile eingebunden und wird nicht aktiv genutzt.

---

## 🔒 Hardening & OS-Konfiguration

Bevor die Dienste ausgerollt wurden, wurde das Basis-System gehärtet:

### 1. SSH-Absicherung

Passwortbasierte Logins sind deaktiviert. Der Zugriff erfolgt ausschließlich über Ed25519-Keys.

```bash
# Berechtigungen korrekt setzen
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

In `/etc/ssh/sshd_config`:

```
PasswordAuthentication no
PubkeyAuthentication yes
```

### 2. MQTT-Authentifizierung

Der Broker erlaubt keine anonymen Verbindungen. Die Zugangsdaten werden über eine Passwortdatei verwaltet:

```bash
# Passwortdatei anlegen (auf dem Pi-Host, nicht im Container)
sudo mosquitto_passwd -c /etc/mosquitto/credentials <username>
```

Die Datei wird schreibgeschützt in den Container gemountet:

```yaml
volumes:
  - /etc/mosquitto/credentials:/etc/mosquitto/credentials:ro
```

### 3. Netzwerk-Resilienz (Lessons Learned: DNS)

**Problem:** `apt update` schlug beim ersten Setup mit `Temporary failure resolving` fehl.

**Ursache:** Der Standard-Resolver war nicht erreichbar.

**Lösung:** Redundante Upstream-Resolver in `/etc/resolv.conf` eintragen:

```
nameserver 8.8.8.8
nameserver 1.1.1.1
```

---

## 🚀 Deployment

### Voraussetzungen

- Docker Engine ≥ 24.x und Docker Compose Plugin installiert
- DHT22-Sensor an GPIO Pin 12 angeschlossen
- MQTT-Passwortdatei unter `/etc/mosquitto/credentials` angelegt (siehe oben)
- `.env`-Datei im `dht22_sensor/`-Verzeichnis vorhanden

**Benötigte `.env`-Variablen:**

```env
MQTT_PASSWORD=<mqtt-passwort>
```

### Startsequenz

Der DHT22-Publisher benötigt den Broker – daher in dieser Reihenfolge starten:

**Schritt 1 – MQTT-Broker starten:**

```bash
cd docker/mosquitto
docker compose up -d
```

Status prüfen:

```bash
docker logs mqtt-broker --follow
```

Erwartete Ausgabe: `mosquitto version 2.x.x running`

**Schritt 2 – DHT22-Publisher starten:**

```bash
cd ../dht22_sensor
docker compose up -d --build
```

Status prüfen:

```bash
docker logs dht22-publisher --follow
```

Erwartete Ausgabe (alle 10 Sekunden):

```
Connected to MQTT Broker at host.docker.internal:1883
Published: {'temperature': 22.5, 'humidity': 58.3, 'host': 'pi5', 'sensor': 'dht22'}
```

### Alle laufenden Container anzeigen

```bash
docker ps
```

---

## 🐛 Troubleshooting

**Publisher verbindet sich nicht mit dem Broker:**
- Läuft Mosquitto? → `docker ps` und `docker logs mqtt-broker`
- Ist `MQTT_PASSWORD` in der `.env` korrekt gesetzt und identisch mit dem Eintrag in der Passwortdatei?
- Firewall prüfen: `sudo ufw status` – Port 1883 muss offen sein

**Sensor gibt `None` zurück:**
- DHT22 benötigt nach dem Einschalten ~2 Sekunden Aufwärmzeit – kurz warten
- Verkabelung prüfen: Signal an GPIO 12, VCC an 3.3V oder 5V, GND an GND
- Typische DHT22-Timing-Fehler werden im Log als `DHT22 read error` ausgegeben und sind nicht kritisch

**Container startet nicht (GPIO-Fehler):**
- Prüfen ob `privileged: true` in der `docker-compose.yml` gesetzt ist
- Alternativ: Device explizit mounten → `devices: - /dev/gpiomem:/dev/gpiomem`

---

## 🗂 Verzeichnisstruktur

```
raspberry_pi/
├── README.md                 	   # Diese Datei
└── docker/
    ├── mosquitto/
    │   ├── config/
    │   │   └── mosquitto.conf     # Broker-Konfiguration
    │   └── docker-compose.yml
    └── dht22_sensor/
        ├── Dockerfile
        ├── docker-compose.yml
        ├── mqtt_publisher.py      # Sensor → MQTT (aktiv)
        ├── humidity.py            # Sensor → HTTP/Flask (experimentell)
        └── requirements.txt
```
