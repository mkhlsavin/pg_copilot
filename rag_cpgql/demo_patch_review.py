"""
Demo script for the Automated Patch Review System.

This script demonstrates the complete patch review pipeline:
1. Parse a sample patch
2. Generate delta CPG
3. Run impact analysis
4. Generate verdicts
5. Output formatted results

Usage:
    python demo_patch_review.py [--db cpg.duckdb]
"""

import argparse
import sys
import logging
from pathlib import Path

import duckdb

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Sample diff for demonstration
SAMPLE_DIFF = '''
diff --git a/src/auth/login.py b/src/auth/login.py
index abc123..def456 100644
--- a/src/auth/login.py
+++ b/src/auth/login.py
@@ -10,6 +10,15 @@ class LoginService:
     def __init__(self, db):
         self.db = db

+    def authenticate(self, username, password):
+        # SECURITY ISSUE: SQL injection vulnerability
+        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
+        result = self.db.execute(query)
+        user = result.fetchone()
+        if user:
+            return {"status": "success", "user_id": user[0]}
+        return None
+
     def login(self, request):
         username = request.get('username')
         password = request.get('password')
@@ -20,3 +29,25 @@ class LoginService:
             return {"error": "Invalid credentials"}

         return {"token": self.generate_token(user)}
+
+    def reset_password(self, email):
+        # PERFORMANCE ISSUE: N+1 query pattern
+        users = self.db.execute("SELECT * FROM users").fetchall()
+        for user in users:
+            if user['email'] == email:
+                # Another query inside loop
+                self.db.execute(f"UPDATE users SET reset_token = '{self.generate_token()}' WHERE id = {user['id']}")
+                return True
+        return False
+
+    def bulk_update_passwords(self, updates):
+        # ERROR ISSUE: No exception handling
+        for update in updates:
+            user_id = update['user_id']
+            new_password = update['password']
+            # Missing null check
+            self.db.execute(f"UPDATE users SET password = '{new_password}' WHERE id = {user_id}")
+
+    def log_login_attempt(self, username, success):
+        # SECURITY ISSUE: Logging sensitive data
+        print(f"Login attempt: username={username}, password={password}, success={success}")
'''


def run_demo(db_path: str):
    """Run the patch review demo."""
    print("=" * 70)
    print("AUTOMATED PATCH REVIEW SYSTEM - DEMO")
    print("=" * 70)
    print()

    # Check if database exists
    if not Path(db_path).exists():
        print(f"Warning: Database {db_path} not found.")
        print("Running in demo mode with limited functionality.")
        print()

    # Connect to database
    try:
        conn = duckdb.connect(db_path)
        print(f"Connected to database: {db_path}")
    except Exception as e:
        print(f"Could not connect to database: {e}")
        print("Creating in-memory database for demo...")
        conn = duckdb.connect(':memory:')

    # Initialize delta tables if needed
    print("\n1. Initializing delta tables...")
    try:
        migration_path = Path(__file__).parent / 'src' / 'cpg_export' / 'migrations' / 'add_delta_tables.sql'
        if migration_path.exists():
            with open(migration_path, 'r') as f:
                sql = f.read()
            for statement in sql.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        conn.execute(statement)
                    except Exception:
                        pass  # Table might already exist
            print("   Delta tables ready")
        else:
            print("   Migration file not found, skipping...")
    except Exception as e:
        print(f"   Warning: {e}")

    # Import components
    print("\n2. Loading patch review components...")
    try:
        from src.patch_review import (
            ReviewWorkflow,
            PatchParser,
            MarkdownFormatter,
            JSONFormatter,
        )
        print("   Components loaded successfully")
    except ImportError as e:
        print(f"   Import error: {e}")
        print("   Make sure you're running from the project root directory")
        return 1

    # Parse the sample patch
    print("\n3. Parsing sample patch...")
    parser = PatchParser()
    try:
        patch = parser.parse_git_diff(SAMPLE_DIFF)
        print(f"   Patch ID: {patch.patch_id}")
        print(f"   Files changed: {len(patch.files)}")
        print(f"   Methods changed: {len(patch.changed_methods)}")
        print(f"   Lines added: {patch.total_additions}")
        print(f"   Lines deleted: {patch.total_deletions}")
    except Exception as e:
        print(f"   Parse error: {e}")
        return 1

    # Run the review workflow
    print("\n4. Running review workflow...")
    try:
        workflow = ReviewWorkflow(conn)
        verdict = workflow.run('git_diff', {'diff': SAMPLE_DIFF})
        print("   Review completed successfully")
    except Exception as e:
        print(f"   Review error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Display results
    print("\n" + "=" * 70)
    print("REVIEW RESULTS")
    print("=" * 70)

    # Summary
    print(f"\n[OVERALL SCORE] {verdict.overall_score:.0f}/100")
    print(f"[RECOMMENDATION] {verdict.recommendation.value.upper()}")

    # Category scores
    print("\n[CATEGORY SCORES]")
    print(f"   Security:     {verdict.security.score:.0f}/100")
    print(f"   Performance:  {verdict.performance.score:.0f}/100")
    print(f"   Error Risk:   {verdict.error.score:.0f}/100")
    print(f"   Architecture: {verdict.architecture.score:.0f}/100")

    # Finding counts
    print("\n[FINDINGS]")
    print(f"   Critical: {verdict.critical_count}")
    print(f"   High:     {verdict.high_count}")
    print(f"   Medium:   {verdict.medium_count}")
    print(f"   Low:      {verdict.low_count}")

    # Key issues
    if verdict.all_findings:
        print("\n[TOP ISSUES]")
        for i, finding in enumerate(verdict.all_findings[:5], 1):
            severity_icon = {
                'critical': '[CRIT]',
                'high': '[HIGH]',
                'medium': '[MED]',
                'low': '[LOW]',
                'info': '[INFO]'
            }.get(finding.severity.value, '-')
            print(f"   {i}. {severity_icon} {finding.title}")
            print(f"      Location: {finding.location}")
            if finding.cwe_id:
                print(f"      CWE: {finding.cwe_id}")

    # Output formatted reports to files
    formatter = MarkdownFormatter()
    report = formatter.format_full_report(verdict)

    md_path = Path("demo_review_output.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n[SAVED] Markdown report saved to: {md_path}")

    # Save JSON output
    json_formatter = JSONFormatter()
    json_output = json_formatter.format_full(verdict)

    json_path = Path("demo_review_output.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        f.write(json_output)
    print(f"[SAVED] JSON output saved to: {json_path}")

    # Cleanup
    conn.close()

    print("\n" + "=" * 70)
    print("DEMO COMPLETED")
    print("=" * 70)

    # Return appropriate exit code
    if verdict.recommendation.value == 'block':
        return 2
    elif verdict.recommendation.value == 'request_changes':
        return 1
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Demo for Automated Patch Review System'
    )
    parser.add_argument(
        '--db', '-d',
        default='cpg.duckdb',
        help='Path to DuckDB CPG database (default: cpg.duckdb)'
    )
    args = parser.parse_args()

    return run_demo(args.db)


if __name__ == '__main__':
    sys.exit(main())
