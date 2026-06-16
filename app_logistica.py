import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime

# Configuración de la página web local
st.set_page_config(page_title="Tablero Logístico Inteligente TEMISA", layout="wide")

st.title("🚚 Sistema de Planificación y Retorno Logístico - TEMISA")
st.write("Simulador avanzado de trayectos, ventanas horarias dinámicas y cálculo de tiempos de retorno al CEDIS.")

# --- BASE DE DATOS GEOGRÁFICA DE CLIENTES ---
CLIENTES_DB = {
    "NYPRO": {"lat": 20.745, "lon": -103.415, "zona": "Zapopan Norte", "dist_km": 24.5},
    "SAN ANGEL": {"lat": 20.730, "lon": -103.430, "zona": "Zapopan Norte", "dist_km": 22.0},
    "CARBOTECNIA": {"lat": 20.720, "lon": -103.400, "zona": "Zapopan Norte", "dist_km": 20.5},
    "O-I MEXICO": {"lat": 20.710, "lon": -103.410, "zona": "Zapopan Norte", "dist_km": 19.8},
    "KASTO MOLINOS": {"lat": 20.750, "lon": -103.390, "zona": "Zapopan Norte", "dist_km": 25.0},
    "EL SALTO 6": {"lat": 20.520, "lon": -103.250, "zona": "El Salto", "dist_km": 21.0},
    "EL SALTO 7": {"lat": 20.525, "lon": -103.245, "zona": "El Salto", "dist_km": 22.3},
    "USI": {"lat": 20.680, "lon": -103.440, "zona": "Periférico Poniente", "dist_km": 15.2},
    "INDUSTRIAS GDL SUR": {"lat": 20.655, "lon": -103.360, "zona": "Urbana Sur", "dist_km": 8.5},
    "CONVERTIDORA": {"lat": 20.640, "lon": -103.340, "zona": "Urbana Sur", "dist_km": 9.2}
}

CEDIS_NOMBRE = "TEMISA (Periférico Sur 6000, San Pedro Tlaquepaque, Jal.)"
CEDIS_LAT, CEDIS_LON = 20.615, -103.385

# --- INICIALIZACIÓN DE LA MEMORIA (SESSION STATE) ---
if "flota" not in st.session_state:
    st.session_state.flota = [
        {"Transportista": "Sandra Melendres", "Tipo": "Plataforma", "Capacidad (TON)": 15.0, "Vel_Prom (km/h)": 45},
        {"Transportista": "Eduardo Melendres", "Tipo": "Camioneta", "Capacidad (TON)": 6.0, "Vel_Prom (km/h)": 60},
        {"Transportista": "SLI", "Tipo": "Camioneta", "Capacidad (TON)": 5.0, "Vel_Prom (km/h)": 60}
    ]

if "resultado_calculado" not in st.session_state:
    st.session_state.resultado_calculado = None

# --- MENÚ LATERAL IZQUIERDO (SIDEBAR): CONTROL TOTAL DE FLOTA Y VELOCIDADES ---
with st.sidebar:
    st.header("⚙️ Configuración de Flota")
    st.write("Edita las capacidades o las velocidades promedio estimadas para hoy.")
    
    df_flota_base = pd.DataFrame(st.session_state.flota)
    df_flota_editable = st.data_editor(
        df_flota_base, 
        hide_index=True, 
        use_container_width=True,
        column_config={
            "Vel_Prom (km/h)": st.column_config.NumberColumn("Vel (km/h)", min_value=10, max_value=110, step=5),
            "Capacidad (TON)": st.column_config.NumberColumn("Cap (TON)", min_value=0.5, max_value=40.0, format="%.1f")
        },
        key="editor_flota_velocidades"
    )
    st.session_state.flota = df_flota_editable.to_dict(orient="records")
    
    with st.form("formulario_flota", clear_on_submit=True):
        st.write("**Añadir Unidad Nueva**")
        nuevo_nombre = st.text_input("Nombre del Operador:")
        nuevo_tipo = st.selectbox("Tipo de Unidad:", ["Camioneta", "Torton", "Plataforma", "Tráiler"])
        nueva_capacidad = st.number_input("Capacidad (TON):", min_value=0.1, max_value=40.0, value=5.0, step=0.5)
        nueva_vel = st.number_input("Velocidad Estimada (km/h):", min_value=10, max_value=110, value=55, step=5)
        btn_guardar_flota = st.form_submit_button("💾 Guardar en Flota")
        
        if btn_guardar_flota:
            if nuevo_nombre:
                st.session_state.flota.append({
                    "Transportista": nuevo_nombre, "Tipo": nuevo_tipo, "Capacidad (TON)": nueva_capacidad, "Vel_Prom (km/h)": nueva_vel
                })
                st.success(f"¡{nuevo_nombre} agregado!")
                st.rerun()

    if st.sidebar.button("🔄 Reiniciar Flota Original"):
        del st.session_state.flota
        st.session_state.resultado_calculado = None
        st.rerun()

    st.header("🏢 Origen Fijo")
    st.caption(f"`{CEDIS_NOMBRE}`")

