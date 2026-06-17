import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime

# Configuración de la página
st.set_page_config(page_title="Optimizador de Rutas TEMISA", layout="wide")

st.title("🚚 Sistema de Consolidación y Optimización de Rutas - TEMISA")
st.write("Agrupamiento inteligente de pedidos por zona, aprovechamiento de capacidad de unidades y viabilidad horaria.")

# --- DIRECCIÓN Y COORDENADAS OFICIALES DEL CEDIS ---
CEDIS_NOMBRE = "TEMISA (Periférico Sur 6000, San Pedro Tlaquepaque, Jal.)"
CEDIS_LAT, CEDIS_LON = 20.6053, -103.3742  # Ubicación exacta al pie de Periférico

# --- INICIALIZACIÓN DEL CATÁLOGO DE CLIENTES EDITABLE (SESSION STATE) ---
if "directorio_clientes" not in st.session_state:
    st.session_state.directorio_clientes = [
        {"Cliente": "NYPRO", "Zona": "Zapopan Norte", "Latitud": 20.745, "Longitud": -103.415, "Dist_KM": 26.5},
        {"SAN ANGEL": "SAN ANGEL", "Zona": "Zapopan Norte", "Latitud": 20.730, "Longitud": -103.430, "Dist_KM": 24.0},
        {"Cliente": "CARBOTECNIA", "Zona": "Zapopan Norte", "Latitud": 20.720, "Longitud": -103.400, "Dist_KM": 22.5},
        {"Cliente": "O-I MEXICO", "Zona": "Zapopan Norte", "Latitud": 20.710, "Longitud": -103.410, "Dist_KM": 21.8},
        {"Cliente": "KASTO MOLINOS", "Zona": "Zapopan Norte", "Latitud": 20.750, "Longitud": -103.390, "Dist_KM": 27.0},
        {"Cliente": "EL SALTO 6", "Zona": "El Salto", "Latitud": 20.520, "Longitud": -103.250, "Dist_KM": 19.5},
        {"Cliente": "EL SALTO 7", "Zona": "El Salto", "Latitud": 20.525, "Longitud": -103.245, "Dist_KM": 20.8},
        {"Cliente": "USI", "Zona": "Periférico Poniente", "Latitud": 20.680, "Longitud": -103.440, "Dist_KM": 16.5},
        {"Cliente": "INDUSTRIAS GDL SUR", "Zona": "Urbana Sur", "Latitud": 20.655, "Longitud": -103.360, "Dist_KM": 9.0},
        {"Cliente": "CONVERTIDORA", "Zona": "Urbana Sur", "Latitud": 20.640, "Longitud": -103.340, "Dist_KM": 8.2}
    ]

if "flota" not in st.session_state:
    st.session_state.flota = [
        {"Transportista": "Sandra Melendres", "Tipo": "Plataforma", "Capacidad (TON)": 15.0, "Vel_Prom (km/h)": 45},
        {"Transportista": "Eduardo Melendres", "Tipo": "Camioneta", "Capacidad (TON)": 6.0, "Vel_Prom (km/h)": 55},
        {"Transportista": "SLI", "Tipo": "Camioneta", "Capacidad (TON)": 5.0, "Vel_Prom (km/h)": 55}
    ]

if "rutas_calculadas" not in st.session_state:
    st.session_state.rutas_calculadas = None

