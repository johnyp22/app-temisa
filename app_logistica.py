import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(
    page_title="MVP Rutas Logísticas",
    page_icon="🚚",
    layout="wide"
)

st.title("MVP de Planeación de Rutas Logísticas 🚚")
st.caption("Versión inicial para evaluar capacidad, secuencia, ventanas de entrega y riesgo de incumplimiento.")

# ============================================================
# Datos base
# ============================================================

clientes = [
    {
        "cliente": "Cliente Zapopan Norte",
        "zona": "Zapopan",
        "ton": 2.5,
        "ventana_fin": "13:00",
        "tiempo_descarga_min": 30,
        "prioridad": 1
    },
    {
        "cliente": "Cliente Tonalá",
        "zona": "Tonalá",
        "ton": 3.0,
        "ventana_fin": "15:00",
        "tiempo_descarga_min": 35,
        "prioridad": 2
    },
    {
        "cliente": "Cliente El Salto",
        "zona": "El Salto",
        "ton": 5.0,
        "ventana_fin": "14:00",
        "tiempo_descarga_min": 45,
        "prioridad": 1
    },
    {
        "cliente": "Cliente Guadalajara",
        "zona": "Guadalajara",
        "ton": 1.5,
        "ventana_fin": "12:30",
        "tiempo_descarga_min": 25,
        "prioridad": 1
    },
    {
        "cliente": "Cliente Tlaquepaque",
        "zona": "Tlaquepaque",
        "ton": 2.0,
        "ventana_fin": "16:00",
        "tiempo_descarga_min": 30,
        "prioridad": 3
    },
]

unidades = [
    {
        "unidad": "Rabón 8 t",
        "capacidad": 8,
        "hora_salida": "08:30"
    },
    {
        "unidad": "Torton 14 t",
        "capacidad": 14,
        "hora_salida": "08:30"
    },
    {
        "unidad": "Tráiler 25 t",
        "capacidad": 25,
        "hora_salida": "08:30"
    },
]

tiempos_desde_planta = {
    "Zapopan": 70,
    "Tonalá": 45,
    "El Salto": 55,
    "Tlaquepaque": 30,
    "Guadalajara": 40,
    "Tlajomulco": 60,
}

tiempos_entre_zonas = {
    ("Zapopan", "Tonalá"): 80,
    ("Zapopan", "El Salto"): 90,
    ("Zapopan", "Tlaquepaque"): 75,
    ("Zapopan", "Guadalajara"): 45,

    ("Tonalá", "Zapopan"): 80,
    ("Tonalá", "El Salto"): 45,
    ("Tonalá", "Tlaquepaque"): 35,
    ("Tonalá", "Guadalajara"): 45,

    ("El Salto", "Zapopan"): 90,
    ("El Salto", "Tonalá"): 45,
    ("El Salto", "Tlaquepaque"): 50,
    ("El Salto", "Guadalajara"): 60,

    ("Tlaquepaque", "Zapopan"): 75,
    ("Tlaquepaque", "Tonalá"): 35,
    ("Tlaquepaque", "El Salto"): 50,
    ("Tlaquepaque", "Guadalajara"): 35,

    ("Guadalajara", "Zapopan"): 45,
    ("Guadalajara", "Tonalá"): 45,
    ("Guadalajara", "El Salto"): 60,
    ("Guadalajara", "Tlaquepaque"): 35,
}


# ============================================================
# Funciones
# ============================================================

def convertir_hora(hora_texto):
    return datetime.strptime(hora_texto, "%H:%M")


def minutos_entre_zonas(origen, destino):
    if origen == "PLANTA":
        return tiempos_desde_planta.get(destino, 60)

    if origen == destino:
        return 20

    return tiempos_entre_zonas.get((origen, destino), 70)


