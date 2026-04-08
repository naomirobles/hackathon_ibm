from db.conexion import get_conn
import uuid
import random


# ============================================================
# 🔥 CREAR REPORTE (tabla: reportes)
# ============================================================
def crear_reporte(data):
    conn = get_conn()
    cur = conn.cursor()

    import uuid
    reporte_id = str(uuid.uuid4())
    codigo = f"RPT-{random.randint(100,999)}"

    query = """
    INSERT INTO reportes (
        id,
        codigo,
        usuario_id,
        descripcion,
        descripcion_audio,
        categoria,
        estado,
        latitud,
        longitud,
        direccion_aprox,
        ciudad,
        fuente_input,
        tiene_imagen
    )
    VALUES (%s,%s,%s,%s,%s,%s,'recibido',%s,%s,%s,'CDMX',%s,%s)
    RETURNING id, codigo;
    """

    values = (
        reporte_id,
        codigo,
        data["usuario_id"],
        data["descripcion"],
        data.get("descripcion_audio"),
        data["categoria"],  # Debe ser uno de: infraestructura, seguridad, areas_verdes, servicios, transporte, medio_ambiente
        data["lat"],
        data["lng"],
        data["direccion"],
        data.get("fuente", "texto"),  # Solo 'texto' o 'audio'
        data.get("tiene_imagen", False)
    )

    cur.execute(query, values)
    result = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return result





def crear_usuario(data):
    conn = get_conn()
    cur = conn.cursor()

    user_id = str(uuid.uuid4())

    cur.execute("""
        INSERT INTO usuarios (
            id,
            nombre_completo,
            correo,
            contrasena_hash,
            rol
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, correo
    """, (
        user_id,
        data["nombre"],
        data["correo"],
        data["password"],  # luego puedes hashear
        "ciudadano"
    ))

    result = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return result
# ============================================================
# 📊 OBTENER REPORTES DEL CIUDADANO
# (usa tu vista optimizada)
# ============================================================
def obtener_reportes_usuario(usuario_id):
    conn = get_conn()
    cur = conn.cursor()

    query = """
    SELECT *
    FROM vista_reportes_ciudadano
    WHERE reporte_id IN (
        SELECT id FROM reportes WHERE usuario_id = %s
    )
    ORDER BY fecha_reporte DESC;
    """

    cur.execute(query, (usuario_id,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# ============================================================
# 🏛️ OBTENER REPORTES PARA GOBIERNO
# ============================================================
def obtener_reportes_gobierno():
    conn = get_conn()
    cur = conn.cursor()

    query = """
    SELECT *
    FROM vista_reporte_completo
    ORDER BY fecha_reporte DESC;
    """

    cur.execute(query)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# ============================================================
# 📈 STATS DASHBOARD
# ============================================================
def obtener_stats_dashboard():
    conn = get_conn()
    cur = conn.cursor()

    query = "SELECT * FROM vista_stats_dashboard;"
    cur.execute(query)

    result = cur.fetchone()

    cur.close()
    conn.close()

    return result


# ============================================================
# 🚨 REPORTES ALTA PRIORIDAD
# ============================================================
def obtener_reportes_urgentes():
    conn = get_conn()
    cur = conn.cursor()

    query = """
    SELECT *
    FROM vista_alta_prioridad;
    """

    cur.execute(query)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# ============================================================
# 🧠 INSERTAR RESULTADO IA
# ============================================================
def insertar_procesamiento_ia(data):
    conn = get_conn()
    cur = conn.cursor()

    query = """
    INSERT INTO procesamiento_ia (
        id,
        reporte_id,
        tipo_problema,
        categoria_detectada,
        prioridad_asignada,
        confianza_pct,
        probabilidad_atencion,
        justificacion,
        recomendacion_gobierno,
        contexto_urbano
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
    """

    values = (
        str(uuid.uuid4()),
        data["reporte_id"],
        data["tipo_problema"],
        data["categoria"],
        data["prioridad"],
        data["confianza"],
        data["probabilidad"],
        data["justificacion"],
        data["recomendacion"],
        data["contexto"]
    )

    cur.execute(query, values)

    conn.commit()
    cur.close()
    conn.close()


# ============================================================
# 📎 GUARDAR EVIDENCIA (imagenes)
# ============================================================
def guardar_evidencia(data):
    conn = get_conn()
    cur = conn.cursor()

    query = """
    INSERT INTO evidencias (
        id,
        reporte_id,
        nombre_archivo,
        url_storage
    )
    VALUES (%s,%s,%s,%s);
    """

    values = (
        str(uuid.uuid4()),
        data["reporte_id"],
        data["nombre"],
        data["url"]
    )

    cur.execute(query, values)

    conn.commit()
    cur.close()
    conn.close()


# ============================================================
# 🧾 RESPUESTA GOBIERNO
# ============================================================
def insertar_respuesta_gobierno(data):
    conn = get_conn()
    cur = conn.cursor()

    query = """
    INSERT INTO respuestas_gobierno (
        id,
        reporte_id,
        usuario_id,
        mensaje,
        estado_nuevo
    )
    VALUES (%s,%s,%s,%s,%s);
    """

    values = (
        str(uuid.uuid4()),
        data["reporte_id"],
        data["usuario_id"],
        data["mensaje"],
        data["estado"]
    )

    cur.execute(query, values)

    conn.commit()
    cur.close()
    conn.close()