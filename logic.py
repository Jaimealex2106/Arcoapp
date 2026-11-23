import sqlite3
import shutil
import os
import csv
from datetime import datetime

import database


def importar_base_de_datos() -> tuple[bool, str]:
    """Invoca la importación desde la capa de base de datos."""
    return database.importar_base_de_datos()


def conectar_bd():
    """Usa siempre la ruta escribible centralizada de database.py (PC y Android)."""
    return database.conectar_bd()


def inicializar_base_datos():
    """Delega la inicialización completa del esquema a database.py."""
    database.inicializar_base_de_datos()


# ==================== GESTIÓN DE RÚBRICAS ====================

def obtener_rubricas():
    """Alias para obtener ID y Nombre de todas las rúbricas base activas."""
    return obtener_todas_las_rubricas()


def obtener_todas_las_rubricas():
    """Obtiene todas las rúbricas base (no individuales/especiales)."""
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre_rubrica FROM rubricas WHERE es_especial = 0")
        filas = cursor.fetchall()
    return filas


def obtener_rubrica_id_por_nombre(nombre_rubrica):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM rubricas WHERE nombre_rubrica = ?", (nombre_rubrica,))
        res = cursor.fetchone()
    return res[0] if res else 1


def crear_rubrica_vacia(nombre_rubrica):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO rubricas (nombre_rubrica, es_especial) VALUES (?, 0)", (nombre_rubrica,))
        return cursor.lastrowid


def crear_rubrica_base(nombre_rubrica, actividades_config=None):
    """Crea una nueva rúbrica base y opcionalmente asigna sus porcentajes."""
    if actividades_config:
        suma = sum(porc for _, porc in actividades_config)
        if abs(suma - 100.0) > 0.01:
            return None, f"Los porcentajes deben sumar 100% (suma actual: {suma:.1f}%)"

    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO rubricas (nombre_rubrica, es_especial) VALUES (?, 0)", (nombre_rubrica,))
        rubrica_id = cursor.lastrowid

        if actividades_config:
            for tipo_id, porcentaje in actividades_config:
                cursor.execute("""
                    INSERT INTO rubrica_actividades (rubrica_id, tipo_actividad_id, porcentaje)
                    VALUES (?, ?, ?)
                """, (rubrica_id, tipo_id, porcentaje))

    return rubrica_id, "Rúbrica creada con éxito"


def crear_o_actualizar_rubrica_especial_miembro(m_id, nombre_miembro, actividades_config):
    """Crea o actualiza una rúbrica única/especial asignada a un miembro específico."""
    suma = sum(porc for _, porc in actividades_config)
    if abs(suma - 100.0) > 0.01:
        return False, f"Los porcentajes deben sumar 100% (suma actual: {suma:.1f}%)"

    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT r.id, r.es_especial FROM miembros m JOIN rubricas r ON m.rubrica_id = r.id WHERE m.id_unico = ?", (m_id,))
        res = cursor.fetchone()

        if res and res[1] == 1:
            rubrica_id = res[0]
        else:
            nombre_unica = f"Caso Especial - {nombre_miembro} ({m_id})"
            cursor.execute("INSERT INTO rubricas (nombre_rubrica, es_especial) VALUES (?, 1)", (nombre_unica,))
            rubrica_id = cursor.lastrowid
            cursor.execute("UPDATE miembros SET rubrica_id = ? WHERE id_unico = ?", (rubrica_id, m_id))

        cursor.execute("DELETE FROM rubrica_actividades WHERE rubrica_id = ?", (rubrica_id,))
        for tipo_id, porcentaje in actividades_config:
            cursor.execute("""
                INSERT INTO rubrica_actividades (rubrica_id, tipo_actividad_id, porcentaje)
                VALUES (?, ?, ?)
            """, (rubrica_id, tipo_id, porcentaje))

    return True, "Rúbrica especial asignada correctamente"


def actualizar_o_crear_rubrica_dinamica_miembro(m_id, nombre_miembro, config_actividades):
    return crear_o_actualizar_rubrica_especial_miembro(m_id, nombre_miembro, config_actividades)


def guardar_rubrica_especial_dinamica(m_id, actividades_config):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nombre_completo FROM miembros WHERE id_unico = ?", (m_id,))
        res = cursor.fetchone()
        nombre_m = res[0] if res else "Miembro"
    return crear_o_actualizar_rubrica_especial_miembro(m_id, nombre_m, actividades_config)


