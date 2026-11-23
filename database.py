import os
import shutil
import sqlite3


# 1. Detectar ruta escribible segura según la plataforma (Android vs PC)
def obtener_ruta_db_activa():
    is_android = hasattr(os, "uname") and "android" in os.uname().release.lower()
    
    if is_android:
        storage_dir = os.environ.get("FLET_APP_STORAGE_DATA") or os.path.expanduser("~")
        os.makedirs(storage_dir, exist_ok=True)
        return os.path.join(storage_dir, "arcoiris.db")
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(BASE_DIR, "arcoiris.db")


DB_PATH = obtener_ruta_db_activa()


def conectar_bd():
    """Conecta a la base de datos local SQLite activa."""
    ruta_activa = obtener_ruta_db_activa()
    conn = sqlite3.connect(ruta_activa)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def generar_siguiente_id_miembro(cursor=None) -> str:
    """Genera el siguiente ID correlativo con el formato ARC-001, ARC-002, etc."""
    debe_cerrar = False
    if cursor is None:
        conn = conectar_bd()
        cursor = conn.cursor()
        debe_cerrar = True

    try:
        cursor.execute("SELECT id_unico FROM miembros WHERE id_unico LIKE 'ARC-%'")
        filas = cursor.fetchall()
        
        max_num = 0
        for (m_id,) in filas:
            try:
                num = int(m_id.split('-')[1])
                if num > max_num:
                    max_num = num
            except (IndexError, ValueError):
                continue
                
        siguiente_num = max_num + 1
        return f"ARC-{siguiente_num:03d}"
    finally:
        if debe_cerrar:
            conn.close()


