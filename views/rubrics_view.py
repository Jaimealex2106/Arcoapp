import flet as ft
import logic

import flet as ft

# Asignar un alias para mantener compatibilidad si Flet en Android no incluye ElevatedButton
if not hasattr(ft, "ElevatedButton"):
    ft.ElevatedButton = ft.FilledButton
    
class RubricsView:
    def __init__(self, page: ft.Page, get_miembros_especiales, on_data_change):
        self.page = page
        self.get_miembros_especiales = get_miembros_especiales
        self.on_data_change = on_data_change

        self.col_rubricas_generales = ft.Column(scroll=ft.ScrollMode.AUTO)

        self.dd_miembros_especiales = ft.Dropdown(
            label="Seleccionar Integrante para Caso Especial", 
            expand=True
        )
        self.lbl_msg_rubrica = ft.Text("", weight=ft.FontWeight.BOLD)

        # Contenedor dinámico para los campos de porcentajes por actividad
        self.row_inputs_dinamicos = ft.Row(wrap=True, spacing=10)
        self.dic_entradas_actividades = {}  # {tipo_id: TextField}

        self.dd_miembros_especiales.on_change = self.al_seleccionar_miembro_especial

        # Inicializar los campos dinámicos
        self.generar_campos_dinamicos_actividades()

        self.view = ft.Column(
            controls=[
                ft.Text("Gestión de Rúbricas y Casos Especiales", size=20, weight=ft.FontWeight.BOLD),
                self.lbl_msg_rubrica,
                ft.Text("1. Editar Porcentajes de Rúbricas Estándar", size=16, weight=ft.FontWeight.BOLD),
                ft.FilledButton(
                    "➕ Agregar Nueva Rúbrica Base", 
                    icon=ft.Icons.ADD, 
                    on_click=self.abrir_modal_nueva_rubrica
                ),
                self.col_rubricas_generales,
                ft.Divider(),
                ft.Text("2. Configurar Rúbrica Personalizada (Caso Especial Único)", size=16, weight=ft.FontWeight.BOLD),
                self.dd_miembros_especiales,
                self.row_inputs_dinamicos,
                ft.FilledButton(
                    "⭐ Guardar Rúbrica Especial Individual", 
                    icon=ft.Icons.STAR, 
                    on_click=self.guardar_caso_especial_click
                )
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=15,
            expand=True
        )

    def generar_campos_dinamicos_actividades(self, valores_previos=None):
        """Genera dinámicamente un TextField para cada tipo de actividad existente en la BD."""
        if valores_previos is None:
            valores_previos = {}

        self.row_inputs_dinamicos.controls.clear()
        self.dic_entradas_actividades.clear()

        tipos_actividades = logic.obtener_tipos_actividades()

        for item in tipos_actividades:
            if isinstance(item, (tuple, list)):
                t_id, nombre = item[0], item[1]
            else:
                t_id, nombre = item, str(item)

            val_defecto = str(valores_previos.get(t_id, 0.0))
            
            txt_campo = ft.TextField(
                label=f"{nombre} (%)",
                value=val_defecto,
                width=140,
                text_align=ft.TextAlign.RIGHT
            )

            self.dic_entradas_actividades[t_id] = txt_campo
            self.row_inputs_dinamicos.controls.append(txt_campo)

        if self.page:
            self.page.update()

    def cargar_tabla_rubricas_generales(self):
        self.col_rubricas_generales.controls.clear()
        rubricas = logic.obtener_todas_las_rubricas()

        for r_id, nombre in rubricas:
            actividades = logic.obtener_actividades_rubrica(r_id)
            
            if actividades:
                resumen_actividades = ", ".join([f"{nombre_act}: {porc}%" for _, _, nombre_act, porc in actividades])
            else:
                resumen_actividades = "Sin actividades configuradas"

            def personalizar_actividades(e, rid=r_id, nom=nombre):
                self.abrir_modal_personalizar_actividades(rid, nom)

            def editar_nombre_rubrica(e, rid=r_id, nom=nombre):
                self.abrir_modal_editar_nombre(rid, nom)

            def eliminar_rubrica_click(e, rid=r_id, nom=nombre):
                if logic.eliminar_rubrica(rid):
                    self.lbl_msg_rubrica.value = f"✅ Rúbrica '{nom}' eliminada correctamente."
                    self.lbl_msg_rubrica.color = ft.Colors.GREEN_700
                    self.cargar_tabla_rubricas_generales()
                else:
                    self.lbl_msg_rubrica.value = f"⚠️ No se puede eliminar '{nom}' porque está en uso."
                    self.lbl_msg_rubrica.color = ft.Colors.RED_700
                self.page.update()

            row = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"🔹 {nombre}", weight=ft.FontWeight.BOLD, size=15, expand=True),
                        ft.OutlinedButton("⚙️ Personalizar", icon=ft.Icons.SETTINGS, width=150, on_click=personalizar_actividades),
                        ft.OutlinedButton("✏️ Renombrar", icon=ft.Icons.EDIT, width=120, on_click=editar_nombre_rubrica),
                        ft.FilledButton("🗑️ Eliminar", icon=ft.Icons.DELETE, width=110, bgcolor=ft.Colors.RED_400, color=ft.Colors.WHITE, on_click=eliminar_rubrica_click)
                    ]),
                    ft.Text(f"Actividades: {resumen_actividades}", size=12, italic=True, color=ft.Colors.GREY_700)
                ]),
                padding=10,
                border=ft.Border.all(1, ft.Colors.GREY_300),
                border_radius=8
            )
            self.col_rubricas_generales.controls.append(row)
        
        # También actualiza los inputs dinámicos por si se crearon nuevas actividades
        self.generar_campos_dinamicos_actividades()

    def guardar_caso_especial_click(self, e):
        m_id = self.dd_miembros_especiales.value
        if not m_id:
            self.lbl_msg_rubrica.value = "⚠️ Selecciona un integrante para aplicar la rúbrica especial."
            self.lbl_msg_rubrica.color = ft.Colors.RED_700
            self.page.update()
            return

        opcion_sel = next((op for op in self.dd_miembros_especiales.options if op.key == m_id), None)
        nombre_m = opcion_sel.text.split(" (")[0] if opcion_sel else "Miembro"

        actividades_config = []
        suma_total = 0.0

        try:
            for t_id, txt_input in self.dic_entradas_actividades.items():
                val = float(txt_input.value or 0.0)
                if val < 0:
                    self.lbl_msg_rubrica.value = "⚠️ Los porcentajes no pueden ser negativos."
                    self.lbl_msg_rubrica.color = ft.Colors.RED_700
                    self.page.update()
                    return
                if val > 0:
                    actividades_config.append((t_id, val))
                suma_total += val

            if abs(suma_total - 100.0) > 0.01:
                self.lbl_msg_rubrica.value = f"⚠️ La suma de la rúbrica especial para {nombre_m} debe dar 100%. (Suma actual: {suma_total:.1f}%)"
                self.lbl_msg_rubrica.color = ft.Colors.RED_700
                self.page.update()
                return

            # Guardar/actualizar caso especial en la BD con estructura dinámica
            if hasattr(logic, "guardar_rubrica_especial_dinamica"):
                logic.guardar_rubrica_especial_dinamica(m_id, actividades_config)
            else:
                # Compatibilidad en caso de que tu logic use la función de asociar rúbrica o crearla
                logic.crear_o_actualizar_rubrica_especial_miembro(m_id, nombre_m, actividades_config)

            self.lbl_msg_rubrica.value = f"⭐ Rúbrica especial de '{nombre_m}' actualizada correctamente."
            self.lbl_msg_rubrica.color = ft.Colors.BLUE_800
            self.cargar_tabla_rubricas_generales()
            self.actualizar_dropdown_miembros_especiales()
            if callable(self.on_data_change):
                self.on_data_change()
            self.page.update()
        except ValueError:
            self.lbl_msg_rubrica.value = "⚠️ Revisa los números de los porcentajes."
            self.lbl_msg_rubrica.color = ft.Colors.RED_700
            self.page.update()

    def actualizar_dropdown_miembros_especiales(self):
        if callable(self.get_miembros_especiales):
            self.dd_miembros_especiales.options = self.get_miembros_especiales()
        if self.page:
            self.page.update()

    def al_seleccionar_miembro_especial(self, e):
        m_id = self.dd_miembros_especiales.value
        if not m_id:
            return
        
        # Obtener actividades configuradas previamente para el miembro
        actividades_miembro = logic.obtener_actividades_de_miembro(m_id) if hasattr(logic, "obtener_actividades_de_miembro") else {}
        
        # Cargar los valores existentes en las cajas dinámicas
        valores = {}
        if isinstance(actividades_miembro, dict):
            valores = actividades_miembro
        elif isinstance(actividades_miembro, list):
            for item in actividades_miembro:
                # tuple (tipo_id, porc)
                valores[item[0]] = item[1]

        self.generar_campos_dinamicos_actividades(valores_previos=valores)

    def abrir_modal_nueva_rubrica(self, e):
        txt_nombre = ft.TextField(label="Nombre de la Rúbrica *", expand=True)
        lbl_error = ft.Text("", color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD)

        def cerrar_dialogo(e=None):
            if hasattr(self.page, "close"):
                self.page.close(dlg)
            else:
                dlg.open = False
                self.page.update()

        def guardar_nueva_rubrica(e):
            if not txt_nombre.value.strip():
                lbl_error.value = "⚠️ El nombre de la rúbrica es obligatorio."
                self.page.update()
                return

            logic.crear_rubrica_base(txt_nombre.value.strip())
            cerrar_dialogo()
            self.cargar_tabla_rubricas_generales()
            self.lbl_msg_rubrica.value = f"✅ Rúbrica '{txt_nombre.value}' creada correctamente. Usa '⚙️ Personalizar' para asignarle porcentajes."
            self.lbl_msg_rubrica.color = ft.Colors.GREEN_700
            if callable(self.on_data_change):
                self.on_data_change()
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Crear Nueva Rúbrica Base", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                txt_nombre,
                lbl_error
            ], spacing=8, height=120),
            actions=[
                ft.TextButton("Cancelar", on_click=cerrar_dialogo),
                ft.TextButton("Crear", on_click=guardar_nueva_rubrica)
            ]
        )
        
        if hasattr(self.page, "open"):
            self.page.open(dlg)
        else:
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()

    def abrir_modal_editar_nombre(self, r_id, nombre_actual):
        txt_nuevo_nombre = ft.TextField(label="Nuevo Nombre de la Rúbrica", value=nombre_actual, expand=True)
        lbl_error = ft.Text("", color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD)

        def cerrar_dialogo(e=None):
            if hasattr(self.page, "close"):
                self.page.close(dlg)
            else:
                dlg.open = False
                self.page.update()

        def guardar_nombre(e):
            if not txt_nuevo_nombre.value.strip():
                lbl_error.value = "⚠️ El nombre no puede estar vacío."
                self.page.update()
                return

            logic.renombrar_rubrica(r_id, txt_nuevo_nombre.value)
            cerrar_dialogo()
            self.cargar_tabla_rubricas_generales()
            self.lbl_msg_rubrica.value = f"✅ Rúbrica renombrada a '{txt_nuevo_nombre.value}' correctamente."
            self.lbl_msg_rubrica.color = ft.Colors.GREEN_700
            self.page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Renombrar Rúbrica", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                txt_nuevo_nombre,
                lbl_error
            ], spacing=10),
            actions=[
                ft.TextButton("Cancelar", on_click=cerrar_dialogo),
                ft.TextButton("Guardar", on_click=guardar_nombre)
            ]
        )
        
        if hasattr(self.page, "open"):
            self.page.open(dlg)
        else:
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()

    def abrir_modal_personalizar_actividades(self, r_id, nombre_rubrica):
        tipos_actividades = logic.obtener_tipos_actividades()
        actividades_actuales = logic.obtener_actividades_rubrica(r_id)
        
        act_actuales_dict = {tipo_id: (porc, ra_id) for ra_id, tipo_id, _, porc in actividades_actuales}
        
        campos_porcentaje = {}
        filas_actividades = []
        
        for item in tipos_actividades:
            if isinstance(item, (tuple, list)):
                tipo_id, nombre_act = item[0], item[1]
            else:
                tipo_id, nombre_act = item, str(item)

            esta_seleccionada = tipo_id in act_actuales_dict
            porc_actual = act_actuales_dict[tipo_id][0] if esta_seleccionada else 0.0
            
            chk = ft.Checkbox(value=esta_seleccionada)
            txt_porc = ft.TextField(
                value=str(porc_actual) if esta_seleccionada else "0.0",
                width=70,
                text_align=ft.TextAlign.CENTER,
                disabled=not esta_seleccionada
            )
            
            campos_porcentaje[tipo_id] = (chk, txt_porc)
            
            def make_on_check_change(tid):
                def on_check_change(e):
                    chk_w, txt_w = campos_porcentaje[tid]
                    txt_w.disabled = not chk_w.value
                    if chk_w.value and txt_w.value == "0.0":
                        txt_w.value = "10.0"
                    self.page.update()
                return on_check_change
            
            chk.on_change = make_on_check_change(tipo_id)
            
            fila = ft.Row([
                ft.Container(
                    content=ft.Row([chk, ft.Text(nombre_act, size=13)], spacing=5),
                    width=180
                ),
                ft.Container(content=txt_porc, width=80),
                ft.Text("%", width=20)
            ], spacing=5, height=40)
            
            filas_actividades.append(fila)
        
        txt_nueva_actividad = ft.TextField(
            label="Crear nueva actividad",
            hint_text="Ej: Oración, Estudio",
            expand=True
        )
        lbl_error = ft.Text("", color=ft.Colors.RED_700, weight=ft.FontWeight.BOLD)

        def cerrar_dialogo(e=None):
            if hasattr(self.page, "close"):
                self.page.close(dlg)
            else:
                dlg.open = False
                self.page.update()
        
        def guardar_personalizacion(e):
            actividades_config = []
            for tipo_id, (chk_w, txt_w) in campos_porcentaje.items():
                if chk_w.value:
                    try:
                        porc = float(txt_w.value)
                        if porc < 0:
                            lbl_error.value = "⚠️ Los porcentajes no pueden ser negativos."
                            self.page.update()
                            return
                        actividades_config.append((tipo_id, porc))
                    except ValueError:
                        lbl_error.value = "⚠️ Ingresa números válidos."
                        self.page.update()
                        return
            
            if not actividades_config:
                lbl_error.value = "⚠️ Selecciona al menos una actividad."
                self.page.update()
                return
            
            suma = sum(p for _, p in actividades_config)
            if abs(suma - 100.0) > 0.01:
                lbl_error.value = f"⚠️ Los porcentajes deben sumar 100% (suma actual: {suma:.1f}%)"
                self.page.update()
                return
            
            exito, mensaje = logic.actualizar_actividades_rubrica(r_id, actividades_config)
            if exito:
                cerrar_dialogo()
                self.cargar_tabla_rubricas_generales()
                self.lbl_msg_rubrica.value = f"✅ Actividades de '{nombre_rubrica}' actualizadas."
                self.lbl_msg_rubrica.color = ft.Colors.GREEN_700
                if callable(self.on_data_change):
                    self.on_data_change()
                self.page.update()
            else:
                lbl_error.value = mensaje
                self.page.update()
        
        def crear_nueva_actividad(e):
            if not txt_nueva_actividad.value.strip():
                lbl_error.value = "⚠️ Ingresa un nombre para la nueva actividad."
                self.page.update()
                return
            
            nuevo_id = logic.crear_tipo_actividad(txt_nueva_actividad.value.strip())
            if nuevo_id:
                if callable(self.on_data_change):
                    self.on_data_change()
                
                cerrar_dialogo()
                self.abrir_modal_personalizar_actividades(r_id, nombre_rubrica)
            else:
                lbl_error.value = f"⚠️ '{txt_nueva_actividad.value}' ya existe."
                self.page.update()
        
        col_actividades = ft.Column(filas_actividades, scroll=ft.ScrollMode.AUTO, spacing=5, height=300)
        
        dlg = ft.AlertDialog(
            title=ft.Text(f"⚙️ Personalizar: {nombre_rubrica}", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                ft.Text("Porcentajes deben sumar 100%", size=11, italic=True, color=ft.Colors.GREY_700),
                ft.Divider(height=5),
                ft.Row([
                    ft.Text("Actividad", size=12, width=180, weight=ft.FontWeight.BOLD),
                    ft.Text("Porcentaje", size=12, width=80, weight=ft.FontWeight.BOLD)
                ], spacing=5, height=30),
                col_actividades,
                ft.Divider(height=5),
                ft.Row([txt_nueva_actividad, ft.FilledButton("Agregar", on_click=crear_nueva_actividad, width=90)]),
                lbl_error,
            ], spacing=8, height=450, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Cancelar", on_click=cerrar_dialogo),
                ft.TextButton("💾 Guardar", on_click=guardar_personalizacion)
            ]
        )
        
        if hasattr(self.page, "open"):
            self.page.open(dlg)
        else:
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()