# --- PANTALLA PRINCIPAL: MATRIZ DE CAPTURA CON MINUTOS DE DESCARGA ---
st.header("📋 Matriz de Pedidos, Horarios y Tiempos en Cliente")
st.write(f"**Punto de Partida Restringido:** Origen de Carga en `{CEDIS_NOMBRE}`")

if "datos_pedidos" not in st.session_state:
    st.session_state.datos_pedidos = pd.DataFrame({
        "Cliente": ["EL SALTO 7", "EL SALTO 6", "USI", "NYPRO", "CONVERTIDORA", "INDUSTRIAS GDL SUR"],
        "Toneladas": [15.0, 6.0, 10.0, 5.0, 2.5, 10.0],
        "Zona": ["El Salto", "El Salto", "Periférico Poniente", "Zapopan Norte", "Urbana Sur", "Urbana Sur"],
        "Inicio Carga CEDIS": [datetime.time(8, 0), datetime.time(8, 0), datetime.time(11, 30), datetime.time(8, 30), datetime.time(13, 0), datetime.time(10, 0)],
        "Min. Carga CEDIS": [40, 30, 35, 25, 20, 45],
        "Min. Descarga Cliente": [45, 30, 40, 20, 15, 40],
        "Cierre Cliente": [datetime.time(13, 0), datetime.time(17, 0), datetime.time(14, 30), datetime.time(17, 0), datetime.time(16, 0), datetime.time(12, 0)]
    })

df_captura = st.data_editor(
    st.session_state.datos_pedidos,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "Inicio Carga CEDIS": st.column_config.TimeColumn("Inicio Carga", format="hh:mm a"),
        "Cierre Cliente": st.column_config.TimeColumn("Hora Cierre", format="hh:mm a"),
        "Min. Carga CEDIS": st.column_config.NumberColumn("Min. Carga", min_value=5, max_value=180, step=5),
        "Min. Descarga Cliente": st.column_config.NumberColumn("Min. Descarga", min_value=5, max_value=180, step=5),
        "Toneladas": st.column_config.NumberColumn("TON", format="%.1f")
    },
    key="editor_pedidos_estabilizado"
)

# --- PROCESAMIENTO LOGÍSTICO COMPLETO ---
st.markdown("---")
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("⚡ OPTIMIZAR Y SIMULAR TIEMPOS COMPLETOS", type="primary", use_container_width=True):
        st.session_state.datos_pedidos = df_captura
        
        if df_captura.empty:
            st.error("La tabla de pedidos está vacía.")
        else:
            registros_tabla = []
            lista_flota_actual = st.session_state.flota
            
            for _, fila in df_captura.iterrows():
                if pd.isna(fila["Cliente"]) or str(fila["Cliente"]).strip() == "":
                    continue
                    
                cliente = str(fila["Cliente"]).upper().strip()
                ton_pedido = float(fila["Toneladas"]) if not pd.isna(fila["Toneladas"]) else 1.0
                zona = str(fila["Zona"]) if not pd.isna(fila["Zona"]) else "ZMG Central"
                h_inicio_carga = fila["Inicio Carga CEDIS"] if pd.notna(fila["Inicio Carga CEDIS"]) else datetime.time(8, 0)
                m_carga = int(fila["Min. Carga CEDIS"]) if not pd.isna(fila["Min. Carga CEDIS"]) else 30
                m_descarga = int(fila["Min. Descarga Cliente"]) if not pd.isna(fila["Min. Descarga Cliente"]) else 30
                h_cierre = fila["Cierre Cliente"] if pd.notna(fila["Cierre Cliente"]) else datetime.time(17, 0)
                
                if ton_pedido >= 12.0:
                    unid = next((f for f in lista_flota_actual if f["Capacidad (TON)"] >= 15.0), lista_flota_actual[0])
                elif ton_pedido >= 6.0:
                    unid = next((f for f in lista_flota_actual if f["Capacidad (TON)"] == 6.0), lista_flota_actual[1])
                else:
                    unid = lista_flota_actual[-1]
                    
                velocidad_usuario = float(unid["Vel_Prom (km/h)"])
                
                datos_geo = CLIENTES_DB.get(cliente, {"dist_km": 15.0})
                distancia = datos_geo["dist_km"]
                
                factor_trafico = 1.20 if unid["Tipo"] == "Plataforma" else 1.0
                tiempo_trayecto_ida = int((distancia / velocidad_usuario) * 60 * factor_trafico)
                tiempo_trayecto_regreso = int((distancia / velocidad_usuario) * 60)
                
                dt_base = datetime.date.today()
                
                comb_inicio_carga = datetime.datetime.combine(dt_base, h_inicio_carga)
                comb_salida_cedis = comb_inicio_carga + datetime.timedelta(minutes=m_carga)
                
                comb_arribo_cliente = comb_salida_cedis + datetime.timedelta(minutes=tiempo_trayecto_ida)
                comb_fin_descarga = comb_arribo_cliente + datetime.timedelta(minutes=m_descarga)
                
                comb_regreso_cedis = comb_fin_descarga + datetime.timedelta(minutes=tiempo_trayecto_regreso)
                
                h_salida_real = comb_salida_cedis.time()
                h_arribo_real = comb_arribo_cliente.time()
                h_regreso_est = comb_regreso_cedis.time()
                
                comb_limite = datetime.datetime.combine(dt_base, h_cierre)
                margen_tiempo = (comb_limite - comb_arribo_cliente).total_seconds() / 60.0
                
                if margen_tiempo > 45:
                    probabilidad = "98%"
                    semaforo = "🟢 Óptimo"
                elif margen_tiempo >= 15:
                    probabilidad = "85%"
                    semaforo = "🟡 Precaución"
                elif margen_tiempo >= 0:
                    probabilidad = "60%"
                    semaforo = "🟠 Riesgo Alto"
                else:
                    probabilidad = "5%"
                    semaforo = "🔴 Rechazo"
                    
                registros_tabla.append({
                    "Operador": f"{unid['Transportista']} ({unid['Tipo']})",
                    "Cliente": cliente,
                    "Carga": f"{ton_pedido} TON",
                    "Vel. Usada": f"{velocidad_usuario} km/h",
                    "Salida TEMISA": h_salida_real.strftime("%I:%M %p"),
                    "Ida": f"{tiempo_trayecto_ida} min",
                    "Arribo Cliente": h_arribo_real.strftime("%I:%M %p"),
                    "Cierre Ventana": h_cierre.strftime("%I:%M %p"),
                    "Semaforo": semaforo,
                    "Prob.": probabilidad,
                    "Descarga": f"{m_descarga} min",
                    "Regreso": f"{tiempo_trayecto_regreso} min",
                    "Retorno Base TEMISA": h_regreso_est.strftime("%I:%M %p")
                })
                
            if registros_tabla:
                st.session_state.resultado_calculado = pd.DataFrame(registros_tabla)
            else:
                st.error("Error al procesar los datos.")

