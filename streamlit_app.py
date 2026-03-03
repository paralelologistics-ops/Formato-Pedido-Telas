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
    except: return {}

@st.cache_data
def cargar_telas():
    df = pd.read_csv('telas.csv')
    df.columns = df.columns.str.strip()
    return df

# --- PERSISTENCIA DE SESIÓN ---
if "carrito" not in st.session_state:
    st.session_state.carrito = []
if "consecutivo" not in st.session_state:
    st.session_state.consecutivo = 198

# --- SIDEBAR (CONTRÓL DE SOLICITUDES) ---
st.sidebar.image(LOGO_URL, width=120)
st.sidebar.title("Panel de Control")

# Opción para manejar la continuidad
opcion_flujo = st.sidebar.radio("Estado de Solicitud:", ["Modificar / Ver Actual", "Generar Nueva (Siguiente No.)"])

if opcion_flujo == "Generar Nueva (Siguiente No.)":
    if st.sidebar.button("Confirmar: Limpiar y Avanzar Consecutivo"):
        st.session_state.carrito = []
        st.session_state.consecutivo += 1
        st.rerun()

# Ajuste manual del consecutivo si es necesario
num_input = st.sidebar.number_input("Consecutivo Actual:", value=st.session_state.consecutivo)
st.session_state.consecutivo = num_input
str_consecutivo = f"PAR-{str(num_input).zfill(7)}"

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Pedido Paralelo Pro", layout="wide")
st.title(f"📑 Solicitud de Pedido: {str_consecutivo}")

df_telas = cargar_telas()
dict_fotos = obtener_estampados()

# --- FORMULARIO ---
with st.expander("➕ Datos del Producto", expanded=True):
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        tela_sel = st.selectbox("Tela", df_telas['REF DE TELAS'].unique())
        precio_base = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, 'sin sublimar'].values[0]
        st.metric("Precio Unitario", f"${precio_base:,.0f}")
    with c2:
        cant = st.number_input("Metros", min_value=0.1, step=0.1, value=1.0)
    with c3:
        opciones = ["Lisa (sin sublimar)", "Ninguno"] + list(dict_fotos.keys())
        dis_sel = st.selectbox("Diseño", opciones)
        id_img = dict_fotos.get(dis_sel, None) if dis_sel != "Lisa (sin sublimar)" else None
        if id_img: st.image(f"https://drive.google.com/uc?id={id_img}", width=80)
    
    obs_input = st.text_input("Observación corta para este producto")

    if st.button("🚀 Agregar al Listado"):
        st.session_state.carrito.append({
            "Tela": tela_sel, "Cant": cant, "Precio": precio_base, 
            "Diseño": dis_sel, "Img": id_img, "Obs": obs_input, "Total": precio_base * cant
        })
        st.rerun()

