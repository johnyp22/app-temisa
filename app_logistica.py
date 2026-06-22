import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Planeador Logístico", page_icon="🚚", layout="wide")

ZONAS = ["Guadalajara", "Zapopan", "Tlaquepaque", "Tonalá", "El Salto", "Tlajomulco", "Otro"]

PRIORIDADES = {
    1: "Crítica",
    2: "Alta",
    3: "Normal",
    4: "Baja",
    5: "Muy baja"
}

TIEMPOS_PLANTA = {
    "Guadalajara": 40,
    "Zapopan": 70,
    "Tlaquepaque": 30,
    "Tonalá": 45,
    "El Salto": 55,
    "Tlajomulco": 60,
    "Otro": 75
}

TIEMPOS_ZONA = {
    ("Guadalajara", "Zapopan"): 45,
    ("Guadalajara", "Tlaquepaque"): 35,
    ("Guadalajara", "Tonalá"): 45,
    ("Guadalajara", "El Salto"): 60,
    ("Guadalajara", "Tlajomulco"): 65,

    ("Zapopan", "Guadalajara"): 45,
    ("Zapopan", "Tlaquepaque"): 75,
    ("Zapopan", "Tonalá"): 80,
    ("Zapopan", "El Salto"): 90,
    ("Zapopan", "Tlajomulco"): 80,

    ("Tlaquepaque", "Guadalajara"): 35,
    ("Tlaquepaque", "Zapopan"): 75,
    ("Tlaquepaque", "Tonalá"): 35,
    ("Tlaquepaque", "El Salto"): 50,
    ("Tlaquepaque", "Tlajomulco"): 45,

    ("Tonalá", "Guadalajara"): 45,
    ("Tonalá", "Zapopan"): 80,
    ("Tonalá", "Tlaquepaque"): 35,
    ("Tonalá", "El Salto"): 45,
    ("Tonalá", "Tlajomulco"): 70,

    ("El Salto", "Guadalajara"): 60,
    ("El Salto", "Zapopan"): 90,
    ("El Salto", "Tlaquepaque"): 50,
    ("El Salto", "Tonalá"): 45,
    ("El Salto", "Tlajomulco"): 55,

    ("Tlajomulco", "Guadalajara"): 65,
    ("Tlajomulco", "Zapopan"): 80,
    ("Tlajomulco", "Tlaquepaque"): 45,
    ("Tlajomulco", "Tonalá"): 70,
    ("Tlajomulco", "El Salto"): 55,
}


def init_state():
    if "clientes" not in st.session_state:
        st.session_state.clientes = pd.DataFrame([
            ["Cliente Zapopan", "Zapopan", "Av. Aviación 5051, Zapopan", "45136", 30, 30, "13:00", 3, True],
            ["Cliente El Salto", "El Salto", "Parque Industrial El Salto", "45680", 45, 60, "14:00", 2, True],
            ["Cliente Tonalá", "Tonalá", "Av. Tonaltecas, Tonalá", "45400", 35, 40, "15:00", 3, True],
            ["Cliente Guadalajara", "Guadalajara", "Zona Industrial Guadalajara", "44940", 25, 25, "12:30", 1, True],
            ["Cliente Tlaquepaque", "Tlaquepaque", "Álamo Industrial", "45593", 30, 30, "16:00", 4, True],
        ], columns=[
            "Cliente",
            "Zona",
            "Dirección",
            "CP",
            "Descarga min default",
            "Carga min default",
            "Ventana fin default",
            "Prioridad cliente default",
            "Activo"
        ])

    if "transportistas" not in st.session_state:
        st.session_state.transportistas = pd.DataFrame([
            ["Proveedor A", "Rabón 8 t", 8.0, 35.0, "08:30", True],
            ["Proveedor B", "Torton 14 t", 14.0, 32.0, "08:30", True],
            ["Proveedor C", "Tráiler 25 t", 25.0, 28.0, "08:30", True],
        ], columns=[
            "Transportista",
            "Vehículo",
            "Capacidad t",
            "Costo estimado km",
            "Hora disponible",
            "Activo"
        ])

    if "programacion" not in st.session_state:
        st.session_state.programacion = pd.DataFrame(columns=[
            "Cliente",
            "Zona",
            "Dirección",
            "CP",
            "Toneladas",
            "Ventana fin",
            "Carga min",
            "Descarga min",
            "Prioridad",
            "Entrega obligatoria hoy"
        ])

    if "restricciones" not in st.session_state:
        st.session_state.restricciones = pd.DataFrame([
            ["Cliente Zapopan", "Proveedor C", "No cabe tráiler por la zona", True],
            ["Cliente Tonalá", "Proveedor A", "Chofer no disponible / restricción operativa", False],
        ], columns=[
            "Cliente",
            "Transportista bloqueado",
            "Motivo",
            "Activa"
        ])