with col_btn2:
    if st.button("🗑️ Limpiar Resultados", use_container_width=True):
        st.session_state.resultado_calculado = None
        st.rerun()

# --- TABLERO DE RESULTADOS ---
if st.session_state.resultado_calculado is not None:
    st.success("📊 Simulación Logística y Horarios de Retorno Calculados")
    
    st.markdown("### 🚦 Significado del Semáforo de Cumplimiento:")
    col1, col2, col3, col4 = st.columns(4)
    col1.info("🟢 **Óptimo (98%)**: El camión llega con más de 45 minutos de colchón antes del cierre.")
    col2.warning("🟡 **Precaución (85%)**: Colchón seguro de entre 15 y 45 minutos contra la ventana.")
    col3.error("🟠 **Riesgo Alto (60%)**: Margen menor a 15 minutos. Cualquier bache o tráfico causará retraso.")
    # LA LÍNEA DE ABAJO YA TIENE EL NOMBRE CORRECTO: unsafe_allow_html
    col4.markdown("<div style='background-color:#ffcccc; padding:10px; border-radius:5px; color:#cc0000;'><b>🔴 Rechazo (5%)</b>: La hora de arribo estimada supera el horario de cierre de almacén.</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.header("📈 Hoja de Ruta Consolidada del Día")
    st.dataframe(st.session_state.resultado_calculado, use_container_width=True, hide_index=True)
    
    st.header("🗺️ Mapa Metropolitano Operativo (Origen: TEMISA)")
    m = folium.Map(location=[20.65, -103.35], zoom_start=11)
    
    folium.Marker([CEDIS_LAT, CEDIS_LON], popup=f"<b>CEDIS MATRIZ:</b><br>{CEDIS_NOMBRE}", icon=folium.Icon(color="red", icon="home")).add_to(m)
    
    for _, fila in df_captura.iterrows():
        if pd.isna(fila["Cliente"]) or str(fila["Cliente"]).strip() == "":
            continue
        nom = str(fila["Cliente"]).upper().strip()
        if nom in CLIENTES_DB:
            coords = CLIENTES_DB[nom]
            folium.Marker(
                [coords["lat"], coords["lon"]], 
                popup=f"<b>CLIENTE: {nom}</b><br>Volumen: {fila['Toneladas']} TON", 
                icon=folium.Icon(color="blue", icon="truck")
            ).add_to(m)
            
    st_folium(m, width=1300, height=500, key="mapa_final_temisa")