def inicializar_base_de_datos():
    """Crea la estructura de tablas relacional e inserta únicamente los catálogos base."""
    with conectar_bd() as conn:
        cursor = conn.cursor()

        # 0. TABLA DE TIPOS DE ACTIVIDADES
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipos_actividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_actividad TEXT NOT NULL UNIQUE
        )
        ''')

        actividades_predefinidas = [
            ('misa',),
            ('hora santa parroquial',),
            ('adoracion al santisimo',),
            ('actividades extras',),
            ('reunion de colores',),
            ('escuelita arcoiris',)
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO tipos_actividades (nombre_actividad)
            VALUES (?)
        ''', actividades_predefinidas)

        # 1. TABLA DE RÚBRICAS
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rubricas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_rubrica TEXT NOT NULL UNIQUE, 
            es_especial INTEGER DEFAULT 0
        )
        ''')

        rubricas_base = [
            ('Normal', 0),
            ('Tarde', 0),
            ('Estudia y Trabaja', 0),
            ('Vive Lejos', 0)
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO rubricas (nombre_rubrica, es_especial)
            VALUES (?, ?)
        ''', rubricas_base)

        # 2. RELACIÓN RÚBRICA - ACTIVIDADES CON PORCENTAJES
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rubrica_actividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rubrica_id INTEGER NOT NULL,
            tipo_actividad_id INTEGER NOT NULL,
            porcentaje REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (rubrica_id) REFERENCES rubricas(id) ON DELETE CASCADE,
            FOREIGN KEY (tipo_actividad_id) REFERENCES tipos_actividades(id) ON DELETE CASCADE,
            UNIQUE(rubrica_id, tipo_actividad_id)
        )
        ''')

        cursor.execute("SELECT id FROM rubricas")
        rubrica_ids = [row[0] for row in cursor.fetchall()]
        for r_id in rubrica_ids:
            actividades_config = [
                (r_id, 1, 20.0),
                (r_id, 2, 15.0),
                (r_id, 3, 15.0),
                (r_id, 4, 15.0),
                (r_id, 5, 20.0),
                (r_id, 6, 15.0)
            ]
            cursor.executemany('''
                INSERT OR IGNORE INTO rubrica_actividades (rubrica_id, tipo_actividad_id, porcentaje)
                VALUES (?, ?, ?)
            ''', actividades_config)

        # 3. TABLA DE MIEMBROS
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS miembros (
            id_unico TEXT PRIMARY KEY,
            nombre_completo TEXT NOT NULL,
            fecha_nacimiento TEXT,
            edad INTEGER,
            corillo TEXT,
            ocupacion_actual TEXT,
            grado_estudio TEXT,
            direccion TEXT,
            telefono TEXT,
            telefono_emergencia TEXT,
            tutor TEXT,
            telefono_tutor TEXT,
            encuentro_numero INTEGER,
            rubrica_id INTEGER,
            historial_morrales TEXT DEFAULT '',
            activo INTEGER DEFAULT 1,
            FOREIGN KEY (rubrica_id) REFERENCES rubricas(id) ON DELETE SET NULL
        )
        ''')

        # Migraciones seguras por si se importa una BD antigua
        for col_sql in [
            "ALTER TABLE miembros ADD COLUMN historial_morrales TEXT DEFAULT ''",
            "ALTER TABLE miembros ADD COLUMN activo INTEGER DEFAULT 1"
        ]:
            try:
                cursor.execute(col_sql)
            except sqlite3.OperationalError:
                pass

        # 4. TABLA DE ACTIVIDADES / EVENTOS
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS actividades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_id INTEGER NOT NULL,
            titulo_descripcion TEXT NOT NULL,
            fecha TEXT NOT NULL,
            FOREIGN KEY (tipo_id) REFERENCES tipos_actividades(id) ON DELETE CASCADE
        )
        ''')

        # 5. TABLA DE ASISTENCIAS
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencias (
            miembro_id TEXT NOT NULL,
            actividad_id INTEGER NOT NULL,
            asistio INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (miembro_id, actividad_id),
            FOREIGN KEY (miembro_id) REFERENCES miembros(id_unico) ON DELETE CASCADE,
            FOREIGN KEY (actividad_id) REFERENCES actividades(id) ON DELETE CASCADE
        )
        ''')

        # 6. TABLA DE ENCUENTROS / RETIROS
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS retiros (
            numero INTEGER PRIMARY KEY,
            descripcion TEXT,
            fecha TEXT
        )
        ''')

        # 7. TABLA DE PARTICIPANTES DEL ENCUENTRO (Servidores y Encuentristas)
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

        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM miembros")
        total_miembros = cursor.fetchone()[0]

    print(f"Base de datos de Arcoíris lista ({total_miembros} miembros registrados).")


# --- FUNCIONES DE ADMINISTRACIÓN Y RESPALDO ---

def vaciar_base_datos() -> tuple[bool, str]:
    """Elimina todos los registros de miembros, actividades y asistencias."""
    try:
        with conectar_bd() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM asistencias;")
            cursor.execute("DELETE FROM actividades;")
            cursor.execute("DELETE FROM miembros;")
            conn.commit()
        return True, "Base de datos vaciada con éxito."
    except Exception as e:
        return False, f"Error al vaciar base de datos: {str(e)}"


def exportar_respaldo_automatico() -> tuple[bool, str]:
    """Copia la base de datos activa hacia la carpeta Descargas del dispositivo."""
    try:
        is_android = hasattr(os, "uname") and "android" in os.uname().release.lower()
        downloads_dir = "/sdcard/Download" if is_android else os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        
        destino = os.path.join(downloads_dir, "arcoiris.db")
        shutil.copy2(DB_PATH, destino)
        return True, f"Base de datos respaldada en Descargas:\n{destino}"
    except Exception as e:
        return False, f"Error al respaldar: {str(e)}"


def importar_base_de_datos() -> tuple[bool, str]:
    """Busca 'arcoiris.db' o 'arcoiris_backup.db' en la carpeta Descargas y reemplaza la base de datos activa."""
    try:
        is_android = hasattr(os, "uname") and "android" in os.uname().release.lower()
        downloads_dir = "/sdcard/Download" if is_android else os.path.join(os.path.expanduser("~"), "Downloads")

        origen_1 = os.path.join(downloads_dir, "arcoiris.db")
        origen_2 = os.path.join(downloads_dir, "arcoiris_backup.db")

        origen_final = None
        if os.path.exists(origen_1):
            origen_final = origen_1
        elif os.path.exists(origen_2):
            origen_final = origen_2

        if not origen_final:
            return False, f"No se encontró 'arcoiris.db' ni 'arcoiris_backup.db' en Descargas ({downloads_dir})."

        shutil.copy2(origen_final, DB_PATH)
        return True, "¡Base de datos importada con éxito desde Descargas!"
    except Exception as e:
        return False, f"Error al importar base de datos: {str(e)}"


importar_respaldo_automatico = importar_base_de_datos

if __name__ == "__main__":
    inicializar_base_de_datos()