def obtener_actividades_de_miembro(m_id):
    """Obtiene la lista de {tipo_id: porcentaje} del miembro."""
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ra.tipo_actividad_id, ra.porcentaje
            FROM rubrica_actividades ra
            JOIN miembros m ON m.rubrica_id = ra.rubrica_id
            WHERE m.id_unico = ?
        """, (m_id,))
        filas = cursor.fetchall()
    return {f[0]: f[1] for f in filas}


def obtener_actividades_miembro_especial(m_id):
    return obtener_actividades_de_miembro(m_id)


def obtener_rubrica_de_miembro(m_id):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.id, r.nombre_rubrica, r.es_especial
            FROM miembros m
            JOIN rubricas r ON m.rubrica_id = r.id
            WHERE m.id_unico = ?
        """, (m_id,))
        rubrica = cursor.fetchone()

        if not rubrica:
            return None

        actividades = obtener_actividades_rubrica(rubrica[0])
    return {
        "rubrica_id": rubrica[0],
        "nombre_rubrica": rubrica[1],
        "es_especial": rubrica[2],
        "actividades": actividades
    }


def renombrar_rubrica(rubrica_id, nuevo_nombre):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE rubricas SET nombre_rubrica = ? WHERE id = ?", (nuevo_nombre, rubrica_id))


def eliminar_rubrica(rubrica_id):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM miembros WHERE rubrica_id = ?", (rubrica_id,))
        count = cursor.fetchone()[0]

        if count > 0:
            return False

        cursor.execute("DELETE FROM rubricas WHERE id = ?", (rubrica_id,))
        return True


# ==================== MIEMBROS Y ASISTENCIAS ====================

def obtener_actividades():
    """Obtiene todas las actividades creadas con el nombre de su tipo para los dropdowns."""
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, ta.nombre_actividad, a.titulo_descripcion, a.fecha 
            FROM actividades a
            JOIN tipos_actividades ta ON a.tipo_id = ta.id
            ORDER BY a.fecha DESC, a.id DESC
        """)
        actividades = cursor.fetchall()
    return actividades


def registrar_miembro(nombre_completo, fecha_nac, edad, corillo, ocupacion, grado_estudio,
                      direccion, telefono, tel_emergencia, tutor, tel_tutor, encuentro_num, rubrica_id, historial_morrales=""):
    """Acepta un `rubrica_id` de tipo entero o una cadena numérica/nombre."""
    with conectar_bd() as conn:
        cursor = conn.cursor()

        nuevo_id = database.generar_siguiente_id_miembro(cursor)

        if isinstance(rubrica_id, str):
            if rubrica_id.isdigit():
                val_rubrica_id = int(rubrica_id)
            else:
                val_rubrica_id = obtener_rubrica_id_por_nombre(rubrica_id)
        else:
            val_rubrica_id = int(rubrica_id) if rubrica_id else 1

        cursor.execute("""
            INSERT INTO miembros (
                id_unico, nombre_completo, fecha_nacimiento, edad, corillo, 
                ocupacion_actual, grado_estudio, direccion, telefono, 
                telefono_emergencia, tutor, telefono_tutor, encuentro_numero, rubrica_id, historial_morrales, activo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (nuevo_id, nombre_completo, fecha_nac, edad, corillo, ocupacion, grado_estudio,
              direccion, telefono, tel_emergencia, tutor, tel_tutor, encuentro_num, val_rubrica_id, historial_morrales))
    return nuevo_id


