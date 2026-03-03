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
        precio_unidad = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, 'sin sublimar'].values[0]
        st.metric("Precio Base (Sin Sublimar)", f"${precio_unidad:,.0f}")

    with col2:
        cant = st.number_input("Cantidad (mts)", min_value=0.1, step=0.1, value=1.0)

    with col3:
        opciones_diseno = ["Lisa (sin sublimar)", "Ninguno"] + list(dict_fotos.keys())
        diseno_sel = st.selectbox("Estampado", opciones_diseno)
        
        id_img = dict_fotos.get(diseno_sel, None)
        if id_img and diseno_sel != "Lisa (sin sublimar)":
            st.image(f"https://drive.google.com/uc?id={id_img}", width=100)

    if st.button("🚀 Agregar al Pedido"):
        st.session_state.carrito.append({
            "Tela": tela_sel,
            "Costo": precio_unidad,
            "Cant": cant,
            "Diseño": diseno_sel,
            "ID_Img": id_img if diseno_sel != "Lisa (sin sublimar)" else None,
            "Total": precio_unidad * cant
        })

# --- TABLA Y LÓGICA DE PDF ---
if st.session_state.carrito:
    df_temp = pd.DataFrame(st.session_state.carrito)
    
    if st.button("🗑️ Borrar último ítem"):
        st.session_state.carrito.pop()
        st.rerun()

    if st.button("📝 Generar PDF"):
        pdf = FPDF()
        pdf.add_page()
        
        # --- ENCABEZADO (DATOS PROVEEDOR) ---
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Solicitud Compra/Servicio a Proveedor Paralelo", ln=True, align="L")
        pdf.set_font("Arial", "", 9)
        pdf.cell(100, 5, "Proveedor: Farides Lino", ln=0)
        pdf.cell(0, 5, f"No. PAR-{datetime.now().strftime('%M%S')}", ln=1, align="R")
        pdf.cell(100, 5, "Dirección: Cra 53 # 75-125", ln=0)
        pdf.cell(0, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=1, align="R")
        pdf.cell(0, 5, "Ciudad: Barranquilla", ln=1)
        pdf.cell(0, 5, "Teléfono: 3015664200", ln=1)
        pdf.ln(10)

        # Encabezados de Tabla
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", "B", 8)
        pdf.cell(55, 8, "DESCRIPCION TELA", 1, 0, "C", True)
        pdf.cell(15, 8, "CANT", 1, 0, "C", True)
        pdf.cell(25, 8, "PRECIO U.", 1, 0, "C", True)
        pdf.cell(40, 8, "ESTAMPADO", 1, 0, "C", True)
        pdf.cell(20, 8, "IMAGEN", 1, 0, "C", True)
        pdf.cell(25, 8, "TOTAL", 1, 1, "C", True)

        pdf.set_font("Arial", "", 8)
        total_acumulado = 0
        alto_celda = 18  # Altura fija para que la imagen quepa bien

        # 1. PRODUCTOS
        for item in st.session_state.carrito:
            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            
            pdf.cell(55, alto_celda, item['Tela'], 1)
            pdf.cell(15, alto_celda, str(item['Cant']), 1, 0, "C")
            pdf.cell(25, alto_celda, f"${item['Costo']:,.0f}", 1, 0, "R")
            pdf.cell(40, alto_celda, item['Diseño'][:25], 1)
            
            # Celda de Imagen (Controlada)
            x_img = pdf.get_x()
            pdf.cell(20, alto_celda, "", 1) # Dibujar el recuadro primero
            if item['ID_Img']:
                try:
                    img_data = requests.get(f"https://drive.google.com/uc?id={item['ID_Img']}").content
                    # Se coloca la imagen dentro de la celda con margen de 2mm
                    pdf.image(BytesIO(img_data), x=x_img+2, y=y_pos+2, w=16, h=14)
                except: pass
            
            pdf.cell(25, alto_celda, f"${item['Total']:,.0f}", 1, 1, "R")
            total_acumulado += item['Total']

        # 2. ESPACIO EN BLANCO (5 líneas)
        for _ in range(5):
            pdf.cell(55, 6, "", 1); pdf.cell(15, 6, "", 1); pdf.cell(25, 6, "", 1)
            pdf.cell(40, 6, "", 1); pdf.cell(20, 6, "", 1); pdf.cell(25, 6, "", 1, 1)

        # 3. FILAS DE ADICIONALES (Costos Fijos)
        # Lógica de detección
        hay_malla = 1 if "Mallatex" in df_temp['Tela'].values else 0
        hay_drill = 1 if df_temp['Tela'].str.contains("Drill Denim o Jean").any() else 0
        excluidos = ["Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"]
        mts_subli = df_temp[~df_temp['Tela'].isin(excluidos) & ~df_temp['Diseño'].isin(["Lisa (sin sublimar)", "Ninguno"])]['Cant'].sum()

        # Fila Mallatex ($8.000)
        tot_m = hay_malla * 8000
        pdf.cell(55, 8, "ADICIONAL MALLATEX", 1); pdf.cell(15, 8, str(hay_malla), 1, 0, "C")
        pdf.cell(25, 8, "$8,000", 1, 0, "R"); pdf.cell(40, 8, "-", 1); pdf.cell(20, 8, "-", 1)
        pdf.cell(25, 8, f"${tot_m:,.0f}", 1, 1, "R")
        total_acumulado += tot_m

        # Fila Drill ($13.995)
        tot_d = hay_drill * 13995
        pdf.cell(55, 8, "ADICIONAL DRILL", 1); pdf.cell(15, 8, str(hay_drill), 1, 0, "C")
        pdf.cell(25, 8, "$13,995", 1, 0, "R"); pdf.cell(40, 8, "-", 1); pdf.cell(20, 8, "-", 1)
        pdf.cell(25, 8, f"${tot_d:,.0f}", 1, 1, "R")
        total_acumulado += tot_d

        # Fila Sublimación ($8.000/mt)
        tot_s = mts_subli * 8000
        pdf.cell(55, 8, "SERVICIO SUBLIMACION", 1); pdf.cell(15, 8, f"{mts_subli}", 1, 0, "C")
        pdf.cell(25, 8, "$8,000", 1, 0, "R"); pdf.cell(40, 8, "Varios", 1); pdf.cell(20, 8, "-", 1)
        pdf.cell(25, 8, f"${tot_s:,.0f}", 1, 1, "R")
        total_acumulado += tot_s

        # GRAN TOTAL
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(155, 10, "VALOR TOTAL A PAGAR", 1, 0, "R", True)
        pdf.cell(25, 10, f"${total_acumulado:,.0f}", 1, 1, "R", True)

        pdf_bytes = bytes(pdf.output())
        st.download_button(label="⬇️ Descargar PDF Final", data=pdf_bytes, file_name="Pedido_Paralelo.pdf", mime="application/pdf")