# --- MENÚ LATERAL: GESTIÓN DE DIRECTORIOS Y FLOTA ---
with st.sidebar:
    st.header("⚙️ Panel de Configuración Master")
    
    # 1. Tabla de Clientes Totalmente Editable
    st.subheader("🗂️ Directorio de Clientes")
    st.caption("Modifica distancias, agrega clientes nuevos o edita coordenadas aquí abajo:")
    df_clientes_edit = st.data_editor(
        pd.DataFrame(st.session_state.directorio_clientes),
        num_rows="dynamic",
        hide_index=True,
        key="editor_directorio_maestro",
        use_container_width=True
    )
    st.session_state.directorio_clientes = df_clientes_edit.to_dict(orient="records")
    
    # Generar diccionario de consulta rápida para el programa
    CLIENTES_DB = {str(c["Cliente"]).upper().strip(): c for c in st.session_state.directorio_clientes if pd.notna(c["Cliente"])}
    lista_nombres_clientes = sorted(list(CLIENTES_DB.keys()))

    st.markdown("---")
    
    # 2. Gestión de Flota
    st.subheader("🚛 Control de Unidades Disponibles")
    df_flota_edit = st.data_editor(
        pd.DataFrame(st.session_state.flota),
        hide_index=True,
        key="editor_flota_maestro",
        use_container_width=True
    )
    st.session_state.flota = df_flota_edit.to_dict(orient="records")

    if st.button("🔄 Restablecer Datos de Fábrica"):
        del st.session_state.directorio_clientes
        del st.session_state.flota
        del st.session_state.rutas_calculadas
        st.rerun()

# --- PANTALLA PRINCIPAL: REGISTRO DE PEDIDOS DEL DÍA ---
st.header("📋 Captura de Pedidos y Ventanas Horarias")
st.write(f"Todos los despachos inician desde: **{CEDIS_NOMBRE}**")

if "datos_pedidos" not in st.session_state:
    st.session_state.datos_pedidos = pd.DataFrame({
        "Cliente": ["EL SALTO 7", "EL SALTO 6", "USI", "CONVERTIDORA", "INDUSTRIAS GDL SUR"],
        "Toneladas": [12.0, 3.0, 5.0, 2.0, 3.5],
        "Inicio Carga CEDIS": [datetime.time(8, 0), datetime.time(8, 0), datetime.time(9, 0), datetime.time(10, 30), datetime.time(10, 30)],
        "Min. Carga CEDIS": [40, 25, 30, 20, 25],
        "Min. Descarga Cliente": [45, 30, 35, 20, 30],
        "Cierre Cliente": [datetime.time(13, 0), datetime.time(16, 0), datetime.time(15, 0), datetime.time(17, 0), datetime.time(14, 0)]
    })

# Desplegar la tabla con menú desplegable para evitar errores de escritura
df_captura = st.data_editor(
    st.session_state.datos_pedidos,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Cliente": st.column_config.SelectboxColumn("Cliente Comercial", options=lista_nombres_clientes, required=True),
        "Inicio Carga CEDIS": st.column_config.TimeColumn("Horario Carga", format="hh:mm a"),
        "Cierre Cliente": st.column_config.TimeColumn("Cierre Almacén", format="hh:mm a"),
        "Min. Carga CEDIS": st.column_config.NumberColumn("Min. Carga", min_value=5, max_value=120, step=5),
        "Min. Descarga Cliente": st.column_config.NumberColumn("Min. Descarga", min_value=5, max_value=120, step=5),
        "Toneladas": st.column_config.NumberColumn("TON", format="%.1f", min_value=0.1)
    },
    key="editor_operaciones_dia"
)

# --- BOTONES DE ACCIÓN ---
st.markdown("---")
c_btn1, c_btn2 = st.columns(2)

