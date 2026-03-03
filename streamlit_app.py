import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN ---
API_KEY = "AIzaSyBipSMJcc_hwiQ-ATlt-mf2YUcG2_Q8uEc"
FOLDER_ID = "17RIBmFQcEqZDZRWouTGsaNTOHQ2b--PG"
LOGO_URL = "https://static.wixstatic.com/media/d0ce54_32d30a8159fd44d4a26c62563d7bfc38~mv2.jpg"

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

# --- ESTADO DE LA SESIÓN ---
if "carrito" not in st.session_state:
    st.session_state.carrito = []
if "consecutivo" not in st.session_state:
    st.session_state.consecutivo = 198

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.image(LOGO_URL, width=130)
st.sidebar.title("Menú de Control")

modo = st.sidebar.radio("Estado de Sesión:", ["Modificar / Ver Actual", "Nueva Solicitud"])
if modo == "Nueva Solicitud":
    if st.sidebar.button("🧹 Limpiar y Siguiente Número"):
        st.session_state.carrito = []
        st.session_state.consecutivo += 1
        st.rerun()

st.sidebar.markdown("---")
num_consecutivo = st.sidebar.number_input("No. Solicitud:", value=st.session_state.consecutivo, step=1)
st.session_state.consecutivo = num_consecutivo
str_consecutivo = f"PAR-{str(num_consecutivo).zfill(7)}"

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Pedido Paralelo Pro", layout="wide")
st.title(f"📄 Solicitud de Pedido: {str_consecutivo}")

df_telas = cargar_telas()
dict_fotos = obtener_estampados()

# --- FORMULARIO DE ENTRADA ---
with st.expander("📝 Datos del Producto", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        tela_sel = st.selectbox("Tela", df_telas['REF DE TELAS'].unique())
        precio_unidad = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, 'sin sublimar'].values[0]
        st.info(f"Precio Base: **${precio_unidad:,.0f}**")
    with c2:
        cant = st.number_input("Metros", min_value=0.1, step=0.1, value=1.0)
    with c3:
        opciones = ["Lisa (sin sublimar)", "Ninguno"] + list(dict_fotos.keys())
        diseno_sel = st.selectbox("Diseño/Estampado", opciones)
        id_img = dict_fotos.get(diseno_sel, None)
        if id_img and diseno_sel != "Lisa (sin sublimar)":
            st.image(f"https://drive.google.com/uc?id={id_img}", width=70)

    obs = st.text_input("Observación corta (máx 3-4 palabras)", placeholder="Ej: Enviar 2 cortes")

    if st.button("➕ Agregar a la Lista"):
        st.session_state.carrito.append({
            "Tela": tela_sel, "Costo": precio_unidad, "Cant": cant,
            "Diseño": diseno_sel, "Obs": obs, "Total": precio_unidad * cant,
            "ID_Img": id_img if diseno_sel != "Lisa (sin sublimar)" else None
        })
        st.rerun()

