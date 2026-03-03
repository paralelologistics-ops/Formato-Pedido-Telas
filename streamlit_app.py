import streamlit as st
import pandas as pd
import requests
from fpdf import FPDF
from io import BytesIO
from datetime import datetime

# --- CONFIGURACIÓN ---
API_KEY = "AIzaSyBipSMJcc_hwiQ-ATlt-mf2YUcG2_Q8uEc"
FOLDER_ID = "17RIBmFQcEqZDZRWouTGsaNTOHQ2b--PG"
LOGO_URL = "https://static.wixstatic.com/media/d0ce54_aee7f80f620b4f278247333f7ef558f5~mv2.png"

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
    st.session_state.consecutivo = 198  # Iniciamos en el 198 según tu dato

# --- INTERFAZ - BARRA LATERAL ---
st.sidebar.image(LOGO_URL, width=150)
st.sidebar.title("Gestión de Pedidos")

modo = st.sidebar.radio("Acción:", ["Modificar Solicitud Actual", "Nueva Solicitud"])

if modo == "Nueva Solicitud":
    if st.sidebar.button("⚠️ Confirmar Limpieza"):
        st.session_state.carrito = []
        st.session_state.consecutivo += 1
        st.rerun()

st.sidebar.markdown("---")
num_consecutivo = st.sidebar.number_input("Número de Solicitud (Consecutivo):", 
                                          value=st.session_state.consecutivo, step=1)
st.session_state.consecutivo = num_consecutivo
str_consecutivo = f"PAR-{str(num_consecutivo).zfill(7)}"

# --- INICIO DE LA APP ---
st.set_page_config(page_title="Pedido Paralelo Pro", layout="wide")
st.title(f"🏭 Solicitud de Pedido: {str_consecutivo}")

df_telas = cargar_telas()
dict_fotos = obtener_estampados()

# --- FORMULARIO DE ENTRADA ---
with st.expander("➕ Agregar Producto", expanded=True):
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        tela_sel = st.selectbox("Seleccione Tela", df_telas['REF DE TELAS'].unique())
        precio_unidad = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, 'sin sublimar'].values[0]
        st.metric("Precio Unitario", f"${precio_unidad:,.0f}")
    with col2:
        cant = st.number_input("Cantidad (mts)", min_value=0.1, step=0.1, value=1.0)
    with col3:
        opciones_diseno = ["Lisa (sin sublimar)", "Ninguno"] + list(dict_fotos.keys())
        diseno_sel = st.selectbox("Estampado", opciones_diseno)
        id_img = dict_fotos.get(diseno_sel, None)
        if id_img and diseno_sel != "Lisa (sin sublimar)":
            st.image(f"https://drive.google.com/uc?id={id_img}", width=100)

    if st.button("🚀 Añadir a la Lista"):
        st.session_state.carrito.append({
            "Tela": tela_sel, "Costo": precio_unidad, "Cant": cant,
            "Diseño": diseno_sel, "ID_Img": id_img if diseno_sel != "Lisa (sin sublimar)" else None,
            "Total": precio_unidad * cant
        })
        st.rerun()