with c_btn1:
    if st.button("⚡ OPTIMIZAR LOGÍSTICA Y CONSOLIDAR RUTAS", type="primary", use_container_width=True):
        st.session_state.datos_pedidos = df_captura
        
        if df_captura.empty:
            st.error("No hay pedidos registrados para procesar.")
        else:
            # 1. Estructurar y limpiar pedidos con base de datos geográfica
            pedidos_validos = []
            for _, fila in df_captura.iterrows():
                nom = str(fila["Cliente"]).upper().strip() if pd.notna(fila["Cliente"]) else ""
                if nom in CLIENTES_DB:
                    pedidos_validos.append({
                        "Cliente": nom,
                        "TON": float(fila["Toneladas"]) if pd.notna(fila["Toneladas"]) else 1.0,
                        "Zona": CLIENTES_DB[nom]["Zona"],
                        "Inicio_Carga": fila["Inicio Carga CEDIS"] if pd.notna(fila["Inicio Carga CEDIS"]) else datetime.time(8, 0),
                        "M_Carga": int(fila["Min. Carga CEDIS"]) if pd.notna(fila["Min. Carga CEDIS"]) else 30,
                        "M_Descarga": int(fila["Min. Descarga Cliente"]) if pd.notna(fila["Min. Descarga Cliente"]) else 30,
                        "Cierre": fila["Cierre Cliente"] if pd.notna(fila["Cierre Cliente"]) else datetime.time(17, 0),
                        "Dist_KM": CLIENTES_DB[nom]["Dist_KM"]
                    })
            
            # 2. Agrupar pedidos por Zona para consolidar
            pedidos_por_zona = {}
            for p in pedidos_validos:
                pedidos_por_zona.setdefault(p["Zona"], []).append(p)
                
            flota_disponible = sorted(st.session_state.flota, key=lambda x: x["Capacidad (TON)"], reverse=True)
            itinerarios_finales = []
            unidades_utilizadas = set()
            
            # 3. Algoritmo de Consolidación Inteligente
            for zona, lista_pedidos in pedidos_por_zona.items():
                # Ordenar pedidos por volumen de mayor a menor
                lista_pedidos = sorted(lista_pedidos, key=lambda x: x["TON"], reverse=True)
                
                while lista_pedidos:
                    ruta_actual = []
                    carga_acumulada = 0.0
                    
                    # Intentar juntar pedidos en una unidad apta
                    for p in list(lista_pedidos):
                        if carga_acumulada + p["TON"] <= 15.0:  # Límite máximo de la unidad mayor
                            ruta_actual.append(p)
                            carga_acumulada += p["TON"]
                            lista_pedidos.remove(p)
                    
                    # Asignar el vehículo ideal más chico disponible para esta carga para no desperdiciar
                    vehiculo_asignado = flota_disponible[-1] # Por defecto el menor
                    for v in flota_disponible:
                        if v["Capacidad (TON)"] >= carga_acumulada and v["Transportista"] not in unidades_utilizadas:
                            vehiculo_asignado = v
                            break
                    
                    unidades_utilizadas.add(vehiculo_asignado["Transportista"])
                    
                    # --- SIMULACIÓN DE LÍNEA DE TIEMPO SECUENCIAL ---
                    dt_base = datetime.date.today()
                    # Tomamos la hora de inicio del primer pedido de la secuencia
                    hora_reloj = datetime.datetime.combine(dt_base, ruta_actual[0]["Inicio_Carga"])
                    
                    detalles_paradas = []
                    total_distancia_viaje = 0.0
                    
                    # Tiempo de carga consolidada en TEMISA
                    total_minutos_carga = sum([p["M_Carga"] for p in ruta_actual])
                    h_salida_temisa = hora_reloj + datetime.timedelta(minutes=total_minutos_carga)
                    
                    hora_reloj = h_salida_temisa
                    
                    for i, item in enumerate(ruta_actual):
                        vel = vehiculo_asignado["Vel_Prom (km/h)"]
                        # Si es el primer cliente mide desde TEMISA; si es el segundo estima una distancia inter-cliente menor
                        dist_tramo = item["Dist_KM"] if i == 0 else abs(item["Dist_KM"] - ruta_actual[i-1]["Dist_KM"]) + 3
                        total_distancia_viaje += dist_tramo
                        
                        tiempo_transito = int((dist_tramo / vel) * 60)
                        hora_arribo = hora_reloj + datetime.timedelta(minutes=tiempo_transito)
                        hora_salida_cliente = hora_arribo + datetime.timedelta(minutes=item["M_Descarga"])
                        
                        # Validar si llega a tiempo a la ventana del cliente
                        limite_cliente = datetime.datetime.combine(dt_base, item["Cierre"])
                        if hora_arribo <= limite_cliente:
                            estatus = "🟢 Óptimo" if (limite_cliente - hora_arribo).total_seconds()/60 > 30 else "🟡 Ajustado"
                        else:
                            estatus = "🔴 Fuera de Ventana"
                            
                        detalles_paradas.append(f"{item['Cliente']} ({hora_arribo.strftime('%I:%M %p')} | {estatus})")
                        hora_reloj = hora_salida_cliente
                    
                    # Regreso final a base TEMISA
                    dist_regreso = ruta_actual[-1]["Dist_KM"]
                    total_distancia_viaje += dist_regreso
                    tiempo_regreso = int((dist_regreso / vehiculo_asignado["Vel_Prom (km/h)"]) * 60)
                    hora_retorno_base = hora_reloj + datetime.timedelta(minutes=tiempo_regreso)
                    
                    itinerarios_finales.append({
                        "Unidad / Operador": f"{vehiculo_asignado['Transportista']} ({vehiculo_asignado['Tipo']})",
                        "Zona Logística": zona,
                        "Clientes Consolidados": " ➡️ ".join([p["Cliente"] for p in ruta_actual]),
                        "Carga Total": f"{carga_acumulada:.1f} / {vehiculo_asignado['Capacidad (TON)']} TON",
                        "Salida TEMISA": h_salida_temisa.strftime("%I:%M %p"),
                        "Secuencia de Arribos": " || ".join(detalles_paradas),
                        "Retorno Estimado TEMISA": hora_retorno_base.strftime("%I:%M %p")
                    })
            
            if itinerarios_finales:
                st.session_state.rutas_calculadas = pd.DataFrame(itinerarios_finales)
                st.success("¡Optimización de rutas consolidada ejecutada exitosamente!")
            else:
                st.error("No se pudieron consolidar las rutas con los datos ingresados.")

