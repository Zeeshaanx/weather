# 🌤 City Weather API

A minimal FastAPI + Nginx weather app — containerized and ready for Kubernetes demos (pods, ingress, scaling, etc).

## What it does

| Route | Description |
|---|---|
| `GET /weather/home` | Landing page — search any city, get live weather + 3-day forecast |
| `GET /weather/city` | Search history — all cities searched this session |

Weather data is fetched live from [wttr.in](https://wttr.in) — no API key needed.

---

## Stack

- **FastAPI** — Python API + Jinja2 HTML templates
- **Nginx** — Reverse proxy, serves on port 80, routes `/weather` → app
- **Docker + Compose** — Single-command local run
- **wttr.in** — Free weather data, no API key

---

## Run locally

```bash
git clone <your-repo>
cd city-weather-api

docker compose up --build
```

Then open: [http://localhost/weather/home](http://localhost/weather/home)

---

## Deploy on EC2 (or any VM)

```bash
# 1. SSH into your EC2 instance
ssh ec2-user@<your-ec2-ip>

# 2. Install Docker + Compose
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo usermod -aG docker ec2-user

# Install Compose v2
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. Clone and run
git clone <your-repo>
cd city-weather-api
docker compose up -d --build
```

Access at: `http://<your-ec2-public-ip>/weather/home`

> **EC2 Security Group**: Make sure port **80** is open for inbound traffic (HTTP).

---

## Kubernetes Demo Usage

This repo is purpose-built for demoing:

### Pods
```bash
kubectl apply -f k8s/
kubectl get pods
kubectl describe pod <weather-pod>
```

### Scaling
```bash
kubectl scale deployment weather-app --replicas=5
kubectl get pods -w   # watch them come up
```

### Ingress
Configure your ingress controller to route `http://<cluster-ip>/weather` → `weather-service:80`

### Health Check
```
GET /healthz  →  {"status": "ok", "service": "city-weather-api"}
```

---

## Project Structure

```
city-weather-api/
├── app/
│   ├── main.py               # FastAPI app, routes, weather fetcher
│   └── templates/
│       ├── home.html         # /weather/home UI
│       └── city.html         # /weather/city UI
├── nginx/
│   └── nginx.conf            # Reverse proxy config (port 80 → 8000)
├── Dockerfile                # App container
├── docker-compose.yml        # Compose: app + nginx
├── requirements.txt
└── README.md
```

---

## Notes

- Search history is **in-memory** (resets on restart) — intentional for demo purposes
- No database, no auth — kept minimal for Kubernetes lab use
- `root_path="/weather"` in FastAPI ensures all URL generation is prefix-aware behind Nginx
"# weather" 
