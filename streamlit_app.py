import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN ---
API_KEY = "AIzaSyBipSMJcc_hwiQ-ATlt-mf2YUcG2_Q8uEc"
FOLDER_ID = "17RIBmFQcEqZDZRWouTGsaNTOHQ2b--PG"

def obtener_estampados():
    try:
        url = f"https://www.googleapis.com/drive/v3/files?q='{FOLDER_ID}'+in+parents+and+trashed=false&key={API_KEY}"
        res = requests.get(url).json()
        return {f['name']: f['id'] for f in res.get('files', [])}
    except:
        return {}

@st.cache_data
def cargar_telas():
    df = pd.read_csv('telas.csv')
    df.columns = df.columns.str.strip()
    return df

# --- INICIO DE LA APP ---
st.set_page_config(page_title="Pedido Paralelo Pro", layout="wide")
st.title("🏭 Generador de Pedidos de Telas")

df_telas = cargar_telas()
dict_fotos = obtener_estampados()

if "carrito" not in st.session_state:
    st.session_state.carrito = []

# --- FORMULARIO DE ENTRADA ---
with st.container():
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        tela_sel = st.selectbox("Seleccione Tela", df_telas['REF DE TELAS'].unique())
        # BUSCARV en columna 'sin sublimar'
        precio_unidad = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, 'sin sublimar'].values[0]
        st.metric("Precio (Sin Sublimar)", f"${precio_unidad:,.0f}")

    with col2:
        cant = st.number_input("Cantidad (mts)", min_value=0.1, step=0.1, value=1.0)

    with col3:
        diseno_sel = st.selectbox("Estampado", ["Ninguno"] + list(dict_fotos.keys()))
        id_img = dict_fotos.get(diseno_sel, None)
        if id_img:
            img_url = f"https://drive.google.com/uc?id={id_img}"
            st.image(img_url, width=120)

    if st.button("🚀 Agregar al Pedido"):
        st.session_state.carrito.append({
            "Tela": tela_sel,
            "Costo": precio_unidad,
            "Cant": cant,
            "Diseño": diseno_sel,
            "ID_Img": id_img,
            "Total": precio_unidad * cant
        })

# --- TABLA Y LÓGICA DE ADICIONALES ---
if st.session_state.carrito:
    df_temp = pd.DataFrame(st.session_state.carrito)
    
    # 1. Adicional Mallatex
    hay_mallatex = 1 if "Mallatex" in df_temp['Tela'].values else 0
    # 2. Adicional Drill
    hay_drill = 1 if df_temp['Tela'].str.contains("Drill Denim o Jean").any() else 0
    # 3. Total Sublimación (Excluyendo los de tu lista)
    excluidos = ["Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"]
    total_subli_mts = df_temp[~df_temp['Tela'].isin(excluidos)]['Cant'].sum()

    st.subheader("Resumen actual")
    st.table(df_temp[['Tela', 'Cant', 'Costo', 'Diseño', 'Total']])

    if st.button("🗑️ Borrar último producto"):
        st.session_state.carrito.pop()
        st.rerun()

    # --- BOTÓN PARA GENERAR PDF ---
    if st.button("💾 Generar y Descargar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "SOLICITUD DE PEDIDO - PARALELO", ln=True, align="C")
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 7, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.ln(5)

        # Encabezados
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(50, 8, "Tela", 1, 0, "C", True)
        pdf.cell(20, 8, "Cant", 1, 0, "C", True)
        pdf.cell(30, 8, "Precio Unit", 1, 0, "C", True)
        pdf.cell(50, 8, "Diseño", 1, 0, "C", True)
        pdf.cell(35, 8, "Total", 1, 1, "C", True)

        pdf.set_font("Arial", "", 9)
        subtotal_productos = 0
        
        # Productos agregados
        for item in st.session_state.carrito:
            pdf.cell(50, 10, item['Tela'], 1)
            pdf.cell(20, 10, f"{item['Cant']}", 1, 0, "C")
            pdf.cell(30, 10, f"${item['Costo']:,.0f}", 1, 0, "R")
            pdf.cell(50, 10, item['Diseño'][:25], 1)
            pdf.cell(35, 10, f"${item['Total']:,.0f}", 1, 1, "R")
            subtotal_productos += item['Total']

        # 4-5 Líneas en blanco para espacio
        for _ in range(5):
            pdf.cell(50, 8, "", 1)
            pdf.cell(20, 8, "", 1)
            pdf.cell(30, 8, "", 1)
            pdf.cell(50, 8, "", 1)
            pdf.cell(35, 8, "", 1, 1)

        # Filas de Adicionales
        pdf.set_font("Arial", "B", 9)
        
        # Fila Mallatex
        pdf.cell(150, 8, "Adicional Mallatex (Flag)", 1, 0, "R")
        pdf.cell(35, 8, str(hay_mallatex), 1, 1, "R")
        
        # Fila Drill
        pdf.cell(150, 8, "Adicional Drill (Flag)", 1, 0, "R")
        pdf.cell(35, 8, str(hay_drill), 1, 1, "R")
        
        # Fila Total Sublimación
        pdf.cell(150, 8, "Total Metros Sublimación", 1, 0, "R")
        pdf.cell(35, 8, f"{total_subli_mts} mts", 1, 1, "R")

        # GRAN TOTAL
        pdf.ln(2)
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(150, 10, "GRAN TOTAL DEL PEDIDO", 1, 0, "R", True)
        pdf.cell(35, 10, f"${subtotal_productos:,.0f}", 1, 1, "R", True)

        # Salida del PDF corregida
        pdf_bytes = pdf.output() 
        st.download_button(
            label="⬇️ Descargar PDF de Pedido",
            data=pdf_bytes,
            file_name=f"Pedido_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf"
        )
