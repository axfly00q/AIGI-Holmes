"""Idempotent SQLite schema migration for existing installations."""
import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), "aigi_holmes.db")
if not os.path.exists(db_path):
    print("数据库文件不存在，跳过迁移（首次启动时 SQLAlchemy 会自动建表）")
    raise SystemExit(0)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
migrations = {
"users": [
    ("display_name",      "ALTER TABLE users ADD COLUMN display_name VARCHAR(64)"),
    ("bio",               "ALTER TABLE users ADD COLUMN bio VARCHAR(200)"),
    ("avatar_b64",        "ALTER TABLE users ADD COLUMN avatar_b64 TEXT"),
    ("is_active",         "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"),
    ("privacy_agreed",    "ALTER TABLE users ADD COLUMN privacy_agreed BOOLEAN NOT NULL DEFAULT 0"),
    ("privacy_agreed_at", "ALTER TABLE users ADD COLUMN privacy_agreed_at DATETIME"),
],
"detection_records": [
    ("verdict_code",   "ALTER TABLE detection_records ADD COLUMN verdict_code VARCHAR(32)"),
    ("risk_score",     "ALTER TABLE detection_records ADD COLUMN risk_score FLOAT"),
    ("signals_json",   "ALTER TABLE detection_records ADD COLUMN signals_json TEXT"),
    ("result_version", "ALTER TABLE detection_records ADD COLUMN result_version VARCHAR(16)"),
],
}

for table, table_migrations in migrations.items():
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    if not cols:
        print(f"跳过尚未创建的表: {table}")
        continue
    for col, sql in table_migrations:
        if col not in cols:
            cur.execute(sql)
            print(f"✅ {table} 已添加列: {col}")
        else:
            print(f"   {table} 已存在列: {col}")

conn.commit()
conn.close()
print("迁移完成")
