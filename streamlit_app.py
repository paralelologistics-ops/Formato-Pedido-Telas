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
    # Limpiamos nombres de columnas por si acaso
    df.columns = df.columns.str.strip()
    return df

# --- INICIO DE LA APP ---
st.set_page_config(page_title="Pedido Paralelo Pro", layout="wide")
st.title("📑 Generador de Pedidos con Estampados")

df_telas = cargar_telas()
dict_fotos = obtener_estampados()

if "carrito" not in st.session_state:
    st.session_state.carrito = []

# --- FORMULARIO DE ENTRADA ---
with st.container():
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        tela_sel = st.selectbox("Seleccione Tela", df_telas['REF DE TELAS'].unique())
        # CAMBIO: Ahora usamos la columna 'sin sublimar'
        precio_unidad = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, 'sin sublimar'].values[0]
        st.metric("Precio (Sin Sublimar)", f"${precio_unidad:,.0f}")

    with col2:
        cant = st.number_input("Cantidad (mts)", min_value=0.1, step=0.1, value=1.0)

    with col3:
        diseno_sel = st.selectbox("Estampado", ["Ninguno"] + list(dict_fotos.keys()))
        id_img = dict_fotos.get(diseno_sel, None)
        if id_img:
            # Link optimizado para visualización
            img_url = f"https://drive.google.com/uc?export=view&id={id_img}"
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

# --- TABLA DE PEDIDO CON OPCIÓN DE BORRAR ---
if st.session_state.carrito:
    st.subheader("Lista de Compra")
    
    # Creamos columnas para simular una tabla con botón de borrar
    for i, item in enumerate(st.session_state.carrito):
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1, 2, 1, 0.5])
        c1.write(item['Tela'])
        c2.write(f"{item['Cant']} m")
        c3.write(f"${item['Costo']:,.0f}")
        c4.write(item['Diseño'])
        c5.write(f"**${item['Total']:,.0f}**")
        if c6.button("🗑️", key=f"del_{i}"):
            st.session_state.carrito.pop(i)
            st.rerun()

    # --- CÁLCULOS ESPECIALES ---
    df_temp = pd.DataFrame(st.session_state.carrito)
    hay_mallatex = 1 if "Mallatex" in df_temp['Tela'].values else ""
    hay_drill = 1 if df_temp['Tela'].str.contains("Drill Denim o Jean").any() else ""
    
    excluidos = ["Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"]
    total_subli = df_temp[~df_temp['Tela'].isin(excluidos)]['Cant'].sum()

    st.sidebar.markdown("### Resumen")
    st.sidebar.write(f"Adicional Mallatex: **{hay_mallatex}**")
    st.sidebar.write(f"Adicional Drill: **{hay_drill}**")
    st.sidebar.write(f"Total Sublimación: **{total_subli} mts**")
    st.sidebar.title(f"TOTAL: ${df_temp['Total'].sum():,.0f}")

    # --- BOTÓN PARA GENERAR PDF ---
    if st.button("💾 Guardar Pedido en PDF"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "SOLICITUD DE PEDIDO - PARALELO", ln=True, align="C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.ln(5)

        # Encabezados de tabla
        pdf.set_fill_color(200, 200, 200)
        pdf.cell(40, 10, "Tela", 1, 0, "C", True)
        pdf.cell(20, 10, "Cant", 1, 0, "C", True)
        pdf.cell(30, 10, "Costo M", 1, 0, "C", True)
        pdf.cell(40, 10, "Diseño", 1, 0, "C", True)
        pdf.cell(30, 10, "Imagen", 1, 1, "C", True)

        for item in st.session_state.carrito:
            pdf.cell(40, 20, item['Tela'], 1)
            pdf.cell(20, 20, str(item['Cant']), 1)
            pdf.cell(30, 20, f"${item['Costo']:,.0f}", 1)
            pdf.cell(40, 20, item['Diseño'], 1)
            
            # Lógica para meter la imagen en el PDF
            if item['ID_Img']:
                try:
                    img_data = requests.get(f"https://drive.google.com/uc?id={item['ID_Img']}").content
                    img_stream = BytesIO(img_data)
                    x, y = pdf.get_x(), pdf.get_y()
                    pdf.image(img_stream, x=x+5, y=y+2, w=20)
                except:
                    pdf.cell(30, 20, "No disponible", 1)
            
            pdf.cell(30, 20, "", 1, 1) # Espacio para la imagen

        pdf_output = pdf.output(dest='S').encode('latin-1')
        st.download_button("⬇️ Descargar Archivo PDF", data=pdf_output, file_name="pedido_telas.pdf", mime="application/pdf")
