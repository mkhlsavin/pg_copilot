#!/usr/bin/env python3
"""CPGQL Security Analysis for fsin_module using DuckDB CPG"""
import duckdb
import json
from datetime import datetime

db_path = "workspace/fsin_module.duckdb"
conn = duckdb.connect(db_path, read_only=True)

findings = []

print("=" * 70)
print("   CPGQL SECURITY ANALYSIS: fsin_module")
print("   База данных: workspace/fsin_module.duckdb")
print("=" * 70)

# =============================================================================
# 1. ПОИСК ОПАСНЫХ ВЫЗОВОВ (eval, exec, pickle, subprocess)
# =============================================================================
print("\n## 1. ОПАСНЫЕ ВЫЗОВЫ (Code Execution)")
print("-" * 50)

dangerous_calls = conn.execute("""
    SELECT c."NAME:string" as call_name,
           c."CODE:string" as code,
           c."LINE_NUMBER:int" as line,
           m."FILENAME:string" as file
    FROM nodes_call c
    LEFT JOIN edges_ast a ON c.":ID" = a.":END_ID"
    LEFT JOIN nodes_method m ON a.":START_ID" = m.":ID"
    WHERE c."NAME:string" IN ('eval', 'exec', 'pickle.loads',
                              'pickle.load', 'subprocess.call', 'subprocess.Popen',
                              'os.system', 'os.popen', '__import__')
""").fetchall()

if dangerous_calls:
    for call_name, code, line, file in dangerous_calls:
        print(f"  [CRITICAL] {call_name}")
        print(f"    File: {file}")
        print(f"    Line: {line}")
        print(f"    Code: {code[:80] if code else 'N/A'}...")
        findings.append({
            "type": "CODE_EXECUTION",
            "severity": "CRITICAL",
            "call": call_name,
            "file": file,
            "line": line,
            "code": code
        })
else:
    print("  [OK] Опасных вызовов eval/exec/pickle не найдено")

# =============================================================================
# 2. SQL INJECTION PATTERNS
# =============================================================================
print("\n## 2. SQL INJECTION PATTERNS")
print("-" * 50)

# Ищем вызовы raw(), execute() с форматированием строк
sql_patterns = conn.execute("""
    SELECT c."NAME:string" as call_name,
           c."CODE:string" as code,
           c."LINE_NUMBER:int" as line,
           m."FILENAME:string" as file
    FROM nodes_call c
    LEFT JOIN edges_ast a ON c.":ID" = a.":END_ID"
    LEFT JOIN nodes_method m ON a.":START_ID" = m.":ID"
    WHERE c."NAME:string" IN ('raw', 'execute', 'executescript', 'executemany')
      AND (c."CODE:string" LIKE '%format%'
           OR c."CODE:string" LIKE '%+%')
""").fetchall()

if sql_patterns:
    for call_name, code, line, file in sql_patterns:
        print(f"  [HIGH] Potential SQL Injection: {call_name}")
        print(f"    File: {file}")
        print(f"    Line: {line}")
        print(f"    Code: {code[:100] if code else 'N/A'}")
        findings.append({
            "type": "SQL_INJECTION",
            "severity": "HIGH",
            "call": call_name,
            "file": file,
            "line": line,
            "code": code
        })
else:
    print("  [OK] Явных паттернов SQL Injection не найдено")
    print("       (Django ORM обычно защищает от SQL Injection)")

# =============================================================================
# 3. FILE OPERATIONS (Path Traversal Risk)
# =============================================================================
print("\n## 3. FILE OPERATIONS (Path Traversal)")
print("-" * 50)

file_ops = conn.execute("""
    SELECT c."NAME:string" as call_name,
           c."CODE:string" as code,
           c."LINE_NUMBER:int" as line,
           m."FILENAME:string" as file
    FROM nodes_call c
    LEFT JOIN edges_ast a ON c.":ID" = a.":END_ID"
    LEFT JOIN nodes_method m ON a.":START_ID" = m.":ID"
    WHERE c."NAME:string" IN ('open', 'remove', 'unlink', 'rmdir', 'rename',
                              'copy', 'copytree', 'move', 'shutil.copy')
""").fetchall()

if file_ops:
    print(f"  Найдено {len(file_ops)} файловых операций:")
    for call_name, code, line, file in file_ops[:10]:
        severity = "HIGH" if call_name in ('remove', 'unlink', 'rmdir') else "MEDIUM"
        print(f"  [{severity}] {call_name}")
        print(f"    File: {file}")
        print(f"    Line: {line}")
        print(f"    Code: {code[:80] if code else 'N/A'}...")
        findings.append({
            "type": "FILE_OPERATION",
            "severity": severity,
            "call": call_name,
            "file": file,
            "line": line,
            "code": code
        })
else:
    print("  [OK] Файловых операций не найдено")

# =============================================================================
# 4. HARDCODED SECRETS IN LITERALS
# =============================================================================
print("\n## 4. HARDCODED SECRETS (Literals Analysis)")
print("-" * 50)

secrets = conn.execute("""
    SELECT l."CODE:string" as literal_value,
           l."LINE_NUMBER:int" as line,
           m."FILENAME:string" as file
    FROM nodes_literal l
    LEFT JOIN edges_ast a ON l.":ID" = a.":END_ID"
    LEFT JOIN nodes_method m ON a.":START_ID" = m.":ID"
    WHERE l."CODE:string" IS NOT NULL
      AND LENGTH(l."CODE:string") > 15
      AND (
        l."CODE:string" LIKE '%password%'
        OR l."CODE:string" LIKE '%secret%'
        OR l."CODE:string" LIKE '%api_key%'
        OR l."CODE:string" LIKE '%token%'
        OR l."CODE:string" LIKE '%-----BEGIN%'
      )
    LIMIT 20
""").fetchall()

