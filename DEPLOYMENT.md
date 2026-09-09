# Deployment Guide: Team Kranti (SIH26122)

This document outlines the deployment strategies for the Intelligent Data Capture & Schedule-Linking platform. Because the application consists of multiple microservices (Frontend, Backend, Celery Worker) and several stateful databases (Postgres, Redis, Qdrant, MinIO), deployment requires orchestrating these containers.

## Architecture Overview
The system runs the following services:
* **Frontend**: Next.js App
* **Backend**: FastAPI REST API
* **Worker**: Celery background task worker
* **Databases/Storage**: 
  * **PostgreSQL 16** (Relational Data)
  * **Redis 7** (Message broker for Celery)
  * **Qdrant** (Vector Database for Semantic Matching)
  * **MinIO** (S3-compatible Object Storage for files/photos)

---

## Option 1: Single-Node VM Deployment (Recommended for Hackathons/Prototypes)
The simplest way to deploy the entire stack is to replicate the local `docker-compose` environment on a single cloud Virtual Machine (VM). 

### 1. Provision a Server
Spin up a VM on your preferred cloud provider (AWS EC2, DigitalOcean Droplet, GCP Compute Engine, Azure VM).
* **OS**: Ubuntu 22.04 LTS
* **Specs**: Minimum 4 vCPUs, 8GB RAM, and 50GB storage (Qdrant, Postgres, and MinIO need memory and disk space).
* **Network**: Open ports `80` (HTTP), `443` (HTTPS), and `22` (SSH). 

### 2. Install Docker & Docker Compose
SSH into your server and run:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin -y
```

### 3. Clone Repository & Configure Environment
```bash
git clone https://github.com/<your-username>/Team-Kranti.git
cd Team-Kranti

# Create production environment variables
cp .env.example .env
nano .env
```
**Important updates for `.env`:**
* Set `APP_ENV=production`
* Update `NEXT_PUBLIC_API_URL` to point to your public domain/IP (e.g., `https://api.yourdomain.com`).
* Change default database passwords (`POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, etc.) to secure values.
* Ensure API keys (e.g., Groq API key) are populated.

### 4. Deploy the Stack
```bash
# Build and start all services in detached mode
docker compose up -d --build
```

### 5. Setup Nginx Reverse Proxy & SSL (Optional but Recommended)
To expose the Frontend on port `80/443` instead of `3000`, and the Backend on a subdomain, configure Nginx and Let's Encrypt.
```bash
sudo apt install nginx certbot python3-certbot-nginx
```
Configure Nginx to proxy `yourdomain.com` to `localhost:3000` (Frontend) and `api.yourdomain.com` to `localhost:8000` (Backend).

---

## Option 2: Managed Cloud Services (Production Ready)
For a highly available, production-grade deployment, you should separate the stateful databases from the stateless applications.

### 1. Managed Databases
Instead of running databases inside Docker, use managed services:
* **PostgreSQL**: AWS RDS, Supabase, or Google Cloud SQL.
* **Redis**: AWS ElastiCache, Upstash, or Redis Cloud.
* **Object Storage**: Amazon S3 (replaces MinIO). Update the Backend to use `boto3` pointing directly to AWS S3.
* **Vector DB**: Qdrant Cloud.

### 2. Stateless App Deployment
* **Frontend (Next.js)**: Deploy to [Vercel](https://vercel.com) or [Netlify](https://netlify.com). It integrates seamlessly with GitHub and handles edge caching automatically.
* **Backend (FastAPI) & Worker (Celery)**: 
  * Deploy using **AWS ECS (Fargate)** or **Google Cloud Run**.
  * Alternatively, use Platform-as-a-Service (PaaS) providers like **Render** or **Fly.io**, creating two services (one web service for FastAPI, one background worker for Celery).

---

## Post-Deployment Checklist
1. **Apply Migrations**: Ensure Alembic migrations are run against the production database:
   ```bash
   docker exec -it sih26122-backend alembic upgrade head
   ```
2. **Seed Initial Data**: If using synthetic data for demo purposes, run the seed script:
   ```bash
   docker exec -it sih26122-worker python scripts/seed_schedule.py
   ```
3. **CORS Configuration**: Ensure the Backend's CORS settings in `main.py` allow requests from the Next.js production domain.
