"""Offline inspection of isolated PostgreSQL evaluation schema.

Not a database deployment or proof of database access security.
"""
from pathlib import Path

SCHEMA = Path(__file__).with_name("private_eval_postgres.sql")

def audit_sql(sql):
    if not isinstance(sql, str):
        raise ValueError("SQL_INPUT_INVALID")
    upper = sql.upper()
    required = (
        "CREATE SCHEMA IF NOT EXISTS B2B_RESEARCH_EVAL",
        "REVOKE ALL ON SCHEMA B2B_RESEARCH_EVAL FROM PUBLIC",
        "CREATE TABLE IF NOT EXISTS B2B_RESEARCH_EVAL.DOCUMENT_META",
        "CREATE TABLE IF NOT EXISTS B2B_RESEARCH_EVAL.REVIEW",
        "CREATE TABLE IF NOT EXISTS B2B_RESEARCH_EVAL.AUDIT_EVENT",
        "ENABLE ROW LEVEL SECURITY",
        "FORCE ROW LEVEL SECURITY",
        "CREATE POLICY",
        "CURRENT_SETTING('B2B_EVAL.ACTOR_ID', TRUE)",
        "CURRENT_SETTING('B2B_EVAL.ACTOR_ROLE', TRUE)",
    )
    missing=[x for x in required if x not in upper]
    forbidden=("DROP SCHEMA", "DROP DATABASE", "TRUNCATE ", "ALTER SYSTEM",
               "CREATE EXTENSION", "GRANT ALL ON DATABASE", "CREATE POLICY PUBLIC")
    dangerous=[x for x in forbidden if x in upper]
    return {"valid_structure":not missing and not dangerous,
            "missing_required":missing,"unsafe_tokens":dangerous,
            "live_database_tested":False,"security_approved":False}
