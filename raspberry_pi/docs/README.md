# 🍓 Raspberry Pi Edge Node: Sensorik & Messaging

Dieser Knoten fungiert als dedizierte Edge-Schnittstelle innerhalb meiner Homelab-Infrastruktur. Seine Hauptaufgabe ist das Erfassen von Umgebungsdaten via GPIO und das Bereitstellen eines lokalen Message-Brokers zur Entkoppelung der Datenströme.

---

## 🏗 System-Architektur

Die Software-Infrastruktur ist vollständig dockerisiert, um Portabilität und einfache Updates zu gewährleisten. Die Architektur besteht aus zwei Kernkomponenten:

1.  **Eclipse Mosquitto (MQTT Broker):** Fungiert als zentrale Kommunikationsdrehscheibe für die Node-to-Node Kommunikation.
2.  **DHT22 Publisher (Custom Python App):** Eine spezialisierte Applikation, die Klimadaten ausliest und via MQTT publiziert.

| Komponente | Details |
| :--- | :--- |
| **Betriebssystem** | Raspberry Pi OS Lite (64-bit) |
| **Runtime** | Docker Engine & Docker Compose |
| **Basis-Image** | `python:3.13-slim` |
| **Messaging** | MQTT (Eclipse Mosquitto:2) |
| **Sensing** | Adafruit DHT22 (GPIO Pin 12) |

---

## 🛰 Custom Service: DHT22 Publisher

Die Sensor-Logik wurde in einen eigenen Container ausgelagert. Um die Hardware-Anbindung aus Docker heraus sicherzustellen, wurden folgende Optimierungen vorgenommen:

* **Hardware-Zugriff:** Nutzung von `privileged: true` im Docker-Compose, um direkten Zugriff auf `/dev/gpiomem` zu erhalten.
* **Image-Härtung:** Installation der `lg`-Bibliothek im Dockerfile, um die C-Extensions für das Pin-Handling auf dem Pi zu unterstützen.
* **Fehlertoleranz:** Das Python-Skript fängt `RuntimeError` (typische Timing-Issues des DHT22) ab, um einen kontinuierlichen Betrieb ohne Container-Absturz zu gewährleisten.
* **Datenformat:** Publiziert strukturierte JSON-Payloads (Temperatur, Luftfeuchtigkeit, Host) im 10-Sekunden-Intervall.

---

## 🔒 Hardening & OS Configuration

Bevor die Dienste ausgerollt wurden, wurde das Basis-System gehärtet:

### 1. SSH-Absicherung
* **Key-only:** Deaktivierung von passwortbasierten Logins zugunsten von Ed25519 Key-Pairs.
* **Berechtigungen:** Strikte Anwendung des Least-Privilege-Prinzips für das `.ssh`-Verzeichnis (`700`) und die `authorized_keys` (`600`).

### 2. Netzwerk-Resilienz (DNS Fix)
* **Problem:** `apt update` schlug fehl aufgrund von "Temporary failure resolving".
* **Lösung:** Konfiguration redundanter Upstream-Resolver (8.8.8.8 / 1.1.1.1) in der `/etc/resolv.conf`.

---

## 🚀 Deployment

Das Deployment erfolgt modular via Docker Compose.

### 1. Startsequenz
Aufgrund der funktionalen Abhängigkeiten (Publisher benötigt Broker) wird folgende Reihenfolge genutzt:

**A) MQTT Broker starten**
```bash
cd docker/mosquitto
docker-compose up -d --build