def h(hora):
    return datetime.strptime(str(hora), "%H:%M")


def traslado(origen, destino):
    if origen == "PLANTA":
        return TIEMPOS_PLANTA.get(destino, 75)

    if origen == destino:
        return 20

    return TIEMPOS_ZONA.get((origen, destino), 75)


def transportista_permitido(cliente, transportista, restricciones):
    if restricciones.empty:
        return True

    bloqueos = restricciones[
        (restricciones["Cliente"] == cliente)
        & (restricciones["Transportista bloqueado"] == transportista)
        & (restricciones["Activa"] == True)
    ]

    return bloqueos.empty


def preparar_programacion(programacion):
    df = programacion.copy()

    df["Prioridad"] = pd.to_numeric(df["Prioridad"], errors="coerce").fillna(3).astype(int)
    df["Prioridad"] = df["Prioridad"].clip(1, 5)

    df["Prioridad texto"] = df["Prioridad"].map(PRIORIDADES)

    df["Obligatoria orden"] = df["Entrega obligatoria hoy"].apply(
        lambda x: 0 if x is True else 1
    )

    df["Ventana orden"] = df["Ventana fin"].apply(lambda x: h(x))

    df = df.sort_values(
        by=["Obligatoria orden", "Prioridad", "Ventana orden"],
        ascending=[True, True, True]
    )

    return df


def calcular_ruta(entregas, unidad):
    carga_total_min = int(entregas["Carga min"].sum())

    hora_disponible = h(unidad["Hora disponible"])
    hora_salida_real = hora_disponible + timedelta(minutes=carga_total_min)

    hora_actual = hora_salida_real
    zona_actual = "PLANTA"

    detalle = []
    cumple_ruta = True

    entregas = preparar_programacion(entregas)

    for _, e in entregas.iterrows():
        min_traslado = traslado(zona_actual, e["Zona"])
        llegada = hora_actual + timedelta(minutes=min_traslado)
        limite = h(e["Ventana fin"])

        cumple = llegada <= limite

        if not cumple:
            cumple_ruta = False

        salida_cliente = llegada + timedelta(minutes=int(e["Descarga min"]))

        detalle.append({
            "Cliente": e["Cliente"],
            "Zona": e["Zona"],
            "Toneladas": e["Toneladas"],
            "Prioridad": e["Prioridad"],
            "Prioridad texto": PRIORIDADES.get(int(e["Prioridad"]), "Normal"),
            "Entrega obligatoria hoy": e["Entrega obligatoria hoy"],
            "Carga min": e["Carga min"],
            "Traslado min": min_traslado,
            "Llegada estimada": llegada.strftime("%H:%M"),
            "Ventana fin": e["Ventana fin"],
            "Descarga min": e["Descarga min"],
            "Salida cliente": salida_cliente.strftime("%H:%M"),
            "Cumple": "Sí" if cumple else "No"
        })

        hora_actual = salida_cliente
        zona_actual = e["Zona"]

    regreso_planta = traslado(zona_actual, "Tlaquepaque")
    hora_regreso = hora_actual + timedelta(minutes=regreso_planta)

    return detalle, cumple_ruta, hora_salida_real.strftime("%H:%M"), carga_total_min, hora_regreso.strftime("%H:%M")


