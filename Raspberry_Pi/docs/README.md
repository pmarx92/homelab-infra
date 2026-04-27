# homelab-infra

> Personal homelab built to gain hands-on DevOps experience.
> Every step was done manually first, documented here, then automated as a script.

This repository documents the setup, configuration, and automation of my private server landscape, consisting of a Debian 13 server and a Raspberry Pi.

---

## Architecture & Tech Stack

| Component           | Details                                              |
| ------------------- | ---------------------------------------------------- |
| **Servers**         | Debian 13 (Trixie), Raspberry Pi OS Light            |
| **Management Host** | Windows 11 via WSL (Windows Subsystem for Linux)     |
| **Authentication**  | OpenSSH with Ed25519 key pairs                       |
| **Backup**          | Pull-based via `rsync` over SSH to local Windows HDD |

---

## Setup Overview

The initial setup focused on two goals: hardening the servers and establishing a local backup strategy.

1. **Security** – Disabled password-based logins, enforced SSH key authentication
2. **Network Resilience** – Configured persistent DNS resolvers to prevent name resolution failures
3. **Disaster Recovery** – Pull-based `rsync` backups from both servers to a local HDD via WSL

---

## Step-by-Step Documentation

### 1. SSH Key Authentication

**Goal:** Secure, passwordless server access using cryptographic key pairs.

```bash
# On local machine (WSL or Linux):
ssh-keygen -t ed25519

# Copy public key to server:
cat ~/.ssh/id_ed25519.pub | ssh user@192.168.X.XX "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

**Result:** Login via SSH key only – no password required.

---

### 2. SSH Config Aliases

**Goal:** Connect to servers without typing IP addresses or usernames.

```text
# Add to ~/.ssh/config on local machine:

Host debian01
    HostName 192.168.X.XX
    User pm
    IdentityFile ~/.ssh/id_ed25519

Host raspberrypi
    HostName 192.168.X.XX
    User pm
    IdentityFile ~/.ssh/id_ed25519
```

**Result:** `ssh debian01` and `ssh raspberrypi` work directly.

---

### 3. Fix DNS Resolution

**Problem:** `apt update` failed with "Temporary failure resolving" – DNS was broken.

**Fix:**

```bash
sudo nano /etc/resolv.conf
```

Add the following lines:

```
nameserver 8.8.8.8
nameserver 1.1.1.1
```

Save with `Ctrl+O`, exit with `Ctrl+X`.

**Result:** Server can resolve domain names again.

---

### 4. Install rsync on Server

**Problem:** `rsync` backup command failed – tool not installed on the remote server.

```bash
# On the Debian server:
sudo apt update && sudo apt install rsync -y
```

**Result:** `rsync` available on both sender and receiver.

---

### 5. Create Backup Directory (WSL)

**Goal:** Prepare local backup target on Windows HDD (Drive D:).

```bash
# In WSL terminal:
mkdir -p /mnt/d/server_backups/debian01
mkdir -p /mnt/d/server_backups/raspberry_pi_01
```

**Result:** Directory structure created idempotently (safe to re-run).

---

### 6. Pull Backup – Debian Server

**Goal:** Incremental, synchronized backup from server to local HDD.

```bash
rsync -avz --delete -e ssh debian01:/home/pm/ /mnt/d/server_backups/debian01/
```

**Result:** Exact mirror of server home directory on local HDD.

---

### 7. Pull Backup – Raspberry Pi

**Problem:** `rsync` with Pi alias failed with "Invalid Argument" – subprocess did not inherit the local SSH config.

```bash
# Workaround: instead of the config I used the direct IP
rsync -avz --delete -e "ssh pm@192.168.X.XX" raspberrypi:/home/pm/ /mnt/d/server_backups/raspberry_pi_01/
```

**Result:** Backup ran successfully with explicit config reference.

---

## Lessons Learned

- **DNS Troubleshooting:** If `ping 8.8.8.8` works but domain names fail → DNS is broken, check `/etc/resolv.conf`.
- **rsync dependencies:** `rsync` must be installed on both the local and remote system.
- **WSL path logic:** Windows drives are mounted under `/mnt/` in WSL (e.g. `D:\` → `/mnt/d/`).
- **SSH subprocess inheritance:** Child processes like `rsync` do not always inherit the local SSH config.
- **Manual before automated:** Every step here was done manually first to understand what each command actually does.

- **Linux Permissions (chmod):** Access rights are managed with a three-digit number (e.g. `chmod 600`).
  Each digit represents a group: **Owner – Group – Everyone else**.
  Each digit is the sum of: Read (4) + Write (2) + Execute (1).

  | chmod | Owner        | Group          | Others         | Typical use                     |
  | ----- | ------------ | -------------- | -------------- | ------------------------------- |
  | `600` | read + write | none           | none           | `authorized_keys`, private keys |
  | `700` | all          | none           | none           | `~/.ssh/` directory             |
  | `644` | read + write | read           | read           | public files                    |
  | `755` | all          | read + execute | read + execute | scripts, directories            |

  SSH refuses to work if `authorized_keys` is writable by anyone other than the owner.
  `chmod 600` is the standard – it keeps the file editable for me while blocking all access for everyone else.

---

## Usage – Manual Backup

```bash
# Debian server:
rsync -avz --delete -e ssh debian01:/home/pm/ /mnt/d/server_backups/debian01/

# Raspberry Pi:
rsync -avz --delete -e ssh pm@192.168.X.XX /mnt/d/server_backups/raspberry_pi_01/
```

---

## Roadmap

- [x] SSH key authentication (Debian + Pi)
- [x] SSH config aliases
- [x] DNS fix
- [x] rsync pull backups via WSL
- [ ] Docker Engine & Docker Compose
- [ ] First containerized workloads
- [ ] Monitoring stack (Prometheus + Grafana)
- [ ] CI/CD Pipeline (GitHub Actions)
- [ ] k3s Kubernetes cluster
