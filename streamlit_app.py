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
    # Nota: Asegúrate que el archivo se llame telas.csv o cambia el nombre aquí
    df = pd.read_csv('telas.csv')
    df.columns = df.columns.str.strip()
    return df

# --- INICIO DE LA APP ---
st.set_page_config(page_title="Pedido Paralelo Pro", layout="wide")
st.title("🏭 Generador de Pedidos de Telas")

# Carga de datos
df_telas = cargar_telas()
dict_fotos = obtener_estampados()

# Inicializar carrito si no existe
if "carrito" not in st.session_state:
    st.session_state.carrito = []

# --- FORMULARIO DE ENTRADA ---
with st.expander("➕ Agregar Producto al Pedido", expanded=True):
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        tela_sel = st.selectbox("Seleccione Tela", df_telas['REF DE TELAS'].unique())
        # Intentar obtener 'sin sublimar', si no, usar la columna de precio disponible
        col_precio = 'sin sublimar' if 'sin sublimar' in df_telas.columns else df_telas.columns[1]
        precio_unidad = df_telas.loc[df_telas['REF DE TELAS'] == tela_sel, col_precio].values[0]
        st.metric("Precio Base", f"${precio_unidad:,.0f}")

    with col2:
        cant = st.number_input("Cantidad (mts)", min_value=0.1, step=0.1, value=1.0)

    with col3:
        opciones_diseno = ["Lisa (sin sublimar)", "Ninguno"] + list(dict_fotos.keys())
        diseno_sel = st.selectbox("Estampado", opciones_diseno)
        
        id_img = dict_fotos.get(diseno_sel, None)
        if id_img and diseno_sel != "Lisa (sin sublimar)":
            st.image(f"https://drive.google.com/uc?id={id_img}", width=100)

    if st.button("🚀 Agregar al Pedido"):
        # Añadir al carrito
        nuevo_item = {
            "Tela": tela_sel,
            "Costo": precio_unidad,
            "Cant": cant,
            "Diseño": diseno_sel,
            "ID_Img": id_img if diseno_sel != "Lisa (sin sublimar)" else None,
            "Total": precio_unidad * cant
        }
        st.session_state.carrito.append(nuevo_item)
        st.success(f"Agregado: {tela_sel}")
        st.rerun() # Esto refresca la lista visual inmediatamente

