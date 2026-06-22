import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Planeador Logístico", page_icon="🚚", layout="wide")

st.title("Planeador Logístico Diario 🚚")
st.caption("MVP funcional para nivel de servicio, rutas, capacidad y alertas operativas.")

# ======================================================
# Catálogos base
# ======================================================

ZONAS = [
    "Guadalajara",
    "Zapopan",
    "Tlaquepaque",
    "Tonalá",
    "El Salto",
    "Tlajomulco",
    "Otro"
]

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

# ======================================================
# Funciones
# ======================================================

def hora_a_datetime(hora):
    if isinstance(hora, str):
        return datetime.strptime(hora, "%H:%M")
    return datetime.combine(datetime.today(), hora)


def minutos_traslado(origen, destino):
    if origen == "PLANTA":
        return TIEMPOS_PLANTA.get(destino, 75)

    if origen == destino:
        return 20

    return TIEMPOS_ZONA.get((origen, destino), 75)


def asignar_rutas(entregas, unidades, hora_carga, tiempo_carga):
    entregas = entregas.copy()
    unidades = unidades.copy()

    entregas = entregas.sort_values(
        by=["Prioridad", "Ventana fin"],
        ascending=[True, True]
    )

    rutas = []
    no_asignadas = []

    for _, unidad in unidades.iterrows():
        capacidad_disponible = unidad["Capacidad t"]
        ruta_entregas = []

        for idx, entrega in entregas.iterrows():
            if entrega["Asignada"]:
                continue

            if entrega["Toneladas"] <= capacidad_disponible:
                ruta_entregas.append(idx)
                capacidad_disponible -= entrega["Toneladas"]
                entregas.at[idx, "Asignada"] = True

        if ruta_entregas:
            rutas.append({
                "Unidad": unidad["Unidad"],
                "Proveedor": unidad["Proveedor"],
                "Capacidad t": unidad["Capacidad t"],
                "Hora salida": unidad["Hora salida"],
                "Tiempo carga min": tiempo_carga,
                "Entregas idx": ruta_entregas
            })

    for _, entrega in entregas[entregas["Asignada"] == False].iterrows():
        no_asignadas.append(entrega["Cliente"])

    return rutas, no_asignadas, entregas


def calcular_ruta(ruta, entregas):
    hora_actual = hora_a_datetime(ruta["Hora salida"]) + timedelta(minutes=ruta["Tiempo carga min"])
    zona_actual = "PLANTA"

    registros = []
    carga_total = 0
    cumple_ruta = True

    subset = entregas.loc[ruta["Entregas idx"]].copy()
    subset = subset.sort_values(by=["Prioridad", "Ventana fin"], ascending=[True, True])

    for _, entrega in subset.iterrows():
        traslado = minutos_traslado(zona_actual, entrega["Zona"])
        llegada = hora_actual + timedelta(minutes=traslado)
        ventana_fin = hora_a_datetime(entrega["Ventana fin"])

        cumple = llegada <= ventana_fin
        if not cumple:
            cumple_ruta = False

        salida_cliente = llegada + timedelta(minutes=int(entrega["Descarga min"]))
        carga_total += entrega["Toneladas"]

        registros.append({
            "Unidad": ruta["Unidad"],
            "Proveedor": ruta["Proveedor"],
            "Cliente": entrega["Cliente"],
            "Zona": entrega["Zona"],
            "Dirección / CP": entrega["Dirección / CP"],
            "Toneladas": entrega["Toneladas"],
            "Traslado min": traslado,
            "Llegada estimada": llegada.strftime("%H:%M"),
            "Ventana fin": entrega["Ventana fin"],
            "Descarga min": entrega["Descarga min"],
            "Salida cliente": salida_cliente.strftime("%H:%M"),
            "Cumple": "Sí" if cumple else "No"
        })

        hora_actual = salida_cliente
        zona_actual = entrega["Zona"]

    regreso = minutos_traslado(zona_actual, "Tlaquepaque")
    hora_regreso = hora_actual + timedelta(minutes=regreso)
    utilizacion = carga_total / ruta["Capacidad t"] * 100

    resumen = {
        "Unidad": ruta["Unidad"],
        "Proveedor": ruta["Proveedor"],
        "Carga total t": round(carga_total, 2),
        "Capacidad t": ruta["Capacidad t"],
        "Utilización %": round(utilizacion, 1),
        "Hora regreso estimada": hora_regreso.strftime("%H:%M"),
        "Cumple ruta": "Sí" if cumple_ruta else "No"
    }

    return registros, resumen


# ======================================================
# Datos editables
# ======================================================

st.sidebar.header("Parámetros")

tiempo_carga = st.sidebar.number_input("Tiempo de carga en planta, min", 0, 240, 30, 5)

st.subheader("1. Programación de entregas")

