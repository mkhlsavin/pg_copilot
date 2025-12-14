# Конкурентная матрица CodeGraph

> Сравнительный анализ для RFP и принятия решений

---

## Резюме

CodeGraph — единственное решение, сочетающее:
- **CPG-based анализ** с верификацией уязвимостей через taint-анализ
- **Интегрированную DLP-защиту** при работе с LLM
- **SIEM-интеграцию** в трёх форматах (Syslog, CEF, LEEF)
- **Российский LLM** (GigaChat) для соответствия 152-ФЗ
- **Многокритериальную валидацию гипотез** для снижения false positives

---

## Сводная таблица сравнения

| Функция | CodeGraph | GitHub Copilot | Sourcegraph | CodeScene | SonarQube |
|---------|:---------:|:--------------:|:-----------:|:---------:|:---------:|
| **Развёртывание** |
| On-Premise | ✅ | ❌ | ✅ | ✅ | ✅ |
| Air-Gapped | ✅ | ❌ | ⚠️ Частично | ⚠️ Частично | ✅ |
| Kubernetes | ✅ | ❌ | ✅ | ✅ | ✅ |
| Docker | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Резиденция данных** |
| Код внутри периметра | ✅ | ❌ | ✅ | ✅ | ✅ |
| Российский LLM | ✅ GigaChat | ❌ | ❌ | ❌ | ❌ |
| 152-ФЗ compliance | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| **Безопасность** |
| RBAC | ✅ 4 роли, 21 разрешение | ⚠️ GitHub roles | ✅ | ✅ | ✅ |
| **Интегрированная DLP** | ✅ 25+ паттернов | ❌ | ❌ | ❌ | ❌ |
| **SIEM интеграция** | ✅ Syslog/CEF/LEEF | ❌ | ❌ | ❌ | ⚠️ Webhook |
| **HashiCorp Vault** | ✅ | ❌ | ❌ | ❌ | ❌ |
| JWT + API Keys | ✅ | ✅ GitHub tokens | ✅ | ✅ | ✅ |
| OAuth2/OIDC | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Анализ кода** |
| Code Property Graph | ✅ Joern CPG | ❌ | ✅ Собственный | ⚠️ Behavioral | ❌ AST |
| Taint Analysis | ✅ | ❌ | ✅ | ❌ | ⚠️ Ограничено |
| **Taint-Verified Vulns** | ✅ | ❌ | ⚠️ Частично | ❌ | ❌ |
| Data Flow | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| Control Flow | ✅ | ❌ | ✅ | ⚠️ | ⚠️ |
| **Поиск уязвимостей** |
| SAST | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Multi-Criteria Scoring** | ✅ | ❌ | ❌ | ❌ | ❌ |
| CWE/CAPEC mapping | ✅ | ❌ | ⚠️ | ⚠️ | ✅ |
| Hypothesis Validation | ✅ | ❌ | ❌ | ❌ | ❌ |
| **LLM интеграция** |
| AI Copilot | ✅ | ✅ | ✅ Cody | ❌ | ❌ |
| LLM Security Layer | ✅ DLP + Audit | ❌ | ❌ | ❌ | ❌ |
| Prompt Protection | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Языки** |
| C/C++ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Java | ✅ | ✅ | ✅ | ✅ | ✅ |
| Python | ✅ | ✅ | ✅ | ✅ | ✅ |
| JavaScript/TypeScript | ✅ | ✅ | ✅ | ✅ | ✅ |
| Go | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Rust | ⚠️ | ✅ | ⚠️ | ❌ | ⚠️ |

**Легенда:** ✅ Полная поддержка | ⚠️ Частичная поддержка | ❌ Не поддерживается

---

## Уникальные преимущества CodeGraph

### 1. Единственная платформа с интегрированной DLP

```
                    CodeGraph                    Конкуренты
                    ─────────                    ──────────
User Query ──► [DLP Scanner] ──► LLM       User Query ──► LLM
                    │                                │
                    ▼                                ▼
              Block/Mask/Log                   Без защиты
```

**Почему это важно:**
- Предотвращение утечки секретов через LLM-промпты
- Маскирование PII в ответах LLM
- Соответствие GDPR и 152-ФЗ

### 2. Единственная платформа с SIEM в трёх форматах

| CodeGraph | GitHub Copilot | Sourcegraph | CodeScene |
|:---------:|:--------------:|:-----------:|:---------:|
| Syslog RFC 5424 | ❌ | ❌ | ❌ |
| CEF (ArcSight) | ❌ | ❌ | ❌ |
| LEEF (QRadar) | ❌ | ❌ | ❌ |

**Почему это важно:**
- Интеграция с существующим SOC
- Centralized security monitoring
- Compliance audit trail

### 3. Единственная платформа с Vault интеграцией

```yaml
# CodeGraph
vault:
  enabled: true
  auth_method: approle
  auto_rotation: true

# Конкуренты: только env vars или plaintext configs
```

