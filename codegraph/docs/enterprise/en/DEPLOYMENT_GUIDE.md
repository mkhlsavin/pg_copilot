# CodeGraph Enterprise Deployment Guide

> Architecture Guide for DevOps and Infrastructure Teams

---

## Table of Contents

- [Overview](#overview)
- [1. System Requirements](#1-system-requirements)
  - [1.1 Hardware Requirements](#11-hardware-requirements)
  - [1.2 Software Requirements](#12-software-requirements)
  - [1.3 Network Ports](#13-network-ports)
- [2. Docker Compose (Development)](#2-docker-compose-development)
  - [2.1 File Structure](#21-file-structure)
  - [2.2 docker-compose.yml](#22-docker-composeyml)
  - [2.3 Environment Variables (.env)](#23-environment-variables-env)
  - [2.4 Startup](#24-startup)
- [3. Kubernetes (Production)](#3-kubernetes-production)
  - [3.1 Architecture](#31-architecture)
  - [3.2 Namespace and ConfigMap](#32-namespace-and-configmap)
  - [3.3 Secrets](#33-secrets)
  - [3.4 Deployment](#34-deployment)
  - [3.5 Service and Ingress](#35-service-and-ingress)
  - [3.6 HorizontalPodAutoscaler](#36-horizontalpodautoscaler)
  - [3.7 NetworkPolicy](#37-networkpolicy)
- [4. Air-Gapped Deployment](#4-air-gapped-deployment)
  - [4.1 Isolated Environment Characteristics](#41-isolated-environment-characteristics)
  - [4.2 Air-Gapped Configuration](#42-air-gapped-configuration)
  - [4.3 Preparing Artifacts for Air-Gapped](#43-preparing-artifacts-for-air-gapped)
  - [4.4 Installation in Air-Gapped Environment](#44-installation-in-air-gapped-environment)
- [5. Deployment Security](#5-deployment-security)
  - [5.1 TLS/SSL Configuration](#51-tlsssl-configuration)
  - [5.2 Pod Security Standards](#52-pod-security-standards)
  - [5.3 Secrets Encryption](#53-secrets-encryption)
- [6. Monitoring and Observability](#6-monitoring-and-observability)
  - [6.1 Prometheus ServiceMonitor](#61-prometheus-servicemonitor)
  - [6.2 Grafana Dashboard](#62-grafana-dashboard)
  - [6.3 Alertmanager Rules](#63-alertmanager-rules)
- [7. Backup and Recovery](#7-backup-and-recovery)
  - [7.1 PostgreSQL Backup](#71-postgresql-backup)
  - [7.2 DuckDB Backup](#72-duckdb-backup)
  - [7.3 Disaster Recovery](#73-disaster-recovery)
- [8. Migration and Upgrades](#8-migration-and-upgrades)
  - [8.1 Rolling Update](#81-rolling-update)
  - [8.2 Database Migration](#82-database-migration)
- [Related Documents](#related-documents)

## Overview

CodeGraph supports multiple deployment modes for different security and scaling requirements:

| Mode | Description | Recommended For |
|------|-------------|-----------------|
| **Docker Compose** | Single node, simple setup | Development, testing |
| **Kubernetes** | Clustered, HA, auto-scaling | Production |
| **Air-Gapped** | Isolated network, local LLM | High-security environments |

---

## 1. System Requirements

### 1.1 Hardware Requirements

| Component | Minimum | Recommended | Production |
|-----------|---------|-------------|------------|
| **CPU** | 4 cores | 8 cores | 16+ cores |
| **RAM** | 8 GB | 16 GB | 32+ GB |
| **SSD** | 50 GB | 100 GB | 500+ GB |
| **GPU** | - | NVIDIA 8GB+ | NVIDIA 24GB+ |

**Note:** GPU is only required for local LLM (air-gapped mode).

### 1.2 Software Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11+ | Main runtime environment |
| **PostgreSQL** | 14+ | User, session, audit storage |
| **DuckDB** | 1.0+ | CPG graph storage |
| **Docker** | 24+ | Containerization (optional) |
| **Kubernetes** | 1.28+ | Orchestration (production) |

> **Note:** Joern (4.0+) is only required for initial CPG generation from source code. Once the CPG is exported to DuckDB, Joern is no longer needed for regular operation.

### 1.3 Network Ports

| Port | Service | Protocol |
|------|---------|----------|
| 8000 | CodeGraph API | HTTP/HTTPS |
| 5432 | PostgreSQL | TCP |
| 8080 | Joern Server | HTTP |
| 514 | SIEM (Syslog) | UDP/TCP |
| 8200 | HashiCorp Vault | HTTP/HTTPS |

---

## 2. Docker Compose (Development)

### 2.1 File Structure

```
codegraph/
├── docker-compose.yml
├── docker-compose.override.yml  # Local settings
├── .env                         # Environment variables
├── config.yaml                  # Application configuration
└── data/
    ├── postgres/                # PostgreSQL data
    ├── duckdb/                  # DuckDB files
    └── joern/                   # Joern workspace
```

### 2.2 docker-compose.yml

```yaml
version: '3.8'

services:
  # ==========================================================================
  # CodeGraph API Server
  # ==========================================================================
  api:
    build:
      context: .
      dockerfile: Dockerfile
    image: codegraph:latest
    container_name: codegraph-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@postgres:5432/codegraph
      - API_JWT_SECRET=${API_JWT_SECRET}
      - GIGACHAT_AUTH_KEY=${GIGACHAT_AUTH_KEY}
      - SECURITY_ENABLED=true
      - DLP_ENABLED=true
      - SIEM_ENABLED=${SIEM_ENABLED:-false}
      - VAULT_ENABLED=${VAULT_ENABLED:-false}
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ./data/duckdb:/app/data/duckdb
    depends_on:
      postgres:
        condition: service_healthy
      joern:
        condition: service_started
    networks:
      - codegraph-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ==========================================================================
  # PostgreSQL Database
  # ==========================================================================
  postgres:
    image: postgres:16-alpine
    container_name: codegraph-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=codegraph
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - codegraph-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ==========================================================================
  # Joern CPG Server
  # ==========================================================================
  joern:
    image: ghcr.io/joernio/joern:latest
    container_name: codegraph-joern
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      - ./data/joern:/workspace
    command: ["joern", "--server", "--server-host", "0.0.0.0"]
    networks:
      - codegraph-network

networks:
  codegraph-network:
    driver: bridge
```

### 2.3 Environment Variables (.env)

```bash
# =============================================================================
# CodeGraph Environment Variables
# =============================================================================

# PostgreSQL
POSTGRES_PASSWORD=<secure-password-here>

# JWT Authentication
API_JWT_SECRET=<64-char-random-string>
API_ADMIN_USERNAME=admin
API_ADMIN_PASSWORD=<secure-admin-password>

# LLM Provider (GigaChat)
GIGACHAT_AUTH_KEY=<base64-encoded-credentials>

# Security Features
SECURITY_ENABLED=true
DLP_ENABLED=true
SIEM_ENABLED=false
VAULT_ENABLED=false

# SIEM (if enabled)
SIEM_SYSLOG_HOST=siem.company.com
SIEM_SYSLOG_PORT=514

# Vault (if enabled)
VAULT_ADDR=https://vault.company.com:8200
VAULT_TOKEN=<vault-token>
```

### 2.4 Startup

```bash
# Create .env file
cp .env.example .env
# Edit variables
nano .env

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f api

# Initialize database
docker compose exec api python -m alembic upgrade head

# Create administrator
docker compose exec api python -m scripts.create_admin
```

---

## 3. Kubernetes (Production)

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           KUBERNETES CLUSTER                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         INGRESS CONTROLLER                           │   │
│  │                     (nginx / traefik / istio)                        │   │
│  │                                                                       │   │
│  │  api.codegraph.company.com ────────────────► codegraph-api:8000     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                       │                                     │
│                                       ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CODEGRAPH NAMESPACE                               │   │
│  │                                                                       │   │
│  │  ┌───────────────────┐  ┌───────────────────┐  ┌─────────────────┐  │   │
│  │  │  codegraph-api    │  │  codegraph-api    │  │  codegraph-api  │  │   │
│  │  │  (replica 1)      │  │  (replica 2)      │  │  (replica 3)    │  │   │
│  │  │                   │  │                   │  │                 │  │   │
│  │  │  CPU: 2           │  │  CPU: 2           │  │  CPU: 2         │  │   │
│  │  │  RAM: 4Gi         │  │  RAM: 4Gi         │  │  RAM: 4Gi       │  │   │
│  │  └───────────────────┘  └───────────────────┘  └─────────────────┘  │   │
│  │            │                    │                      │             │   │
│  │            └────────────────────┼──────────────────────┘             │   │
│  │                                 │                                    │   │
│  │                                 ▼                                    │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │                      SERVICES                                  │  │   │
│  │  │                                                                │  │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐   │  │   │
│  │  │  │ PostgreSQL  │  │   Joern     │  │   HashiCorp Vault   │   │  │   │
│  │  │  │ (StatefulSet)│  │ (StatefulSet)│  │   (External)       │   │  │   │
│  │  │  │             │  │             │  │                     │   │  │   │
│  │  │  │ PVC: 100Gi  │  │ PVC: 50Gi   │  │                     │   │  │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────────────┘   │  │   │
│  │  │                                                                │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Namespace and ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: codegraph
  labels:
    name: codegraph
    istio-injection: enabled  # If using Istio
---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: codegraph-config
  namespace: codegraph
data:
  config.yaml: |
    domain:
      name: postgresql
      auto_activate: true

    api:
      host: "0.0.0.0"
      port: 8000
      workers: 4

    security:
      enabled: true
      dlp:
        enabled: true
        pre_request:
          enabled: true
          default_action: "WARN"
        post_response:
          enabled: true
          default_action: "MASK"
      siem:
        enabled: true
        syslog:
          enabled: true
          host: "siem-syslog.security.svc.cluster.local"
          port: 514
      vault:
        enabled: true
        url: "http://vault.vault.svc.cluster.local:8200"
        auth_method: "kubernetes"
        kubernetes:
          role: "codegraph"
```

### 3.3 Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: codegraph-secrets
  namespace: codegraph
type: Opaque
stringData:
  DATABASE_URL: "postgresql+asyncpg://postgres:password@postgres:5432/codegraph"
  API_JWT_SECRET: "<64-char-random-string>"
  GIGACHAT_AUTH_KEY: "<base64-credentials>"
---
# For production use External Secrets Operator + Vault
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: codegraph-vault-secrets
  namespace: codegraph
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: codegraph-secrets
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: codegraph/database
        property: url
    - secretKey: API_JWT_SECRET
      remoteRef:
        key: codegraph/api
        property: jwt_secret
    - secretKey: GIGACHAT_AUTH_KEY
      remoteRef:
        key: codegraph/llm
        property: gigachat_credentials
```

### 3.4 Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: codegraph-api
  namespace: codegraph
  labels:
    app: codegraph
    component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: codegraph
      component: api
  template:
    metadata:
      labels:
        app: codegraph
        component: api
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/api/v1/metrics"
    spec:
      serviceAccountName: codegraph
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000

      containers:
        - name: api
          image: codegraph:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - secretRef:
                name: codegraph-secrets
          env:
            - name: SECURITY_ENABLED
              value: "true"
            - name: SIEM_ENABLED
              value: "true"
            - name: VAULT_ENABLED
              value: "true"
          volumeMounts:
            - name: config
              mountPath: /app/config.yaml
              subPath: config.yaml
            - name: duckdb-data
              mountPath: /app/data/duckdb
          resources:
            requests:
              cpu: "1"
              memory: "2Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
          livenessProbe:
            httpGet:
              path: /api/v1/health/live
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /api/v1/health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL

      volumes:
        - name: config
          configMap:
            name: codegraph-config
        - name: duckdb-data
          persistentVolumeClaim:
            claimName: codegraph-duckdb-pvc

      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: codegraph
                topologyKey: kubernetes.io/hostname
```

### 3.5 Service and Ingress

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: codegraph-api
  namespace: codegraph
spec:
  type: ClusterIP
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP
      name: http
  selector:
    app: codegraph
    component: api
---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: codegraph-ingress
  namespace: codegraph
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.codegraph.company.com
      secretName: codegraph-tls
  rules:
    - host: api.codegraph.company.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: codegraph-api
                port:
                  number: 8000
```

### 3.6 HorizontalPodAutoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: codegraph-api-hpa
  namespace: codegraph
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: codegraph-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
```

### 3.7 NetworkPolicy

```yaml
# networkpolicy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: codegraph-network-policy
  namespace: codegraph
spec:
  podSelector:
    matchLabels:
      app: codegraph
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow traffic from ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
    # Allow traffic from Prometheus
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 8000
  egress:
    # PostgreSQL
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    # Joern
    - to:
        - podSelector:
            matchLabels:
              app: joern
      ports:
        - protocol: TCP
          port: 8080
    # Vault
    - to:
        - namespaceSelector:
            matchLabels:
              name: vault
      ports:
        - protocol: TCP
          port: 8200
    # SIEM (Syslog)
    - to:
        - namespaceSelector:
            matchLabels:
              name: security
      ports:
        - protocol: UDP
          port: 514
    # GigaChat API (external)
    - to:
        - ipBlock:
            cidr: 0.0.0.0/0
      ports:
        - protocol: TCP
          port: 443
    # DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

---

## 4. Air-Gapped Deployment

### 4.1 Isolated Environment Characteristics

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AIR-GAPPED ENVIRONMENT                            │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        NO INTERNET ACCESS                        │   │
│  │                                                                   │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │ CodeGraph   │  │  Local LLM  │  │  Local Container       │  │   │
│  │  │ API         │  │  (llama.cpp)│  │  Registry               │  │   │
│  │  │             │──│             │  │                         │  │   │
│  │  │ DLP: ON     │  │ Qwen3-30B   │  │ registry.local:5000    │  │   │
│  │  │ SIEM: ON    │  │ LLMxCPG-Q   │  │                         │  │   │
│  │  │ Vault: ON   │  │             │  │                         │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│                           ❌ NO EXTERNAL LLM APIs                       │
│                           ✅ ALL DATA STAYS ON-PREMISE                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Air-Gapped Configuration

```yaml
# config.yaml for air-gapped
llm:
  # Use local LLM instead of GigaChat
  provider: "local"

  local:
    # Path to model (transferred on media)
    model_path: "/models/LLMxCPG-Q-32B-Q4_K_M.gguf"
    use_llmxcpg: true
    n_ctx: 8192
    n_gpu_layers: -1  # All layers on GPU
    n_batch: 512
    n_threads: 8

security:
  enabled: true

  # DLP works locally
  dlp:
    enabled: true
    webhook:
      enabled: false  # No external webhooks

  # SIEM — local server
  siem:
    enabled: true
    syslog:
      enabled: true
      host: "siem.local"
      port: 514

  # Vault — local instance
  vault:
    enabled: true
    url: "http://vault.local:8200"
    auth_method: "approle"
```

### 4.3 Preparing Artifacts for Air-Gapped

```bash
#!/bin/bash
# prepare-airgapped.sh — run on internet-connected machine

# 1. Download Docker images
docker pull codegraph:latest
docker pull postgres:16-alpine
docker pull ghcr.io/joernio/joern:latest
docker pull hashicorp/vault:1.15

# 2. Save images to tar
docker save codegraph:latest postgres:16-alpine \
  ghcr.io/joernio/joern:latest hashicorp/vault:1.15 \
  | gzip > codegraph-images.tar.gz

# 3. Download LLM model
wget https://huggingface.co/company/LLMxCPG-Q-32B-GGUF/resolve/main/LLMxCPG-Q-32B-Q4_K_M.gguf

# 4. Download Python dependencies
pip download -d ./packages -r requirements.txt

# 5. Package everything
tar -czvf codegraph-airgapped-bundle.tar.gz \
  codegraph-images.tar.gz \
  LLMxCPG-Q-32B-Q4_K_M.gguf \
  packages/ \
  config/ \
  scripts/
```

### 4.4 Installation in Air-Gapped Environment

```bash
#!/bin/bash
# install-airgapped.sh — run in isolated environment

# 1. Extract bundle
tar -xzvf codegraph-airgapped-bundle.tar.gz

# 2. Load Docker images
gunzip -c codegraph-images.tar.gz | docker load

# 3. Install Python dependencies from local cache
pip install --no-index --find-links=./packages -r requirements.txt

# 4. Copy model
cp LLMxCPG-Q-32B-Q4_K_M.gguf /models/

# 5. Start services
docker compose -f docker-compose.airgapped.yml up -d
```

---

## 5. Deployment Security

### 5.1 TLS/SSL Configuration

```yaml
# Nginx Ingress with TLS 1.3
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: codegraph-ingress
  annotations:
    nginx.ingress.kubernetes.io/ssl-protocols: "TLSv1.3"
    nginx.ingress.kubernetes.io/ssl-ciphers: "TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256"
    nginx.ingress.kubernetes.io/configuration-snippet: |
      add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
      add_header X-Content-Type-Options "nosniff" always;
      add_header X-Frame-Options "DENY" always;
      add_header X-XSS-Protection "1; mode=block" always;
```

### 5.2 Pod Security Standards

```yaml
# PodSecurityPolicy / Pod Security Admission
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: codegraph-restricted
spec:
  privileged: false
  runAsUser:
    rule: MustRunAsNonRoot
  seLinux:
    rule: RunAsAny
  fsGroup:
    rule: RunAsAny
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  hostNetwork: false
  hostIPC: false
  hostPID: false
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
```

### 5.3 Secrets Encryption

```yaml
# EncryptionConfiguration for etcd
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources:
      - secrets
    providers:
      - aescbc:
          keys:
            - name: key1
              secret: <base64-encoded-32-byte-key>
      - identity: {}
```

---

## 6. Monitoring and Observability

### 6.1 Prometheus ServiceMonitor

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: codegraph-monitor
  namespace: codegraph
spec:
  selector:
    matchLabels:
      app: codegraph
  endpoints:
    - port: http
      path: /api/v1/metrics
      interval: 30s
```

### 6.2 Grafana Dashboard

| Panel | Metric | Description |
|-------|--------|-------------|
| **Request Rate** | `rate(http_requests_total[5m])` | Requests per second |
| **Error Rate** | `rate(http_requests_total{status=~"5.."}[5m])` | 5xx errors |
| **Latency P95** | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` | 95th percentile latency |
| **DLP Blocks** | `rate(dlp_blocks_total[5m])` | DLP blocks |
| **LLM Tokens** | `sum(rate(llm_tokens_total[1h]))` | Token usage |

### 6.3 Alertmanager Rules

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: codegraph-alerts
  namespace: codegraph
spec:
  groups:
    - name: codegraph
      rules:
        - alert: CodeGraphHighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "High error rate on CodeGraph API"

        - alert: CodeGraphDLPHighBlockRate
          expr: rate(dlp_blocks_total[5m]) / rate(llm_requests_total[5m]) > 0.2
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "DLP blocking more than 20% of requests"

        - alert: CodeGraphPodNotReady
          expr: kube_pod_status_ready{namespace="codegraph", condition="true"} == 0
          for: 5m
          labels:
            severity: critical
          annotations:
            summary: "CodeGraph pod not ready"
```

---

## 7. Backup and Recovery

### 7.1 PostgreSQL Backup

```bash
#!/bin/bash
# backup-postgres.sh

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
NAMESPACE="codegraph"

# Create backup
kubectl exec -n $NAMESPACE postgres-0 -- \
  pg_dump -U postgres codegraph | gzip > $BACKUP_DIR/codegraph_$DATE.sql.gz

# Remove old backups (older than 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### 7.2 DuckDB Backup

```bash
#!/bin/bash
# backup-duckdb.sh

BACKUP_DIR="/backups/duckdb"
DATE=$(date +%Y%m%d_%H%M%S)

# Copy DuckDB files
kubectl cp codegraph/codegraph-api-0:/app/data/duckdb $BACKUP_DIR/duckdb_$DATE

# Compress
tar -czvf $BACKUP_DIR/duckdb_$DATE.tar.gz -C $BACKUP_DIR duckdb_$DATE
rm -rf $BACKUP_DIR/duckdb_$DATE
```

### 7.3 Disaster Recovery

| RPO | RTO | Strategy |
|-----|-----|----------|
| 1 hour | 4 hours | Hourly snapshots, standby cluster |
| 24 hours | 24 hours | Daily backups, manual recovery |
| 1 week | 72 hours | Weekly backups, cold standby |

---

## 8. Migration and Upgrades

### 8.1 Rolling Update

```bash
# Update image with zero downtime
kubectl set image deployment/codegraph-api \
  api=codegraph:v2.0.0 \
  -n codegraph

# Monitor rollout
kubectl rollout status deployment/codegraph-api -n codegraph

# Rollback on issues
kubectl rollout undo deployment/codegraph-api -n codegraph
```

### 8.2 Database Migration

```bash
# Run Alembic migrations
kubectl exec -n codegraph deployment/codegraph-api -- \
  python -m alembic upgrade head

# Check current version
kubectl exec -n codegraph deployment/codegraph-api -- \
  python -m alembic current
```

---

## Related Documents

- [Enterprise Security Brief](./SECURITY_BRIEF.md) — Security overview
- [RBAC Authorization](./RBAC.md) — Access control
- [SIEM Integration](./SIEM.md) — SIEM integration
- [LLM Security](./LLM_SECURITY.md) — LLM interaction protection

---

*Version: 1.0 | December 2025*
