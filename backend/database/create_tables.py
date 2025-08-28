import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Nombre fijo de la base de datos
DB_NAME = "brand_logo_detector_db"

def connect():
    try:
        database_url = os.getenv("DATABASE_URL")
        pg_user = os.getenv("PGUSER")
        pg_password = os.getenv("PGPASSWORD")

        if not database_url:
            raise logger.error(f" {database_url} no está definida")

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
        logger.info(f"Conectado a la base de datos: {DB_NAME}")
   
        return conn
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        return None

def disconnect(conn):
    if conn:
        conn.close()
        logger.info("Conexión cerrada")

def create_logo_detection_table():
    conn = connect()
    if conn is None:
        return

    cursor = conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id_video SERIAL PRIMARY KEY,
                type VARCHAR(20) NOT NULL CHECK (type IN ('url', 'mp4', 'streaming')),
                name VARCHAR(255) DEFAULT 'unknown',
                total_video_time_segs FLOAT NOT NULL,
                date_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logo_detector (
                id_process SERIAL PRIMARY KEY,
                id_video INTEGER NOT NULL,
                label_name VARCHAR(100) NOT NULL,
                qty_frames_detected INTEGER NOT NULL,
                frame_per_second FLOAT NOT NULL,
                frames_appearance_in_percentage FLOAT NOT NULL,
                date_registered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_video
                    FOREIGN KEY(id_video) 
                    REFERENCES videos(id_video)
                    ON DELETE CASCADE
            );
        """)
        conn.commit()
        logger.info(f"Tablas 'videos' y 'logo_detector' creadas/actualizadas exitosamente en {DB_NAME}")
    except Exception as e:
        logger.error(f"Error al crear las tablas: {e}")
        conn.rollback()
    finally:
        cursor.close()
        disconnect(conn)

if __name__ == "__main__":
    create_logo_detection_table()
