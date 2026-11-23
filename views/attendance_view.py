import flet as ft
import logic
from views.shared import exportar_csv, mostrar_snackbar, validar_fecha

import flet as ft
import flet as ft

# Asignar un alias para mantener compatibilidad si Flet en Android no incluye ElevatedButton
if not hasattr(ft, "ElevatedButton"):
    ft.ElevatedButton = ft.FilledButton
    
class AttendanceView:
    def __init__(self, page: ft.Page, state, on_data_change):
        self.page = page
        self.state = state
        self.on_data_change = on_data_change

        # Controles principales
        self.txt_buscar_asistencia = ft.TextField(
            label="Buscar Asistencia",
            hint_text="Nombre, ID o corillo",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=lambda e: self.cargar_lista_asistencia()
        )
        self.txt_fecha_inicio_ranking = ft.TextField(
            label="Fecha inicio", 
            hint_text="AAAA-MM-DD",
            expand=True,
            keyboard_type=ft.KeyboardType.DATETIME
        )
        self.txt_fecha_fin_ranking = ft.TextField(
            label="Fecha fin", 
            hint_text="AAAA-MM-DD",
            expand=True,
            keyboard_type=ft.KeyboardType.DATETIME
        )

        self.dd_actividades_existentes = ft.Dropdown(
            label="Actividad Activa", 
            expand=True
        )
        self.dd_actividades_existentes.on_change = lambda e: self.cargar_lista_asistencia()

        self.col_lista_asistencia = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        self.col_ranking_servidores = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
        self.btn_cargar_asistencia = ft.IconButton(
            icon=ft.Icons.REFRESH, 
            tooltip="Refrescar Lista",
            on_click=lambda e: self.cargar_lista_asistencia()
        )

        # Contenedores para las vistas individuales
        self.view_asistencia = ft.Column(
            controls=[
                ft.ResponsiveRow([
                    ft.Container(self.dd_actividades_existentes, col={"xs": 10, "sm": 11}),
                    ft.Container(
                        self.btn_cargar_asistencia, 
                        col={"xs": 2, "sm": 1}, 
                        alignment=ft.Alignment(0, 0)
                    ),
                ]),
                
                ft.ResponsiveRow([
                    ft.Container(self.txt_buscar_asistencia, col={"xs": 12}),
                ]),
                ft.Row([
                    ft.Text("Ordenar por:", size=12, weight=ft.FontWeight.BOLD),
                    ft.OutlinedButton("ID", on_click=lambda e: self.cambiar_orden("id") or self.cargar_lista_asistencia()),
                    ft.OutlinedButton("Nombre", on_click=lambda e: self.cambiar_orden("nombre") or self.cargar_lista_asistencia()),
                    ft.OutlinedButton("Corillo", on_click=lambda e: self.cambiar_orden("corillo") or self.cargar_lista_asistencia()),
                ], scroll=ft.ScrollMode.AUTO),
                ft.Row([
                    ft.OutlinedButton("Exportar Asistencia CSV", icon=ft.Icons.DOWNLOAD, on_click=self.exportar_asistencia_csv)
                ]),
                ft.Divider(),
                self.col_lista_asistencia
            ],
            expand=True
        )

        self.view_ranking = ft.Column(
            controls=[
                ft.ResponsiveRow([
                    ft.Container(self.txt_fecha_inicio_ranking, col={"xs": 6, "sm": 6}),
                    ft.Container(self.txt_fecha_fin_ranking, col={"xs": 6, "sm": 6}),
                ]),
                ft.ResponsiveRow([
                    ft.Container(
                        ft.FilledButton("Aplicar filtro", icon=ft.Icons.FILTER_ALT, on_click=self.calcular_ranking_click),
                        col={"xs": 12, "sm": 6}
                    ),
                    ft.Container(
                        ft.OutlinedButton("Exportar Ranking CSV", icon=ft.Icons.DOWNLOAD, on_click=self.exportar_ranking_csv),
                        col={"xs": 12, "sm": 6}
                    ),
                ]),
                ft.Divider(),
                self.col_ranking_servidores
            ],
            expand=True
        )

        # Contenedor dinámico de contenido
        self.container_contenido = ft.Container(content=self.view_asistencia, expand=True)

        def cambiar_pestana(e):
            seleccionados = list(e.control.selected) if e.control.selected else []
            if seleccionados and "0" in seleccionados:
                self.container_contenido.content = self.view_asistencia
            else:
                self.container_contenido.content = self.view_ranking
            self.page.update()

        # Usamos una lista ["0"] en lugar del set {"0"}
        self.selector_pestañas = ft.SegmentedButton(
            selected=["0"],
            on_change=cambiar_pestana,
            segments=[
                ft.Segment(
                    value="0",
                    label=ft.Text("Toma de Asistencia"),
                    icon=ft.Icon(ft.Icons.CHECK_BOX)
                ),
                ft.Segment(
                    value="1",
                    label=ft.Text("Acumulado / Ranking"),
                    icon=ft.Icon(ft.Icons.LEADERBOARD)
                ),
            ]
        )

        self.view = ft.Container(
            padding=10,
            expand=True,
            content=ft.Column(
                controls=[
                    ft.Text("Gestión de Asistencia y Puntajes", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row([self.selector_pestañas], alignment=ft.MainAxisAlignment.CENTER),
                    self.container_contenido
                ],
                expand=True
            )
        )

    def actualizar_dropdown_actividades(self):
        actividades = logic.obtener_actividades()
        self.dd_actividades_existentes.options = [
            ft.dropdown.Option(key=str(a[0]), text=f"[{a[3]}] {a[1]} - {a[2]}") for a in actividades
        ]
        if actividades:
            self.dd_actividades_existentes.value = str(actividades[0][0])
        else:
            self.dd_actividades_existentes.value = None
        self.page.update()

    def cambiar_orden(self, criterio):
        self.state.criterio_orden = criterio

    def cargar_lista_asistencia(self):
        self.col_lista_asistencia.controls.clear()
        miembros = logic.obtener_miembros_ordenados(self.state.criterio_orden)
        filtro_asistencia = self.txt_buscar_asistencia.value.lower().strip() if self.txt_buscar_asistencia.value else ""

        if filtro_asistencia:
            miembros = [m for m in miembros if filtro_asistencia in m[0].lower() or filtro_asistencia in m[1].lower() or filtro_asistencia in (m[2] or "").lower()]

        if not miembros:
            self.col_lista_asistencia.controls.append(ft.Text("No hay miembros registrados."))
            self.page.update()
            return

        act_id = int(self.dd_actividades_existentes.value) if self.dd_actividades_existentes.value else None
        asistencias_guardadas = logic.obtener_estado_asistencia(act_id) if act_id else {}

        for m_id, nombre, corillo, ocupacion, grado, rubrica, historial_morrales in miembros:
            estado_previo = bool(asistencias_guardadas.get(m_id, 0))
            sw_asistencia = ft.Switch(value=estado_previo)

            def switch_changed(e, id_m=m_id):
                if self.dd_actividades_existentes.value:
                    val = 1 if e.control.value else 0
                    logic.marcar_asistencia(id_m, int(self.dd_actividades_existentes.value), val)
                    self.calcular_ranking_click(None)

            sw_asistencia.on_change = switch_changed

            row = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Row([
                            ft.Text(f"ID: {m_id}", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.BLUE_700),
                            ft.Text(f"• Rúbrica: {rubrica}", size=11, italic=True, color=ft.Colors.GREY_700),
                        ]),
                        ft.Text(nombre, weight=ft.FontWeight.BOLD, size=14),
                        ft.Text(corillo if corillo else "Sin corillo", size=11, color=ft.Colors.GREY_600)
                    ], expand=True),
                    sw_asistencia
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=12,
                border=ft.Border.all(1, ft.Colors.GREY_300),  # Corregido aquí
                border_radius=8
            )
            self.col_lista_asistencia.controls.append(row)

        self.calcular_ranking_click(None)
        self.page.update()

    def calcular_ranking_click(self, e):
        self.col_ranking_servidores.controls.clear()

        fecha_inicio = self.txt_fecha_inicio_ranking.value if validar_fecha(self.txt_fecha_inicio_ranking.value) else None
        fecha_fin = self.txt_fecha_fin_ranking.value if validar_fecha(self.txt_fecha_fin_ranking.value) else None

        if self.txt_fecha_inicio_ranking.value and not fecha_inicio:
            mostrar_snackbar(self.page, "⚠️ Fecha de inicio incorrecta. Usa AAAA-MM-DD.", ft.Colors.RED_700)
            return
        if self.txt_fecha_fin_ranking.value and not fecha_fin:
            mostrar_snackbar(self.page, "⚠️ Fecha fin incorrecta. Usa AAAA-MM-DD.", ft.Colors.RED_700)
            return

        ranking = logic.obtener_ranking_servidores(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

        for lugar, item in enumerate(ranking, start=1):
            medalla = "🥇" if lugar == 1 else "🥈" if lugar == 2 else "🥉" if lugar == 3 else f"#{lugar}"
            
            self.col_ranking_servidores.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(medalla, size=18, width=30),
                        ft.Column([
                            ft.Text(f"{item['id']} - {item['nombre']}", weight=ft.FontWeight.BOLD, size=13),
                            ft.Text(f"Corillo: {item['corillo']}", size=11, color=ft.Colors.GREY_700)
                        ], expand=True),
                        ft.Column([
                            ft.Text(f"{item['asistencias']}/{item['total_actividades']}", size=12, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{item['puntaje']}%", size=14, color=ft.Colors.BLUE_800, weight=ft.FontWeight.BOLD)
                        ], horizontal_alignment=ft.CrossAxisAlignment.END)
                    ]),
                    padding=10,
                    bgcolor=ft.Colors.BLUE_50 if lugar <= 3 else ft.Colors.GREY_100,
                    border_radius=8
                )
            )
        self.page.update()

    def exportar_asistencia_csv(self, e):
        act_id = int(self.dd_actividades_existentes.value) if self.dd_actividades_existentes.value else None
        miembros = logic.obtener_miembros_ordenados(self.state.criterio_orden)
        asistencias_guardadas = logic.obtener_estado_asistencia(act_id) if act_id else {}
        rows = []
        for m_id, nombre, corillo, ocupacion, grado, rubrica in miembros:
            estado = "Asistió" if asistencias_guardadas.get(m_id, 0) == 1 else "Falta"
            rows.append([m_id, nombre, corillo, rubrica, estado])
        if rows:
            exportar_csv("asistencia_export", rows, ["ID", "Nombre", "Corillo", "Rúbrica", "Estado"], self.page)

    def exportar_ranking_csv(self, e):
        fecha_inicio = self.txt_fecha_inicio_ranking.value if validar_fecha(self.txt_fecha_inicio_ranking.value) else None
        fecha_fin = self.txt_fecha_fin_ranking.value if validar_fecha(self.txt_fecha_fin_ranking.value) else None
        rows = [
            [item["id"], item["nombre"], item["corillo"], item["asistencias"], item["total_actividades"], item["puntaje"]]
            for item in logic.obtener_ranking_servidores(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        ]
        if rows:
            exportar_csv("ranking_export", rows, ["ID", "Nombre", "Corillo", "Asistencias", "Total Actividades", "Puntaje"], self.page)