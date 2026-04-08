"""
Script de prueba para verificar la conexión a NeonDB y probar operaciones básicas.
Ejecutar: python test_db.py
"""

from db.conexion import get_conn
from db.queries import crear_reporte

def test_connection():
    """Probar conexión básica a la base de datos."""
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Consulta simple
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print("✅ Conexión exitosa!")
        print(f"Versión de PostgreSQL: {version[0]}")

        # Verificar tablas
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        print("📋 Tablas en la base de datos:")
        for table in tables:
            print(f"  - {table[0]}")

        cur.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def test_demo_users():
    """Verificar que los usuarios demo existen."""
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT id, nombre_completo, rol FROM usuarios;")
        users = cur.fetchall()

        print("👥 Usuarios en la base de datos:")
        for user in users:
            print(f"  - ID: {user[0]}, Nombre: {user[1]}, Rol: {user[2]}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error al consultar usuarios: {e}")

def test_insert_report():
    """Probar insertar un reporte de prueba."""
    try:
        # Usar el ID del usuario demo ciudadano
        test_data = {
            "usuario_id": "550e8400-e29b-41d4-a716-446655440000",  # Ana García
            "descripcion": "Prueba de reporte desde script de test",
            "categoria": "infraestructura",  # Valor válido del enum
            "lat": 19.4326,
            "lng": -99.1332,
            "direccion": "Centro Histórico, CDMX",
            "fuente": "texto",  # Solo 'texto' o 'audio'
            "tiene_imagen": False
        }

        result = crear_reporte(test_data)
        print("✅ Reporte de prueba insertado exitosamente!")
        print(f"   ID: {result[0]}, Código: {result[1]}")

    except Exception as e:
        print(f"❌ Error al insertar reporte de prueba: {e}")

def test_select_reports():
    """Verificar que los reportes se pueden consultar."""
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, codigo, descripcion, estado, created_at
            FROM reportes
            ORDER BY created_at DESC
            LIMIT 5;
        """)
        reports = cur.fetchall()

        print("📄 Últimos reportes en la base de datos:")
        for report in reports:
            print(f"  - ID: {report[0]}, Código: {report[1]}, Estado: {report[3]}")
            print(f"    Descripción: {report[2][:50]}...")
            print(f"    Fecha: {report[4]}")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error al consultar reportes: {e}")

if __name__ == "__main__":
    print("🧪 Probando conexión a NeonDB...\n")

    if test_connection():
        print("\n" + "="*50)
        test_demo_users()
        print("\n" + "="*50)
        test_insert_report()
        print("\n" + "="*50)
        test_select_reports()
        print("\n" + "="*50)
        print("✅ Todas las pruebas completadas!")
    else:
        print("❌ No se pudo conectar a la base de datos. Revisa la configuración.")