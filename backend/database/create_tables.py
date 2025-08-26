import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

# Nombre fijo de la base de datos
DB_NAME = "brand_logo_detector_db"

def connect():
    try:
        database_url = os.getenv("DATABASE_URL")
        pg_user = os.getenv("PGUSER")
        pg_password = os.getenv("PGPASSWORD")

        if not database_url:
            raise ValueError("DATABASE_URL no está definida")

        parsed_url = urlparse(database_url)
        host = parsed_url.hostname
        port = parsed_url.port or 5432

        # Conexión forzada a brand_logo_detector_db
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=pg_user,
            password=pg_password,
            host=host,
            port=port
        )
        print(f"🔗 Conectado a la base de datos: {DB_NAME}")
   
        return conn
    except Exception as e:
        print("❌ Error al conectar:", e)
        return None

def disconnect(conn):
    if conn:
        conn.close()

def create_logo_detection_table():
    conn = connect()
    if conn is None:
        return

    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detecciones_logos (
                id SERIAL PRIMARY KEY,
                video_id VARCHAR(100) NOT NULL,
                brand_name VARCHAR(100) NOT NULL,
                frames_detected INTEGER NOT NULL,
                frames_per_second FLOAT NOT NULL,
                total_video_time_in_segs FLOAT NOT NULL,
                frames_duration_in_segs FLOAT GENERATED ALWAYS AS (frames_detected / frames_per_second) STORED,
                frames_appearance_in_percentage FLOAT GENERATED ALWAYS AS ((frames_detected / frames_per_second) / total_video_time_in_segs * 100) STORED,
                date_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        print(f"✅ Tabla 'detecciones_logos' creada/actualizada exitosamente en {DB_NAME}")
    except Exception as e:
        print("❌ Error al crear la tabla:", e)
        conn.rollback()
    finally:
        cursor.close()
        disconnect(conn)

if __name__ == "__main__":
    create_logo_detection_table()