entregas_base = pd.DataFrame([
    ["Cliente Zapopan", "Zapopan", "Av. Aviación 5051, Zapopan", 2.5, "13:00", 30, 1, False],
    ["Cliente El Salto", "El Salto", "Carretera El Salto, Parque Industrial", 5.0, "14:00", 45, 1, False],
    ["Cliente Tonalá", "Tonalá", "Av. Tonaltecas, Tonalá", 3.0, "15:00", 35, 2, False],
    ["Cliente Guadalajara", "Guadalajara", "Zona Industrial Guadalajara", 1.5, "12:30", 25, 1, False],
    ["Cliente Tlaquepaque", "Tlaquepaque", "Álamo Industrial, Tlaquepaque", 2.0, "16:00", 30, 3, False],
], columns=[
    "Cliente",
    "Zona",
    "Dirección / CP",
    "Toneladas",
    "Ventana fin",
    "Descarga min",
    "Prioridad",
    "Asignada"
])

entregas = st.data_editor(
    entregas_base,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Zona": st.column_config.SelectboxColumn("Zona", options=ZONAS),
        "Toneladas": st.column_config.NumberColumn("Toneladas", min_value=0.1, step=0.5),
        "Ventana fin": st.column_config.TextColumn("Ventana fin HH:MM"),
        "Descarga min": st.column_config.NumberColumn("Descarga min", min_value=0, step=5),
        "Prioridad": st.column_config.NumberColumn("Prioridad", min_value=1, max_value=5, step=1),
        "Asignada": st.column_config.CheckboxColumn("Asignada")
    }
)

st.subheader("2. Unidades disponibles")

unidades_base = pd.DataFrame([
    ["Rabón 8 t", "Proveedor A", 8.0, "08:30"],
    ["Torton 14 t", "Proveedor B", 14.0, "08:30"],
    ["Tráiler 25 t", "Proveedor C", 25.0, "08:30"],
], columns=[
    "Unidad",
    "Proveedor",
    "Capacidad t",
    "Hora salida"
])

unidades = st.data_editor(
    unidades_base,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Capacidad t": st.column_config.NumberColumn("Capacidad t", min_value=0.1, step=1.0),
        "Hora salida": st.column_config.TextColumn("Hora salida HH:MM")
    }
)

# ======================================================
# Planeación
# ======================================================

if st.button("Generar plan de rutas", type="primary"):
    if entregas.empty or unidades.empty:
        st.error("Necesitas al menos una entrega y una unidad.")
        st.stop()

    entregas["Asignada"] = False

    rutas, no_asignadas, entregas_asignadas = asignar_rutas(
        entregas,
        unidades,
        None,
        tiempo_carga
    )

    todos_registros = []
    resumen_rutas = []

    for ruta in rutas:
        registros, resumen = calcular_ruta(ruta, entregas_asignadas)
        todos_registros.extend(registros)
        resumen_rutas.append(resumen)

    df_resumen = pd.DataFrame(resumen_rutas)
    df_detalle = pd.DataFrame(todos_registros)

    st.subheader("3. Resumen operativo")

    total_entregas = len(entregas)
    entregas_cumplen = len(df_detalle[df_detalle["Cumple"] == "Sí"]) if not df_detalle.empty else 0
    otif_estimado = entregas_cumplen / total_entregas * 100 if total_entregas > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Entregas programadas", total_entregas)
    col2.metric("Entregas a tiempo estimadas", entregas_cumplen)
    col3.metric("OTIF proyectado", f"{otif_estimado:.1f}%")
    col4.metric("Rutas generadas", len(rutas))

    if otif_estimado >= 95:
        st.success("Buen plan: el nivel de servicio proyectado es alto.")
    elif otif_estimado >= 85:
        st.warning("Plan aceptable, pero con riesgo. Revisa entregas críticas.")
    else:
        st.error("Plan débil para servicio. Aquí se te pueden ir varios incumplimientos.")

    st.dataframe(df_resumen, use_container_width=True)

    st.subheader("4. Detalle de rutas")

    st.dataframe(df_detalle, use_container_width=True)

    incumplimientos = df_detalle[df_detalle["Cumple"] == "No"]

    st.subheader("5. Alertas")

    if not incumplimientos.empty:
        st.error("Entregas con riesgo de incumplimiento:")
        st.dataframe(incumplimientos, use_container_width=True)
        st.write("Acciones sugeridas: adelantar salida, dividir ruta, cambiar secuencia o asignar unidad dedicada.")
    else:
        st.success("No hay incumplimientos proyectados por ventana de entrega.")

    if no_asignadas:
        st.error("Entregas no asignadas por falta de capacidad:")
        st.write(", ".join(no_asignadas))

    rutas_baja_utilizacion = df_resumen[df_resumen["Utilización %"] < 70]

    if not rutas_baja_utilizacion.empty:
        st.warning("Rutas con baja utilización:")
        st.dataframe(rutas_baja_utilizacion, use_container_width=True)

else:
    st.info("Edita entregas y unidades. Después presiona 'Generar plan de rutas'.")

st.markdown("---")
st.caption("Versión sin Google Maps. Usa tiempos estándar por zona para evaluar servicio y capacidad.")
