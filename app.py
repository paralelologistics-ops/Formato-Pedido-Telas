import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURACIÓN DE SEGURIDAD (TUS DATOS) ---
API_KEY = "AIzaSyBipSMJcc_hwiQ-ATlt-mf2YUcG2_Q8uEc" 
FOLDER_ID = "17RIBmFQcEqZDZRWouTGsaNTOHQ2b--PG" 

# --- FUNCIÓN PARA LEER TUS ESTAMPADOS DE DRIVE ---
def obtener_estampados():
    try:
        # Consultamos a Google por los archivos en tu carpeta
        url = f"https://www.googleapis.com/drive/v3/files?q='{FOLDER_ID}'+in+parents+and+trashed=false&key={API_KEY}"
        res = requests.get(url).json()
        files = res.get('files', [])
        # Retorna una lista de nombres de tus imágenes
        return {f['name']: f['id'] for f in files}
    except Exception as e:
        return {"Error al cargar": ""}

# --- CARGAR TU ARCHIVO DE TELAS (EL BUSCARV) ---
@st.cache_data
def cargar_telas():
    # Asegúrate de que el archivo se llame exactamente así en GitHub
    df = pd.read_csv('Formato Pedido Telas - TELAS.csv')
    # Limpiar nombres por si hay espacios
    df['REF DE TELAS'] = df['REF DE TELAS'].str.strip()
    return df

# --- DISEÑO DE LA APLICACIÓN ---
st.set_page_config(page_title="Pedido Telas Paralelo", layout="wide")
st.title("🏭 Generador de Pedido de Telas")

df_telas = cargar_telas()
dict_fotos = obtener_estampados()

# Encabezado del Formulario
with st.expander("Información del Proveedor", expanded=True):
    c_prov1, c_prov2 = st.columns(2)
    with c_prov1:
        proveedor = st.text_input("Proveedor", "Farides Lino")
        direccion = st.text_input("Dirección", "Cra 53 ·75-125")
    with c_prov2:
        telefono = st.text_input("Teléfono", "3015664200")
        fecha_pedido = datetime.now().strftime("%d/%m/%Y")
        st.write(f"**Fecha:** {fecha_pedido}")

st.divider()

# Sección para agregar productos
col_tela, col_cant, col_img = st.columns([2, 1, 2])

with col_tela:
    tela_sel = st.selectbox("1. Escoge la Tela", df_telas['REF DE TELAS'].unique())
    # FÓRMULA BUSCARV: Obtener el precio automáticamente
    precio_unidad = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, 'PRECIO X METRO'].values[0]
    st.info(f"Costo por metro: ${precio_unidad:,.0f}")

with col_cant:
    cantidad_mts = st.number_input("2. Cantidad (mts)", min_value=0.0, step=0.1, value=1.0)

with col_img:
    diseno_sel = st.selectbox("3. Escoge el Estampado", ["Seleccione..."] + list(dict_fotos.keys()))
    if diseno_sel != "Seleccione...":
        id_imagen = dict_fotos[diseno_sel]
        # Mostramos la imagen de Drive en tiempo real
        st.image(f"https://drive.google.com/uc?id={id_imagen}", width=150, caption="Diseño seleccionado")

# Botón para añadir a la lista
if st.button("➕ Agregar al Pedido"):
    if "carrito" not in st.session_state:
        st.session_state.carrito = []
    
    st.session_state.carrito.append({
        "Tela": tela_sel,
        "Costo Metro": precio_unidad,
        "Cantidad": cantidad_mts,
        "Diseño": diseno_sel if diseno_sel != "Seleccione..." else "Sin diseño",
        "Total": precio_unidad * cantidad_mts
    })

# --- MOSTRAR EL PEDIDO Y TUS FÓRMULAS ---
if "carrito" in st.session_state and len(st.session_state.carrito) > 0:
    df_pedido = pd.DataFrame(st.session_state.carrito)
    st.subheader("Resumen del Pedido")
    st.table(df_pedido)

    # APLICANDO TUS FÓRMULAS DE EXCEL:
    
    # 1. Tela Adicional Mallatex: =SI(SUMAPRODUCTO(--(C18:C30 = "Mallatex")) > 0; 1; "")
    hay_mallatex = 1 if "Mallatex" in df_pedido['Tela'].values else ""
    
    # 2. Tela Adicional Drill: =SI(SUMAPRODUCTO(--REGEXMATCH(C18:C31; "Drill Denim o Jean")) > 0; 1; "")
    hay_drill = 1 if df_pedido['Tela'].str.contains("Drill Denim o Jean").any() else ""
    
    # 3. Sublimación: (Suma cantidades excepto los excluidos)
    excluidos = [
        "Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", 
        "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", 
        "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"
    ]
    total_sublimacion = df_pedido[~df_pedido['Tela'].isin(excluidos)]['Cantidad'].sum()

    # Mostrar resultados automáticos
    st.sidebar.header("Cálculos Automáticos")
    st.sidebar.write(f"**Tela Adicional Mallatex:** {hay_mallatex}")
    st.sidebar.write(f"**Tela Adicional Drill:** {hay_drill}")
    st.sidebar.write(f"**Total Sublimación (mts):** {total_sublimacion}")
    st.sidebar.divider()
    st.sidebar.subheader(f"TOTAL: ${df_pedido['Total'].sum():,.0f}")

    if st.sidebar.button("🗑️ Borrar Todo"):
        st.session_state.carrito = []
        st.rerun()
