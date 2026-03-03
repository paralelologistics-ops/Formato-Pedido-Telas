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

# --- CONFIGURACIÓN DE COSTOS ADICIONALES (En el Sidebar) ---
st.sidebar.header("Configuración de Precios Adicionales")
p_mallatex = st.sidebar.number_input("Costo Adicional Mallatex ($)", value=0)
p_drill = st.sidebar.number_input("Costo Adicional Drill ($)", value=0)
p_sublimacion = st.sidebar.number_input("Costo Servicio Sublimación ($/mt)", value=0)

if "carrito" not in st.session_state:
    st.session_state.carrito = []

# --- FORMULARIO DE ENTRADA ---
with st.container():
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        tela_sel = st.selectbox("Seleccione Tela", df_telas['REF DE TELAS'].unique())
        precio_unidad = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, 'sin sublimar'].values[0]
        st.metric("Precio Base (Sin Sublimar)", f"${precio_unidad:,.0f}")

    with col2:
        cant = st.number_input("Cantidad (mts)", min_value=0.1, step=0.1, value=1.0)

    with col3:
        # Mejora: Opción "Lisa (sin sublimar)" añadida
        opciones_diseno = ["Lisa (sin sublimar)", "Ninguno"] + list(dict_fotos.keys())
        diseno_sel = st.selectbox("Estampado", opciones_diseno)
        
        id_img = dict_fotos.get(diseno_sel, None)
        # Si es Lisa, no mostramos imagen
        if id_img and diseno_sel != "Lisa (sin sublimar)":
            img_url = f"https://drive.google.com/uc?id={id_img}"
            st.image(img_url, width=100)

    if st.button("🚀 Agregar al Pedido"):
        st.session_state.carrito.append({
            "Tela": tela_sel,
            "Costo": precio_unidad,
            "Cant": cant,
            "Diseño": diseno_sel,
            "ID_Img": id_img if diseno_sel != "Lisa (sin sublimar)" else None,
            "Total": precio_unidad * cant
        })

# --- LÓGICA DE CÁLCULO Y PDF ---
if st.session_state.carrito:
    df_temp = pd.DataFrame(st.session_state.carrito)
    
    # Cálculos lógicos para adicionales
    val_mallatex = 1 if "Mallatex" in df_temp['Tela'].values else 0
    val_drill = 1 if df_temp['Tela'].str.contains("Drill Denim o Jean").any() else 0
    
    excluidos = ["Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"]
    # Los metros a sublimar solo cuentan si el diseño NO es "Lisa (sin sublimar)" o "Ninguno"
    total_subli_mts = df_temp[~df_temp['Tela'].isin(excluidos) & ~df_temp['Diseño'].isin(["Lisa (sin sublimar)", "Ninguno"])]['Cant'].sum()

    st.subheader("Productos en el carrito")
    st.table(df_temp[['Tela', 'Cant', 'Costo', 'Diseño', 'Total']])

    if st.button("🗑️ Borrar último ítem"):
        st.session_state.carrito.pop()
        st.rerun()

    if st.button("📝 Generar PDF con Adicionales"):
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
        pdf.cell(60, 8, "DESCRIPCION TELA", 1, 0, "C", True)
        pdf.cell(15, 8, "CANT", 1, 0, "C", True)
        pdf.cell(25, 8, "PRECIO U.", 1, 0, "C", True)
        pdf.cell(35, 8, "ESTAMPADO", 1, 0, "C", True)
        pdf.cell(20, 8, "IMAGEN", 1, 0, "C", True)
        pdf.cell(30, 8, "TOTAL", 1, 1, "C", True)

        pdf.set_font("Arial", "", 8)
        total_acumulado = 0

        # 1. PRODUCTOS PEDIDOS
        for item in st.session_state.carrito:
            y_start = pdf.get_y()
            pdf.cell(60, 12, item['Tela'], 1)
            pdf.cell(15, 12, str(item['Cant']), 1, 0, "C")
            pdf.cell(25, 12, f"${item['Costo']:,.0f}", 1, 0, "R")
            pdf.cell(35, 12, item['Diseño'][:20], 1)
            
            # Imagen
            x_img = pdf.get_x()
            pdf.cell(20, 12, "", 1)
            if item['ID_Img']:
                try:
                    img_data = requests.get(f"https://drive.google.com/uc?id={item['ID_Img']}").content
                    pdf.image(BytesIO(img_data), x=x_img+4, y=y_start+2, w=12)
                except: pass
            
            pdf.cell(30, 12, f"${item['Total']:,.0f}", 1, 1, "R")
            total_acumulado += item['Total']

        # 2. ESPACIO EN BLANCO (5 líneas)
        for _ in range(5):
            pdf.cell(60, 6, "", 1)
            pdf.cell(15, 6, "", 1)
            pdf.cell(25, 6, "", 1)
            pdf.cell(35, 6, "", 1)
            pdf.cell(20, 6, "", 1)
            pdf.cell(30, 6, "", 1, 1)

        # 3. FILAS DE ADICIONALES (Con la lógica pedida)
        pdf.set_font("Arial", "B", 8)
        
        # Fila Mallatex
        tot_malla = val_mallatex * p_mallatex
        pdf.cell(60, 8, "ADICIONAL MALLATEX", 1)
        pdf.cell(15, 8, str(val_mallatex), 1, 0, "C")
        pdf.cell(25, 8, f"${p_mallatex:,.0f}", 1, 0, "R")
        pdf.cell(35, 8, "-", 1)
        pdf.cell(20, 8, "-", 1)
        pdf.cell(30, 8, f"${tot_malla:,.0f}", 1, 1, "R")
        total_acumulado += tot_malla

        # Fila Drill
        tot_drill = val_drill * p_drill
        pdf.cell(60, 8, "ADICIONAL DRILL", 1)
        pdf.cell(15, 8, str(val_drill), 1, 0, "C")
        pdf.cell(25, 8, f"${p_drill:,.0f}", 1, 0, "R")
        pdf.cell(35, 8, "-", 1)
        pdf.cell(20, 8, "-", 1)
        pdf.cell(30, 8, f"${tot_drill:,.0f}", 1, 1, "R")
        total_acumulado += tot_drill

        # Fila Sublimación
        tot_subli = total_subli_mts * p_sublimacion
        pdf.cell(60, 8, "TOTAL METROS A SUBLIMAR", 1)
        pdf.cell(15, 8, f"{total_subli_mts}", 1, 0, "C")
        pdf.cell(25, 8, f"${p_sublimacion:,.0f}", 1, 0, "R")
        pdf.cell(35, 8, "Servicio", 1)
        pdf.cell(20, 8, "-", 1)
        pdf.cell(30, 8, f"${tot_subli:,.0f}", 1, 1, "R")
        total_acumulado += tot_subli

        # 4. GRAN TOTAL
        pdf.ln(4)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(180, 200, 255)
        pdf.cell(155, 10, "VALOR TOTAL DEL PEDIDO (INCL. ADICIONALES)", 1, 0, "R", True)
        pdf.cell(30, 10, f"${total_acumulado:,.0f}", 1, 1, "R", True)

        # Generar descarga
        pdf_output = pdf.output()
        if isinstance(pdf_output, bytearray): pdf_output = bytes(pdf_output)
        
        st.download_button(
            label="⬇️ Descargar PDF Profesional",
            data=pdf_output,
            file_name=f"Pedido_{datetime.now().strftime('%d%m%Y')}.pdf",
            mime="application/pdf"
        )
