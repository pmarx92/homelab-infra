# Multi-Node Homelab Infrastructure

[![Architecture](https://img.shields.io/badge/Architecture-Hybrid%20Edge-blue)](#)
[![Tech Stack](https://img.shields.io/badge/Stack-Docker%20|%20MQTT%20|%20InfluxDB-orange)](#)

Dieses Repository dokumentiert den Aufbau und die Automatisierung meiner privaten Infrastruktur. Es dient als "Proof of Concept" für ein hybrides Monitoring-System, das Daten von Edge-Devices (Raspberry Pi) sicher an einen zentralen Server (Debian) übermittelt.


## 🏗 System-Architektur

Das Setup ist in zwei logische Ebenen unterteilt:

### 1. Central Services (Debian 13)
* **Data Lake:** InfluxDB 2.x zur Speicherung von Zeitreihendaten.
* **Visualization:** Grafana für das Echtzeit-Monitoring.
* **Ingestion:** Ein Python-basierter Subscriber, der MQTT-Daten validiert und in die InfluxDB schreibt.

### 2. Edge Layer (Raspberry Pi 5)
* **Connectivity:** Mosquitto MQTT Broker als zentrale Kommunikationsschnittstelle.
* **Sensing:** Python-Services zur Abfrage von DHT22-Sensoren (Temperatur/Feuchtigkeit) via GPIO.
* **Deployment:** Container-basierte Workloads, die via Docker Compose verwaltet werden.

## 🚀 Key Features & DevOps Praktiken

* **Containerization:** Alle Dienste sind vollständig dockerisiert. Die `Dockerfile`-Optimierung nutzt `python-slim` für minimale Image-Größen und schnellere Deployments.
* **Security by Design:**
    * Vollständiger Verzicht auf Passwort-Authentifizierung (Ed25519 SSH-Keys).
    * Strikte Trennung von Konfiguration und Geheimnissen über Umgebungsvariablen.
    * `.gitignore` Strategie zum Schutz von Infrastructure-Secrets (Terraform States, Keys).
* **Self-Healing:** Implementierung von Docker Healthchecks, die die Aktualität der Sensordaten überwachen und Container bei Bedarf neu starten.
* **Infrastructure-Documentation:** Detaillierte "Lessons Learned" Sektionen über DNS-Resolution und Linux-Berechtigungsmodelle (`chmod`).

## 🛠 Tech Stack

| Bereich | Technologien |
| :--- | :--- |
| **OS** | Debian 13 (Trixie), Raspberry Pi OS |
| **Runtime** | Docker, Docker Compose |
| **Languages** | Python 3.13 (CircuitPython, Paho-MQTT, InfluxDB-Client) |
| **Messaging** | MQTT (Eclipse Mosquitto) |
| **Storage** | InfluxDB 2.7 |

## 📈 Roadmap & Development
- [x] Containerisierung der Sensor-Pipeline
- [x] Automatisierte Backup-Strategie (Pull-Prinzip)
- [ ] Orchestrierung mit k3s oder Lightweight Kubernetes
- [ ] Integration von GitHub Actions für Automated Testing (CI)
- [ ] Infrastructure as Code (IaC) mit Terraform/OpenTofu für das Provisioning

---
*Dieses Projekt wird aktiv gepflegt, um moderne DevOps-Workflows in einer kontrollierten Umgebung zu evaluieren.*