# --- VISUALIZACIÓN DEL CARRITO ---
if st.session_state.carrito:
    st.subheader("🛒 Resumen del Pedido")
    df_visual = pd.DataFrame(st.session_state.carrito)
    st.dataframe(df_visual[['Tela', 'Cant', 'Costo', 'Diseño', 'Total']], use_container_width=True)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Borrar Todo"):
            st.session_state.carrito = []
            st.rerun()
    
    with col_btn2:
        generar_pdf = st.button("📝 Generar PDF Profesional")

    # --- LÓGICA DEL PDF ---
    if generar_pdf:
        pdf = FPDF()
        pdf.add_page()
        
        # --- ENCABEZADO ---
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Solicitud Compra/Servicio a Proveedor Paralelo", ln=True)
        pdf.set_font("Arial", "", 9)
        pdf.cell(100, 5, "Proveedor: Farides Lino", ln=0)
        pdf.cell(0, 5, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=1, align="R")
        pdf.cell(100, 5, "Dirección: Cra 53 # 75-125", ln=0)
        pdf.cell(0, 5, "Ciudad: Barranquilla", ln=1, align="R")
        pdf.cell(0, 5, "Teléfono: 3015664200", ln=1)
        pdf.ln(10)

        # TABLA CABECERA
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Arial", "B", 8)
        headers = [("DESCRIPCION TELA", 55), ("CANT", 15), ("PRECIO U.", 25), ("ESTAMPADO", 40), ("IMAGEN", 20), ("TOTAL", 25)]
        for h, w in headers:
            pdf.cell(w, 8, h, 1, 0, "C", True)
        pdf.ln()

        pdf.set_font("Arial", "", 8)
        total_final = 0
        alto_fila = 20 # Suficiente para que la imagen no se salga

        # 1. PRODUCTOS
        for item in st.session_state.carrito:
            curr_y = pdf.get_y()
            pdf.cell(55, alto_fila, item['Tela'], 1)
            pdf.cell(15, alto_fila, str(item['Cant']), 1, 0, "C")
            pdf.cell(25, alto_fila, f"${item['Costo']:,.0f}", 1, 0, "R")
            pdf.cell(40, alto_fila, item['Diseño'][:22], 1)
            
            # Celda de imagen
            x_img = pdf.get_x()
            pdf.cell(20, alto_fila, "", 1)
            if item['ID_Img']:
                try:
                    img_data = requests.get(f"https://drive.google.com/uc?id={item['ID_Img']}").content
                    # Imagen centrada dentro de la celda de 20x20
                    pdf.image(BytesIO(img_data), x=x_img+2, y=curr_y+2, w=16, h=16)
                except:
                    pass
            
            pdf.cell(25, alto_fila, f"${item['Total']:,.0f}", 1, 1, "R")
            total_final += item['Total']

        # 2. ESPACIOS VACÍOS
        for _ in range(4):
            pdf.cell(55, 6, "", 1); pdf.cell(15, 6, "", 1); pdf.cell(25, 6, "", 1)
            pdf.cell(40, 6, "", 1); pdf.cell(20, 6, "", 1); pdf.cell(25, 6, "", 1, 1)

        # 3. ADICIONALES
        hay_malla = 1 if any("Mallatex" in x['Tela'] for x in st.session_state.carrito) else 0
        hay_drill = 1 if any("Drill" in x['Tela'] for x in st.session_state.carrito) else 0
        excluidos = ["Drill Denim o Jean Liso Blanco", "Drill Denim o Jean Liso Negro", "Drill Grueso Negro", "Drill Liso Blanco", "Drill Liso Lila", "Drill Liso Negro", "Drill Liso Rojo", "Mallatex lisa"]
        mts_subli = sum(x['Cant'] for x in st.session_state.carrito if x['Tela'] not in excluidos and x['Diseño'] not in ["Lisa (sin sublimar)", "Ninguno"])

        # Fila Mallatex
        tot_m = hay_malla * 8000
        pdf.cell(55, 8, "ADICIONAL MALLATEX", 1); pdf.cell(15, 8, str(hay_malla), 1, 0, "C")
        pdf.cell(25, 8, "$8,000", 1, 0, "R"); pdf.cell(40, 8, "-", 1); pdf.cell(20, 8, "-", 1); pdf.cell(25, 8, f"${tot_m:,.0f}", 1, 1, "R")
        
        # Fila Drill
        tot_d = hay_drill * 13995
        pdf.cell(55, 8, "ADICIONAL DRILL", 1); pdf.cell(15, 8, str(hay_drill), 1, 0, "C")
        pdf.cell(25, 8, "$13,995", 1, 0, "R"); pdf.cell(40, 8, "-", 1); pdf.cell(20, 8, "-", 1); pdf.cell(25, 8, f"${tot_d:,.0f}", 1, 1, "R")

        # Fila Sublimación
        tot_s = mts_subli * 8000
        pdf.cell(55, 8, "SERVICIO SUBLIMACION", 1); pdf.cell(15, 8, str(mts_subli), 1, 0, "C")
        pdf.cell(25, 8, "$8,000", 1, 0, "R"); pdf.cell(40, 8, "Varios", 1); pdf.cell(20, 8, "-", 1); pdf.cell(25, 8, f"${tot_s:,.0f}", 1, 1, "R")
        
        total_final += (tot_m + tot_d + tot_s)

        # GRAN TOTAL
        pdf.ln(4)
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(155, 10, "VALOR TOTAL A PAGAR", 1, 0, "R", True)
        pdf.cell(25, 10, f"${total_final:,.0f}", 1, 1, "R", True)

        # Botón de descarga
        pdf_bytes = bytes(pdf.output())
        st.download_button("⬇️ Descargar PDF de Pedido", data=pdf_bytes, file_name="Pedido_Final.pdf", mime="application/pdf")
