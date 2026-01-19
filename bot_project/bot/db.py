import os
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST
    )


def get_user_permissions(tg_id: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=DictCursor)

    query = """
    SELECT 
    u.id AS user_id,
    r.name AS role_name,
    p.can_view,
    p.can_edit,
    p.can_add,
    p.can_delete
FROM users u
LEFT JOIN user_role r ON r.id = u.role_id
LEFT JOIN user_role_permissions rp ON rp.role_id = r.id
LEFT JOIN user_permission p ON p.id = rp.permission_id
WHERE u.tg_id = %s;
    """
    cur.execute(query, (tg_id,))
    rows = cur.fetchall()
    print(rows)
    cur.close()
    conn.close()
    return rows
