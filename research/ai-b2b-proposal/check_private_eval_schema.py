"""Offline inspection of isolated PostgreSQL evaluation schema.

Not a database deployment or proof of database access security.
"""
from pathlib import Path
import re

SCHEMA = Path(__file__).with_name("private_eval_postgres.sql")

def audit_sql(sql):
    if not isinstance(sql, str):
        raise ValueError("SQL_INPUT_INVALID")
    # Ignore explanatory SQL comments when looking for executable statements.
    executable = re.sub(r'/\\*.*?\\*/', '', sql, flags=re.S)
    executable = re.sub(r'--[^\\n]*', '', executable)
    upper = executable.upper()
    required = (
        "CREATE SCHEMA IF NOT EXISTS B2B_RESEARCH_EVAL",
        "REVOKE ALL ON SCHEMA B2B_RESEARCH_EVAL FROM PUBLIC",
        "CREATE TABLE IF NOT EXISTS B2B_RESEARCH_EVAL.DOCUMENT_META",
        "CREATE TABLE IF NOT EXISTS B2B_RESEARCH_EVAL.REVIEW",
        "CREATE TABLE IF NOT EXISTS B2B_RESEARCH_EVAL.AUDIT_EVENT",
        "ENABLE ROW LEVEL SECURITY",
        "FORCE ROW LEVEL SECURITY",
    )
    missing=[x for x in required if x not in upper]
    forbidden=("DROP SCHEMA", "DROP DATABASE", "TRUNCATE ", "ALTER SYSTEM",
               "CREATE EXTENSION", "GRANT ALL ON DATABASE", "CREATE POLICY",
               "CURRENT_SETTING(", "GRANT SELECT", "GRANT INSERT", "CREATE ROLE")
    dangerous=[x for x in forbidden if x in upper]
    return {"valid_structure":not missing and not dangerous,
            "missing_required":missing,"unsafe_tokens":dangerous,
            "live_database_tested":False,"security_approved":False}
