"""
Localization for security reports.

Provides translations for report templates in multiple languages.
"""

from typing import Dict, Optional


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'ru': {
        # Headers
        'security_audit_report': 'Отчёт по безопасности',
        'project_path': 'Путь к проекту',
        'audit_time': 'Время аудита',
        'duration': 'Длительность',
        'duration_seconds': 'секунд',
        'files_scanned': 'Проанализировано файлов',
        'methods_analyzed': 'Проанализировано методов',
        'calls_analyzed': 'Проанализировано вызовов',

        # Summary
        'executive_summary': 'Краткое резюме',
        'severity': 'Серьёзность',
        'count': 'Количество',
        'total': 'ВСЕГО',
        'metric': 'Метрика',
        'value': 'Значение',

        # Risk assessment
        'risk_assessment': 'Оценка рисков',
        'critical_risk': 'КРИТИЧЕСКИЙ РИСК: В проекте обнаружены критические уязвимости, требующие немедленного исправления!',
        'high_risk': 'ВЫСОКИЙ РИСК: В проекте обнаружены серьёзные уязвимости, которые следует исправить в ближайшее время.',
        'medium_risk': 'СРЕДНИЙ РИСК: В проекте обнаружены уязвимости средней серьёзности.',
        'low_risk': 'НИЗКИЙ РИСК: В проекте обнаружены незначительные проблемы безопасности.',

        # Findings
        'potential_vulnerabilities': 'Потенциальные уязвимости',
        'findings': 'Найденные уязвимости',
        'severity_findings': 'Уязвимости уровня',
        'pattern_id': 'ID паттерна',
        'pattern_name': 'Название паттерна',
        'file': 'Файл',
        'line': 'Строка',
        'method': 'Метод',
        'code': 'Код',
        'description': 'Описание',
        'vulnerable_code': 'Уязвимый код',
        'cwe': 'CWE',

        # D3FEND
        'd3fend_compliance': 'Соответствие D3FEND Source Code Hardening',
        'd3fend_section': 'D3FEND Hardening',
        'technique': 'Техника',
        'technique_name': 'Название техники',
        'found': 'Найдено',
        'status': 'Статус',
        'compliance_score': 'Общий показатель соответствия',
        'passing': 'Соответствует',
        'failing': 'Не соответствует',
        'not_checked': 'Не проверено',
        'applicability': 'Применимость',
        'c_cpp_only': 'Только C/C++ (не применимо для Python)',
        'python_applicable': 'Применимо для Python',
        'applicable': 'Применимо',
        'applicable_techniques': 'применимых техник',
        'credential_findings_detail': 'Детали найденных учётных данных (D3-CS)',

        # D3FEND technique descriptions
        'd3-vi': 'Инициализация переменных',
        'd3-cs': 'Очистка учётных данных',
        'd3-irv': 'Валидация диапазонов целых чисел',
        'd3-pv': 'Валидация указателей',
        'd3-rn': 'Обнуление ссылок',
        'd3-tl': 'Использование доверенных библиотек',
        'd3-vtv': 'Валидация типов переменных',
        'd3-mbsv': 'Валидация границ блоков памяти',
        'd3-npc': 'Проверка NULL-указателей',
        'd3-dlv': 'Валидация доменной логики',
        'd3-olv': 'Валидация операционной логики',

        # Severity labels
        'critical': 'КРИТИЧЕСКИЙ',
        'high': 'ВЫСОКИЙ',
        'medium': 'СРЕДНИЙ',
        'low': 'НИЗКИЙ',
        'info': 'ИНФОРМАЦИЯ',

        # ORM Analysis
        'orm_usage_analysis': 'Анализ использования ORM',
        'operation': 'Операция',
        'calls_count': 'Количество вызовов',
        'operation_description': 'Описание',

        # Recommendations
        'recommendations': 'Рекомендации',
        'recommendations_summary': 'Сводка рекомендаций',
        'problem': 'Проблема',
        'solution': 'Решение',
        'example': 'Пример',
        'priority': 'Приоритет',
        'effort': 'Трудозатраты',
        'effort_low': 'Низкие',
        'effort_medium': 'Средние',
        'effort_high': 'Высокие',
        'priority_high': 'Высокий',
        'priority_medium': 'Средний',
        'priority_low': 'Низкий',

        # Vulnerability types
        'sql_injection': 'SQL-инъекция',
        'sql_injection_desc': 'Возможность SQL-инъекции при конкатенации пользовательского ввода',
        'xss': 'Межсайтовый скриптинг (XSS)',
        'xss_desc': 'Неэкранированный пользовательский ввод в HTML-ответе',
        'csrf': 'Межсайтовая подделка запроса (CSRF)',
        'csrf_desc': 'Отсутствие CSRF-защиты на эндпоинте',
        'path_traversal': 'Обход пути (Path Traversal)',
        'path_traversal_desc': 'Возможность доступа к произвольным файлам',
        'command_injection': 'Инъекция команд',
        'command_injection_desc': 'Выполнение произвольных команд ОС',
        'insecure_deserialization': 'Небезопасная десериализация',
        'insecure_deserialization_desc': 'Десериализация данных из ненадёжного источника',
        'hardcoded_credentials': 'Захардкоженные учётные данные',
        'hardcoded_credentials_desc': 'Пароли или ключи API в исходном коде',
        'auth_bypass': 'Обход аутентификации',
        'auth_bypass_desc': 'Отсутствие проверки аутентификации',

        # Remediation templates
        'use_parameterized_queries': 'Используйте параметризованные запросы вместо конкатенации строк',
        'escape_output': 'Экранируйте пользовательский ввод перед выводом в HTML',
        'add_csrf_protection': 'Добавьте CSRF-токен или декоратор @csrf_protect',
        'validate_file_paths': 'Валидируйте пути файлов и используйте os.path.basename()',
        'avoid_shell_true': 'Избегайте shell=True и используйте списки аргументов',
        'use_safe_deserialize': 'Используйте безопасные методы десериализации',
        'use_env_variables': 'Храните учётные данные в переменных окружения',
        'add_auth_decorator': 'Добавьте декоратор @login_required или @permission_required',

        # D3FEND specific remediation
        'remediation_d3_cs': 'Никогда не храните учётные данные в исходном коде:\n- Используйте переменные окружения: os.environ["SECRET_KEY"]\n- Используйте файлы конфигурации (не в VCS)\n- Используйте сервисы управления секретами (Vault, AWS Secrets Manager)',
        'remediation_d3_vi': 'Всегда инициализируйте переменные при объявлении:\n- Используйте = 0 для целых чисел\n- Используйте = NULL для указателей\n- Используйте = {} или = {0} для структур/массивов',
        'remediation_d3_npc': 'Всегда проверяйте результаты выделения памяти перед использованием:\n- Проверяйте на NULL сразу после выделения\n- Обрабатывайте ошибки выделения корректно',
        'remediation_d3_tl': 'Замените небезопасные функции безопасными альтернативами:\n- strcpy → strncpy, strlcpy или snprintf\n- sprintf → snprintf\n- gets → fgets\n- strtok → strtok_r',
        'remediation_d3_rn': 'Всегда обнуляйте указатели после освобождения:\n- Устанавливайте указатель в NULL сразу после free()\n- Используйте макросы, объединяющие free и обнуление',
        'remediation_sql_injection': 'Используйте параметризованные запросы или Django ORM вместо raw SQL',
        'remediation_path_traversal': 'Валидируйте пути с помощью os.path.realpath() и проверяйте префикс',

        # File-based pattern remediation (FILE_*)
        'remediation_file_secret_fallback_001': 'Удалите fallback-значение: SECRET_KEY = os.environ["SECRET_KEY"]',
        'remediation_file_django_debug_001': 'Установите DEBUG=False в production, используйте env var без True по умолчанию',
        'remediation_file_cors_001': 'Установите CORS_ALLOW_ALL_ORIGINS=False, используйте CORS_ALLOWED_ORIGINS',
        'remediation_file_hosts_001': 'Укажите явные имена хостов в ALLOWED_HOSTS',
        'remediation_file_jwt_001': 'Установите ACCESS_TOKEN_LIFETIME в минутах, используйте refresh tokens',
        'remediation_file_db_001': 'Удалите fallback для пароля БД, требуйте DB_PASSWORD через env var',
        'remediation_file_toolbar_001': 'Включайте debug_toolbar только когда DEBUG=True',
        'remediation_file_path_001': 'Валидируйте пути с помощью os.path.realpath() и проверяйте префикс',
        'remediation_file_debug_perm_001': 'Никогда не используйте DEBUG в проверках разрешений, используйте RBAC',
        'remediation_file_pagesize_001': 'Установите PAGE_SIZE в разумное значение (10-100), добавьте MAX_PAGE_SIZE',

        # File-based pattern descriptions (FILE_*)
        'desc_file_secret_fallback_001': 'SECRET_KEY с небезопасным fallback-значением',
        'desc_file_django_debug_001': 'Django DEBUG режим включён по умолчанию',
        'desc_file_cors_001': 'CORS настроен на разрешение всех origin',
        'desc_file_hosts_001': 'ALLOWED_HOSTS содержит wildcard',
        'desc_file_jwt_001': 'Слишком долгое время жизни JWT access token (дни/недели)',
        'desc_file_db_001': 'Пароль БД по умолчанию в настройках',
        'desc_file_toolbar_001': 'Django Debug Toolbar безусловно включён',
        'desc_file_path_001': 'Файловая операция без валидации пути',
        'desc_file_debug_perm_001': 'Проверка разрешений на основе DEBUG',
        'desc_file_pagesize_001': 'Слишком большой PAGE_SIZE в REST_FRAMEWORK (риск DoS)',

        # Appendix
        'appendix': 'Приложение',
        'security_patterns_checked': 'Проверенные паттерны безопасности',
        'pattern': 'Паттерн',
        'detected': 'Обнаружено',
        'not_detected': 'Не обнаружено',
        'review_needed': 'Требует проверки',

        # Remediation (label)
        'remediation': 'Рекомендация',

        # Footer
        'generated_by': 'Отчёт сгенерирован CodeGraph Security Audit Pipeline',
        'report_version': 'Версия отчёта',

        # Errors
        'errors_during_scan': 'Ошибки во время сканирования',
    },
    'en': {
        # Headers
        'security_audit_report': 'Security Audit Report',
        'project_path': 'Project Path',
        'audit_time': 'Audit Time',
        'duration': 'Duration',
        'duration_seconds': 'seconds',
        'files_scanned': 'Files Scanned',
        'methods_analyzed': 'Methods Analyzed',
        'calls_analyzed': 'Calls Analyzed',

        # Summary
        'executive_summary': 'Executive Summary',
        'severity': 'Severity',
        'count': 'Count',
        'total': 'TOTAL',
        'metric': 'Metric',
        'value': 'Value',

        # Risk assessment
        'risk_assessment': 'Risk Assessment',
        'critical_risk': 'CRITICAL RISK: This project has critical security vulnerabilities that must be addressed immediately!',
        'high_risk': 'HIGH RISK: This project has high severity vulnerabilities that should be addressed soon.',
        'medium_risk': 'MEDIUM RISK: This project has medium severity vulnerabilities.',
        'low_risk': 'LOW RISK: This project has minor security issues.',

        # Findings
        'potential_vulnerabilities': 'Potential Vulnerabilities',
        'findings': 'Findings',
        'severity_findings': 'Severity Findings',
        'pattern_id': 'Pattern ID',
        'pattern_name': 'Pattern Name',
        'file': 'File',
        'line': 'Line',
        'method': 'Method',
        'code': 'Code',
        'description': 'Description',
        'vulnerable_code': 'Vulnerable Code',
        'cwe': 'CWE',

        # D3FEND
        'd3fend_compliance': 'D3FEND Source Code Hardening Compliance',
        'd3fend_section': 'D3FEND Hardening',
        'technique': 'Technique',
        'technique_name': 'Technique Name',
        'found': 'Found',
        'status': 'Status',
        'compliance_score': 'Overall Compliance Score',
        'passing': 'Passing',
        'failing': 'Failing',
        'not_checked': 'Not Checked',
        'applicability': 'Applicability',
        'c_cpp_only': 'C/C++ only (not applicable for Python)',
        'python_applicable': 'Applicable for Python',
        'applicable': 'Applicable',
        'applicable_techniques': 'applicable techniques',
        'credential_findings_detail': 'Credential Findings Details (D3-CS)',

        # D3FEND technique descriptions
        'd3-vi': 'Variable Initialization',
        'd3-cs': 'Credential Scrubbing',
        'd3-irv': 'Integer Range Validation',
        'd3-pv': 'Pointer Validation',
        'd3-rn': 'Reference Nullification',
        'd3-tl': 'Trusted Library',
        'd3-vtv': 'Variable Type Validation',
        'd3-mbsv': 'Memory Block Start Validation',
        'd3-npc': 'Null Pointer Checking',
        'd3-dlv': 'Domain Logic Validation',
        'd3-olv': 'Operational Logic Validation',

        # Severity labels
        'critical': 'CRITICAL',
        'high': 'HIGH',
        'medium': 'MEDIUM',
        'low': 'LOW',
        'info': 'INFO',

        # ORM Analysis
        'orm_usage_analysis': 'ORM Usage Analysis',
        'operation': 'Operation',
        'calls_count': 'Call Count',
        'operation_description': 'Description',

        # Recommendations
        'recommendations': 'Recommendations',
        'recommendations_summary': 'Recommendations Summary',
        'problem': 'Problem',
        'solution': 'Solution',
        'example': 'Example',
        'priority': 'Priority',
        'effort': 'Effort',
        'effort_low': 'Low',
        'effort_medium': 'Medium',
        'effort_high': 'High',
        'priority_high': 'High',
        'priority_medium': 'Medium',
        'priority_low': 'Low',

        # Vulnerability types
        'sql_injection': 'SQL Injection',
        'sql_injection_desc': 'SQL Injection via user input concatenation',
        'xss': 'Cross-Site Scripting (XSS)',
        'xss_desc': 'Unescaped user input in HTML response',
        'csrf': 'Cross-Site Request Forgery (CSRF)',
        'csrf_desc': 'Missing CSRF protection on endpoint',
        'path_traversal': 'Path Traversal',
        'path_traversal_desc': 'Arbitrary file access vulnerability',
        'command_injection': 'Command Injection',
        'command_injection_desc': 'Arbitrary OS command execution',
        'insecure_deserialization': 'Insecure Deserialization',
        'insecure_deserialization_desc': 'Deserializing data from untrusted source',
        'hardcoded_credentials': 'Hardcoded Credentials',
        'hardcoded_credentials_desc': 'Passwords or API keys in source code',
        'auth_bypass': 'Authentication Bypass',
        'auth_bypass_desc': 'Missing authentication check',

        # Remediation templates
        'use_parameterized_queries': 'Use parameterized queries instead of string concatenation',
        'escape_output': 'Escape user input before rendering in HTML',
        'add_csrf_protection': 'Add CSRF token or @csrf_protect decorator',
        'validate_file_paths': 'Validate file paths and use os.path.basename()',
        'avoid_shell_true': 'Avoid shell=True and use argument lists',
        'use_safe_deserialize': 'Use safe deserialization methods',
        'use_env_variables': 'Store credentials in environment variables',
        'add_auth_decorator': 'Add @login_required or @permission_required decorator',

        # Appendix
        'appendix': 'Appendix',
        'security_patterns_checked': 'Security Patterns Checked',
        'pattern': 'Pattern',
        'detected': 'Detected',
        'not_detected': 'Not Detected',
        'review_needed': 'Review Needed',

        # Remediation (label)
        'remediation': 'Remediation',

        # Footer
        'generated_by': 'Report generated by CodeGraph Security Audit Pipeline',
        'report_version': 'Report Version',

        # Errors
        'errors_during_scan': 'Errors During Scan',
    }
}