def actualizar_miembro(m_id, nombre_completo, corillo, ocupacion, grado_estudio, rubrica_id, historial_morrales=""):
    """Acepta un `rubrica_id` entero o una cadena numérica/nombre."""
    if isinstance(rubrica_id, str):
        if rubrica_id.isdigit():
            val_rubrica_id = int(rubrica_id)
        else:
            val_rubrica_id = obtener_rubrica_id_por_nombre(rubrica_id)
    else:
        val_rubrica_id = int(rubrica_id) if rubrica_id else 1

    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE miembros 
            SET nombre_completo=?, corillo=?, ocupacion_actual=?, grado_estudio=?, rubrica_id=?, historial_morrales=?
            WHERE id_unico=?
        """, (nombre_completo, corillo, ocupacion, grado_estudio, val_rubrica_id, historial_morrales, m_id))


def eliminar_miembro(m_id):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM miembros WHERE id_unico=?", (m_id,))


def eliminar_todos_los_miembros():
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM asistencias")
        cursor.execute("DELETE FROM miembros")


def obtener_miembros_ordenados(criterio="nombre"):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        
        sql = """
            SELECT m.id_unico, m.nombre_completo, m.corillo, m.ocupacion_actual, 
                   m.grado_estudio, r.nombre_rubrica, m.historial_morrales
            FROM miembros m
            LEFT JOIN rubricas r ON m.rubrica_id = r.id
        """
        
        if criterio == "id":
            sql += " ORDER BY m.id_unico ASC"
        elif criterio == "corillo":
            sql += " ORDER BY m.corillo ASC, m.nombre_completo ASC"
        else:
            sql += " ORDER BY m.nombre_completo ASC"
            
        cursor.execute(sql)
        return cursor.fetchall()


def crear_actividad(tipo, titulo_descripcion, fecha):
    """Crea una nueva actividad aceptando `tipo` como `tipo_id` entero o buscando por nombre."""
    with conectar_bd() as conn:
        cursor = conn.cursor()
        
        if isinstance(tipo, str) and not tipo.isdigit():
            cursor.execute("SELECT id FROM tipos_actividades WHERE nombre_actividad = ?", (tipo,))
            res = cursor.fetchone()
            tipo_id = res[0] if res else crear_tipo_actividad(tipo)
        else:
            tipo_id = int(tipo)

        cursor.execute("""
            INSERT INTO actividades (tipo_id, titulo_descripcion, fecha)
            VALUES (?, ?, ?)
        """, (tipo_id, titulo_descripcion, fecha))
        act_id = cursor.lastrowid
    return act_id


def marcar_asistencia(id_miembro, id_actividad, asistio):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        val_asistio = 1 if (asistio is True or asistio == 1 or asistio == "Presente") else 0
        cursor.execute("""
            INSERT INTO asistencias (miembro_id, actividad_id, asistio)
            VALUES (?, ?, ?)
            ON CONFLICT(miembro_id, actividad_id) DO UPDATE SET asistio=excluded.asistio
        """, (id_miembro, id_actividad, val_asistio))


def obtener_estado_asistencia(id_actividad):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT miembro_id, asistio FROM asistencias WHERE actividad_id=?", (id_actividad,))
        filas = cursor.fetchall()
    return {f[0]: f[1] for f in filas}


# ==================== RANKING Y PUNTAJES DINÁMICOS ====================

def obtener_ranking_servidores(fecha_inicio=None, fecha_fin=None):
    with conectar_bd() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id_unico, nombre_completo, corillo, rubrica_id FROM miembros")
        miembros = cursor.fetchall()

        filtro_fecha = ""
        params_fecha = []
        if fecha_inicio and fecha_inicio.strip():
            filtro_fecha += " AND fecha >= ?"
            params_fecha.append(fecha_inicio.strip())
        if fecha_fin and fecha_fin.strip():
            filtro_fecha += " AND fecha <= ?"
            params_fecha.append(fecha_fin.strip())

        cursor.execute(f"SELECT tipo_id, COUNT(*) FROM actividades WHERE 1=1{filtro_fecha} GROUP BY tipo_id", tuple(params_fecha))
        conteo_por_tipo = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute(f"SELECT COUNT(*) FROM actividades WHERE 1=1{filtro_fecha}", tuple(params_fecha))
        total_actividades_periodo = cursor.fetchone()[0] or 0

        ranking = []

        for m_id, nombre, corillo, rubrica_id in miembros:
            if not rubrica_id:
                ranking.append({
                    "id": m_id,
                    "nombre": nombre,
                    "corillo": corillo or "Sin Corillo",
                    "asistencias": 0,
                    "total_actividades": total_actividades_periodo,
                    "puntaje": 0.0
                })
                continue

            cursor.execute("""
                SELECT tipo_actividad_id, porcentaje 
                FROM rubrica_actividades 
                WHERE rubrica_id = ?
            """, (rubrica_id,))
            pesos_rubrica = cursor.fetchall()

            puntaje_total = 0.0
            total_asistencias_miembro = 0

            for tipo_id, porcentaje_ponderado in pesos_rubrica:
                total_eventos_tipo = conteo_por_tipo.get(tipo_id, 0)

                query_asist = f"""
                    SELECT COUNT(*) 
                    FROM asistencias a
                    JOIN actividades act ON a.actividad_id = act.id
                    WHERE a.miembro_id = ? 
                      AND act.tipo_id = ? 
                      AND a.asistio = 1
                      {filtro_fecha.replace('fecha', 'act.fecha')}
                """
                cursor.execute(query_asist, (m_id, tipo_id, *params_fecha))
                asistencias_tipo = cursor.fetchone()[0] or 0

                total_asistencias_miembro += asistencias_tipo

                if total_eventos_tipo > 0:
                    tasa_asistencia = asistencias_tipo / total_eventos_tipo
                    puntaje_total += tasa_asistencia * porcentaje_ponderado

            ranking.append({
                "id": m_id,
                "nombre": nombre,
                "corillo": corillo or "Sin Corillo",
                "asistencias": total_asistencias_miembro,
                "total_actividades": total_actividades_periodo,
                "puntaje": round(puntaje_total, 1)
            })

    ranking.sort(key=lambda x: x["puntaje"], reverse=True)
    return ranking


def obtener_ranking_acumulado(fecha_inicio=None, fecha_fin=None):
    """Alias compatible con las vistas."""
    return obtener_ranking_servidores(fecha_inicio, fecha_fin)


# ==================== GESTIÓN DE ACTIVIDADES PERSONALIZABLES ====================

def obtener_tipos_actividades():
    """Obtiene la lista de tipos de actividades globales disponibles."""
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre_actividad FROM tipos_actividades ORDER BY nombre_actividad")
        actividades = cursor.fetchall()
    return actividades


def obtener_actividades_rubrica(rubrica_id):
    """Obtiene las actividades configuradas para una rúbrica específica con sus porcentajes."""
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ra.id, ta.id, ta.nombre_actividad, ra.porcentaje
            FROM rubrica_actividades ra
            JOIN tipos_actividades ta ON ra.tipo_actividad_id = ta.id
            WHERE ra.rubrica_id = ?
            ORDER BY ta.nombre_actividad
        """, (rubrica_id,))
        actividades = cursor.fetchall()
    return actividades


