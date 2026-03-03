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
    df.columns = df.columns.str.strip() # Limpia espacios en los nombres de columnas
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
        # IMPORTANTE: Usamos la columna 'sin sublimar' como pediste
        try:
            precio_unidad = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, 'sin sublimar'].values[0]
        except KeyError:
            st.error("No se encontró la columna 'sin sublimar' en el CSV. Revisa el encabezado.")
            precio_unidad = 0
            
        st.metric("Precio Base (Sin Sublimar)", f"${precio_unidad:,.0f}")

    with col2:
        cant = st.number_input("Cantidad (mts)", min_value=0.1, step=0.1, value=1.0)

    with col3:
        diseno_sel = st.selectbox("Estampado", ["Ninguno"] + list(dict_fotos.keys()))
        id_img = dict_fotos.get(diseno_sel, None)
        if id_img:
            img_url = f"https://drive.google.com/uc?id={id_img}"
            st.image(img_url, width=100)

    if st.button("🚀 Agregar al Pedido"):
        st.session_state.carrito.append({
            "Tela": tela_sel,
            "Costo": precio_unidad,
            "Cant": cant,
            "Diseño": diseno_sel,
            "ID_Img": id_img,
            "Total": precio_unidad * cant
        })

# --- LÓGICA DE CÁLCULO Y PDF ---
if st.session_state.carrito:
    df_temp = pd.DataFrame(st.session_state.carrito)
    
    # 1. Cálculos de Adicionales
    hay_mallatex = 1 if "Mallatex" in df_temp['Tela'].values else 0
    hay_drill = 1 if df_temp['Tela'].str.contains("Drill Denim o Jean").any() else 0
    
    excluidos = ["Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"]
    total_subli_mts = df_temp[~df_temp['Tela'].isin(excluidos)]['Cant'].sum()

    st.subheader("Productos en el carrito")
    st.table(df_temp[['Tela', 'Cant', 'Costo', 'Diseño', 'Total']])

    if st.button("🗑️ Borrar último ítem"):
        st.session_state.carrito.pop()
        st.rerun()

    if st.button("📝 Preparar PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "SOLICITUD DE PEDIDO - PARALELO", ln=True, align="C")
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 7, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        pdf.ln(5)

        # Encabezados de Tabla
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(50, 8, "DESCRIPCION TELA", 1, 0, "C", True)
        pdf.cell(15, 8, "CANT", 1, 0, "C", True)
        pdf.cell(25, 8, "PRECIO U.", 1, 0, "C", True)
        pdf.cell(45, 8, "ESTAMPADO", 1, 0, "C", True)
        pdf.cell(20, 8, "IMAGEN", 1, 0, "C", True)
        pdf.cell(30, 8, "TOTAL", 1, 1, "C", True)

        pdf.set_font("Arial", "", 8)
        suma_productos = 0

        # Dibujar Productos con Imagen
        for item in st.session_state.carrito:
            x_start = pdf.get_x()
            y_start = pdf.get_y()
            
            pdf.cell(50, 15, item['Tela'], 1)
            pdf.cell(15, 15, str(item['Cant']), 1, 0, "C")
            pdf.cell(25, 15, f"${item['Costo']:,.0f}", 1, 0, "R")
            pdf.cell(45, 15, item['Diseño'][:25], 1)
            
            # Espacio para Imagen
            x_img = pdf.get_x()
            pdf.cell(20, 15, "", 1) 
            if item['ID_Img']:
                try:
                    img_data = requests.get(f"https://drive.google.com/uc?id={item['ID_Img']}").content
                    img_file = BytesIO(img_data)
                    pdf.image(img_file, x=x_img+2, y=y_start+2, w=11)
                except:
                    pass
            
            pdf.cell(30, 15, f"${item['Total']:,.0f}", 1, 1, "R")
            suma_productos += item['Total']

        # --- LAS 5 LÍNEAS EN BLANCO ---
        pdf.ln(2)
        for _ in range(5):
            pdf.cell(50, 6, "", 1)
            pdf.cell(15, 6, "", 1)
            pdf.cell(25, 6, "", 1)
            pdf.cell(45, 6, "", 1)
            pdf.cell(20, 6, "", 1)
            pdf.cell(30, 6, "", 1, 1)

        # --- SECCIÓN DE ADICIONALES (Mismo formato de tabla) ---
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(245, 245, 245)
        
        # Fila Mallatex
        pdf.cell(135, 8, "ADICIONAL MALLATEX", 1, 0, "R", True)
        pdf.cell(20, 8, "-", 1, 0, "C", True)
        pdf.cell(30, 8, str(hay_mallatex), 1, 1, "R", True)
        
        # Fila Drill
        pdf.cell(135, 8, "ADICIONAL DRILL", 1, 0, "R", True)
        pdf.cell(20, 8, "-", 1, 0, "C", True)
        pdf.cell(30, 8, str(hay_drill), 1, 1, "R", True)
        
        # Fila Sublimación
        pdf.cell(135, 8, "TOTAL METROS A SUBLIMAR (DESPERDICIO)", 1, 0, "R", True)
        pdf.cell(20, 8, f"{total_subli_mts} m", 1, 0, "C", True)
        pdf.cell(30, 8, "CÁLCULO INTERNO", 1, 1, "R", True)

        # --- GRAN TOTAL FINAL ---
        pdf.ln(3)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(180, 200, 255)
        pdf.cell(155, 10, "VALOR TOTAL DEL PEDIDO", 1, 0, "R", True)
        pdf.cell(30, 10, f"${suma_productos:,.0f}", 1, 1, "R", True)

        # SOLUCIÓN AL ERROR: Convertir a bytes explícitamente
        pdf_bytes = pdf.output()
        if isinstance(pdf_bytes, bytearray):
            pdf_bytes = bytes(pdf_bytes)

        st.download_button(
            label="⬇️ Descargar PDF Final",
            data=pdf_bytes,
            file_name="Solicitud_Pedido_Paralelo.pdf",
            mime="application/pdf"
        )