# --- TABLA Y GENERACIÓN DE PDF ---
if st.session_state.carrito:
    st.table(pd.DataFrame(st.session_state.carrito)[['Tela', 'Cant', 'Diseño', 'Obs', 'Total']])
    
    if st.button("🗑️ Eliminar último ítem"):
        st.session_state.carrito.pop(); st.rerun()

    if st.button("📝 Generar Documento PDF"):
        pdf = FPDF()
        pdf.add_page()
        
        # --- ENCABEZADO CORREGIDO (Nombre, Dirección, Teléfono) ---
        try:
            pdf.image(BytesIO(requests.get(LOGO_URL).content), 10, 10, 22)
        except: pass
        pdf.set_xy(35, 10)
        pdf.set_font("Arial", "B", 12); pdf.cell(0, 7, "Solicitud Compra a Proveedor Paralelo", ln=1)
        pdf.set_font("Arial", "", 8); pdf.set_x(35)
        pdf.cell(100, 4, "Proveedor: Farides Lino", ln=0)
        pdf.set_font("Arial", "B", 10); pdf.cell(0, 4, f"No. {str_consecutivo}", ln=1, align="R")
        pdf.set_font("Arial", "", 8); pdf.set_x(35)
        pdf.cell(100, 4, "Dirección: Cra 53 # 75-125 | Barranquilla", ln=0)
        pdf.cell(0, 4, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=1, align="R")
        pdf.set_x(35)
        pdf.cell(100, 4, "Teléfono: 3015664200", ln=1)
        pdf.ln(10)

        # TABLA CABECERA
        pdf.set_fill_color(240, 240, 240); pdf.set_font("Arial", "B", 8)
        pdf.cell(45, 8, "DESCRIPCION TELA", 1, 0, "C", True)
        pdf.cell(12, 8, "CANT", 1, 0, "C", True)
        pdf.cell(22, 8, "PRECIO U.", 1, 0, "C", True)
        pdf.cell(33, 8, "DISEÑO", 1, 0, "C", True)
        pdf.cell(18, 8, "IMG", 1, 0, "C", True)
        pdf.cell(25, 8, "TOTAL", 1, 0, "C", True)
        pdf.cell(35, 8, "OBSERVACION", 1, 1, "C", True)

        pdf.set_font("Arial", "", 7.5)
        total_final = 0
        alto = 16

        # 1. Productos
        for i in st.session_state.carrito:
            curr_y = pdf.get_y()
            pdf.cell(45, alto, i['Tela'][:28], 1)
            pdf.cell(12, alto, str(i['Cant']), 1, 0, "C")
            pdf.cell(22, alto, f"${i['Precio']:,.0f}", 1, 0, "R")
            pdf.cell(33, alto, i['Diseño'][:20], 1)
            x_img = pdf.get_x()
            pdf.cell(18, alto, "", 1)
            if i['Img']:
                try: pdf.image(BytesIO(requests.get(f"https://drive.google.com/uc?id={i['Img']}").content), x_img+2, curr_y+2, 14, 12)
                except: pass
            pdf.cell(25, alto, f"${i['Total']:,.0f}", 1, 0, "R")
            pdf.cell(35, alto, i['Obs'][:25], 1, 1)
            total_final += i['Total']

        # 2. Espacios en blanco (5 líneas)
        for _ in range(5):
            pdf.cell(45, 6, "", 1); pdf.cell(12, 6, "", 1); pdf.cell(22, 6, "", 1)
            pdf.cell(33, 6, "", 1); pdf.cell(18, 6, "", 1); pdf.cell(25, 6, "", 1); pdf.cell(35, 6, "", 1, 1)

        # 3. Adicionales (Fijos y lógicos)
        m = 1 if any("Mallatex" in x['Tela'] for x in st.session_state.carrito) else 0
        d = 1 if any("Drill" in x['Tela'] for x in st.session_state.carrito) else 0
        ex = ["Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"]
        s = sum(x['Cant'] for x in st.session_state.carrito if x['Tela'] not in ex and x['Diseño'] not in ["Lisa (sin sublimar)", "Ninguno"])

        for nom, c, p in [("ADICIONAL MALLATEX", m, 8000), ("ADICIONAL DRILL", d, 13995), ("SERVICIO SUBLIMACION", s, 8000)]:
            t_row = c * p
            pdf.set_font("Arial", "B", 7.5)
            pdf.cell(45, 8, nom, 1); pdf.cell(12, 8, str(c), 1, 0, "C")
            pdf.cell(22, 8, f"${p:,.0f}", 1, 0, "R"); pdf.cell(33, 8, "-", 1); pdf.cell(18, 8, "-", 1)
            pdf.cell(25, 8, f"${t_row:,.0f}", 1, 0, "R"); pdf.cell(35, 8, "-", 1, 1)
            total_final += t_row

        # TOTAL NETO
        pdf.ln(4)
        pdf.set_font("Arial", "B", 10); pdf.set_fill_color(200, 220, 255)
        pdf.cell(155, 10, "VALOR TOTAL NETO A PAGAR", 1, 0, "R", True)
        pdf.cell(35, 10, f"${total_final:,.0f}", 1, 1, "R", True)

        st.download_button(f"Descargar {str_consecutivo}", data=bytes(pdf.output()), file_name=f"{str_consecutivo}.pdf")
