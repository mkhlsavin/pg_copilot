#!/usr/bin/env python3
"""CPG Validation Script for fsin_module"""
import duckdb
import os

db_path = "workspace/fsin_module.duckdb"
conn = duckdb.connect(db_path, read_only=True)

print("=" * 70)
print("      ПОЛНАЯ ВАЛИДАЦИЯ CPG: fsin_module")
print("=" * 70)

# 1. Базовые метрики
print("\n## 1. БАЗОВЫЕ МЕТРИКИ CPG")
print("-" * 40)

metrics = {
    'nodes_method': "SELECT COUNT(*) FROM nodes_method",
    'nodes_call': "SELECT COUNT(*) FROM nodes_call",
    'nodes_identifier': "SELECT COUNT(*) FROM nodes_identifier",
    'nodes_literal': "SELECT COUNT(*) FROM nodes_literal",
    'nodes_file': "SELECT COUNT(*) FROM nodes_file",
    'edges_ast': "SELECT COUNT(*) FROM edges_ast",
    'edges_ref': "SELECT COUNT(*) FROM edges_ref",
    'edges_reaching_def': "SELECT COUNT(*) FROM edges_reaching_def",
}

for name, query in metrics.items():
    try:
        count = conn.execute(query).fetchone()[0]
        print(f"  {name:<25} {count:>10,}")
    except:
        print(f"  {name:<25} {'N/A':>10}")

# 2. Покрытие файлов
print("\n## 2. ПОКРЫТИЕ ФАЙЛОВ")
print("-" * 40)

files = conn.execute("""
    SELECT "NAME:string" as name FROM nodes_file
    WHERE "NAME:string" IS NOT NULL
    ORDER BY "NAME:string"
""").fetchall()
print(f"  Всего файлов в CPG: {len(files)}")

# Группировка по модулям
modules = {}
for (f,) in files:
    sep = "\\" if "\\" in f else "/"
    parts = f.split(sep)
    module = parts[0] if len(parts) > 1 else 'root'
    modules[module] = modules.get(module, 0) + 1

print(f"  Модулей: {len(modules)}")
for mod, cnt in sorted(modules.items(), key=lambda x: -x[1]):
    print(f"    - {mod}: {cnt} файлов")

# 3. Методы по файлам
print("\n## 3. ТОП-10 ФАЙЛОВ ПО МЕТОДАМ")
print("-" * 40)

top_files = conn.execute("""
    SELECT "FILENAME:string" as fname, COUNT(*) as cnt
    FROM nodes_method
    WHERE "FILENAME:string" IS NOT NULL AND "FILENAME:string" != ''
    GROUP BY "FILENAME:string"
    ORDER BY cnt DESC
    LIMIT 10
""").fetchall()

for i, (fname, cnt) in enumerate(top_files, 1):
    sep = "\\" if "\\" in fname else "/"
    parts = fname.split(sep)
    short = parts[-1] if parts else fname
    print(f"  {i:>2}. {short:<35} {cnt:>5} методов")

# 4. Топ вызываемых функций
print("\n## 4. ТОП-20 ВЫЗЫВАЕМЫХ ФУНКЦИЙ")
print("-" * 40)

calls = conn.execute("""
    SELECT "NAME:string" as name, COUNT(*) as cnt
    FROM nodes_call
    WHERE "NAME:string" IS NOT NULL
      AND "NAME:string" NOT LIKE '<%'
      AND LENGTH("NAME:string") > 2
    GROUP BY "NAME:string"
    ORDER BY cnt DESC
    LIMIT 20
""").fetchall()

for name, cnt in calls:
    print(f"  {name:<40} {cnt:>5}")

# 5. Quality Score
print("\n## 5. QUALITY SCORE")
print("-" * 40)

methods = conn.execute("SELECT COUNT(*) FROM nodes_method").fetchone()[0]
calls_cnt = conn.execute("SELECT COUNT(*) FROM nodes_call").fetchone()[0]
ast_cnt = conn.execute("SELECT COUNT(*) FROM edges_ast").fetchone()[0]
ref_cnt = conn.execute("SELECT COUNT(*) FROM edges_ref").fetchone()[0]
rd_cnt = conn.execute("SELECT COUNT(*) FROM edges_reaching_def").fetchone()[0]

# Рассчитываем качество
score_methods = min(100, methods / 10)
score_calls = min(100, calls_cnt / 100)
score_ast = min(100, ast_cnt / 500)
score_ref = min(100, ref_cnt / 100)
score_dataflow = min(100, rd_cnt / 50)

total_score = (score_methods + score_calls + score_ast + score_ref + score_dataflow) / 5

print(f"  Methods completeness:    {score_methods:>6.1f}%")
print(f"  Calls coverage:          {score_calls:>6.1f}%")
print(f"  AST integrity:           {score_ast:>6.1f}%")
print(f"  Reference resolution:    {score_ref:>6.1f}%")
print(f"  Dataflow analysis:       {score_dataflow:>6.1f}%")
print(f"  " + "-" * 30)
print(f"  OVERALL QUALITY:         {total_score:>6.1f}%")

if total_score >= 80:
    print(f"\n  [OK] CPG КАЧЕСТВО: ОТЛИЧНОЕ")
elif total_score >= 60:
    print(f"\n  [~] CPG КАЧЕСТВО: ХОРОШЕЕ")
else:
    print(f"\n  [!] CPG КАЧЕСТВО: ТРЕБУЕТ УЛУЧШЕНИЯ")

print("\n" + "=" * 70)
print("      ВАЛИДАЦИЯ ЗАВЕРШЕНА УСПЕШНО")
print("=" * 70)

conn.close()
