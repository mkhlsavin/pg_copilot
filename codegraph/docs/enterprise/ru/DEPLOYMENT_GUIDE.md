# Руководство по корпоративному развёртыванию CodeGraph

> Архитектурное руководство для DevOps и инфраструктурных команд

---

## Table of Contents

- [Обзор](#обзор)
- [1. Системные требования](#1-системные-требования)
  - [1.1 Аппаратные требования](#11-аппаратные-требования)
  - [1.2 Программные требования](#12-программные-требования)
  - [1.3 Сетевые порты](#13-сетевые-порты)
- [2. Docker Compose (разработка)](#2-docker-compose-разработка)
  - [2.1 Структура файлов](#21-структура-файлов)
  - [2.2 docker-compose.yml](#22-docker-composeyml)
  - [2.3 Переменные окружения (.env)](#23-переменные-окружения-env)
  - [2.4 Запуск](#24-запуск)
- [3. Kubernetes (production)](#3-kubernetes-production)
  - [3.1 Архитектура](#31-архитектура)
  - [3.2 Namespace и ConfigMap](#32-namespace-и-configmap)
  - [3.3 Secrets](#33-secrets)
  - [3.4 Deployment](#34-deployment)
  - [3.5 Service и Ingress](#35-service-и-ingress)
  - [3.6 HorizontalPodAutoscaler](#36-horizontalpodautoscaler)
  - [3.7 NetworkPolicy](#37-networkpolicy)
- [4. Air-Gapped развёртывание](#4-air-gapped-развёртывание)
  - [4.1 Особенности изолированной среды](#41-особенности-изолированной-среды)
  - [4.2 Конфигурация для air-gapped](#42-конфигурация-для-air-gapped)
  - [4.3 Подготовка артефактов для air-gapped](#43-подготовка-артефактов-для-air-gapped)
  - [4.4 Установка в air-gapped среде](#44-установка-в-air-gapped-среде)
- [5. Безопасность развёртывания](#5-безопасность-развёртывания)
  - [5.1 TLS/SSL конфигурация](#51-tlsssl-конфигурация)
  - [5.2 Pod Security Standards](#52-pod-security-standards)
  - [5.3 Secrets Encryption](#53-secrets-encryption)
- [6. Мониторинг и наблюдаемость](#6-мониторинг-и-наблюдаемость)
  - [6.1 Prometheus ServiceMonitor](#61-prometheus-servicemonitor)
  - [6.2 Grafana Dashboard](#62-grafana-dashboard)
  - [6.3 Alertmanager правила](#63-alertmanager-правила)
- [7. Резервное копирование и восстановление](#7-резервное-копирование-и-восстановление)
  - [7.1 Бэкап PostgreSQL](#71-бэкап-postgresql)
  - [7.2 Бэкап DuckDB](#72-бэкап-duckdb)
  - [7.3 Disaster Recovery](#73-disaster-recovery)
- [8. Миграция и обновление](#8-миграция-и-обновление)
  - [8.1 Rolling Update](#81-rolling-update)
  - [8.2 Миграция базы данных](#82-миграция-базы-данных)
- [Связанные документы](#связанные-документы)

## Обзор

CodeGraph поддерживает несколько режимов развёртывания для различных требований безопасности и масштабирования:

| Режим | Описание | Рекомендуется для |
|-------|----------|-------------------|
| **Docker Compose** | Один узел, простая настройка | Разработка, тестирование |
| **Kubernetes** | Кластер, HA, автомасштабирование | Production |
| **Air-Gapped** | Изолированная сеть, локальный LLM | Режимные объекты |

---

## 1. Системные требования

### 1.1 Аппаратные требования

| Компонент | Минимум | Рекомендуется | Production |
|-----------|---------|---------------|------------|
| **CPU** | 4 ядра | 8 ядер | 16+ ядер |
| **RAM** | 8 GB | 16 GB | 32+ GB |
| **SSD** | 50 GB | 100 GB | 500+ GB |
| **GPU** | - | NVIDIA 8GB+ | NVIDIA 24GB+ |

**Примечание:** GPU требуется только для локального LLM (air-gapped режим).

### 1.2 Программные требования

| Компонент | Версия | Назначение |
|-----------|--------|------------|
| **Python** | 3.11+ | Основная среда выполнения |
| **PostgreSQL** | 14+ | Хранение пользователей, сессий, аудита |
| **DuckDB** | 1.0+ | Хранение CPG графов |
| **Docker** | 24+ | Контейнеризация (опционально) |
| **Kubernetes** | 1.28+ | Оркестрация (production) |

> **Примечание:** Joern (4.0+) требуется только для первоначальной генерации CPG из исходного кода. После экспорта CPG в DuckDB, Joern больше не нужен для обычной работы.

### 1.3 Сетевые порты

| Порт | Сервис | Протокол |
|------|--------|----------|
| 8000 | CodeGraph API | HTTP/HTTPS |
| 5432 | PostgreSQL | TCP |
| 8080 | Joern Server | HTTP |
| 514 | SIEM (Syslog) | UDP/TCP |
| 8200 | HashiCorp Vault | HTTP/HTTPS |

---

## 2. Docker Compose (разработка)

### 2.1 Структура файлов

```
codegraph/
├── docker-compose.yml
├── docker-compose.override.yml  # Локальные настройки
├── .env                         # Переменные окружения
├── config.yaml                  # Конфигурация приложения
└── data/
    ├── postgres/                # PostgreSQL данные
    ├── duckdb/                  # DuckDB файлы
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

### 2.3 Переменные окружения (.env)

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

# SIEM (если включён)
SIEM_SYSLOG_HOST=siem.company.com
SIEM_SYSLOG_PORT=514

# Vault (если включён)
VAULT_ADDR=https://vault.company.com:8200
VAULT_TOKEN=<vault-token>
```

### 2.4 Запуск

```bash
# Создание .env файла
cp .env.example .env
# Редактирование переменных
nano .env

# Запуск всех сервисов
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f api

# Инициализация базы данных
docker compose exec api python -m alembic upgrade head

# Создание администратора
docker compose exec api python -m scripts.create_admin
```

---

## 3. Kubernetes (production)

### 3.1 Архитектура

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

### 3.2 Namespace и ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: codegraph
  labels:
    name: codegraph
    istio-injection: enabled  # Если используется Istio
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
# Для production используйте External Secrets Operator + Vault
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

### 3.5 Service и Ingress

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
    # Разрешить трафик от ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
    # Разрешить трафик от Prometheus
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
    # GigaChat API (внешний)
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

## 4. Air-Gapped развёртывание

### 4.1 Особенности изолированной среды

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

### 4.2 Конфигурация для air-gapped

```yaml
# config.yaml для air-gapped
llm:
  # Использовать локальный LLM вместо GigaChat
  provider: "local"

  local:
    # Путь к модели (перенесена на носителе)
    model_path: "/models/LLMxCPG-Q-32B-Q4_K_M.gguf"
    use_llmxcpg: true
    n_ctx: 8192
    n_gpu_layers: -1  # Все слои на GPU
    n_batch: 512
    n_threads: 8

security:
  enabled: true

  # DLP работает локально
  dlp:
    enabled: true
    webhook:
      enabled: false  # Нет внешних вебхуков

  # SIEM — локальный сервер
  siem:
    enabled: true
    syslog:
      enabled: true
      host: "siem.local"
      port: 514

  # Vault — локальный экземпляр
  vault:
    enabled: true
    url: "http://vault.local:8200"
    auth_method: "approle"
```

### 4.3 Подготовка артефактов для air-gapped

```bash
#!/bin/bash
# prepare-airgapped.sh — запустить на машине с интернетом

# 1. Скачать Docker образы
docker pull codegraph:latest
docker pull postgres:16-alpine
docker pull ghcr.io/joernio/joern:latest
docker pull hashicorp/vault:1.15

# 2. Сохранить образы в tar
docker save codegraph:latest postgres:16-alpine \
  ghcr.io/joernio/joern:latest hashicorp/vault:1.15 \
  | gzip > codegraph-images.tar.gz

# 3. Скачать LLM модель
wget https://huggingface.co/company/LLMxCPG-Q-32B-GGUF/resolve/main/LLMxCPG-Q-32B-Q4_K_M.gguf

# 4. Скачать Python зависимости
pip download -d ./packages -r requirements.txt

# 5. Упаковать всё
tar -czvf codegraph-airgapped-bundle.tar.gz \
  codegraph-images.tar.gz \
  LLMxCPG-Q-32B-Q4_K_M.gguf \
  packages/ \
  config/ \
  scripts/
```

### 4.4 Установка в air-gapped среде

```bash
#!/bin/bash
# install-airgapped.sh — запустить в изолированной среде

# 1. Распаковать бандл
tar -xzvf codegraph-airgapped-bundle.tar.gz

# 2. Загрузить Docker образы
gunzip -c codegraph-images.tar.gz | docker load

# 3. Установить Python зависимости из локального кэша
pip install --no-index --find-links=./packages -r requirements.txt

# 4. Скопировать модель
cp LLMxCPG-Q-32B-Q4_K_M.gguf /models/

# 5. Запустить сервисы
docker compose -f docker-compose.airgapped.yml up -d
```

---

## 5. Безопасность развёртывания

### 5.1 TLS/SSL конфигурация

```yaml
# Nginx Ingress с TLS 1.3
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
# EncryptionConfiguration для etcd
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

## 6. Мониторинг и наблюдаемость

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

| Панель | Метрика | Описание |
|--------|---------|----------|
| **Request Rate** | `rate(http_requests_total[5m])` | Запросы в секунду |
| **Error Rate** | `rate(http_requests_total{status=~"5.."}[5m])` | Ошибки 5xx |
| **Latency P95** | `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))` | 95-й перцентиль задержки |
| **DLP Blocks** | `rate(dlp_blocks_total[5m])` | Блокировки DLP |
| **LLM Tokens** | `sum(rate(llm_tokens_total[1h]))` | Использование токенов |

### 6.3 Alertmanager правила

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

## 7. Резервное копирование и восстановление

### 7.1 Бэкап PostgreSQL

```bash
#!/bin/bash
# backup-postgres.sh

BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
NAMESPACE="codegraph"

# Создать бэкап
kubectl exec -n $NAMESPACE postgres-0 -- \
  pg_dump -U postgres codegraph | gzip > $BACKUP_DIR/codegraph_$DATE.sql.gz

# Удалить старые бэкапы (старше 30 дней)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

### 7.2 Бэкап DuckDB

```bash
#!/bin/bash
# backup-duckdb.sh

BACKUP_DIR="/backups/duckdb"
DATE=$(date +%Y%m%d_%H%M%S)

# Копировать файлы DuckDB
kubectl cp codegraph/codegraph-api-0:/app/data/duckdb $BACKUP_DIR/duckdb_$DATE

# Сжать
tar -czvf $BACKUP_DIR/duckdb_$DATE.tar.gz -C $BACKUP_DIR duckdb_$DATE
rm -rf $BACKUP_DIR/duckdb_$DATE
```

### 7.3 Disaster Recovery

| RPO | RTO | Стратегия |
|-----|-----|-----------|
| 1 час | 4 часа | Ежечасные снапшоты, запасной кластер |
| 24 часа | 24 часа | Ежедневные бэкапы, ручное восстановление |
| 1 неделя | 72 часа | Еженедельные бэкапы, cold standby |

---

## 8. Миграция и обновление

### 8.1 Rolling Update

```bash
# Обновление образа с нулевым простоем
kubectl set image deployment/codegraph-api \
  api=codegraph:v2.0.0 \
  -n codegraph

# Мониторинг rollout
kubectl rollout status deployment/codegraph-api -n codegraph

# Откат при проблемах
kubectl rollout undo deployment/codegraph-api -n codegraph
```

### 8.2 Миграция базы данных

```bash
# Запуск миграций Alembic
kubectl exec -n codegraph deployment/codegraph-api -- \
  python -m alembic upgrade head

# Проверка текущей версии
kubectl exec -n codegraph deployment/codegraph-api -- \
  python -m alembic current
```

---

## Связанные документы

- [Enterprise Security Brief](./SECURITY_BRIEF.md) — Обзор безопасности
- [RBAC Authorization](./RBAC.md) — Контроль доступа
- [SIEM Integration](./SIEM.md) — Интеграция с SIEM
- [LLM Security](./LLM_SECURITY.md) — Защита LLM-взаимодействий

---

*Версия: 1.0 | Декабрь 2025*