# --- TABLA Y PDF ---
if st.session_state.carrito:
    st.subheader("Lista de Productos")
    df_vis = pd.DataFrame(st.session_state.carrito)
    st.table(df_vis[['Tela', 'Cant', 'Costo', 'Diseño', 'Total']])
    
    if st.button("🗑️ Eliminar último ítem"):
        st.session_state.carrito.pop()
        st.rerun()

    if st.button("💾 Generar Documento PDF"):
        pdf = FPDF()
        pdf.add_page()
        
        # --- LOGO REDONDO (Simulado con máscara de posición) ---
        try:
            logo_data = requests.get(LOGO_URL).content
            logo_stream = BytesIO(logo_data)
            # Dibujamos el logo arriba a la derecha
            pdf.image(logo_stream, x=10, y=10, w=25) 
        except: pass

        # --- ENCABEZADO ---
        pdf.set_xy(40, 10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Solicitud Compra/Servicio a Proveedor Paralelo", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.set_x(40)
        pdf.cell(100, 5, "Proveedor: Farides Lino", ln=0)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 5, f"No. {str_consecutivo}", ln=1, align="R")
        pdf.set_font("Arial", "", 9)
        pdf.set_x(40)
        pdf.cell(100, 5, "Dirección: Cra 53 # 75-125", ln=0)
        pdf.cell(0, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=1, align="R")
        pdf.set_x(40)
        pdf.cell(0, 5, "Ciudad: Barranquilla | Tel: 3015664200", ln=1)
        pdf.ln(15)

        # TABLA CABECERA
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(55, 8, "DESCRIPCION TELA", 1, 0, "C", True)
        pdf.cell(15, 8, "CANT", 1, 0, "C", True)
        pdf.cell(25, 8, "PRECIO U.", 1, 0, "C", True)
        pdf.cell(40, 8, "ESTAMPADO", 1, 0, "C", True)
        pdf.cell(20, 8, "IMAGEN", 1, 0, "C", True)
        pdf.cell(25, 8, "TOTAL", 1, 1, "C", True)

        pdf.set_font("Arial", "", 8)
        total_acum = 0
        alto = 20

        for item in st.session_state.carrito:
            y_act = pdf.get_y()
            pdf.cell(55, alto, item['Tela'], 1)
            pdf.cell(15, alto, str(item['Cant']), 1, 0, "C")
            pdf.cell(25, alto, f"${item['Costo']:,.0f}", 1, 0, "R")
            pdf.cell(40, alto, item['Diseño'][:22], 1)
            
            x_img = pdf.get_x()
            pdf.cell(20, alto, "", 1)
            if item['ID_Img']:
                try:
                    img_d = requests.get(f"https://drive.google.com/uc?id={item['ID_Img']}").content
                    pdf.image(BytesIO(img_d), x=x_img+2, y=y_act+2, w=16, h=16)
                except: pass
            
            pdf.cell(25, alto, f"${item['Total']:,.0f}", 1, 1, "R")
            total_acum += item['Total']

        # ESPACIOS Y ADICIONALES
        pdf.ln(2)
        for _ in range(4):
            pdf.cell(55, 6, "", 1); pdf.cell(15, 6, "", 1); pdf.cell(25, 6, "", 1)
            pdf.cell(40, 6, "", 1); pdf.cell(20, 6, "", 1); pdf.cell(25, 6, "", 1, 1)

        # LÓGICA ADICIONALES
        hay_m = 1 if any("Mallatex" in x['Tela'] for x in st.session_state.carrito) else 0
        hay_d = 1 if any("Drill" in x['Tela'] for x in st.session_state.carrito) else 0
        excl = ["Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"]
        mts_s = sum(x['Cant'] for x in st.session_state.carrito if x['Tela'] not in excl and x['Diseño'] not in ["Lisa (sin sublimar)", "Ninguno"])

        # Filas Adicionales
        for nom, cant_a, precio_a in [("ADICIONAL MALLATEX", hay_m, 8000), ("ADICIONAL DRILL", hay_d, 13995), ("SERVICIO SUBLIMACION", mts_s, 8000)]:
            t_a = cant_a * precio_a
            pdf.cell(55, 8, nom, 1); pdf.cell(15, 8, str(cant_a), 1, 0, "C")
            pdf.cell(25, 8, f"${precio_a:,.0f}", 1, 0, "R"); pdf.cell(40, 8, "-", 1); pdf.cell(20, 8, "-", 1)
            pdf.cell(25, 8, f"${t_a:,.0f}", 1, 1, "R")
            total_acum += t_a

        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(155, 10, "VALOR TOTAL NETO", 1, 0, "R", True)
        pdf.cell(25, 10, f"${total_acum:,.0f}", 1, 1, "R", True)

        st.download_button("⬇️ Descargar PDF " + str_consecutivo, data=bytes(pdf.output()), 
                           file_name=f"Solicitud_{str_consecutivo}.pdf", mime="application/pdf")
