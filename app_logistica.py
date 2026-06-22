from datetime import datetime, timedelta

# -------------------------
# Datos base
# -------------------------

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
]

unidades = [
    {"unidad": "Rabón 8 t", "capacidad": 8, "hora_salida": "08:30"},
    {"unidad": "Torton 14 t", "capacidad": 14, "hora_salida": "08:30"},
]

# Tiempo estimado desde planta a cada zona
tiempos_desde_planta = {
    "Zapopan": 70,
    "Tonalá": 45,
    "El Salto": 55,
    "Tlaquepaque": 30,
    "Guadalajara": 40,
    "Tlajomulco": 60,
}

# Tiempo estimado entre zonas
tiempos_entre_zonas = {
    ("Zapopan", "Tonalá"): 80,
    ("Zapopan", "El Salto"): 90,
    ("Tonalá", "El Salto"): 45,
    ("Tonalá", "Zapopan"): 80,
    ("El Salto", "Zapopan"): 90,
    ("El Salto", "Tonalá"): 45,
}


# -------------------------
# Funciones
# -------------------------

def convertir_hora(hora_texto):
    return datetime.strptime(hora_texto, "%H:%M")


def minutos_entre_zonas(origen, destino):
    if origen == "PLANTA":
        return tiempos_desde_planta.get(destino, 60)
    
    if origen == destino:
        return 20

    return tiempos_entre_zonas.get((origen, destino), 70)


def planear_ruta(clientes, unidad):
    carga_total = sum(c["ton"] for c in clientes)

    if carga_total > unidad["capacidad"]:
        return {
            "unidad": unidad["unidad"],
            "viable": False,
            "motivo": "Excede capacidad",
            "carga_total": carga_total,
            "capacidad": unidad["capacidad"],
            "entregas": []
        }

    # Orden simple: primero prioridad alta, luego ventana más temprana
    clientes_ordenados = sorted(
        clientes,
        key=lambda c: (c["prioridad"], convertir_hora(c["ventana_fin"]))
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
            "cliente": cliente["cliente"],
            "zona": cliente["zona"],
            "ton": cliente["ton"],
            "hora_llegada": hora_llegada.strftime("%H:%M"),
            "ventana_fin": cliente["ventana_fin"],
            "cumple": cumple
        })

        hora_actual = hora_llegada + timedelta(minutes=cliente["tiempo_descarga_min"])
        zona_actual = cliente["zona"]

    utilizacion = carga_total / unidad["capacidad"]

    return {
        "unidad": unidad["unidad"],
        "viable": cumple_todo,
        "carga_total": carga_total,
        "capacidad": unidad["capacidad"],
        "utilizacion": round(utilizacion * 100, 1),
        "entregas": entregas
    }


def imprimir_resultado(resultado):
    print("\n==============================")
    print(f"Unidad: {resultado['unidad']}")
    print(f"Carga total: {resultado['carga_total']} t")
    print(f"Capacidad: {resultado['capacidad']} t")

    if "utilizacion" in resultado:
        print(f"Utilización: {resultado['utilizacion']}%")

    print(f"Viable para servicio: {'SÍ' if resultado['viable'] else 'NO'}")

    if not resultado["viable"] and "motivo" in resultado:
        print(f"Motivo: {resultado['motivo']}")

    print("\nEntregas:")

    for e in resultado["entregas"]:
        estado = "OK" if e["cumple"] else "RIESGO / INCUMPLE"
        print(
            f"- {e['cliente']} | {e['zona']} | "
            f"{e['ton']} t | llegada {e['hora_llegada']} | "
            f"límite {e['ventana_fin']} | {estado}"
        )


# -------------------------
# Ejecución
# -------------------------

for unidad in unidades:
    resultado = planear_ruta(clientes, unidad)
    imprimir_resultado(resultado)