def crear_tipo_actividad(nombre_actividad):
    """Crea un nuevo tipo de actividad global."""
    with conectar_bd() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO tipos_actividades (nombre_actividad) VALUES (?)", (nombre_actividad.strip(),))
            tipo_id = cursor.lastrowid
            return tipo_id
        except sqlite3.IntegrityError:
            cursor.execute("SELECT id FROM tipos_actividades WHERE nombre_actividad = ?", (nombre_actividad.strip(),))
            res = cursor.fetchone()
            return res[0] if res else None


def actualizar_actividades_rubrica(rubrica_id, actividades_config):
    suma = sum(porcentaje for _, porcentaje in actividades_config)
    if abs(suma - 100.0) > 0.01:
        return False, f"Los porcentajes deben sumar 100% (suma actual: {suma:.1f}%)"

    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rubrica_actividades WHERE rubrica_id = ?", (rubrica_id,))

        for tipo_id, porcentaje in actividades_config:
            cursor.execute("""
                INSERT INTO rubrica_actividades (rubrica_id, tipo_actividad_id, porcentaje)
                VALUES (?, ?, ?)
            """, (rubrica_id, tipo_id, porcentaje))

    return True, "Actividades actualizadas correctamente"


def agregar_actividad_rubrica(rubrica_id, tipo_actividad_id, porcentaje):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO rubrica_actividades (rubrica_id, tipo_actividad_id, porcentaje)
                VALUES (?, ?, ?)
            """, (rubrica_id, tipo_actividad_id, porcentaje))
            return True
        except sqlite3.IntegrityError:
            return False


def eliminar_actividad_rubrica(rubrica_id, tipo_actividad_id):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM rubrica_actividades
            WHERE rubrica_id = ? AND tipo_actividad_id = ?
        """, (rubrica_id, tipo_actividad_id))