def planear(programacion, unidades, restricciones):
    pendientes = preparar_programacion(programacion)
    pendientes["Asignada"] = False

    rutas = []
    detalles = []
    no_asignadas_motivos = []

    for _, unidad in unidades.iterrows():
        capacidad = float(unidad["Capacidad t"])
        carga = 0.0
        idxs = []

        for idx, entrega in pendientes.iterrows():
            if pendientes.at[idx, "Asignada"]:
                continue

            cliente = entrega["Cliente"]
            transportista = unidad["Transportista"]
            ton = float(entrega["Toneladas"])

            if not transportista_permitido(cliente, transportista, restricciones):
                continue

            if carga + ton <= capacidad:
                idxs.append(idx)
                carga += ton
                pendientes.at[idx, "Asignada"] = True

        if idxs:
            entregas_ruta = pendientes.loc[idxs].copy()

            detalle, cumple, salida_real, carga_min_total, regreso = calcular_ruta(
                entregas_ruta,
                unidad
            )

            ruta_id = f"Ruta {len(rutas) + 1}"
            clientes_consolidados = " + ".join(entregas_ruta["Cliente"].tolist())
            llenado = carga / capacidad * 100

            obligatorias = int(entregas_ruta["Entrega obligatoria hoy"].sum())

            rutas.append({
                "Ruta": ruta_id,
                "Transportista": unidad["Transportista"],
                "Vehículo": unidad["Vehículo"],
                "Clientes consolidados": clientes_consolidados,
                "Número clientes": len(entregas_ruta),
                "Entregas obligatorias": obligatorias,
                "Toneladas vehículo": round(carga, 2),
                "Capacidad t": capacidad,
                "Llenado %": round(llenado, 1),
                "Hora disponible": unidad["Hora disponible"],
                "Carga total min": carga_min_total,
                "Hora salida real": salida_real,
                "Hora regreso estimada": regreso,
                "Cumple ruta": "Sí" if cumple else "No"
            })

            for d in detalle:
                d["Ruta"] = ruta_id
                d["Vehículo"] = unidad["Vehículo"]
                d["Transportista"] = unidad["Transportista"]
                detalles.append(d)

    no_asignadas = pendientes[pendientes["Asignada"] == False].copy()

    for _, e in no_asignadas.iterrows():
        cliente = e["Cliente"]
        motivos = []

        for _, u in unidades.iterrows():
            permitido = transportista_permitido(cliente, u["Transportista"], restricciones)
            cabe = float(e["Toneladas"]) <= float(u["Capacidad t"])

            if not permitido:
                motivos.append(f"bloqueado con {u['Transportista']}")
            elif not cabe:
                motivos.append(f"no cabe en {u['Vehículo']}")

        motivo_final = "; ".join(motivos) if motivos else "sin capacidad disponible por consolidación previa"

        no_asignadas_motivos.append({
            "Cliente": cliente,
            "Toneladas": e["Toneladas"],
            "Zona": e["Zona"],
            "Prioridad": e["Prioridad"],
            "Prioridad texto": PRIORIDADES.get(int(e["Prioridad"]), "Normal"),
            "Entrega obligatoria hoy": e["Entrega obligatoria hoy"],
            "Motivo probable": motivo_final
        })

    return pd.DataFrame(rutas), pd.DataFrame(detalles), pd.DataFrame(no_asignadas_motivos)


init_state()

st.title("Planeador Logístico Diario 🚚")
st.caption("Clientes, transportistas, restricciones, prioridad 1-5, entregas obligatorias, carga por pedido, consolidación, llenado y OTIF proyectado.")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Banco de clientes",
    "2. Transportistas",
    "3. Restricciones",
    "4. Programación del día",
    "5. Plan de rutas",
    "6. Ayuda prioridad"
])

