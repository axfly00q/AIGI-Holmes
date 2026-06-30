"""Run once: add new columns to existing users table."""
import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), "aigi_holmes.db")
if not os.path.exists(db_path):
    print("数据库文件不存在，跳过迁移（首次启动时 SQLAlchemy 会自动建表）")
    raise SystemExit(0)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA table_info(users)")
cols = [row[1] for row in cur.fetchall()]
print("现有列:", cols)

migrations = [
    ("display_name",      "ALTER TABLE users ADD COLUMN display_name VARCHAR(64)"),
    ("bio",               "ALTER TABLE users ADD COLUMN bio VARCHAR(200)"),
    ("avatar_b64",        "ALTER TABLE users ADD COLUMN avatar_b64 TEXT"),
    ("is_active",         "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"),
    ("privacy_agreed",    "ALTER TABLE users ADD COLUMN privacy_agreed BOOLEAN NOT NULL DEFAULT 0"),
    ("privacy_agreed_at", "ALTER TABLE users ADD COLUMN privacy_agreed_at DATETIME"),
]

for col, sql in migrations:
    if col not in cols:
        cur.execute(sql)
        print(f"✅ 已添加列: {col}")
    else:
        print(f"   已存在列: {col}")

conn.commit()
conn.close()
print("迁移完成")