def exportar_base_de_datos(ruta_destino):
    """Copia el archivo de base de datos activo a la ruta especificada por el usuario."""
    try:
        shutil.copy2(database.obtener_ruta_db_activa(), ruta_destino)
        return True, "✅ Respaldo de la base de datos exportado con éxito."
    except Exception as e:
        return False, f"⚠️ Error al exportar la base de datos: {str(e)}"


def obtener_ruta_descargas():
    is_android = hasattr(os, "uname") and "android" in os.uname().release.lower()
    dir_descargas = "/sdcard/Download" if is_android else os.path.join(os.path.expanduser("~"), "Downloads")
    os.makedirs(dir_descargas, exist_ok=True)
    return dir_descargas


# ==================== EXPORTACIÓN Y ENCUENTROS ====================

def exportar_directorio_general():
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT encuentro_numero, corillo, id_unico, nombre_completo, edad, telefono, tutor 
                FROM miembros 
                ORDER BY CAST(encuentro_numero AS INTEGER) ASC, corillo ASC, nombre_completo ASC
            ''')
            datos = cursor.fetchall()

        ruta = os.path.join(obtener_ruta_descargas(), f"Directorio_Arcoiris_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
        with open(ruta, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(["No. Encuentro", "Corillo", "ID", "Nombre Completo", "Edad", "Teléfono", "Tutor"])
            writer.writerows(datos)
        return True, f"Directorio exportado en Descargas:\n{os.path.basename(ruta)}"
    except Exception as e:
        return False, f"Error al exportar directorio: {e}"


def crear_retiro(numero, descripcion):
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS retiros (
                numero INTEGER PRIMARY KEY,
                descripcion TEXT,
                fecha TEXT
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS participaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                retiro_numero INTEGER NOT NULL,
                miembro_id TEXT NOT NULL,
                tipo_participacion TEXT NOT NULL,
                rol TEXT,
                corillo_asignado TEXT,
                FOREIGN KEY (retiro_numero) REFERENCES retiros(numero) ON DELETE CASCADE,
                FOREIGN KEY (miembro_id) REFERENCES miembros(id_unico) ON DELETE CASCADE,
                UNIQUE(retiro_numero, miembro_id)
            )
            ''')
            cursor.execute("INSERT INTO retiros (numero, descripcion, fecha) VALUES (?, ?, ?)", 
                           (numero, descripcion, datetime.now().strftime('%Y-%m-%d')))
            conn.commit()
        return True, f"Encuentro #{numero} creado correctamente."
    except Exception as e:
        return False, f"Error BD: {str(e)}"


def obtener_retiros():
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS retiros (
                numero INTEGER PRIMARY KEY,
                descripcion TEXT,
                fecha TEXT
            )
            ''')
            cursor.execute("SELECT numero, descripcion FROM retiros ORDER BY numero DESC")
            return cursor.fetchall()
    except Exception:
        return []


def existe_retiro(numero) -> bool:
    """Verifica si ya existe un encuentro registrado con ese número."""
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM retiros WHERE numero = ?", (int(numero),))
            return cursor.fetchone() is not None
    except Exception:
        return False


def agregar_participante(retiro_numero, miembro_id, tipo, rol="", corillo=""):
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO participaciones (retiro_numero, miembro_id, tipo_participacion, rol, corillo_asignado)
                VALUES (?, ?, ?, ?, ?)
            ''', (retiro_numero, miembro_id, tipo, rol, corillo))
            conn.commit()
        return True, f"Participante agregado como {tipo}."
    except Exception as e:
        return False, f"Error al agregar participante: {e}"


