from db_connection import connect, disconnect

def create_database(db_name):
    conn = connect()
    if conn is None:
        return

    conn.autocommit = True
    cursor = conn.cursor()

    try:
        cursor.execute(f"CREATE DATABASE {db_name};")
        print(f"📦 Base de datos '{db_name}' creada")
    except Exception as e:
        print("❌ Error al crear la base de datos:", e)
    finally:
        cursor.close()
        disconnect(conn)


if __name__ == "__main__":
    create_database("brand_logo_detector_db")
