import streamlit as st
import pandas as pd
import datetime
import math

# Configuración de la página
st.set_page_config(page_title="Control de Rutas TEMISA", layout="wide")

st.title("🚚 Optimizador de Rutas Automatizado - TEMISA")
st.write("Direcciones completas y cálculo automático de kilometrajes reales para máxima eficiencia de unidades.")

# --- DATOS OFICIALES DEL CEDIS (CORREGIDO: COLONIA ARTESANOS) ---
CEDIS_NOMBRE = "TEMISA (Anillo Perif. Sur Manuel Gómez Morín 6000, Col. Artesanos, CP 45590, San Pedro Tlaquepaque, Jal.)"
CEDIS_LAT, CEDIS_LON = 20.5901, -103.3211  # Ubicación exacta real en Artesanos

# Coordenadas de los municipios para el cálculo automático de distancia real desde Artesanos
MUNICIPIOS_GEO = {
    "ZAPOPAN": (20.72, -103.41),
    "EL SALTO": (20.52, -103.24),
    "GUADALAJARA": (20.65, -103.35),
    "TLAQUEPAQUE": (20.61, -103.31),
    "TONALA": (20.62, -103.24),
    "TLAJOMULCO": (20.47, -103.44)
}

def calcular_distancia_automatica(lat_destino, lon_destino):
    # Fórmula de Haversine para cálculo de distancia vial desde el nuevo punto de Artesanos
    rad = math.pi / 180
    dlat = (lat_destino - CEDIS_LAT) * rad
    dlon = (lon_destino - CEDIS_LON) * rad
    a = math.sin(dlat/2)**2 + math.cos(CEDIS_LAT*rad) * math.cos(lat_destino*rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distancia_lineal = 6371 * c
    return round(distancia_lineal * 1.35, 1) # Factor de desvío optimizado para Periférico Sur Oriente

# --- INICIALIZACIÓN DEL CATÁLOGO AUTOMÁTICO ---
if "directorio_completo_temisa" not in st.session_state:
    st.session_state.directorio_completo_temisa = [
        {"Cliente": "NYPRO", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Av. de la Corona 140, Parque Industrial Gdl, Zapopan, Jalisco", "Lat": 20.745, "Lon": -103.415},
        {"Cliente": "SAN ANGEL", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Av. Camino a San Isidro 450, Col. San Esteban, Zapopan, Jalisco", "Lat": 20.730, "Lon": -103.430},
        {"Cliente": "CARBOTECNIA", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Prolongación Laureles 320, Col. Sifón, Zapopan, Jalisco", "Lat": 20.720, "Lon": -103.400},
        {"Cliente": "O-I MEXICO", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Av. Aviación 4000, Col. San Juan de Ocotán, Zapopan, Jalisco", "Lat": 20.710, "Lon": -103.410},
        {"Cliente": "KASTO MOLINOS", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Calle Puerto Guaymas 315, Col. Miramar, Zapopan, Jalisco", "Lat": 20.750, "Lon": -103.390},
        {"Cliente": "EL SALTO 6", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Calle C No. 510, Zona Industrial El Salto, El Salto, Jalisco", "Lat": 20.520, "Lon": -103.250},
        {"Cliente": "EL SALTO 7", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Av. de la Pintura 1230, Parque Industrial El Salto, El Salto, Jalisco", "Lat": 20.525, "Lon": -103.245},
        {"Cliente": "USI", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Av. Prolongación Tepeyac 1020, Col. El Colli, Zapopan, Jalisco", "Lat": 20.680, "Lon": -103.440},
        {"Cliente": "INDUSTRIAS GDL SUR", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Calle 14 No. 2540, Zona Industrial, Guadalajara, Jalisco", "Lat": 20.655, "Lon": -103.360},
        {"Cliente": "CONVERTIDORA", "Dirección Completa (Calle, Número, Colonia, Municipio, Estado)": "Av. 8 de Julio 3400, Zona Industrial, Guadalajara, Jalisco", "Lat": 20.640, "Lon": -103.340}
    ]

if "flota" not in st.session_state:
    st.session_state.flota = [
        {"Transportista": "Sandra Melendres", "Tipo": "Plataforma", "Capacidad (TON)": 15.0, "Vel_Prom (km/h)": 45},
        {"Transportista": "Eduardo Melendres", "Tipo": "Camioneta", "Capacidad (TON)": 6.0, "Vel_Prom (km/h)": 55},
        {"Transportista": "SLI", "Tipo": "Camioneta", "Capacidad (TON)": 5.0, "Vel_Prom (km/h)": 55}
    ]

if "rutas_calculadas" not in st.session_state:
    st.session_state.rutas_calculadas = None

# --- PANEL DE EDICIÓN ---
with st.sidebar:
    st.header("⚙️ Catálogo Maestro")
    st.subheader("🗂️ Directorio de Clientes")
    st.caption("Escribe la dirección con el formato solicitado. El sistema detectará el Municipio automáticamente:")
    
    df_clientes_edit = st.data_editor(
        pd.DataFrame(st.session_state.directorio_completo_temisa),
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "Lat": st.column_config.NumberColumn("Lat (Opcional)", format="%.4f"),
            "Lon": st.column_config.NumberColumn("Lon (Opcional)", format="%.4f")
        },
        key="editor_completo_clientes",
        use_container_width=True
    )
    st.session_state.directorio_completo_temisa = df_clientes_edit.to_dict(orient="records")
    
    # Procesar base de datos
    CLIENTES_DB = {}
    for c in st.session_state.directorio_completo_temisa:
        if pd.notna(c["Cliente"]):
            nom_comercial = str(c["Cliente"]).upper().strip()
            direccion = str(c["Dirección Completa (Calle, Número, Colonia, Municipio, Estado)"]).upper()
            
            mun_detectado = "GUADALAJARA"
            for m_name in MUNICIPIOS_GEO.keys():
                if m_name in direccion:
                    mun_detectado = m_name
                    break
            
            lat_f = c["Lat"] if (pd.notna(c["Lat"]) and c["Lat"] != 0) else MUNICIPIOS_GEO[mun_detectado][0]
            lon_f = c["Lon"] if (pd.notna(c["Lon"]) and c["Lon"] != 0) else MUNICIPIOS_GEO[mun_detectado][1]
            
            CLIENTES_DB[nom_comercial] = {
                "Cliente": c["Cliente"],
                "Direccion": c["Dirección Completa (Calle, Número, Colonia, Municipio, Estado)"],
                "Municipio": mun_detectado,
                "Lat": lat_f,
                "Lon": lon_f,
                "KM": calcular_distancia_automatica(lat_f, lon_f)
            }
            
    lista_nombres_clientes = sorted(list(CLIENTES_DB.keys()))

    st.markdown("---")
    st.subheader("🚛 Rendimiento de Flota")
    df_flota_edit = st.data_editor(
        pd.DataFrame(st.session_state.flota),
        hide_index=True,
        key="editor_flota_completo",
        use_container_width=True
    )
    st.session_state.flota = df_flota_edit.to_dict(orient="records")

    if st.button("🔄 Forzar Reinicio y Actualizar Mapa"):
        del st.session_state.directorio_completo_temisa
        del st.session_state.rutas_calculadas
        st.rerun()

# --- PANTALLA PRINCIPAL: OPERACIONES ---
st.header("📋 Programación de Pedidos Diarios")
st.write(f"Despacho Centralizado: **{CEDIS_NOMBRE}**")

if "datos_pedidos" not in st.session_state:
    st.session_state.datos_pedidos = pd.DataFrame({
        "Cliente": ["EL SALTO 7", "EL SALTO 6", "USI", "CONVERTIDORA", "INDUSTRIAS GDL SUR"],
        "Toneladas": [12.0, 3.0, 5.0, 2.0, 3.5],
        "Inicio Carga CEDIS": [datetime.time(8, 0), datetime.time(8, 0), datetime.time(9, 0), datetime.time(10, 30), datetime.time(10, 30)],
        "Min. Carga CEDIS": [40, 25, 30, 20, 25],
        "Min. Descarga Cliente": [45, 30, 35, 20, 30],
        "Cierre Cliente": [datetime.time(13, 0), datetime.time(16, 0), datetime.time(15, 0), datetime.time(17, 0), datetime.time(14, 0)]
    })

df_captura = st.data_editor(
    st.session_state.datos_pedidos,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Cliente": st.column_config.SelectboxColumn("Elegir Cliente", options=lista_nombres_clientes, required=True),
        "Inicio Carga CEDIS": st.column_config.TimeColumn("Hora Carga TEMISA", format="hh:mm a"),
        "Cierre Cliente": st.column_config.TimeColumn("Cierre Almacén", format="hh:mm a"),
        "Min. Carga CEDIS": st.column_config.NumberColumn("Min. Carga", min_value=5, max_value=120, step=5),
        "Min. Descarga Cliente": st.column_config.NumberColumn("Min. Descarga", min_value=5, max_value=120, step=5),
        "Toneladas": st.column_config.NumberColumn("TON", format="%.1f", min_value=0.1)
    },
    key="editor_pedidos_completo"
)

st.markdown("---")
col_acc1, col_acc2 = st.columns(2)

with col_acc1:
    if st.button("⚡ CONSOLIDAR EMBARQUES Y CALCULAR TIEMPOS", type="primary", use_container_width=True):
        st.session_state.datos_pedidos = df_captura
        
        if df_captura.empty:
            st.error("Por favor registra al menos un pedido para simular.")
        else:
            pedidos_procesados = []
            for _, fila in df_captura.iterrows():
                nom = str(fila["Cliente"]).upper().strip() if pd.notna(fila["Cliente"]) else ""
                if nom in CLIENTES_DB:
                    pedidos_procesados.append({
                        "Cliente": nom,
                        "Direccion": CLIENTES_DB[nom]["Direccion"],
                        "Municipio": CLIENTES_DB[nom]["Municipio"],
                        "KM": CLIENTES_DB[nom]["KM"],
                        "TON": float(fila["Toneladas"]) if pd.notna(fila["Toneladas"]) else 1.0,
                        "Inicio_Carga": fila["Inicio Carga CEDIS"] if pd.notna(fila["Inicio Carga CEDIS"]) else datetime.time(8, 0),
                        "M_Carga": int(fila["Min. Carga CEDIS"]) if pd.notna(fila["Min. Carga CEDIS"]) else 30,
                        "M_Descarga": int(fila["Min. Descarga Cliente"]) if pd.notna(fila["Min. Descarga Cliente"]) else 30,
                        "Cierre": fila["Cierre Cliente"] if pd.notna(fila["Cierre Cliente"]) else datetime.time(17, 0)
                    })
            
            grupos_por_municipio = {}
            for p in pedidos_procesados:
                grupos_por_municipio.setdefault(p["Municipio"], []).append(p)
                
            flota_lista = sorted(st.session_state.flota, key=lambda x: x["Capacidad (TON)"], reverse=True)
            resultados_hoja = []
            unidades_en_uso = set()
            
            for mun, lista_p in grupos_por_municipio.items():
                lista_p = sorted(lista_p, key=lambda x: x["TON"], reverse=True)
                
                while lista_p:
                    viaje_actual = []
                    peso_viaje = 0.0
                    
                    for p in list(lista_p):
                        if peso_viaje + p["TON"] <= 15.0:
                            viaje_actual.append(p)
                            peso_viaje += p["TON"]
                            lista_p.remove(p)
                    
                    unid = flota_lista[-1]
                    for v in flota_lista:
                        if v["Capacidad (TON)"] >= peso_viaje and v["Transportista"] not in unidades_en_uso:
                            unid = v
                            break
                    
                    unidades_en_uso.add(unid["Transportista"])
                    
                    dt_b = datetime.date.today()
                    reloj = datetime.datetime.combine(dt_b, viaje_actual[0]["Inicio_Carga"])
                    
                    m_carga_total = sum([x["M_Carga"] for x in viaje_actual])
                    salida_cedis = reloj + datetime.timedelta(minutes=m_carga_total)
                    reloj = salida_cedis
                    
                    itinerario_texto = []
                    
                    for i, item in enumerate(viaje_actual):
                        v_km = unid["Vel_Prom (km/h)"]
                        dist_tramo = item["KM"] if i == 0 else abs(item["KM"] - viaje_actual[i-1]["KM"]) + 3
                        
                        t_viaje = int((dist_tramo / v_km) * 60)
                        arribo_c = reloj + datetime.timedelta(minutes=t_viaje)
                        salida_c = arribo_c + datetime.timedelta(minutes=item["M_Descarga"])
                        
                        limite = datetime.datetime.combine(dt_b, item["Cierre"])
                        estatus = "🟢 A Tiempo" if arribo_c <= limite else "🔴 Retrasado"
                        
                        itinerario_texto.append(f"{item['Cliente']} || Dir: {item['Direccion']} || Arribo: {arribo_c.strftime('%I:%M %p')} ({estatus})")
                        reloj = salida_c
                        
                    km_regreso = viaje_actual[-1]["KM"]
                    t_regreso = int((km_regreso / unid["Vel_Prom (km/h)"]) * 60)
                    retorno_base = reloj + datetime.timedelta(minutes=t_regreso)
                    
                    resultados_hoja.append({
                        "Unidad / Chofer": f"{unid['Transportista']} ({unid['Tipo']})",
                        "Ruta Municipio": mun,
                        "Clientes Consolidados": " ➡️ ".join([x["Cliente"] for x in viaje_actual]),
                        "Capacidad Utilizada": f"{peso_viaje:.1f} / {unid['Capacidad (TON)']} TON",
                        "Salida TEMISA": salida_cedis.strftime("%I:%M %p"),
                        "Hoja de Ruta (Direcciones Reales y Horarios)": " || ".join(itinerario_texto),
                        "Retorno Estimado TEMISA": retorno_base.strftime("%I:%M %p")
                    })
                    
            if resultados_hoja:
                st.session_state.rutas_calculadas = pd.DataFrame(resultados_hoja)
            else:
                st.error("Error al procesar la ruta.")

with col_acc2:
    if st.button("🗑️ Limpiar Plan Diario", use_container_width=True):
        st.session_state.rutas_calculadas = None
        st.rerun()

if st.session_state.rutas_calculadas is not None:
    st.markdown("---")
    st.header("📋 Plan Diario de Distribución Consolidada")
    st.dataframe(st.session_state.rutas_calculadas, use_container_width=True, hide_index=True)