if secrets:
    for literal, line, file in secrets:
        print(f"  [HIGH] Potential Hardcoded Secret")
        print(f"    File: {file}")
        print(f"    Line: {line}")
        print(f"    Value: {literal[:50]}...")
        findings.append({
            "type": "HARDCODED_SECRET",
            "severity": "HIGH",
            "file": file,
            "line": line,
            "value": literal[:50]
        })
else:
    print("  [OK] Явных hardcoded secrets в литералах не найдено")

# =============================================================================
# 5. INSECURE DESERIALIZATION
# =============================================================================
print("\n## 5. INSECURE DESERIALIZATION")
print("-" * 50)

deserialize = conn.execute("""
    SELECT c."NAME:string" as call_name,
           c."CODE:string" as code,
           c."LINE_NUMBER:int" as line,
           m."FILENAME:string" as file
    FROM nodes_call c
    LEFT JOIN edges_ast a ON c.":ID" = a.":END_ID"
    LEFT JOIN nodes_method m ON a.":START_ID" = m.":ID"
    WHERE c."NAME:string" IN ('loads', 'load', 'loadb')
      AND (c."CODE:string" LIKE '%pickle%'
           OR c."CODE:string" LIKE '%yaml%'
           OR c."CODE:string" LIKE '%marshal%')
""").fetchall()

if deserialize:
    for call_name, code, line, file in deserialize:
        print(f"  [CRITICAL] Insecure Deserialization: {call_name}")
        print(f"    File: {file}")
        print(f"    Line: {line}")
        findings.append({
            "type": "INSECURE_DESERIALIZATION",
            "severity": "CRITICAL",
            "call": call_name,
            "file": file,
            "line": line
        })
else:
    print("  [OK] Опасной десериализации не найдено")

# =============================================================================
# 6. DEBUG/LOGGING SENSITIVE DATA
# =============================================================================
print("\n## 6. SENSITIVE DATA IN LOGGING")
print("-" * 50)

logging_calls = conn.execute("""
    SELECT c."NAME:string" as call_name,
           c."CODE:string" as code,
           c."LINE_NUMBER:int" as line,
           m."FILENAME:string" as file
    FROM nodes_call c
    LEFT JOIN edges_ast a ON c.":ID" = a.":END_ID"
    LEFT JOIN nodes_method m ON a.":START_ID" = m.":ID"
    WHERE c."NAME:string" IN ('debug', 'info', 'warning', 'error', 'print')
      AND (c."CODE:string" LIKE '%password%'
           OR c."CODE:string" LIKE '%token%'
           OR c."CODE:string" LIKE '%secret%')
""").fetchall()

if logging_calls:
    for call_name, code, line, file in logging_calls:
        print(f"  [MEDIUM] Sensitive Data Logged: {call_name}")
        print(f"    File: {file}")
        print(f"    Line: {line}")
        findings.append({
            "type": "SENSITIVE_LOGGING",
            "severity": "MEDIUM",
            "call": call_name,
            "file": file,
            "line": line
        })
else:
    print("  [OK] Логирование чувствительных данных не обнаружено")

# =============================================================================
# 7. DJANGO-SPECIFIC SECURITY CHECKS
# =============================================================================
print("\n## 7. DJANGO SECURITY PATTERNS")
print("-" * 50)

# Check for @csrf_exempt
csrf_exempt = conn.execute("""
    SELECT DISTINCT m."FILENAME:string" as file, m."NAME:string" as method
    FROM nodes_method m
    WHERE m."CODE:string" LIKE '%csrf_exempt%'
       OR m."FULL_NAME:string" LIKE '%csrf_exempt%'
""").fetchall()

if csrf_exempt:
    for file, method in csrf_exempt:
        print(f"  [HIGH] @csrf_exempt decorator found")
        print(f"    File: {file}")
        print(f"    Method: {method}")
        findings.append({
            "type": "CSRF_EXEMPT",
            "severity": "HIGH",
            "file": file,
            "method": method
        })

# Check for permission_classes = []
no_permissions = conn.execute("""
    SELECT l."CODE:string" as code,
           l."LINE_NUMBER:int" as line,
           m."FILENAME:string" as file
    FROM nodes_literal l
    LEFT JOIN edges_ast a ON l.":ID" = a.":END_ID"
    LEFT JOIN nodes_method m ON a.":START_ID" = m.":ID"
    WHERE l."CODE:string" LIKE '%permission_classes%=%[]%'
       OR l."CODE:string" = '[]'
""").fetchall()

print(f"  Проверено {len(csrf_exempt)} CSRF и permission паттернов")

# =============================================================================
# 8. SUMMARY
# =============================================================================
print("\n" + "=" * 70)
print("   SUMMARY CPGQL SECURITY ANALYSIS")
print("=" * 70)

severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
for f in findings:
    severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

print(f"\n  Всего уязвимостей найдено: {len(findings)}")
print(f"    - CRITICAL: {severity_counts['CRITICAL']}")
print(f"    - HIGH:     {severity_counts['HIGH']}")
print(f"    - MEDIUM:   {severity_counts['MEDIUM']}")
print(f"    - LOW:      {severity_counts['LOW']}")

# Save findings to JSON
output_file = "workspace/cpgql_findings.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump({
        "project": "fsin_module",
        "analysis_time": datetime.now().isoformat(),
        "findings_count": len(findings),
        "severity_summary": severity_counts,
        "findings": findings
    }, f, indent=2, ensure_ascii=False)

print(f"\n  Результаты сохранены: {output_file}")
print("\n" + "=" * 70)

conn.close()
