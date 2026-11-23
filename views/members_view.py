import os
from datetime import datetime
import flet as ft

import logic
from views.shared import mostrar_snackbar, validar_fecha

# Asignar un alias para mantener compatibilidad si Flet en Android no incluye ElevatedButton
if not hasattr(ft, "ElevatedButton"):
    ft.ElevatedButton = ft.FilledButton


class MembersView:
    def __init__(self, page: ft.Page, state, on_data_change):
        self.page = page
        self.state = state
        self.on_data_change = on_data_change

        # Campos del formulario
        self.txt_buscar_directorio = ft.TextField(
            label="Buscar Miembro",
            hint_text="Nombre, ID o Corillo",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_change=lambda e: self.cargar_directorio_tabla()
        )

        self.txt_nombre = ft.TextField(label="Nombre Completo *", expand=True)
        self.txt_fecha_nac = ft.TextField(
            label="Fecha Nacimiento (AAAA-MM-DD)",
            value="2008-05-15",
            expand=True,
            on_change=self.actualizar_edad_automatica
        )
        self.txt_edad = ft.TextField(
            label="Edad (Auto)",
            value=str(self.calcular_edad("2008-05-15")),
            read_only=True,
            expand=True
        )
        
        # --- Selección de Tipo de Integrante ---
        self.dd_tipo = ft.Dropdown(
            label="Tipo de Registro *",
            value="Encuentrista",
            options=[ft.dropdown.Option("Encuentrista"), ft.dropdown.Option("Servidor")],
            expand=True
        )
        self.dd_tipo.on_change = self.cambiar_tipo_registro

        self.dd_corillo = ft.Dropdown(
            label="Corillo Actual (Último asignado)",
            value="Por Asignar",
            expand=True,
            options=[
                ft.dropdown.Option("Por Asignar"),
                ft.dropdown.Option("Celeste (Santa María)"),
                ft.dropdown.Option("Rojo (San Felipe)"),
                ft.dropdown.Option("Amarillo (San Pablo)"),
                ft.dropdown.Option("Café (San Pedro)"),
                ft.dropdown.Option("Verde (San José)"),
                ft.dropdown.Option("Blanco (San Juan)"),
            ]
        )

        # --- SISTEMA CRONOLÓGICO DE MORRALES ---
        self.txt_historial_ordenado = ft.TextField(
            label="Orden cronológico (Se llena solo al marcar las casillas)", 
            read_only=True, 
            expand=True
        )

        self.chk_celeste = ft.Checkbox(label="Celeste")
        self.chk_rojo = ft.Checkbox(label="Rojo")
        self.chk_amarillo = ft.Checkbox(label="Amarillo")
        self.chk_cafe = ft.Checkbox(label="Café")
        self.chk_verde = ft.Checkbox(label="Verde")
        self.chk_blanco = ft.Checkbox(label="Blanco")
        
        self.checks_historial = [self.chk_celeste, self.chk_rojo, self.chk_amarillo, self.chk_cafe, self.chk_verde, self.chk_blanco]
        
        for chk in self.checks_historial:
            chk.on_change = self.actualizar_orden_historial
        
        # Contenedores para ocultarlos/mostrarlos limpiamente
        self.container_corillo = ft.Container(self.dd_corillo, col={"xs": 12}, visible=False)
        
        self.container_historial = ft.Container(
            content=ft.Column([
                ft.Text("Historial (¡Márcalos en el orden que los vivió!):", weight="bold", size=12),
                ft.Row(self.checks_historial, wrap=True),
                self.txt_historial_ordenado
            ]),
            col={"xs": 12},
            bgcolor=ft.Colors.GREY_100, padding=10, border_radius=5, visible=False
        )

        self.dd_ocupacion = ft.Dropdown(
            label="Ocupación",
            value="Estudiante",
            expand=True,
            options=[
                ft.dropdown.Option("Estudiante"), ft.dropdown.Option("Empleado"),
                ft.dropdown.Option("Desempleado"), ft.dropdown.Option("Hogar"), ft.dropdown.Option("Otro"),
            ]
        )
        self.dd_grado = ft.Dropdown(
            label="Grado de Estudio",
            value="Preparatoria",
            expand=True,
            options=[
                ft.dropdown.Option("Primaria"), ft.dropdown.Option("Secundaria"),
                ft.dropdown.Option("Preparatoria"), ft.dropdown.Option("Universidad / Licenciatura"),
                ft.dropdown.Option("Maestría / Postgrado"), ft.dropdown.Option("Ninguno / Otro"),
            ]
        )

        self.txt_direccion = ft.TextField(label="Dirección", expand=True)
        self.txt_telefono = ft.TextField(label="Teléfono", expand=True)
        self.txt_tel_emergencia = ft.TextField(label="Tel. Emergencia", expand=True)
        self.txt_tutor = ft.TextField(label="Nombre del Tutor", expand=True)
        self.txt_tel_tutor = ft.TextField(label="Teléfono del Tutor", expand=True)
        self.txt_encuentro = ft.TextField(label="No. Encuentro", value="5", expand=True)
        
        self.dd_rubrica = ft.Dropdown(label="Tipo de Rúbrica", expand=True)
        self.cargar_opciones_rubrica()

        self.lbl_mensaje_registro = ft.Text("", color=ft.Colors.GREEN_700, weight=ft.FontWeight.BOLD)
        self.col_tabla_directorio = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

        # Fila de botones administrativos protegidos
        self.row_admin = ft.Container(
            ft.Row([
                ft.FilledButton(" Exportar Directorio", icon=ft.Icons.TABLE_CHART, on_click=self.exportar_directorio_click),
                ft.FilledButton(" Gestión Encuentros", icon=ft.Icons.GROUPS, on_click=self.abrir_gestion_encuentros),
                ft.FilledButton(" Respaldar BD", icon=ft.Icons.BACKUP, on_click=self.exportar_bd_click),
                ft.FilledButton(" Importar BD", icon=ft.Icons.RESTORE_PAGE, on_click=self.importar_bd_click),
                ft.FilledButton(" Datos Ejemplo", icon=ft.Icons.AUTO_FIX_HIGH, on_click=self.llenar_datos_ejemplo),
                ft.FilledButton(" Vaciar BD", icon=ft.Icons.DELETE_FOREVER, bgcolor=ft.Colors.RED_400, color=ft.Colors.WHITE, on_click=self.vaciar_bd_click)
            ], wrap=True),
            col={"xs": 12, "md": 12}, alignment=ft.Alignment(1, 0), visible=False
        )

        # Contenedor principal de la vista
        self.view = ft.Column(
            controls=[
                ft.ResponsiveRow([
                    ft.Container(ft.Text("Registrar Integrante", size=20, weight=ft.FontWeight.BOLD), col={"xs": 12, "md": 5}),
                    self.row_admin
                ]),
                
                ft.ResponsiveRow([
                    ft.Container(self.txt_buscar_directorio, col={"xs": 12}),
                    ft.Container(self.txt_nombre, col={"xs": 12, "sm": 7}),
                    ft.Container(self.dd_tipo, col={"xs": 12, "sm": 5}),
                    
                    ft.Container(self.txt_fecha_nac, col={"xs": 8, "sm": 4}),
                    ft.Container(self.txt_edad, col={"xs": 4, "sm": 2}),
                    ft.Container(self.dd_ocupacion, col={"xs": 12, "sm": 3}),
                    ft.Container(self.dd_grado, col={"xs": 12, "sm": 3}),
                    
                    self.container_corillo,
                    self.container_historial,
                    
                    ft.Container(self.txt_direccion, col={"xs": 12}),
                    ft.Container(self.txt_telefono, col={"xs": 12, "sm": 6}),
                    ft.Container(self.txt_tel_emergencia, col={"xs": 12, "sm": 6}),
                    ft.Container(self.txt_tutor, col={"xs": 12, "sm": 6}),
                    ft.Container(self.txt_tel_tutor, col={"xs": 12, "sm": 6}),
                    
                    ft.Container(self.txt_encuentro, col={"xs": 12, "sm": 6}),
                    ft.Container(self.dd_rubrica, col={"xs": 12, "sm": 6}),
                ], run_spacing=8),

                ft.ElevatedButton("Guardar en Directorio", icon=ft.Icons.SAVE, on_click=self.guardar_miembro_click, width=200),
                self.lbl_mensaje_registro,
                ft.Divider(),
                
                ft.Row([
                    ft.Text("Ordenar por:", weight=ft.FontWeight.BOLD, size=12),
                    ft.OutlinedButton("ID", on_click=lambda e: self.cambiar_orden("id")),
                    ft.OutlinedButton("Nombre", on_click=lambda e: self.cambiar_orden("nombre")),
                    ft.OutlinedButton("Corillo", on_click=lambda e: self.cambiar_orden("corillo")),
                ], scroll=ft.ScrollMode.AUTO),
                
                self.col_tabla_directorio
            ],
            scroll=ft.ScrollMode.AUTO, spacing=12, expand=True
        )

    # --- CÁLCULO AUTOMÁTICO DE EDAD ---
    def calcular_edad(self, fecha_str: str) -> int:
        try:
            nacimiento = datetime.strptime(fecha_str.strip(), "%Y-%m-%d")
            hoy = datetime.now()
            edad = hoy.year - nacimiento.year - (
                (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
            )
            return max(0, edad)
        except ValueError:
            return 0

    def actualizar_edad_automatica(self, e):
        fecha_texto = self.txt_fecha_nac.value.strip()
        if len(fecha_texto) == 10 and validar_fecha(fecha_texto):
            self.txt_edad.value = str(self.calcular_edad(fecha_texto))
        else:
            self.txt_edad.value = ""
        self.txt_edad.update()

    # --- LÓGICA PARA ARMAR EL ORDEN CRONOLÓGICO DE LOS CHECKBOXES ---
    def actualizar_orden_historial(self, e):
        color = e.control.label
        actuales = [c.strip() for c in self.txt_historial_ordenado.value.split(",") if c.strip()]
        
        if e.control.value:
            if color not in actuales:
                actuales.append(color)
        else:
            if color in actuales:
                actuales.remove(color)
                
        self.txt_historial_ordenado.value = ",".join(actuales)
        self.txt_historial_ordenado.update()

    # --- MÉTODO PARA MOSTRAR/OCULTAR CAMPOS SEGÚN EL TIPO ---
    def cambiar_tipo_registro(self, e):
        es_servidor = self.dd_tipo.value == "Servidor"
        
        self.container_corillo.visible = es_servidor
        self.container_historial.visible = es_servidor
        
        if not es_servidor:
            self.dd_corillo.value = "Por Asignar"
            for chk in self.checks_historial:
                chk.value = False
            self.txt_historial_ordenado.value = ""
                
        self.page.update()

    # -------------------------------------------------------------
    # IMPORTACIÓN Y EXPORTACIÓN DE BASE DE DATOS
    # -------------------------------------------------------------
    def importar_bd_click(self, e):
        try:
            if hasattr(logic, "importar_base_de_datos"):
                exito, mensaje = logic.importar_base_de_datos()
            else:
                from database import importar_respaldo_automatico
                exito, mensaje = importar_respaldo_automatico()

            if exito:
                self.lbl_mensaje_registro.value = f"✅ {mensaje}"
                self.lbl_mensaje_registro.color = ft.Colors.GREEN_700
                self.cargar_directorio_tabla()
                self.on_data_change()
            else:
                self.lbl_mensaje_registro.value = f"⚠ {mensaje}"
                self.lbl_mensaje_registro.color = ft.Colors.RED_700

            self.page.update()
        except Exception as ex:
            self.lbl_mensaje_registro.value = f"⚠️ Error al importar: {ex}"
            self.lbl_mensaje_registro.color = ft.Colors.RED_700
            self.page.update()

    def exportar_bd_click(self, e):
        try:
            is_android = hasattr(os, "uname") and "android" in os.uname().release.lower()

            if is_android:
                download_dir = "/sdcard/Download"
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir, exist_ok=True)
                nombre_archivo = f"arcoiris_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                ruta_destino = os.path.join(download_dir, nombre_archivo)
                exito, mensaje = logic.exportar_base_de_datos(ruta_destino)
                if exito:
                    self.lbl_mensaje_registro.value = f"📱 Respaldo guardado en Descargas: {nombre_archivo}"
                    self.lbl_mensaje_registro.color = ft.Colors.GREEN_700
                else:
                    self.lbl_mensaje_registro.value = mensaje
                    self.lbl_mensaje_registro.color = ft.Colors.RED_700
            else:
                from tkinter import filedialog, Tk
                root = Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                ruta_destino = filedialog.asksaveasfilename(
                    title="Guardar Respaldo de Base de Datos", defaultextension=".db",
                    initialfile="arcoiris_backup.db", filetypes=[("Base de Datos SQLite", "*.db"), ("Todos los archivos", "*.*")]
                )
                root.destroy()
                if ruta_destino:
                    exito, mensaje = logic.exportar_base_de_datos(ruta_destino)
                    self.lbl_mensaje_registro.value = mensaje
                    self.lbl_mensaje_registro.color = ft.Colors.GREEN_700 if exito else ft.Colors.RED_700
                else:
                    self.lbl_mensaje_registro.value = "ℹ️ Exportación cancelada."
                    self.lbl_mensaje_registro.color = ft.Colors.ORANGE_700
            self.page.update()

        except Exception as ex:
            self.lbl_mensaje_registro.value = f"⚠️ Error al exportar: {ex}"
            self.lbl_mensaje_registro.color = ft.Colors.RED_700
            self.page.update()

    # -------------------------------------------------------------
    # MÉTODOS AUXILIARES Y ACCIONES DE BD
    # -------------------------------------------------------------
    def cargar_opciones_rubrica(self):
        rubricas = logic.obtener_rubricas()
        options = [ft.dropdown.Option(key=str(r[0]), text=r[1]) for r in rubricas]
        self.dd_rubrica.options = options
        if options:
            self.dd_rubrica.value = options[0].key

    def actualizar_dropdown_miembros_especiales(self):
        miembros = logic.obtener_miembros_ordenados("nombre")
        options = []
        for m in miembros:
            m_id = m[0]
            nombre = m[1]
            rubrica = m[5] if len(m) > 5 else "Normal"
            options.append(ft.dropdown.Option(key=str(m_id), text=f"{nombre} ({m_id}) - [{rubrica}]"))
        return options

    def guardar_miembro_click(self, e):
        if not self.txt_nombre.value:
            self.lbl_mensaje_registro.value = "⚠ El nombre completo es obligatorio."
            self.lbl_mensaje_registro.color = ft.Colors.RED_700
            self.page.update()
            return

        if not validar_fecha(self.txt_fecha_nac.value):
            self.lbl_mensaje_registro.value = "⚠️ La fecha de nacimiento debe tener formato AAAA-MM-DD."
            self.lbl_mensaje_registro.color = ft.Colors.RED_700
            self.page.update()
            return

        rubrica_id = int(self.dd_rubrica.value) if self.dd_rubrica.value else 1
        
        es_servidor = self.dd_tipo.value == "Servidor"
        corillo_final = self.dd_corillo.value if es_servidor else "Por Asignar"
        historial_final = self.txt_historial_ordenado.value if es_servidor else ""
        edad_calculada = self.calcular_edad(self.txt_fecha_nac.value)
        encuentro_num = int(self.txt_encuentro.value) if self.txt_encuentro.value.isdigit() else 1

        nuevo_id = logic.registrar_miembro(
            nombre_completo=self.txt_nombre.value,
            fecha_nac=self.txt_fecha_nac.value,
            edad=edad_calculada,
            corillo=corillo_final,
            ocupacion=self.dd_ocupacion.value,
            grado_estudio=self.dd_grado.value,
            direccion=self.txt_direccion.value,
            telefono=self.txt_telefono.value,
            tel_emergencia=self.txt_tel_emergencia.value,
            tutor=self.txt_tutor.value,
            tel_tutor=self.txt_tel_tutor.value,
            encuentro_num=encuentro_num,
            rubrica_id=rubrica_id,
            historial_morrales=historial_final
        )

        # Auto-matricular si es Encuentrista y el Encuentro indicado ya existe en la BD
        nota_matricula = ""
        if not es_servidor and logic.existe_retiro(encuentro_num):
            logic.agregar_participante(encuentro_num, nuevo_id, "Encuentrista", "", "Por Asignar")
            nota_matricula = f" y matriculado en Encuentro #{encuentro_num}"

        self.lbl_mensaje_registro.value = f"✅ Miembro registrado: {nuevo_id}{nota_matricula}"
        self.lbl_mensaje_registro.color = ft.Colors.GREEN_700
        
        self.txt_nombre.value = ""
        self.txt_edad.value = str(self.calcular_edad(self.txt_fecha_nac.value))
        for chk in self.checks_historial:
            chk.value = False
        self.txt_historial_ordenado.value = ""
        
        self.cargar_directorio_tabla()
        self.on_data_change()
        self.page.update()

    def llenar_datos_ejemplo(self, e):
        rubricas = {nombre: r_id for r_id, nombre in logic.obtener_rubricas()}

        miembros_ejemplo = [
            ("María Guadalupe Pérez", "2007-03-12", 17, "Celeste (Santa María)", "Estudiante", "Preparatoria", "Normal"),
            ("Carlos Eduardo Gómez", "2006-11-20", 18, "Rojo (San Felipe)", "Empleado", "Preparatoria", "Tarde"),
        ]

        for nombre, fnac, edad, corillo, ocup, grado, nombre_rubrica in miembros_ejemplo:
            r_id = rubricas.get(nombre_rubrica, 1)
            logic.registrar_miembro(
                nombre_completo=nombre, fecha_nac=fnac, edad=self.calcular_edad(fnac), corillo=corillo,
                ocupacion=ocup, grado_estudio=grado, direccion="Av. Central #123",
                telefono="9611234567", tel_emergencia="9617654321", tutor="Padre/Tutor",
                tel_tutor="9610000000", encuentro_num=1, rubrica_id=r_id
            )

        self.cargar_directorio_tabla()
        self.on_data_change()
        self.lbl_mensaje_registro.value = "⚡ ¡Se cargaron datos!"
        self.lbl_mensaje_registro.color = ft.Colors.BLUE_700
        self.page.update()

    def vaciar_bd_click(self, e):
        logic.eliminar_todos_los_miembros()
        self.cargar_directorio_tabla()
        self.on_data_change()
        self.lbl_mensaje_registro.value = "🗑️ Se han eliminado todos los datos de la BD."
        self.lbl_mensaje_registro.color = ft.Colors.ORANGE_800
        self.page.update()

    def cambiar_orden(self, criterio):
        self.state.criterio_orden = criterio
        self.cargar_directorio_tabla()

    def abrir_modal_editar(self, m_id, nombre, corillo, ocupacion, grado, rubrica, historial_previo=""):
        txt_edit_historial = ft.TextField(label="Orden cronológico", value=historial_previo, read_only=True, expand=True)
        
        chk_edit_celeste = ft.Checkbox(label="Celeste")
        chk_edit_rojo = ft.Checkbox(label="Rojo")
        chk_edit_amarillo = ft.Checkbox(label="Amarillo")
        chk_edit_cafe = ft.Checkbox(label="Café")
        chk_edit_verde = ft.Checkbox(label="Verde")
        chk_edit_blanco = ft.Checkbox(label="Blanco")
        checks_edicion = [chk_edit_celeste, chk_edit_rojo, chk_edit_amarillo, chk_edit_cafe, chk_edit_verde, chk_edit_blanco]

        def chk_edit_change(e):
            color = e.control.label
            actuales = [c.strip() for c in txt_edit_historial.value.split(",") if c.strip()]
            if e.control.value:
                if color not in actuales:
                    actuales.append(color)
            else:
                if color in actuales:
                    actuales.remove(color)
            txt_edit_historial.value = ",".join(actuales)
            txt_edit_historial.update()

        for chk in checks_edicion:
            chk.on_change = chk_edit_change
            if chk.label in historial_previo:
                chk.value = True

        edit_nombre = ft.TextField(label="Nombre Completo", value=nombre, expand=True)
        edit_corillo = ft.Dropdown(
            label="Corillo Actual",
            value=corillo,
            expand=True,
            options=[
                ft.dropdown.Option("Por Asignar"),
                ft.dropdown.Option("Celeste (Santa María)"),
                ft.dropdown.Option("Rojo (San Felipe)"),
                ft.dropdown.Option("Amarillo (San Pablo)"),
                ft.dropdown.Option("Café (San Pedro)"),
                ft.dropdown.Option("Verde (San José)"),
                ft.dropdown.Option("Blanco (San Juan)"),
            ]
        )
        edit_ocupacion = ft.Dropdown(
            label="Ocupación", value=ocupacion, expand=True,
            options=[
                ft.dropdown.Option("Estudiante"), ft.dropdown.Option("Empleado"),
                ft.dropdown.Option("Desempleado"), ft.dropdown.Option("Hogar"), ft.dropdown.Option("Otro"),
            ]
        )
        edit_grado = ft.Dropdown(
            label="Grado de Estudio", value=grado, expand=True,
            options=[
                ft.dropdown.Option("Primaria"), ft.dropdown.Option("Secundaria"),
                ft.dropdown.Option("Preparatoria"), ft.dropdown.Option("Universidad / Licenciatura"),
                ft.dropdown.Option("Maestría / Postgrado"), ft.dropdown.Option("Ninguno / Otro"),
            ]
        )
        
        rubricas = logic.obtener_rubricas()
        rubrica_options = [ft.dropdown.Option(key=str(r[0]), text=r[1]) for r in rubricas]
        rubrica_id_actual = next((str(r[0]) for r in rubricas if r[1] == rubrica), "1")

        edit_rubrica = ft.Dropdown(label="Rúbrica", value=rubrica_id_actual, expand=True, options=rubrica_options)

        def guardar_cambios_click(e):
            logic.actualizar_miembro(
                m_id, edit_nombre.value, edit_corillo.value,
                edit_ocupacion.value, edit_grado.value, int(edit_rubrica.value), 
                txt_edit_historial.value
            )
            bs.open = False
            self.page.update()
            self.cargar_directorio_tabla()
            self.on_data_change()

        bs = ft.BottomSheet(
            ft.Container(
                content=ft.Column([
                    ft.Text(f"Editar Integrante: {m_id}", size=18, weight=ft.FontWeight.BOLD),
                    edit_nombre,
                    ft.ResponsiveRow([
                        ft.Container(edit_corillo, col={"xs": 12, "sm": 6}),
                        ft.Container(edit_rubrica, col={"xs": 12, "sm": 6}),
                        ft.Container(edit_ocupacion, col={"xs": 12, "sm": 6}),
                        ft.Container(edit_grado, col={"xs": 12, "sm": 6}),
                    ]),
                    ft.Text("Historial (Márcalos o desmárcalos según el orden vivido):", weight="bold", size=12),
                    ft.Row(checks_edicion, wrap=True),
                    txt_edit_historial,
                    ft.Row([
                        ft.ElevatedButton("Guardar Cambios", icon=ft.Icons.SAVE, on_click=guardar_cambios_click),
                        ft.OutlinedButton("Cancelar", on_click=lambda e: setattr(bs, "open", False) or self.page.update())
                    ], alignment=ft.MainAxisAlignment.END)
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                padding=20
            ),
            open=True
        )
        self.page.overlay.append(bs)
        self.page.update()

    def eliminar_miembro_click(self, m_id):
        logic.eliminar_miembro(m_id)
        self.cargar_directorio_tabla()
        self.on_data_change()

    def cargar_directorio_tabla(self):
        self.col_tabla_directorio.controls.clear()
        miembros = logic.obtener_miembros_ordenados(self.state.criterio_orden)
        filtro = self.txt_buscar_directorio.value.lower().strip() if self.txt_buscar_directorio.value else ""

        if filtro:
            miembros = [m for m in miembros if filtro in m[0].lower() or filtro in m[1].lower() or filtro in (m[2] or "").lower()]

        if not miembros:
            self.col_tabla_directorio.controls.append(ft.Text("Directorio vacío."))
            self.page.update()
            return

        for m in miembros:
            m_id = m[0]
            nombre = m[1]
            corillo = m[2] if len(m) > 2 else "Por Asignar"
            ocupacion = m[3] if len(m) > 3 else ""
            grado = m[4] if len(m) > 4 else ""
            rubrica = m[5] if len(m) > 5 else "Normal"
            historial = m[6] if len(m) > 6 and m[6] else "" 

            item_row = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"ID: {m_id}", weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.BLUE_700),
                        ft.Row([
                            ft.IconButton(
                                icon=ft.Icons.EDIT, icon_size=20, tooltip="Editar",
                                on_click=lambda e, mi=m_id, n=nombre, c=corillo, o=ocupacion, g=grado, r=rubrica, h=historial: self.abrir_modal_editar(mi, n, c, o, g, r, h)
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE, icon_size=20, icon_color=ft.Colors.RED_600, tooltip="Eliminar",
                                on_click=lambda e, mi=m_id: self.eliminar_miembro_click(mi)
                            )
                        ], spacing=0)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(nombre, weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(f"Corillo: {corillo if corillo else 'Sin asignación'}", size=12, color=ft.Colors.GREY_800),
                    ft.Text(f"{ocupacion} | {grado}", size=11, color=ft.Colors.GREY_600)
                ], spacing=3),
                padding=10,
                border=ft.Border(
                    top=ft.BorderSide(1, ft.Colors.GREY_300),
                    bottom=ft.BorderSide(1, ft.Colors.GREY_300),
                    left=ft.BorderSide(1, ft.Colors.GREY_300),
                    right=ft.BorderSide(1, ft.Colors.GREY_300)
                ),
                border_radius=8
            )
            self.col_tabla_directorio.controls.append(item_row)
        self.page.update()

    # -------------------------------------------------------------
    # NUEVAS FUNCIONES DE ENCUENTROS Y EXPORTACIÓN
    # -------------------------------------------------------------
    def exportar_directorio_click(self, e):
        exito, msj = logic.exportar_directorio_general()
        self.lbl_mensaje_registro.value = msj
        self.lbl_mensaje_registro.color = ft.Colors.GREEN_700 if exito else ft.Colors.RED_700
        self.page.update()

    def abrir_gestion_encuentros(self, e):
        try:
            txt_num_encuentro = ft.TextField(label="Número de Encuentro", width=150)
            txt_desc_encuentro = ft.TextField(label="Descripción", expand=True)
            dd_seleccionar_retiro = ft.Dropdown(label="Selecciona el Encuentro", expand=True)

            txt_filtro_servidor = ft.TextField(
                label="Filtrar servidor por nombre o ID",
                prefix_icon=ft.Icons.SEARCH,
                height=42,
                text_size=12
            )
            dd_servidor = ft.Dropdown(label="Seleccionar Servidor", options=[], expand=True)
            txt_rol_servidor = ft.TextField(label="Rol (Ej. Cocina)", width=180)

            txt_filtro_encuentrista = ft.TextField(
                label="Filtrar encuentrista nuevo por nombre o ID",
                prefix_icon=ft.Icons.SEARCH,
                height=42,
                text_size=12
            )
            dd_encuentrista = ft.Dropdown(label="Seleccionar Encuentrista (Últimos agregados arriba)", options=[], expand=True)

            def refrescar_listas_candidatos(e=None):
                if not dd_seleccionar_retiro.value:
                    return
                retiro_id = int(dd_seleccionar_retiro.value)

                # 1. Candidatos a Servidor (excluye los ya matriculados en este encuentro)
                serv_disp = logic.obtener_candidatos_retiro(retiro_id, "Servidor")
                q_serv = (txt_filtro_servidor.value or "").lower().strip()
                if q_serv:
                    serv_disp = [s for s in serv_disp if q_serv in s[1].lower() or q_serv in s[0].lower()]
                dd_servidor.options = [ft.dropdown.Option(key=s[0], text=f"{s[1]} ({s[0]})") for s in serv_disp]
                dd_servidor.value = dd_servidor.options[0].key if dd_servidor.options else None

                # 2. Candidatos a Encuentrista (solo nuevos 'Por Asignar', ordenados del último ID al primero)
                enc_disp = logic.obtener_candidatos_retiro(retiro_id, "Encuentrista")
                q_enc = (txt_filtro_encuentrista.value or "").lower().strip()
                if q_enc:
                    enc_disp = [x for x in enc_disp if q_enc in x[1].lower() or q_enc in x[0].lower()]
                dd_encuentrista.options = [ft.dropdown.Option(key=x[0], text=f"{x[0]} - {x[1]}") for x in enc_disp]
                dd_encuentrista.value = dd_encuentrista.options[0].key if dd_encuentrista.options else None

                self.page.update()

            def refrescar_dropdown_retiros():
                opciones_retiros = logic.obtener_retiros()
                if opciones_retiros:
                    dd_seleccionar_retiro.options = [ft.dropdown.Option(key=str(r[0]), text=f"Encuentro #{r[0]} | {r[1]}") for r in opciones_retiros]
                    dd_seleccionar_retiro.value = dd_seleccionar_retiro.options[0].key
                    refrescar_listas_candidatos()
                self.page.update()

            dd_seleccionar_retiro.on_change = refrescar_listas_candidatos
            txt_filtro_servidor.on_change = refrescar_listas_candidatos
            txt_filtro_encuentrista.on_change = refrescar_listas_candidatos

            def btn_crear_retiro_click(e):
                if txt_num_encuentro.value.isdigit():
                    exito, msj = logic.crear_retiro(int(txt_num_encuentro.value), txt_desc_encuentro.value)
                    mostrar_snackbar(self.page, msj)
                    txt_num_encuentro.value = ""
                    txt_desc_encuentro.value = ""
                    refrescar_dropdown_retiros()
                else:
                    mostrar_snackbar(self.page, "El número debe ser entero.")

            def btn_add_servidor(e):
                if dd_seleccionar_retiro.value and dd_servidor.value:
                    logic.agregar_participante(int(dd_seleccionar_retiro.value), dd_servidor.value, "Servidor", txt_rol_servidor.value)
                    mostrar_snackbar(self.page, "Servidor agregado.")
                    txt_rol_servidor.value = ""
                    refrescar_listas_candidatos()
            
            def btn_add_encuentrista(e):
                if dd_seleccionar_retiro.value and dd_encuentrista.value:
                    logic.agregar_participante(int(dd_seleccionar_retiro.value), dd_encuentrista.value, "Encuentrista", "", "Por Asignar")
                    mostrar_snackbar(self.page, "Encuentrista matriculado.")
                    refrescar_listas_candidatos()

            def btn_matricular_masivo(e):
                if dd_seleccionar_retiro.value:
                    exito, msj = logic.matricular_todos_los_nuevos(int(dd_seleccionar_retiro.value))
                    mostrar_snackbar(self.page, msj)
                    refrescar_listas_candidatos()

            def btn_distribuir_encuentristas(e):
                if dd_seleccionar_retiro.value:
                    retiro_id = int(dd_seleccionar_retiro.value)
                    exito, msj = logic.distribuir_corillos_automaticamente(retiro_id)
                    mostrar_snackbar(self.page, msj)
                    cargar_lista_edicion()
                    refrescar_listas_candidatos()
                    if hasattr(self, 'cargar_directorio_tabla'):
                        self.cargar_directorio_tabla()

            def btn_distribuir_todos(e):
                if dd_seleccionar_retiro.value:
                    retiro_id = int(dd_seleccionar_retiro.value)
                    logic.distribuir_corillos_automaticamente(retiro_id)
                    logic.asignar_colores_servidores_por_historial(retiro_id)
                    mostrar_snackbar(self.page, "¡Colores distribuidos a Servidores y Encuentristas!")
                    cargar_lista_edicion()
                    refrescar_listas_candidatos()
                    if hasattr(self, 'cargar_directorio_tabla'):
                        self.cargar_directorio_tabla()

            def btn_exportar_listas(e):
                if dd_seleccionar_retiro.value:
                    exito, msj = logic.exportar_listas_encuentro(int(dd_seleccionar_retiro.value))
                    mostrar_snackbar(self.page, msj)

            vista_crear = ft.Container(padding=15, content=ft.Column([
                ft.Text("Registrar un nuevo Encuentro en el sistema:", weight="bold"),
                ft.Row([txt_num_encuentro, txt_desc_encuentro]),
                ft.FilledButton("Crear Encuentro", on_click=btn_crear_retiro_click)
            ], spacing=15))

            vista_matricular = ft.Container(padding=15, content=ft.Column([
                dd_seleccionar_retiro, ft.Divider(),
                ft.Text("A) Registrar Servidores:", weight="bold"),
                txt_filtro_servidor,
                ft.Row([dd_servidor, txt_rol_servidor, ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=btn_add_servidor, icon_color="green")]),
                ft.Divider(),
                ft.Row([
                    ft.Text("B) Registrar Encuentristas Nuevos:", weight="bold", expand=True),
                    ft.ElevatedButton("⚡ Matricular todos los nuevos", on_click=btn_matricular_masivo, bgcolor=ft.Colors.BLUE_50)
                ]),
                txt_filtro_encuentrista,
                ft.Row([dd_encuentrista, ft.IconButton(ft.Icons.ADD_CIRCLE, on_click=btn_add_encuentrista, icon_color="blue")]),
            ], spacing=8, scroll=ft.ScrollMode.AUTO))

            lista_edicion = ft.Column(spacing=5, scroll=ft.ScrollMode.AUTO, expand=True)
            
            def cambiar_color_manual(e, miembro_id):
                if dd_seleccionar_retiro.value:
                    nuevo_color = e.control.value
                    logic.actualizar_corillo_individual(int(dd_seleccionar_retiro.value), miembro_id, nuevo_color)
                    cargar_lista_edicion()
                    mostrar_snackbar(self.page, f"Color actualizado a {nuevo_color}")

            def quitar_participante_click(e, miembro_id, nombre_m):
                if dd_seleccionar_retiro.value:
                    exito, msj = logic.eliminar_participante_retiro(int(dd_seleccionar_retiro.value), miembro_id)
                    if exito:
                        cargar_lista_edicion()
                        refrescar_listas_candidatos()
                        mostrar_snackbar(self.page, f"🗑️ {nombre_m} quitado del encuentro.")
                    else:
                        mostrar_snackbar(self.page, msj)

            def cargar_lista_edicion():
                lista_edicion.controls.clear()
                if dd_seleccionar_retiro.value:
                    participantes = logic.obtener_todos_participantes_edicion(int(dd_seleccionar_retiro.value))
                    colores_ops = [ft.dropdown.Option(c) for c in ["Celeste", "Rojo", "Amarillo", "Café", "Verde", "Blanco", "Por Asignar"]]
                    
                    conteo_colores = {"Celeste": 0, "Rojo": 0, "Amarillo": 0, "Café": 0, "Verde": 0, "Blanco": 0}
                    for p in participantes:
                        if p[2] == "Encuentrista" and p[3] in conteo_colores:
                            conteo_colores[p[3]] += 1
                    
                    resumen_texto = " | ".join([f"{c}: {tot}" for c, tot in conteo_colores.items() if tot > 0])
                    
                    lista_edicion.controls.append(
                        ft.Container(
                            content=ft.Text(f"📊 Totales Encuentristas: {resumen_texto if resumen_texto else 'Sin encuentristas'}", weight="bold", color="green_800"),
                            bgcolor=ft.Colors.GREEN_50, padding=10, border_radius=5, margin=5
                        )
                    )
                    
                    for p in participantes:
                        icono = ft.Icons.STAR if p[2] == "Servidor" else ft.Icons.PERSON
                        color_dd = ft.Dropdown(value=p[3], options=colores_ops, width=135, height=40, text_size=12)
                        color_dd.on_change = lambda e, m_id=p[0]: cambiar_color_manual(e, m_id)
                        
                        btn_quitar = ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.RED_600,
                            icon_size=20,
                            tooltip="Quitar de este encuentro",
                            on_click=lambda e, m_id=p[0], nom=p[1]: quitar_participante_click(e, m_id, nom)
                        )
                        
                        lista_edicion.controls.append(
                            ft.Row([
                                ft.Icon(icono, size=16, color="blue"),
                                ft.Text(f"{p[1]} ({p[2]})", expand=True, size=12),
                                color_dd,
                                btn_quitar
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                        )
                self.page.update()

            vista_magia = ft.Container(padding=15, content=ft.Column([
                ft.Text("Opciones Mágicas:", weight="bold", color="blue"),
                ft.Row([
                    ft.ElevatedButton(
                        "🎒 Solo Encuentristas (Familias)", 
                        on_click=btn_distribuir_encuentristas, 
                        bgcolor=ft.Colors.BLUE_100,
                        expand=True
                    ),
                    ft.ElevatedButton(
                        "🎨 Todos (Servidores + Encuentristas)", 
                        on_click=btn_distribuir_todos, 
                        bgcolor=ft.Colors.PURPLE_100,
                        expand=True
                    ),
                ], spacing=10),
                ft.Divider(),
                ft.Text("Revisión Manual (Cambia colores o elimina errores):", weight="bold"),
                ft.Container(content=lista_edicion, height=220, bgcolor=ft.Colors.GREY_100, padding=10, border_radius=5),
                ft.Divider(),
                ft.ElevatedButton("📄 Exportar Lista Definitiva", icon=ft.Icons.DOWNLOAD, on_click=btn_exportar_listas, bgcolor=ft.Colors.GREEN_100)
            ], spacing=10))

            contenedor_vistas = ft.Container(content=vista_crear, expand=True)

            def cambiar_pestana(e):
                btn_tab1.icon = None
                btn_tab2.icon = None
                btn_tab3.icon = None
                e.control.icon = ft.Icons.CHECK_CIRCLE
                if e.control.data == 1:
                    contenedor_vistas.content = vista_crear
                elif e.control.data == 2:
                    refrescar_listas_candidatos()
                    contenedor_vistas.content = vista_matricular
                elif e.control.data == 3:
                    cargar_lista_edicion()
                    contenedor_vistas.content = vista_magia
                self.page.update()

            btn_tab1 = ft.TextButton("1. Crear", data=1, on_click=cambiar_pestana, icon=ft.Icons.CHECK_CIRCLE)
            btn_tab2 = ft.TextButton("2. Matricular", data=2, on_click=cambiar_pestana)
            btn_tab3 = ft.TextButton("3. Previsualizar", data=3, on_click=cambiar_pestana)

            estructura_modal = ft.Column([
                ft.Row([btn_tab1, btn_tab2, btn_tab3], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(height=1),
                contenedor_vistas
            ], expand=True)

            dlg = ft.AlertDialog(
                title=ft.Text("⛺ Gestión de Encuentros"),
                content=ft.Container(width=650, height=580, content=estructura_modal),
                actions=[ft.TextButton("Cerrar", on_click=lambda e: setattr(dlg, "open", False) or self.page.update())]
            )

            refrescar_dropdown_retiros()
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()

        except Exception as ex:
            print(f"ERROR: {ex}")