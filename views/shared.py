import csv
from datetime import datetime
import flet as ft
import flet as ft

# Asignar un alias para mantener compatibilidad si Flet en Android no incluye ElevatedButton
if not hasattr(ft, "ElevatedButton"):
    ft.ElevatedButton = ft.FilledButtonfle

def mostrar_snackbar(page: ft.Page, mensaje: str, color=ft.Colors.GREEN_700):
    """Muestra un mensaje flotante SnackBar usando la API actualizada de Flet."""
    snack = ft.SnackBar(
        content=ft.Text(mensaje, color=ft.Colors.WHITE),
        bgcolor=color,
        action="Cerrar",
    )
    # Forma compatible y moderna para desplegar el SnackBar
    page.overlay.append(snack)
    snack.open = True
    page.update()


def validar_fecha(texto: str) -> bool:
    """Valida que una fecha en formato YYYY-MM-DD sea calendáricamente real."""
    if not texto or not texto.strip():
        return True  # Permite campos de fecha opcionales vacíos
    
    try:
        # strptime valida años bisiestos, días según el mes, etc.
        datetime.strptime(texto.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def exportar_csv(prefijo_archivo: str, filas, encabezados, page: ft.Page):
    """Exporta datos a un archivo CSV con codificación compatible con Excel."""
    nombre_archivo = f"{prefijo_archivo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    try:
        # 'utf-8-sig' añade el BOM para que Excel abra los acentos/emojis correctamente
        with open(nombre_archivo, "w", newline="", encoding="utf-8-sig") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(encabezados)
            escritor.writerows(filas)
            
        mostrar_snackbar(page, f"✅ Exportado correctamente: {nombre_archivo}")
        
    except PermissionError:
        mostrar_snackbar(
            page, 
            f"⚠️ Error: El archivo '{nombre_archivo}' está abierto en otro programa.", 
            color=ft.Colors.RED_700
        )
    except Exception as e:
        mostrar_snackbar(
            page, 
            f"⚠️ No se pudo exportar el archivo: {str(e)}", 
            color=ft.Colors.RED_700
        )