def eliminar_participante_retiro(retiro_numero, miembro_id):
    """Elimina a un participante (Servidor o Encuentrista) únicamente de un retiro específico."""
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM participaciones 
                WHERE retiro_numero = ? AND miembro_id = ?
            ''', (retiro_numero, miembro_id))
            conn.commit()
        return True, "Participante eliminado del encuentro."
    except Exception as e:
        return False, f"Error al eliminar del encuentro: {e}"


def obtener_candidatos_retiro(retiro_numero, tipo_candidato="Encuentrista"):
    """
    Devuelve solo los miembros elegibles que AÚN NO están inscritos en `retiro_numero`:
    - Para 'Encuentrista': prioriza a los recién registrados ('Por Asignar') ordenados del ID más reciente al más antiguo.
    - Para 'Servidor': muestra a quienes ya tienen corillo/historial primero, ordenados alfabéticamente.
    """
    with conectar_bd() as conn:
        cursor = conn.cursor()
        if tipo_candidato == "Encuentrista":
            cursor.execute('''
                SELECT m.id_unico, m.nombre_completo, m.corillo
                FROM miembros m
                WHERE m.activo = 1
                  AND (m.corillo IS NULL OR m.corillo = '' OR m.corillo = 'Por Asignar')
                  AND m.id_unico NOT IN (
                      SELECT miembro_id FROM participaciones WHERE retiro_numero = ?
                  )
                ORDER BY CAST(SUBSTR(m.id_unico, 5) AS INTEGER) DESC, m.nombre_completo ASC
            ''', (retiro_numero,))
        else:
            cursor.execute('''
                SELECT m.id_unico, m.nombre_completo, m.corillo
                FROM miembros m
                WHERE m.activo = 1
                  AND m.id_unico NOT IN (
                      SELECT miembro_id FROM participaciones WHERE retiro_numero = ?
                  )
                ORDER BY 
                    CASE WHEN m.corillo IS NOT NULL AND m.corillo != '' AND m.corillo != 'Por Asignar' THEN 0 ELSE 1 END,
                    m.nombre_completo ASC
            ''', (retiro_numero,))
        return cursor.fetchall()


def matricular_todos_los_nuevos(retiro_numero):
    """Matricula de un solo golpe a todos los miembros nuevos ('Por Asignar') que no estén aún en el retiro."""
    try:
        candidatos = obtener_candidatos_retiro(retiro_numero, "Encuentrista")
        if not candidatos:
            return False, "No hay encuentristas nuevos pendientes por matricular."

        with conectar_bd() as conn:
            cursor = conn.cursor()
            registros = [(retiro_numero, c[0], "Encuentrista", "", "Por Asignar") for c in candidatos]
            cursor.executemany('''
                INSERT OR IGNORE INTO participaciones (retiro_numero, miembro_id, tipo_participacion, rol, corillo_asignado)
                VALUES (?, ?, ?, ?, ?)
            ''', registros)
            conn.commit()
        return True, f"✅ Se matricularon {len(registros)} encuentristas nuevos automáticamente."
    except Exception as e:
        return False, f"Error en matrícula masiva: {e}"


def obtener_participantes_retiro(retiro_numero, tipo):
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.miembro_id, m.nombre_completo, p.rol, p.corillo_asignado, m.tutor
            FROM participaciones p
            JOIN miembros m ON p.miembro_id = m.id_unico
            WHERE p.retiro_numero = ? AND p.tipo_participacion = ?
        ''', (retiro_numero, tipo))
        return cursor.fetchall()


def obtener_todos_participantes_edicion(retiro_numero):
    """Obtiene todos los inscritos de un retiro para la vista de previsualización."""
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.miembro_id, m.nombre_completo, p.tipo_participacion, 
                   COALESCE(NULLIF(p.corillo_asignado, ''), 'Por Asignar')
            FROM participaciones p
            JOIN miembros m ON p.miembro_id = m.id_unico
            WHERE p.retiro_numero = ?
            ORDER BY p.tipo_participacion DESC, m.nombre_completo ASC
        ''', (retiro_numero,))
        return cursor.fetchall()


def obtener_participantes_detallados_retiro(retiro_numero, tipo):
    """Obtiene todos los datos de contacto necesarios para exportar las listas del encuentro."""
    with conectar_bd() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.miembro_id, m.nombre_completo, p.rol, p.corillo_asignado,
                   m.direccion, m.telefono, m.fecha_nacimiento, m.edad, m.tutor, m.corillo
            FROM participaciones p
            JOIN miembros m ON p.miembro_id = m.id_unico
            WHERE p.retiro_numero = ? AND p.tipo_participacion = ?
            ORDER BY m.nombre_completo ASC
        ''', (retiro_numero, tipo))
        return cursor.fetchall()


# ==================== ALGORITMO INTELIGENTE DE COLORES ====================

MAPA_NOMBRES_CORILLO = {
    "Celeste": "Celeste (Santa María)",
    "Rojo": "Rojo (San Felipe)",
    "Amarillo": "Amarillo (San Pablo)",
    "Café": "Café (San Pedro)",
    "Verde": "Verde (San José)",
    "Blanco": "Blanco (San Juan)"
}


