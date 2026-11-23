import flet as ft
from types import SimpleNamespace
import os

# Importación directa desde database.py
from database import inicializar_base_de_datos as inicializar_bd

from views.activities_view import ActivitiesView
from views.attendance_view import AttendanceView
from views.members_view import MembersView
from views.rubrics_view import RubricsView

CLAVE_ADMIN = "1234"


def main(page: ft.Page):
    # 1. Inicializar la Base de Datos
    inicializar_bd()

    page.title = "Sistema Arcoíris - Gestión de Asistencia y Directorio"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 900
    page.padding = 10

    state = SimpleNamespace(criterio_orden="id")

    # 2. Callbacks de actualización entre vistas
    def callback_members_changed():
        if 'attendance_view' in locals():
            attendance_view.cargar_lista_asistencia()
        if 'rubrics_view' in locals():
            rubrics_view.actualizar_dropdown_miembros_especiales()

    def callback_activity_created():
        if 'attendance_view' in locals():
            attendance_view.actualizar_dropdown_actividades()
            attendance_view.cargar_lista_asistencia()

    def callback_rubrics_changed():
        if 'attendance_view' in locals():
            attendance_view.cargar_lista_asistencia()
        if 'members_view' in locals():
            members_view.cargar_directorio_tabla()
        if 'activities_view' in locals():
            activities_view.actualizar_dropdown_tipos_actividades()

    def callback_attendance_changed():
        if 'rubrics_view' in locals():
            rubrics_view.actualizar_dropdown_miembros_especiales()
        if 'members_view' in locals():
            members_view.cargar_directorio_tabla()

    # 3. Instanciación de Vistas
    attendance_view = AttendanceView(
        page, 
        state, 
        on_data_change=callback_attendance_changed
    )

    members_view = MembersView(
        page,
        state,
        on_data_change=callback_members_changed,
    )

    activities_view = ActivitiesView(
        page,
        on_activity_created=callback_activity_created,
    )

    rubrics_view = RubricsView(
        page,
        get_miembros_especiales=getattr(members_view, 'actualizar_dropdown_miembros_especiales', lambda: None),
        on_data_change=callback_rubrics_changed,
    )

    # 4. Carga inicial de datos
    attendance_view.actualizar_dropdown_actividades()
    activities_view.actualizar_dropdown_tipos_actividades()
    members_view.cargar_directorio_tabla()
    attendance_view.cargar_lista_asistencia()
    rubrics_view.cargar_tabla_rubricas_generales()
    rubrics_view.actualizar_dropdown_miembros_especiales()

    container_contenido = ft.Container(content=members_view.view, expand=True, padding=10)

    # 5. Autenticación para Desbloquear Botones de Administración
    def mostrar_login_admin(e):
        txt_password = ft.TextField(
            label="Contraseña de Administrador",
            password=True,
            can_reveal_password=True,
            width=280,
            autofocus=True
        )
        txt_error = ft.Text("", color=ft.Colors.RED_400, size=12)

        def validar_password(e_val):
            if txt_password.value == CLAVE_ADMIN:
                dialogo_login.open = False
                txt_password.value = ""
                txt_error.value = ""
                
                # Hacer visibles los botones de la vista miembros
                members_view.row_admin.visible = True
                
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(" MODO ADMINISTRADOR ACTIVADO"),
                    bgcolor=ft.Colors.GREEN_600,
                    open=True
                )
                page.update()
            else:
                txt_error.value = "Contraseña incorrecta."
                page.update()

        dialogo_login = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.LOCK, color=ft.Colors.AMBER_700),
                ft.Text("Acceso Restringido")
            ]),
            content=ft.Column(
                [
                    ft.Text("Ingresa la clave para activar las herramientas avanzadas:"),
                    txt_password,
                    txt_error
                ],
                tight=True,
                spacing=10
            ),
            actions=[
                ft.TextButton(
                    "Cancelar", 
                    on_click=lambda _: setattr(dialogo_login, "open", False) or page.update()
                ),
                ft.FilledButton("Desbloquear", on_click=validar_password)
            ]
        )

        page.overlay.append(dialogo_login)
        dialogo_login.open = True
        page.update()

    # 6. Encabezado Superior con Ícono de Candado / Administración
    header_app = ft.Container(
        content=ft.Row(
            [
                ft.Text("Sistema Arcoíris", size=20, weight=ft.FontWeight.BOLD),
                ft.IconButton(
                    icon=ft.Icons.ADMIN_PANEL_SETTINGS,
                    icon_color=ft.Colors.BLUE_800,
                    icon_size=28,
                    tooltip="Activar Modo Administrador",
                    on_click=mostrar_login_admin
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        padding=ft.Padding(15, 8, 15, 8),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border_radius=8
    )

    # 7. Navegación
    def on_nav_change(e):
        idx = e.control.selected_index
        if idx == 0:
            members_view.cargar_directorio_tabla()
            container_contenido.content = members_view.view
        elif idx == 1:
            activities_view.actualizar_dropdown_tipos_actividades()
            container_contenido.content = activities_view.view
        elif idx == 2:
            attendance_view.cargar_lista_asistencia()
            container_contenido.content = attendance_view.view
        elif idx == 3:
            rubrics_view.cargar_tabla_rubricas_generales()
            rubrics_view.actualizar_dropdown_miembros_especiales()
            container_contenido.content = rubrics_view.view
        page.update()

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.PERSON_ADD_OUTLINED,
                selected_icon=ft.Icons.PERSON_ADD,
                label="Directorio"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.EVENT_NOTE_OUTLINED,
                selected_icon=ft.Icons.EVENT_NOTE,
                label="Actividades"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.CHECK_BOX_OUTLINED,
                selected_icon=ft.Icons.CHECK_BOX,
                label="Asistencia"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.TUNE_OUTLINED,
                selected_icon=ft.Icons.TUNE,
                label="Rúbricas"
            ),
        ],
        on_change=on_nav_change,
    )

    page.add(
        ft.Column(
            [
                header_app,
                container_contenido
            ],
            expand=True
        )
    )


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8550))
    ft.run(
        main,
        view=ft.AppView.WEB_BROWSER,
        host="0.0.0.0",
        port=puerto
    )