"""
Ruby Security Patterns

Patterns for detecting vulnerabilities specific to Ruby and Rails:
- Eval/system injection
- YAML deserialization (CVE-2013-0156)
- Mass assignment
- SQL injection via ActiveRecord
- XSS in ERB templates

CWE-78, CWE-89, CWE-94, CWE-502, CWE-79, CWE-915
"""

from typing import Dict
from .._base import (
    SecurityPattern,
    VulnerabilityCategory,
    VulnerabilitySeverity,
)


EVAL_INJECTION_RUBY_PATTERN = SecurityPattern(
    id="RUBY_EVAL_001",
    name="Code Injection via eval/instance_eval",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Dynamic code execution using eval, instance_eval, class_eval, or "
        "module_eval with user-controlled input."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'EVAL_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('eval', 'instance_eval', 'class_eval', 'module_eval',
                          'instance_exec', 'class_exec', 'send', 'public_send')
          AND nc.method_full_name NOT LIKE 'test_%'
          AND nc.method_full_name NOT LIKE '*_spec*'
        LIMIT 50;
    """,
    cwe_ids=["CWE-94", "CWE-95"],
    remediation=(
        "1. Never use eval with user input\n"
        "2. Use safe alternatives (JSON.parse, case statements)\n"
        "3. Use send with symbol whitelist only\n"
        "4. Implement Content Security Policy"
    ),
    example_code="""
        # VULNERABLE
        eval(params[:code])
        instance_eval(user_input)
        send(params[:method], args)

        # SECURE
        allowed_methods = [:method1, :method2]
        method = params[:method].to_sym
        send(method, args) if allowed_methods.include?(method)
    """,
    test_cases=[
        {"name": "eval with params", "method": "execute", "expected": True, "contains": ["eval"]}
    ]
)


COMMAND_INJECTION_RUBY_PATTERN = SecurityPattern(
    id="RUBY_CMD_001",
    name="Command Injection via system/exec/backticks",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "OS command injection through system(), exec(), backticks (`), %x{}, "
        "or Open3 with unsanitized user input."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'COMMAND_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('system', 'exec', 'spawn', 'popen', 'Open3.capture2',
                          'Open3.capture3', 'IO.popen')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-78"],
    remediation=(
        "1. Use array form of system() to avoid shell\n"
        "2. Use Shellwords.escape for shell arguments\n"
        "3. Validate input against strict whitelist\n"
        "4. Use Ruby libraries instead of shell commands"
    ),
    example_code="""
        # VULNERABLE
        system("ls #{params[:dir]}")
        `grep #{user_input} file.txt`

        # SECURE
        system("ls", "-la", sanitized_dir)
        system(["grep", user_input, "file.txt"])
    """,
    test_cases=[
        {"name": "system with interpolation", "method": "listFiles", "expected": True, "contains": ["system"]}
    ]
)


YAML_DESERIALIZATION_PATTERN = SecurityPattern(
    id="RUBY_YAML_001",
    name="Unsafe YAML Deserialization",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "Unsafe YAML.load allows arbitrary Ruby object instantiation, "
        "leading to remote code execution (CVE-2013-0156)."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'YAML_DESERIALIZATION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name = 'load'
          AND nc.code LIKE '%YAML%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-502"],
    remediation=(
        "1. Use YAML.safe_load instead of YAML.load\n"
        "2. Specify permitted_classes if needed\n"
        "3. Use JSON for untrusted data\n"
        "4. Update to Ruby >= 3.1 with Psych 4.0"
    ),
    example_code="""
        # VULNERABLE
        data = YAML.load(user_input)
        YAML.load(File.read(user_path))

        # SECURE
        data = YAML.safe_load(user_input)
        YAML.safe_load(content, permitted_classes: [Date, Time])
    """,
    test_cases=[
        {"name": "YAML.load with user input", "method": "parseConfig", "expected": True, "contains": ["YAML.load"]}
    ]
)


SQL_INJECTION_RAILS_PATTERN = SecurityPattern(
    id="RUBY_SQL_001",
    name="SQL Injection in ActiveRecord",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.CRITICAL,
    description=(
        "SQL injection in Rails via string interpolation in where(), find_by_sql(), "
        "or other ActiveRecord methods."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'SQL_INJECTION' AS vulnerability_type,
            'CRITICAL' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('where', 'find_by_sql', 'execute', 'select', 'order',
                          'group', 'having', 'joins', 'from')
          AND (nc.code LIKE '%#%'
               OR nc.code LIKE '%+%')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-89"],
    remediation=(
        "1. Use placeholder syntax: where('name = ?', name)\n"
        "2. Use hash conditions: where(name: name)\n"
        "3. Use sanitize_sql for complex cases\n"
        "4. Use Arel for dynamic queries"
    ),
    example_code="""
        # VULNERABLE
        User.where("name = '#{params[:name]}'")
        User.find_by_sql("SELECT * FROM users WHERE id = " + params[:id])

        # SECURE
        User.where("name = ?", params[:name])
        User.where(name: params[:name])
    """,
    test_cases=[
        {"name": "where with interpolation", "method": "findUser", "expected": True, "contains": ["where", "#{"]}
    ]
)


MASS_ASSIGNMENT_PATTERN = SecurityPattern(
    id="RUBY_MASS_001",
    name="Mass Assignment Vulnerability",
    category=VulnerabilityCategory.ACCESS_CONTROL,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Mass assignment allows attackers to set model attributes that should "
        "be protected (admin, role, password, etc.)."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'MASS_ASSIGNMENT' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('create', 'update', 'update_attributes', 'new',
                          'assign_attributes', 'attributes=')
          AND nc.code LIKE '%params%'
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-915"],
    remediation=(
        "1. Use Strong Parameters in Rails 4+\n"
        "2. Use permit to whitelist attributes\n"
        "3. Never use params.permit! in production\n"
        "4. Define permitted attributes in controller"
    ),
    example_code="""
        # VULNERABLE
        User.create(params[:user])
        @user.update(params[:user].permit!)

        # SECURE
        def user_params
          params.require(:user).permit(:name, :email)
        end
        User.create(user_params)
    """,
    test_cases=[
        {"name": "create with raw params", "method": "createUser", "expected": True, "contains": ["create", "params"]}
    ]
)


XSS_ERB_PATTERN = SecurityPattern(
    id="RUBY_XSS_001",
    name="XSS in ERB Templates",
    category=VulnerabilityCategory.INJECTION,
    severity=VulnerabilitySeverity.HIGH,
    description=(
        "Cross-site scripting via raw() or html_safe in ERB templates, "
        "bypassing Rails automatic escaping."
    ),
    cpgql_query="""
        SELECT DISTINCT
            nc.id,
            nc.name AS method_name,
            nc.method_full_name AS full_name,
            nc.filename,
            nc.line_number,
            nc.code,
            'XSS' AS vulnerability_type,
            'HIGH' AS severity
        FROM nodes_call nc
        WHERE nc.name IN ('raw', 'html_safe', 'safe_concat')
          AND nc.method_full_name NOT LIKE 'test_%'
        LIMIT 50;
    """,
    cwe_ids=["CWE-79"],
    remediation=(
        "1. Avoid raw() and html_safe with user input\n"
        "2. Use sanitize() helper for HTML content\n"
        "3. Use content_tag for dynamic HTML\n"
        "4. Implement Content Security Policy"
    ),
    example_code="""
        # VULNERABLE
        <%= raw(user.bio) %>
        <%= user.content.html_safe %>

        # SECURE
        <%= user.bio %>
        <%= sanitize(user.content) %>
    """,
    test_cases=[
        {"name": "raw with user data", "method": "showBio", "expected": True, "contains": ["raw"]}
    ]
)


# Registry of Ruby patterns
RUBY_PATTERNS: Dict[str, SecurityPattern] = {
    "EVAL_INJECTION": EVAL_INJECTION_RUBY_PATTERN,
    "COMMAND_INJECTION": COMMAND_INJECTION_RUBY_PATTERN,
    "YAML_DESERIALIZATION": YAML_DESERIALIZATION_PATTERN,
    "SQL_INJECTION": SQL_INJECTION_RAILS_PATTERN,
    "MASS_ASSIGNMENT": MASS_ASSIGNMENT_PATTERN,
    "XSS_ERB": XSS_ERB_PATTERN,
}