**Почему это важно:**
- Централизованное управление секретами
- Автоматическая ротация API-ключей
- Kubernetes-native авторизация

### 4. Taint-Verified уязвимости

```
CodeGraph:
Source ──[data flow]──► Sink = CONFIRMED vulnerability

Традиционный SAST:
Pattern match = POSSIBLE vulnerability (high false positive rate)
```

**Результат:**
- 100% CVE detection rate (3/3 целевых CVE)
- Снижение false positives на 60%+
- Приоритизация по реальному риску

### 5. Многокритериальная валидация гипотез

```
Priority Score = (CWE Frequency × 0.40)
               + (Attack Similarity × 0.30)
               + (Codebase Exposure × 0.30)
```

**Конкуренты:** статический severity без учёта контекста кодовой базы

---

## Сравнение по сценариям использования

### Сценарий 1: Enterprise Security Audit

| Требование | CodeGraph | GitHub Copilot | Sourcegraph |
|------------|:---------:|:--------------:|:-----------:|
| Выявление buffer overflow | ✅ CPG + Taint | ❌ | ✅ |
| Верификация потока данных | ✅ | ❌ | ✅ |
| Приоритизация по риску | ✅ Multi-criteria | ❌ | ⚠️ Severity only |
| Аудит LLM-взаимодействий | ✅ | ❌ | ❌ |
| SIEM отчётность | ✅ | ❌ | ❌ |

### Сценарий 2: Код-ревью с AI

| Требование | CodeGraph | GitHub Copilot | Sourcegraph Cody |
|------------|:---------:|:--------------:|:----------------:|
| AI-assisted review | ✅ | ✅ | ✅ |
| CPG-based analysis | ✅ | ❌ | ⚠️ |
| DLP protection | ✅ | ❌ | ❌ |
| On-premise LLM | ✅ GigaChat | ❌ Cloud only | ⚠️ Limited |
| Audit trail | ✅ | ❌ | ⚠️ |

### Сценарий 3: Compliance (152-ФЗ, GDPR)

| Требование | CodeGraph | GitHub Copilot | Sourcegraph |
|------------|:---------:|:--------------:|:-----------:|
| Данные в РФ | ✅ On-prem | ❌ US cloud | ⚠️ On-prem |
| Российский LLM | ✅ GigaChat | ❌ | ❌ |
| DLP для PII | ✅ | ❌ | ❌ |
| Audit logging | ✅ | ⚠️ | ⚠️ |
| SIEM integration | ✅ | ❌ | ❌ |

---

## Ценообразование (ориентировочное)

| Решение | Модель | Примерная стоимость |
|---------|--------|---------------------|
| **CodeGraph** | Per-developer | $20-50/dev/month |
| GitHub Copilot Business | Per-developer | $19/dev/month |
| GitHub Copilot Enterprise | Per-developer | $39/dev/month |
| Sourcegraph Enterprise | Per-developer | $49+/dev/month |
| CodeScene | Per-developer | Custom pricing |
| SonarQube Enterprise | Per-instance | $20K+/year |

**Примечание:** CodeGraph включает все enterprise-функции (DLP, SIEM, Vault) без дополнительной платы.

---

## Матрица соответствия требованиям

### Для финансовых организаций (ГОСТ Р 57580)

| Требование | CodeGraph | Альтернативы |
|------------|:---------:|:------------:|
| On-premise развёртывание | ✅ | ⚠️ |
| Аудит всех операций | ✅ | ⚠️ |
| RBAC с гранулярными правами | ✅ | ⚠️ |
| Интеграция с SIEM | ✅ | ❌ |
| Шифрование at-rest | ✅ | ✅ |
| Управление секретами | ✅ Vault | ⚠️ |

### Для государственных организаций

| Требование | CodeGraph | Альтернативы |
|------------|:---------:|:------------:|
| 152-ФЗ compliance | ✅ | ❌ |
| Российский LLM | ✅ | ❌ |
| Сертификация ФСТЭК (roadmap) | ⚠️ Planned | ❌ |
| Air-gapped deployment | ✅ | ⚠️ |

---

## Заключение

CodeGraph — **единственное решение** на рынке, объединяющее:

1. **CPG-based анализ** с taint-verified уязвимостями
2. **Интегрированную DLP** для защиты LLM-взаимодействий
3. **SIEM интеграцию** в трёх enterprise-форматах
4. **HashiCorp Vault** для управления секретами
5. **Российский LLM** для compliance с 152-ФЗ
6. **Многокритериальную валидацию** для снижения false positives

Ни один конкурент не предлагает все эти возможности в едином решении.

---

## Связанные документы

- [Enterprise Security Brief](./ENTERPRISE_SECURITY_BRIEF.md) — Обзор безопасности
- [Hypothesis Validation Whitepaper](./HYPOTHESIS_VALIDATION_WHITEPAPER.md) — Техническое описание
- [Business Case](../sber500/BUSINESS_CASE.md) — Бизнес-кейс

---

*Версия: 1.0 | Декабрь 2025*
