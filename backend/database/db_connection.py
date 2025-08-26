import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def connect():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        print("✅ Conexión exitosa")
        return conn
    except Exception as e:
        print("❌ Error al conectar:", e)
        return None

def disconnect(conn):
    if conn:
        conn.close()
        print("🔌 Conexión cerrada")

if __name__ == "__main__":
    conn = connect()
    disconnect(conn)