def planear_ruta(clientes_ruta, unidad):
    carga_total = sum(c["ton"] for c in clientes_ruta)

    if carga_total > unidad["capacidad"]:
        return {
            "unidad": unidad["unidad"],
            "viable": False,
            "motivo": "Excede capacidad de la unidad.",
            "carga_total": carga_total,
            "capacidad": unidad["capacidad"],
            "utilizacion": round((carga_total / unidad["capacidad"]) * 100, 1),
            "entregas": []
        }

    clientes_ordenados = sorted(
        clientes_ruta,
        key=lambda c: (
            c["prioridad"],
            convertir_hora(c["ventana_fin"])
        )
    )

    hora_actual = convertir_hora(unidad["hora_salida"])
    zona_actual = "PLANTA"
    entregas = []
    cumple_todo = True

    for cliente in clientes_ordenados:
        traslado = minutos_entre_zonas(zona_actual, cliente["zona"])
        hora_llegada = hora_actual + timedelta(minutes=traslado)
        hora_limite = convertir_hora(cliente["ventana_fin"])

        cumple = hora_llegada <= hora_limite

        if not cumple:
            cumple_todo = False

        entregas.append({
            "Cliente": cliente["cliente"],
            "Zona": cliente["zona"],
            "Toneladas": cliente["ton"],
            "Traslado min": traslado,
            "Hora llegada": hora_llegada.strftime("%H:%M"),
            "Ventana fin": cliente["ventana_fin"],
            "Descarga min": cliente["tiempo_descarga_min"],
            "Cumple": "Sí" if cumple else "No"
        })

        hora_actual = hora_llegada + timedelta(
            minutes=cliente["tiempo_descarga_min"]
        )
        zona_actual = cliente["zona"]

    return {
        "unidad": unidad["unidad"],
        "viable": cumple_todo,
        "motivo": "" if cumple_todo else "Una o más entregas llegan fuera de ventana.",
        "carga_total": carga_total,
        "capacidad": unidad["capacidad"],
        "utilizacion": round((carga_total / unidad["capacidad"]) * 100, 1),
        "entregas": entregas
    }


# ============================================================
# Barra lateral
# ============================================================

st.sidebar.header("Configuración de ruta")

unidad_seleccionada = st.sidebar.selectbox(
    "Unidad",
    [u["unidad"] for u in unidades]
)

unidad = next(
    u.copy() for u in unidades
    if u["unidad"] == unidad_seleccionada
)

hora_salida = st.sidebar.time_input(
    "Hora de salida",
    value=convertir_hora(unidad["hora_salida"]).time()
)

unidad["hora_salida"] = hora_salida.strftime("%H:%M")

st.sidebar.markdown("---")
st.sidebar.write("Selecciona entregas a incluir:")

clientes_seleccionados = []

for cliente in clientes:
    incluir = st.sidebar.checkbox(
        cliente["cliente"],
        value=True
    )

    if incluir:
        clientes_seleccionados.append(cliente)


# ============================================================
# Vista principal
# ============================================================

st.subheader("Entregas disponibles")

df_clientes = pd.DataFrame(clientes)

st.dataframe(
    df_clientes,
    use_container_width=True
)

if not clientes_seleccionados:
    st.warning("Selecciona al menos una entrega en la barra lateral.")
    st.stop()

resultado = planear_ruta(clientes_seleccionados, unidad)

st.subheader("Resultado de planeación")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Unidad", resultado["unidad"])
col2.metric("Carga total", f"{resultado['carga_total']} t")
col3.metric("Capacidad", f"{resultado['capacidad']} t")
col4.metric("Utilización", f"{resultado['utilizacion']}%")

if resultado["viable"]:
    st.success("La ruta es viable para nivel de servicio.")
else:
    st.error("La ruta NO es viable para nivel de servicio.")
    st.warning(resultado["motivo"])

st.subheader("Secuencia sugerida de entregas")

if resultado["entregas"]:
    df_entregas = pd.DataFrame(resultado["entregas"])

    st.dataframe(
        df_entregas,
        use_container_width=True
    )
else:
    st.info("No se generó secuencia porque la carga excede la capacidad.")

st.subheader("Lectura operativa")

if resultado["utilizacion"] < 70:
    st.warning(
        "La unidad va subutilizada. Revisa si conviene consolidar más carga "
        "o usar una unidad más pequeña."
    )
elif resultado["utilizacion"] > 100:
    st.error("La unidad excede capacidad.")
else:
    st.success("La utilización de la unidad es razonable.")

if not resultado["viable"]:
    st.write(
        "Acción sugerida: dividir la ruta, adelantar la salida, cambiar secuencia "
        "o asignar otra unidad."
    )
else:
    st.write(
        "Acción sugerida: liberar ruta, siempre que producto, documentación "
        "y unidad estén listos."
    )

st.markdown("---")
st.caption(
    "Nota: esta versión usa tiempos estimados por zona. No considera tráfico real, "
    "citas dinámicas ni cálculo exacto por Google Maps."
)