with c_btn2:
    if st.button("🗑️ Limpiar Resultados del Tablero", use_container_width=True):
        st.session_state.rutas_calculadas = None
        st.rerun()

# --- DESPLIEGUE DEL PLAN OPERATIVO LOGÍSTICO ---
if st.session_state.rutas_calculadas is not None:
    st.markdown("---")
    st.header("📈 Hoja de Ruta Consolidada Máxima Eficiencia")
    st.write("El sistema agrupó los pedidos con base en la cercanía de zona para maximizar la capacidad útil del transporte.")
    st.dataframe(st.session_state.rutas_calculadas, use_container_width=True, hide_index=True)
    
    # Renderizado del mapa con los pines correctos
    st.header("🗺️ Mapa Logístico de Rutas Activas")
    m = folium.Map(location=[20.65, -103.35], zoom_start=11)
    
    # Pin de TEMISA exacto
    folium.Marker(
        [CEDIS_LAT, CEDIS_LON], 
        popup=f"<b>CEDIS MATRIZ TEMISA</b><br>{CEDIS_NOMBRE}", 
        icon=folium.Icon(color="red", icon="home")
    ).add_to(m)
    
    # Colocar los pines dinámicos de los clientes activos en la captura
    for _, fila in df_captura.iterrows():
        nom_c = str(fila["Cliente"]).upper().strip() if pd.notna(fila["Cliente"]) else ""
        if nom_c in CLIENTES_DB:
            geo = CLIENTES_DB[nom_c]
            folium.Marker(
                [geo["Latitud"], geo["Longitud"]],
                popup=f"<b>Cliente: {nom_c}</b><br>Zona: {geo['Zona']}<br>Carga: {fila['Toneladas']} TON",
                icon=folium.Icon(color="blue", icon="truck")
            ).add_to(m)
            
    st_folium(m, width=1300, height=500, key="mapa_rutas_consolidadas")