def distribuir_corillos_automaticamente(retiro_numero):
    try:
        encuentristas = obtener_participantes_retiro(retiro_numero, "Encuentrista")
        if not encuentristas:
            return False, "No hay encuentristas registrados en este retiro."

        familias = {}
        for enc in encuentristas:
            m_id, nombre, rol, corillo, tutor = enc
            llave_familia = tutor.strip().lower() if tutor and len(tutor.strip()) > 3 else " ".join(nombre.strip().split()[-2:]).lower()
            
            if llave_familia not in familias:
                familias[llave_familia] = []
            familias[llave_familia].append(m_id)

        grupos_ordenados = sorted(familias.values(), key=len, reverse=True)
        colores = ["Celeste", "Rojo", "Amarillo", "Café", "Verde", "Blanco"]
        conteos = {c: 0 for c in colores}
        asignaciones = []

        for grupo in grupos_ordenados:
            color_elegido = min(conteos, key=conteos.get)
            for m_id in grupo:
                asignaciones.append((color_elegido, retiro_numero, m_id))
                conteos[color_elegido] += 1

        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                UPDATE participaciones SET corillo_asignado = ? 
                WHERE retiro_numero = ? AND miembro_id = ? AND tipo_participacion = 'Encuentrista'
            ''', asignaciones)
            
            for color, ret_num, m_id in asignaciones:
                corillo_completo = MAPA_NOMBRES_CORILLO.get(color, color)
                
                cursor.execute("SELECT historial_morrales FROM miembros WHERE id_unico = ?", (m_id,))
                res = cursor.fetchone()
                hist_actual = res[0] if res and res[0] else ""
                lista_hist = [c.strip() for c in hist_actual.split(",") if c.strip()]
                
                if color not in lista_hist:
                    lista_hist.append(color)
                nuevo_historial = ",".join(lista_hist)

                cursor.execute('''
                    UPDATE miembros 
                    SET corillo = ?, encuentro_numero = ?, historial_morrales = ? 
                    WHERE id_unico = ?
                ''', (corillo_completo, ret_num, nuevo_historial, m_id))
            conn.commit()

        return True, "Corillos asignados, balanceados y graduados al historial."
    except Exception as e:
        return False, f"Error en el algoritmo: {e}"


def asignar_colores_servidores_por_historial(retiro_numero):
    colores_arcoiris = ["Celeste", "Rojo", "Amarillo", "Café", "Verde", "Blanco"]
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.miembro_id, m.historial_morrales 
                FROM participaciones p
                JOIN miembros m ON p.miembro_id = m.id_unico
                WHERE p.retiro_numero = ? AND p.tipo_participacion = 'Servidor'
            ''', (retiro_numero,))
            servidores = cursor.fetchall()

            conteo_asignados = {c: 0 for c in colores_arcoiris}

            for s in servidores:
                m_id, historial_str = s[0], s[1] if s[1] else ""
                historial_lista = [c.strip() for c in historial_str.split(",") if c.strip()]

                if len(historial_lista) >= 6:
                    opciones_validas = historial_lista[:4]
                else:
                    opciones_validas = [c for c in colores_arcoiris if c not in historial_lista]

                if not opciones_validas:
                    opciones_validas = colores_arcoiris

                opciones_validas.sort(key=lambda c: conteo_asignados[c])
                nuevo_color = opciones_validas[0]
                conteo_asignados[nuevo_color] += 1

                cursor.execute('''
                    UPDATE participaciones SET corillo_asignado = ? 
                    WHERE retiro_numero = ? AND miembro_id = ?
                ''', (nuevo_color, retiro_numero, m_id))

                nuevo_historial = f"{historial_str},{nuevo_color}".strip(",")
                corillo_completo = MAPA_NOMBRES_CORILLO.get(nuevo_color, nuevo_color)
                cursor.execute('''
                    UPDATE miembros 
                    SET corillo = ?, historial_morrales = ? 
                    WHERE id_unico = ?
                ''', (corillo_completo, nuevo_historial, m_id))
            
            conn.commit()
        return True, "Colores de servidores asignados y sincronizados."
    except Exception as e:
        return False, f"Error en historial de servidores: {e}"