with tab1:
    st.subheader("Banco editable de clientes")

    st.session_state.clientes = st.data_editor(
        st.session_state.clientes,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Zona": st.column_config.SelectboxColumn("Zona", options=ZONAS),
            "Descarga min default": st.column_config.NumberColumn("Descarga min default", min_value=0, step=5),
            "Carga min default": st.column_config.NumberColumn("Carga min default", min_value=0, step=5),
            "Prioridad cliente default": st.column_config.NumberColumn(
                "Prioridad cliente default",
                min_value=1,
                max_value=5,
                step=1
            ),
            "Activo": st.column_config.CheckboxColumn("Activo")
        }
    )

with tab2:
    st.subheader("Banco editable de transportistas / unidades")

    st.session_state.transportistas = st.data_editor(
        st.session_state.transportistas,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Capacidad t": st.column_config.NumberColumn("Capacidad t", min_value=0.1, step=1.0),
            "Costo estimado km": st.column_config.NumberColumn("Costo estimado km", min_value=0.0, step=1.0),
            "Activo": st.column_config.CheckboxColumn("Activo")
        }
    )

with tab3:
    st.subheader("Restricciones cliente - transportista")

    st.write(
        "Aquí bloqueas combinaciones que no deben ocurrir: "
        "no cabe la unidad, proveedor castigado, chofer no disponible, cliente no acepta ese transporte, etc."
    )

    clientes_lista = st.session_state.clientes["Cliente"].dropna().unique().tolist()
    transportistas_lista = st.session_state.transportistas["Transportista"].dropna().unique().tolist()

    st.session_state.restricciones = st.data_editor(
        st.session_state.restricciones,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Cliente": st.column_config.SelectboxColumn("Cliente", options=clientes_lista),
            "Transportista bloqueado": st.column_config.SelectboxColumn(
                "Transportista bloqueado",
                options=transportistas_lista
            ),
            "Activa": st.column_config.CheckboxColumn("Activa")
        }
    )

with tab4:
    st.subheader("Selecciona clientes desde el banco y arma la matriz del día")

    clientes_activos = st.session_state.clientes[
        st.session_state.clientes["Activo"] == True
    ].copy()

    seleccion = st.multiselect(
        "Clientes a programar",
        clientes_activos["Cliente"].tolist()
    )

    if st.button("Cargar clientes seleccionados a programación"):
        filas = []

        for cliente in seleccion:
            base = clientes_activos[clientes_activos["Cliente"] == cliente].iloc[0]

            filas.append({
                "Cliente": base["Cliente"],
                "Zona": base["Zona"],
                "Dirección": base["Dirección"],
                "CP": base["CP"],
                "Toneladas": 1.0,
                "Ventana fin": base["Ventana fin default"],
                "Carga min": base["Carga min default"],
                "Descarga min": base["Descarga min default"],
                "Prioridad": int(base["Prioridad cliente default"]),
                "Entrega obligatoria hoy": False
            })

        st.session_state.programacion = pd.DataFrame(filas)

    st.session_state.programacion = st.data_editor(
        st.session_state.programacion,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Zona": st.column_config.SelectboxColumn("Zona", options=ZONAS),
            "Toneladas": st.column_config.NumberColumn("Toneladas", min_value=0.1, step=0.5),
            "Carga min": st.column_config.NumberColumn("Carga min", min_value=0, step=5),
            "Descarga min": st.column_config.NumberColumn("Descarga min", min_value=0, step=5),
            "Prioridad": st.column_config.NumberColumn(
                "Prioridad",
                min_value=1,
                max_value=5,
                step=1,
                help="1 = Crítica, 2 = Alta, 3 = Normal, 4 = Baja, 5 = Muy baja"
            ),
            "Entrega obligatoria hoy": st.column_config.CheckboxColumn("Entrega obligatoria hoy")
        }
    )

