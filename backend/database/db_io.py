import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

DB_NAME = "brand_logo_detector_db"

def connect():
    database_url = os.getenv("DATABASE_URL")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")

    if not database_url:
        raise RuntimeError("DATABASE_URL no está definida")

    parsed = urlparse(database_url)
    host = parsed.hostname
    port = parsed.port or 5432

    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=pg_user,
        password=pg_password,
        host=host,
        port=port,
    )
    return conn

def disconnect(conn):
    if conn:
        conn.close()

def insert_video(conn, *, vtype: str, name: str, total_secs: float) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO videos (type, name, total_video_time_segs)
            VALUES (%s, %s, %s)
            RETURNING id_video;
            """,
            (vtype, name, float(total_secs)),
        )
        vid = cur.fetchone()[0]
        conn.commit()
        return vid

def insert_detection(
    conn,
    *,
    id_video: int,
    label_name: str,
    qty_frames_detected: int,
    fps: float,
    percent: float,
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO logo_detector
            (id_video, label_name, qty_frames_detected, frame_per_second, frames_appearance_in_percentage)
            VALUES (%s, %s, %s, %s, %s);
            """,
            (id_video, label_name, int(qty_frames_detected), float(fps), float(percent)),
        )
    conn.commit()
