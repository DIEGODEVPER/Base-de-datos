from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(
    page_title="SIFODS | Análisis Arquitectónico BD",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

FILE_2026 = DATA_DIR / "Extraccion_DB_SIFODS_2026.xlsx"
FILE_BENCH = BASE_DIR / "Benchmark_SIFODS_2024_vs_2026.xlsx"

# =====================================================
# LOAD DATA
# =====================================================
@st.cache_data
def load_2026():
    return pd.read_excel(FILE_2026, engine="openpyxl")

df = load_2026()

df["tabla_id"] = df["Esquema"].astype(str) + "." + df["Nombre_Tabla"].astype(str)

# =====================================================
# TITLE
# =====================================================
st.title("📊 SIFODS – Análisis Arquitectónico de Base de Datos (PRD)")
st.caption("Vista actual 2026 | Metadata técnica")

# =====================================================
# TABS
# =====================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📌 Resumen Ejecutivo",
    "🏗️ Arquitectura",
    "🔑 Llaves y Relaciones",
    "🚨 Alertas",
    "📈 Benchmarking"
])

# =====================================================
# TAB 1 – RESUMEN
# =====================================================
with tab1:
    total_tablas = df["tabla_id"].nunique()
    total_campos = df.shape[0]
    total_esquemas = df["Esquema"].nunique()
    tablas_sin_datos = (
        df.groupby("tabla_id")["Total_Registros"].max().eq(0).sum()
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Esquemas", total_esquemas)
    c2.metric("Tablas", total_tablas)
    c3.metric("Campos", total_campos)
    c4.metric("Tablas sin datos", tablas_sin_datos)

    obj = df.groupby("Tipo_Objeto")["tabla_id"].nunique().reset_index()
    obj.columns = ["Tipo_Objeto", "Tablas"]

    fig = px.pie(
        obj,
        names="Tipo_Objeto",
        values="Tablas",
        hole=0.45,
        title="Distribución de objetos BD"
    )
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# TAB 2 – ARQUITECTURA
# =====================================================
with tab2:
    esquema_tablas = (
        df.groupby("Esquema")["tabla_id"].nunique()
        .reset_index(name="Tablas")
        .sort_values("Tablas", ascending=False)
    )

    fig = px.bar(
        esquema_tablas,
        x="Esquema",
        y="Tablas",
        title="Tablas por esquema",
        text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(esquema_tablas, use_container_width=True)

# =====================================================
# TAB 3 – LLAVES
# =====================================================
with tab3:
    llaves = (
        df[df["Tipo_Llave"].notna()]
        .groupby(["Esquema", "Tipo_Llave"])
        .size()
        .reset_index(name="Cantidad")
    )

    fig = px.bar(
        llaves,
        x="Esquema",
        y="Cantidad",
        color="Tipo_Llave",
        title="Distribución de PK y FK por esquema",
        barmode="group"
    )
    st.plotly_chart(fig, use_container_width=True)

    tablas_sin_pk = (
        df.groupby("tabla_id")["Tipo_Llave"]
        .apply(lambda x: "PK" not in x.values)
        .reset_index(name="Sin_PK")
    )

    st.metric("Tablas sin PK", tablas_sin_pk["Sin_PK"].sum())

# =====================================================
# TAB 4 – ALERTAS
# =====================================================
with tab4:
    alertas = (
        df.groupby(["Esquema", "tabla_id"])
        .agg(
            Total_Registros=("Total_Registros", "max"),
            Campos=("Nombre_Campo", "count")
        )
        .reset_index()
    )

    alertas = alertas[alertas["Total_Registros"] == 0]

    fig = px.bar(
        alertas.groupby("Esquema").size().reset_index(name="Tablas"),
        x="Esquema",
        y="Tablas",
        title="Tablas sin registros por esquema",
        text_auto=True
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(alertas, use_container_width=True)

# =====================================================
# TAB 5 – BENCHMARK
# =====================================================
with tab5:
    if not FILE_BENCH.exists():
        st.warning("Benchmarking aún no generado.")
    else:
        dfb = pd.read_excel(FILE_BENCH, engine="openpyxl")
        estado = dfb["estado"].value_counts().reset_index()
        estado.columns = ["Estado", "Tablas"]

        fig = px.bar(
            estado,
            x="Estado",
            y="Tablas",
            color="Estado",
            title="Estado de tablas – 2024 vs 2026",
            text_auto=True
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(dfb, use_container_width=True)
