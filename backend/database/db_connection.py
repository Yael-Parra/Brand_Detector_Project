import os
import psycopg2
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

def connect():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        logger.info("Conexión a la base de datos establecida")
        return conn
    except Exception as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        return None

def disconnect(conn):
    if conn:
        conn.close()
        logger.info("Conexión a la base de datos cerrada")

if __name__ == "__main__":
    conn = connect()
    disconnect(conn)