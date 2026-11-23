import flet as ft
import logic
from views.shared import mostrar_snackbar, validar_fecha

import flet as ft
import flet as ft

# Asignar un alias para mantener compatibilidad si Flet en Android no incluye ElevatedButton
if not hasattr(ft, "ElevatedButton"):
    ft.ElevatedButton = ft.FilledButton
    
class ActivitiesView:
    def __init__(self, page: ft.Page, on_activity_created=None):
        self.page = page
        self.on_activity_created = on_activity_created

        # Dropdown dinámico para cargar desde la BD
        self.dd_tipo_actividad = ft.Dropdown(
            label="Tipo de Actividad",
            expand=True,
            options=[]
        )
        self.txt_fecha_actividad = ft.TextField(
            label="Fecha (AAAA-MM-DD)", 
            value="2026-08-15", 
            expand=True,
            keyboard_type=ft.KeyboardType.DATETIME
        )
        self.txt_titulo_actividad = ft.TextField(
            label="Título / Descripción *", 
            expand=True,
            multiline=True,
            min_lines=1,
            max_lines=3
        )
        self.lbl_mensaje_actividad = ft.Text("", weight=ft.FontWeight.BOLD)

        # Cargar los tipos dinámicos de la BD
        self.actualizar_dropdown_tipos_actividades()

        # Estructura adaptable (ResponsiveRow)
        self.view = ft.Container(
            padding=15,
            expand=True,
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Registrar Nueva Actividad o Evento", 
                        size=20, 
                        weight=ft.FontWeight.BOLD
                    ),
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(self.dd_tipo_actividad, col={"xs": 12, "sm": 6}),
                            ft.Container(self.txt_fecha_actividad, col={"xs": 12, "sm": 6}),
                        ],
                        run_spacing=10,
                    ),
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(self.txt_titulo_actividad, col={"xs": 12}),
                        ]
                    ),
                    ft.FilledButton(
                        "Crear Actividad", 
                        icon=ft.Icons.EVENT, 
                        on_click=self.guardar_actividad_click,
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                    ),
                    self.lbl_mensaje_actividad
                ],
                spacing=15,
                scroll=ft.ScrollMode.AUTO,
                expand=True
            )
        )

    def actualizar_dropdown_tipos_actividades(self):
        """Obtiene los tipos de actividad dinámicos de la BD y actualiza el desplegable."""
        tipos = logic.obtener_tipos_actividades()
        
        opciones = []
        for item in tipos:
            # Soporta tupla (id, nombre) o cadena simple
            if isinstance(item, (tuple, list)):
                t_id, nombre = item[0], item[1]
                opciones.append(ft.dropdown.Option(key=str(t_id), text=nombre))
            else:
                opciones.append(ft.dropdown.Option(key=str(item), text=str(item)))
        
        self.dd_tipo_actividad.options = opciones
        if opciones and not self.dd_tipo_actividad.value:
            self.dd_tipo_actividad.value = opciones[0].key

        if self.page:
            self.page.update()

    def guardar_actividad_click(self, e):
        if not self.dd_tipo_actividad.value:
            self.lbl_mensaje_actividad.value = "⚠️ Debes seleccionar un tipo de actividad."
            self.lbl_mensaje_actividad.color = ft.Colors.RED_700
            self.page.update()
            return

        if not self.txt_titulo_actividad.value.strip():
            self.lbl_mensaje_actividad.value = "⚠️ El título/descripción es obligatorio."
            self.lbl_mensaje_actividad.color = ft.Colors.RED_700
            self.page.update()
            return

        if not validar_fecha(self.txt_fecha_actividad.value):
            self.lbl_mensaje_actividad.value = "⚠️ La fecha debe tener formato AAAA-MM-DD."
            self.lbl_mensaje_actividad.color = ft.Colors.RED_700
            self.page.update()
            return

        # Adaptable a tu función crear_actividad (acepta tipo/tipo_id, descripcion y fecha)
        val_tipo = self.dd_tipo_actividad.value
        tipo_param = int(val_tipo) if val_tipo.isdigit() else val_tipo

        try:
            act_id = logic.crear_actividad(
                tipo=tipo_param,
                titulo_descripcion=self.txt_titulo_actividad.value.strip(),
                fecha=self.txt_fecha_actividad.value
            )
        except TypeError:
            # Si tu logic.crear_actividad usa nombres de parámetros distintos:
            act_id = logic.crear_actividad(
                tipo_param,
                self.txt_fecha_actividad.value,
                self.txt_titulo_actividad.value.strip()
            )

        self.lbl_mensaje_actividad.value = f"✅ Actividad '{self.txt_titulo_actividad.value}' creada (ID: {act_id})."
        self.lbl_mensaje_actividad.color = ft.Colors.GREEN_700
        self.txt_titulo_actividad.value = ""
        
        self.page.update()
        if callable(self.on_activity_created):
            self.on_activity_created()