with tab5:
    st.subheader("Plan de rutas consolidadas")

    unidades_activas = st.session_state.transportistas[
        st.session_state.transportistas["Activo"] == True
    ].copy()

    if st.button("Generar rutas consolidadas", type="primary"):
        if st.session_state.programacion.empty:
            st.error("Primero carga clientes en la programación del día.")
            st.stop()

        if unidades_activas.empty:
            st.error("No hay transportistas activos.")
            st.stop()

        restricciones_activas = st.session_state.restricciones[
            st.session_state.restricciones["Activa"] == True
        ].copy()

        rutas, detalle, no_asignadas = planear(
            st.session_state.programacion,
            unidades_activas,
            restricciones_activas
        )

        st.subheader("Resumen por vehículo")

        if not rutas.empty:
            st.dataframe(rutas, use_container_width=True)

            total_entregas = len(st.session_state.programacion)
            entregas_ok = len(detalle[detalle["Cumple"] == "Sí"]) if not detalle.empty else 0
            otif = entregas_ok / total_entregas * 100 if total_entregas > 0 else 0

            obligatorias_total = int(st.session_state.programacion["Entrega obligatoria hoy"].sum())
            obligatorias_ok = len(
                detalle[
                    (detalle["Entrega obligatoria hoy"] == True)
                    & (detalle["Cumple"] == "Sí")
                ]
            ) if not detalle.empty else 0

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Entregas", total_entregas)
            col2.metric("Entregas a tiempo", entregas_ok)
            col3.metric("OTIF proyectado", f"{otif:.1f}%")
            col4.metric("Obligatorias", obligatorias_total)
            col5.metric("Obligatorias OK", obligatorias_ok)

            st.subheader("Detalle por ruta / cliente")

            orden_cols = [
                "Ruta",
                "Transportista",
                "Vehículo",
                "Cliente",
                "Zona",
                "Toneladas",
                "Prioridad",
                "Prioridad texto",
                "Entrega obligatoria hoy",
                "Carga min",
                "Traslado min",
                "Llegada estimada",
                "Ventana fin",
                "Descarga min",
                "Salida cliente",
                "Cumple"
            ]

            st.dataframe(detalle[orden_cols], use_container_width=True)

            st.subheader("Lectura operativa")

            bajas = rutas[rutas["Llenado %"] < 70]
            incumplen = detalle[detalle["Cumple"] == "No"]

            if not bajas.empty:
                st.warning("Vehículos con llenado menor a 70%.")
                st.dataframe(
                    bajas[[
                        "Ruta",
                        "Transportista",
                        "Vehículo",
                        "Toneladas vehículo",
                        "Capacidad t",
                        "Llenado %"
                    ]],
                    use_container_width=True
                )

            if not incumplen.empty:
                st.error("Entregas con riesgo de incumplimiento.")
                st.dataframe(incumplen, use_container_width=True)
            else:
                st.success("No hay incumplimientos proyectados por ventana.")

        else:
            st.error("No se pudo generar ninguna ruta.")

        if not no_asignadas.empty:
            st.error("Entregas no asignadas.")
            st.dataframe(no_asignadas, use_container_width=True)

with tab6:
    st.subheader("Cómo usar prioridad")

    prioridad_df = pd.DataFrame([
        [1, "Crítica", "Cliente estratégico, riesgo de paro, exportación urgente, penalización fuerte"],
        [2, "Alta", "Pedido comprometido para hoy o cliente importante"],
        [3, "Normal", "Pedido estándar"],
        [4, "Baja", "Puede moverse un día sin mucho daño"],
        [5, "Muy baja", "Reabasto, consignación o entrega flexible"],
    ], columns=["Prioridad", "Significado", "Ejemplo"])

    st.dataframe(prioridad_df, use_container_width=True)

    st.info(
        "El sistema ordena primero las entregas obligatorias, luego prioridad 1 a 5, "
        "y después las ventanas de entrega más tempranas."
    )

    st.warning(
        "Esto NO es optimización matemática exacta. Es una heurística práctica. "
        "Mejora la decisión, pero no garantiza el óptimo global."
    )

st.markdown("---")
st.caption("Versión sin Google Maps. Usa tiempos estándar por zona, prioridades, entregas obligatorias y restricciones manuales.")