# --- TABLA Y PDF ---
if st.session_state.carrito:
    st.markdown("### 📋 Vista Previa")
    st.table(pd.DataFrame(st.session_state.carrito)[['Tela', 'Cant', 'Diseño', 'Obs', 'Total']])
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Eliminar último"):
            st.session_state.carrito.pop(); st.rerun()
            
    with col_b:
        if st.button("🖨️ Generar PDF Vertical"):
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            
            # Encabezado con Logo
            try:
                logo_d = requests.get(LOGO_URL).content
                pdf.image(BytesIO(logo_d), x=10, y=10, w=22)
            except: pass

            pdf.set_xy(35, 10)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 7, "Solicitud Compra/Servicio a Proveedor Paralelo", ln=True)
            pdf.set_font("Arial", "", 8)
            pdf.set_x(35)
            pdf.cell(100, 4, "Proveedor: Farides Lino | Nit: 22444555-1", ln=0)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 4, f"No. {str_consecutivo}", ln=1, align="R")
            pdf.set_font("Arial", "", 8)
            pdf.set_x(35)
            pdf.cell(100, 4, "Dirección: Cra 53 # 75-125 | Barranquilla", ln=0)
            pdf.cell(0, 4, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=1, align="R")
            pdf.ln(12)

            # TABLA (Ajuste de anchos para Vertical)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Arial", "B", 8)
            # Total ancho ~190mm
            pdf.cell(45, 8, "TELA", 1, 0, "C", True)
            pdf.cell(12, 8, "CANT", 1, 0, "C", True)
            pdf.cell(22, 8, "PRECIO", 1, 0, "C", True)
            pdf.cell(33, 8, "DISEÑO", 1, 0, "C", True)
            pdf.cell(18, 8, "IMG", 1, 0, "C", True)
            pdf.cell(35, 8, "OBSERV.", 1, 0, "C", True) # Columna de Observación
            pdf.cell(25, 8, "TOTAL", 1, 1, "C", True)

            pdf.set_font("Arial", "", 7.5)
            t_acum = 0
            alto_f = 16

            for it in st.session_state.carrito:
                y_f = pdf.get_y()
                pdf.cell(45, alto_f, it['Tela'][:30], 1)
                pdf.cell(12, alto_f, str(it['Cant']), 1, 0, "C")
                pdf.cell(22, alto_f, f"${it['Costo']:,.0f}", 1, 0, "R")
                pdf.cell(33, alto_f, it['Diseño'][:20], 1)
                
                # Imagen dentro de la celda
                x_i = pdf.get_x()
                pdf.cell(18, alto_f, "", 1)
                if it['ID_Img']:
                    try:
                        img_raw = requests.get(f"https://drive.google.com/uc?id={it['ID_Img']}").content
                        pdf.image(BytesIO(img_raw), x=x_i+2, y=y_f+2, w=14, h=12)
                    except: pass
                
                pdf.cell(35, alto_f, it['Obs'][:25], 1) # Texto de observación
                pdf.cell(25, alto_f, f"${it['Total']:,.0f}", 1, 1, "R")
                t_acum += it['Total']

            # ESPACIOS Y ADICIONALES
            pdf.ln(1)
            for _ in range(4):
                pdf.cell(45, 5, "", 1); pdf.cell(12, 5, "", 1); pdf.cell(22, 5, "", 1)
                pdf.cell(33, 5, "", 1); pdf.cell(18, 5, "", 1); pdf.cell(35, 5, "", 1); pdf.cell(25, 5, "", 1, 1)

            # LÓGICA DE COSTOS EXTRAS
            m = 1 if any("Mallatex" in x['Tela'] for x in st.session_state.carrito) else 0
            d = 1 if any("Drill" in x['Tela'] for x in st.session_state.carrito) else 0
            ex = ["Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"]
            s = sum(x['Cant'] for x in st.session_state.carrito if x['Tela'] not in ex and x['Diseño'] not in ["Lisa (sin sublimar)", "Ninguno"])

            for n, c, p in [("ADICIONAL MALLATEX", m, 8000), ("ADICIONAL DRILL", d, 13995), ("SERVICIO SUBLIMACION", s, 8000)]:
                subt = c * p
                pdf.set_font("Arial", "B", 7.5)
                pdf.cell(130, 7, n, 1, 0, "R")
                pdf.set_font("Arial", "", 7.5)
                pdf.cell(35, 7, f"Cant: {c} x ${p:,.0f}", 1, 0, "C")
                pdf.cell(25, 7, f"${subt:,.0f}", 1, 1, "R")
                t_acum += subt

            # GRAN TOTAL
            pdf.ln(3)
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(165, 9, "TOTAL GENERAL A PAGAR", 1, 0, "R", True)
            pdf.cell(25, 9, f"${t_acum:,.0f}", 1, 1, "R", True)

            st.download_button(f"⬇️ Descargar {str_consecutivo}", data=bytes(pdf.output()), 
                               file_name=f"{str_consecutivo}.pdf", mime="application/pdf")