class ReportLocalizer:
    """
    Localization helper for security reports.

    Usage:
        loc = ReportLocalizer('ru')
        print(loc.t('executive_summary'))  # -> 'Краткое резюме'
    """

    def __init__(self, language: str = 'en'):
        """
        Initialize localizer with specified language.

        Args:
            language: Language code ('en' or 'ru')
        """
        self.language = language
        self.translations = TRANSLATIONS.get(language, TRANSLATIONS['en'])

    def t(self, key: str, default: Optional[str] = None) -> str:
        """
        Get translation for key.

        Args:
            key: Translation key
            default: Default value if key not found

        Returns:
            Translated string
        """
        return self.translations.get(key, default or key)

    def severity_label(self, severity: str) -> str:
        """Get localized severity label."""
        return self.t(severity.lower(), severity.upper())

    def severity_emoji(self, severity: str) -> str:
        """Get emoji for severity level."""
        emojis = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢',
            'info': '🔵',
        }
        return emojis.get(severity.lower(), '⚪')

    def d3fend_technique_name(self, technique_id: str) -> str:
        """Get localized D3FEND technique name."""
        key = technique_id.lower().replace('_', '-')
        return self.t(key, technique_id)

    def effort_label(self, effort: str) -> str:
        """Get localized effort label."""
        key = f'effort_{effort.lower()}'
        return self.t(key, effort)

    def priority_label(self, priority: str) -> str:
        """Get localized priority label."""
        key = f'priority_{priority.lower()}'
        return self.t(key, priority)

    def localize_remediation(self, finding: dict) -> str:
        """
        Get localized remediation text for a finding.

        Args:
            finding: Finding dictionary with pattern_id, d3fend_id, or remediation

        Returns:
            Localized remediation text
        """
        # Try D3FEND-specific remediation first
        d3fend_id = finding.get('d3fend_id', '')
        if d3fend_id:
            key = f'remediation_{d3fend_id.lower().replace("-", "_")}'
            localized = self.translations.get(key)
            if localized:
                return localized

        # Try pattern-specific remediation
        pattern_id = finding.get('pattern_id', '')
        if pattern_id:
            # Try FILE_* pattern keys first (e.g., FILE_SECRET_FALLBACK_001 -> remediation_file_secret_fallback_001)
            if pattern_id.upper().startswith('FILE_'):
                key = f'remediation_{pattern_id.lower()}'
                localized = self.translations.get(key)
                if localized:
                    return localized

            # Map common patterns to localization keys
            pattern_map = {
                'SQL_INJECTION': 'remediation_sql_injection',
                'DJANGO_SQL_INJECTION': 'remediation_sql_injection',
                'PATH_TRAVERSAL': 'remediation_path_traversal',
                'FILE_PATH_001': 'remediation_path_traversal',
                'HARDCODED_CREDENTIAL': 'remediation_d3_cs',
                'D3-CS-001': 'remediation_d3_cs',
            }
            key = pattern_map.get(pattern_id.upper())
            if key:
                localized = self.translations.get(key)
                if localized:
                    return localized

        # Fall back to original remediation text
        return finding.get('remediation', '')

    def localize_description(self, finding: dict) -> str:
        """
        Get localized description text for a finding.

        Args:
            finding: Finding dictionary with pattern_id or description

        Returns:
            Localized description text
        """
        pattern_id = finding.get('pattern_id', '')
        if pattern_id:
            # Try FILE_* pattern keys first (e.g., FILE_SECRET_FALLBACK_001 -> desc_file_secret_fallback_001)
            if pattern_id.upper().startswith('FILE_'):
                key = f'desc_{pattern_id.lower()}'
                localized = self.translations.get(key)
                if localized:
                    return localized

            # Map common patterns to localization keys
            pattern_map = {
                'SQL_INJECTION': 'sql_injection_desc',
                'DJANGO_SQL_INJECTION': 'sql_injection_desc',
                'PATH_TRAVERSAL': 'path_traversal_desc',
                'HARDCODED_CREDENTIAL': 'hardcoded_credentials_desc',
                'D3-CS-001': 'hardcoded_credentials_desc',
            }
            key = pattern_map.get(pattern_id.upper())
            if key:
                localized = self.translations.get(key)
                if localized:
                    return localized

        # Fall back to original description text
        return finding.get('description', '')


def get_localizer(language: str = 'en') -> ReportLocalizer:
    """
    Factory function to get a localizer instance.

    Args:
        language: Language code ('en' or 'ru')

    Returns:
        ReportLocalizer instance
    """
    return ReportLocalizer(language)


__all__ = ['ReportLocalizer', 'get_localizer', 'TRANSLATIONS']