def actualizar_corillo_individual(retiro_numero, miembro_id, nuevo_corillo):
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE participaciones SET corillo_asignado = ? 
                WHERE retiro_numero = ? AND miembro_id = ?
            ''', (nuevo_corillo, retiro_numero, miembro_id))
            
            if nuevo_corillo != "Por Asignar":
                corillo_completo = MAPA_NOMBRES_CORILLO.get(nuevo_corillo, nuevo_corillo)
                cursor.execute("SELECT historial_morrales FROM miembros WHERE id_unico = ?", (miembro_id,))
                res = cursor.fetchone()
                hist = res[0] if res and res[0] else ""
                lista_hist = [c.strip() for c in hist.split(",") if c.strip()]
                
                if lista_hist:
                    lista_hist[-1] = nuevo_corillo
                else:
                    lista_hist.append(nuevo_corillo)
                    
                cursor.execute('''
                    UPDATE miembros SET corillo = ?, historial_morrales = ? WHERE id_unico = ?
                ''', (corillo_completo, ",".join(lista_hist), miembro_id))
            conn.commit()
        return True
    except Exception:
        return False


def exportar_listas_encuentro(retiro_numero):
    try:
        servidores = obtener_participantes_detallados_retiro(retiro_numero, "Servidor")
        encuentristas = obtener_participantes_detallados_retiro(retiro_numero, "Encuentrista")
        
        ruta = os.path.join(obtener_ruta_descargas(), f"Listas_Encuentro_{retiro_numero}_{datetime.now().strftime('%H%M')}.csv")
        with open(ruta, mode='w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            
            # SECCIÓN 1: SERVIDORES
            writer.writerow(["", "", "", "S E R V I D O R E S", "", "", "", "", ""])
            writer.writerow(["No.", "NOMBRE", "ROL", "CORRILLO", "DIRECCION", "TELEFONO", "FECHA DE NAC.", "EDAD", "TUTOR"])
            
            lista_servidores = []
            for s in servidores:
                rol_mostrar = s[2] if s[2] else "Servidor"
                corillo_real = s[3] if s[3] and s[3] != "Por Asignar" else (s[9] if s[9] else "Sin Corillo")
                lista_servidores.append({
                    "nombre": s[1], "rol": rol_mostrar, "corillo": corillo_real,
                    "direccion": s[4], "telefono": s[5], "fecha_nac": s[6], "edad": s[7], "tutor": s[8]
                })
            
            lista_servidores.sort(key=lambda x: (x["corillo"], x["nombre"]))
            for index, s in enumerate(lista_servidores, start=1):
                writer.writerow([index, s["nombre"], s["rol"], s["corillo"], s["direccion"], s["telefono"], s["fecha_nac"], s["edad"], s["tutor"]])
                
            writer.writerow([])
            writer.writerow([])
            
            # SECCIÓN 2: ENCUENTRISTAS
            corillos_dict = {}
            for e in encuentristas:
                color = e[3] if e[3] and e[3] != "Por Asignar" else "SIN ASIGNAR"
                if color not in corillos_dict:
                    corillos_dict[color] = []
                corillos_dict[color].append(e)
            
            nombres_santos = {
                "Celeste": "SANTA MARÍA", "Rojo": "SAN FELIPE", "Amarillo": "SAN PABLO",
                "Café": "SAN PEDRO", "Verde": "SAN JOSÉ", "Blanco": "SAN JUAN"
            }
            
            for color, lista_miembros in sorted(corillos_dict.items()):
                santo = nombres_santos.get(color, "VIRTUD").upper()
                total_ninos = len(lista_miembros)
                titulo_corillo = f"CORRILLO DE {santo} ({color.upper()}) - TOTAL: {total_ninos} INTEGRANTES"
                
                writer.writerow(["", "", titulo_corillo, "", "", "", ""])
                writer.writerow(["No.", "NOMBRE", "DIRECCION", "TELEFONO", "FECHA DE NAC.", "EDAD", "TUTOR"])
                
                for index, e in enumerate(lista_miembros, start=1):
                    writer.writerow([index, e[1], e[4], e[5], e[6], e[7], e[8]])
                    
                writer.writerow([])
                writer.writerow([])
                
        return True, f"Listas generadas con éxito en Descargas:\n{os.path.basename(ruta)}"
    except Exception as e:
        return False, f"Error al exportar listas: {e}"