from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

# ======================================
# CONFIGURACIÓN GENERAL
# ======================================
st.set_page_config(
    page_title="Benchmark BD SIFODS - 2026",
    layout="wide"
)

# ======================================
# RUTAS LÓGICAS DEL PROYECTO
# ======================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BENCH_FILE = BASE_DIR / "Benchmark_SIFODS_2024_vs_2026.xlsx"

# ======================================
# VALIDACIONES
# ======================================
if not BENCH_FILE.exists():
    st.error(f"No se encontró el archivo de benchmark: {BENCH_FILE}")
    st.stop()

# ======================================
# CARGA DE DATOS
# ======================================
@st.cache_data
def load_data():
    return pd.read_excel(BENCH_FILE, engine="openpyxl")

df = load_data()

# ======================================
# TÍTULO
# ======================================
st.title("Benchmark Base de Datos SIFODS")
st.caption("Comparativo PRD 2024 vs 2026")

# ======================================
# KPIs
# ======================================
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total de tablas", df.shape[0])
col2.metric("Tablas nuevas", (df["estado"] == "Nueva").sum())
col3.metric("Tablas eliminadas", (df["estado"] == "Eliminada").sum())
col4.metric("Tablas modificadas", (df["estado"] == "Modificada").sum())

# ======================================
# GRÁFICO – ESTADO DE TABLAS (FIX)
# ======================================
st.subheader("Distribución del estado de tablas")

estado_count = df["estado"].value_counts().reset_index()

# Normalización segura de nombres de columnas
estado_count.columns = ["Estado", "Cantidad"]

fig_estado = px.bar(
    estado_count,
    x="Estado",
    y="Cantidad",
    color="Estado",
    title="Estado de las tablas",
    text_auto=True
)

st.plotly_chart(fig_estado, use_container_width=True)


# ======================================
# FILTROS
# ======================================
st.subheader("Filtro de tablas")

estado_seleccionado = st.multiselect(
    "Estado de tabla",
    options=df["estado"].unique(),
    default=df["estado"].unique()
)

df_filtrado = df[df["estado"].isin(estado_seleccionado)]

# ======================================
# TABLA DETALLE
# ======================================
st.subheader("Detalle comparativo por tabla")

st.dataframe(
    df_filtrado.sort_values("estado"),
    use_container_width=True
)

# ======================================
# DESCARGA
# ======================================
st.download_button(
    label="Descargar Benchmark (Excel)",
    data=BENCH_FILE.read_bytes(),
    file_name="Benchmark_SIFODS_2024_vs_2026.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)