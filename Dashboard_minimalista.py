#ESTRUCTURA:
# 1. Imports
# 2. Configuración Streamlit
# 3. Rutas y carga de datos
# 4. Preparación / cálculos (ANÁLISIS)
# 5. Visualización (gráficos, tablas, textos)



from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================
st.set_page_config(
    page_title="SIFODS | Análisis BD PRD 2026",
    layout="wide"
)

# =====================================================
# RUTAS
# =====================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

FILE_2026 = DATA_DIR / "Extraccion_DB_SIFODS_2026.xlsx"
FILE_BENCH = BASE_DIR / "Benchmark_SIFODS_2024_vs_2026.xlsx"

# =====================================================
# CARGA ROBUSTA DE METADATA
# =====================================================
@st.cache_data
def load_metadata(file_path):
    xls = pd.ExcelFile(file_path)
    for sheet in xls.sheet_names:
        tmp = pd.read_excel(xls, sheet_name=sheet)
        cols = tmp.columns.astype(str).str.strip().str.upper().str.replace(" ", "_")
        if "ESQUEMA" in cols and "NOMBRE_TABLA" in cols:
            tmp.columns = cols
            return tmp
    raise ValueError("No se encontró metadata válida")

df = load_metadata(FILE_2026)
df["TABLA_ID"] = df["ESQUEMA"] + "." + df["NOMBRE_TABLA"]

# =====================================================
# ANÁLISIS BASE
# =====================================================
ta = (
    df.groupby(["ESQUEMA", "TABLA_ID"])
    .agg(
        TOTAL_REGISTROS=("TOTAL_REGISTROS", "max"),
        PKS=("TIPO_LLAVE", lambda x: (x == "PK").sum()),
        FKS=("TIPO_LLAVE", lambda x: (x == "FK").sum())
    )
    .reset_index()
)

ta["TIENE_PK"] = ta["PKS"] > 0
ta["TIENE_DATOS"] = ta["TOTAL_REGISTROS"] > 0

def integridad(r):
    if not r.TIENE_PK and r.FKS == 0:
        return "HUERFANA"
    if not r.TIENE_PK and r.FKS > 0:
        return "SOLO_FK"
    return "OK_PK"

ta["INTEGRIDAD"] = ta.apply(integridad, axis=1)

def riesgo(r):
    if r.INTEGRIDAD in ["HUERFANA","SOLO_FK"] and not r.TIENE_DATOS:
        return "CRITICO"
    if r.INTEGRIDAD != "OK_PK":
        return "ALTO"
    if not r.TIENE_DATOS:
        return "MEDIO"
    return "BAJO"

ta["RIESGO"] = ta.apply(riesgo, axis=1)

def accion(r):
    if r.RIESGO == "CRITICO":
        return "ELIMINAR"
    if r.RIESGO in ["ALTO", "MEDIO"]:
        return "ANALIZAR"
    return "CONSERVAR"

ta["ACCION"] = ta.apply(accion, axis=1)
ta["USO"] = ta["TIENE_DATOS"].map({True: "CON_DATOS", False: "SIN_DATOS"})

# =====================================================
# DASHBOARD
# =====================================================
st.title("📊 Estado de la Base de Datos SIFODS – PRD 2026")
st.caption("Visión ejecutiva • Riesgos • Recomendaciones")

tab1, tab2, tab3 = st.tabs([
    "Vista General",
    "Análisis Tabla por Tabla",
    "Benchmark"
])

# =====================================================
# TAB 1 – VISTA GENERAL (BALANCEADA)
# =====================================================
with tab1:

    # ---------------- KPIs SUPERIORES ----------------
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Esquemas", ta["ESQUEMA"].nunique())
    k2.metric("Tablas", ta.shape[0])
    k3.metric("Sin PK", (~ta["TIENE_PK"]).sum())
    k4.metric("Sin datos", (~ta["TIENE_DATOS"]).sum())
    k5.metric("Críticas", (ta["RIESGO"] == "CRITICO").sum())

    st.divider()

    # ---------------- BLOQUE PRINCIPAL ----------------
    col_riesgo, col_accion, col_uso = st.columns(3)

    # ----- Riesgos -----
    riesgo_dist = ta["RIESGO"].value_counts().reset_index()
    riesgo_dist.columns = ["RIESGO", "TABLAS"]

    fig_riesgo = px.pie(
        riesgo_dist,
        names="RIESGO",
        values="TABLAS",
        hole=0.5,
        color="RIESGO",
        color_discrete_map={
            "CRITICO": "#d62728",
            "ALTO": "#ff7f0e",
            "MEDIO": "#ffbf00",
            "BAJO": "#2ca02c"
        },
        title="Riesgo de tablas"
    )
    col_riesgo.plotly_chart(fig_riesgo, use_container_width=True)

    # ----- Recomendaciones -----
    accion_dist = ta["ACCION"].value_counts().reset_index()
    accion_dist.columns = ["ACCION", "TABLAS"]

    fig_accion = px.bar(
        accion_dist,
        x="ACCION",
        y="TABLAS",
        color="ACCION",
        text="TABLAS",
        color_discrete_map={
            "ELIMINAR": "#d62728",
            "ANALIZAR": "#ffbf00",
            "CONSERVAR": "#2ca02c"
        },
        title="Acción recomendada"
    )
    col_accion.plotly_chart(fig_accion, use_container_width=True)

    # ----- Uso -----
    uso_dist = ta["USO"].value_counts().reset_index()
    uso_dist.columns = ["USO", "TABLAS"]

    fig_uso = px.bar(
        uso_dist,
        x="USO",
        y="TABLAS",
        color="USO",
        text="TABLAS",
        color_discrete_map={
            "CON_DATOS": "#1f77b4",
            "SIN_DATOS": "#9467bd"
        },
        title="Uso real de las tablas"
    )
    col_uso.plotly_chart(fig_uso, use_container_width=True)

    st.divider()

    # ---------------- POR ESQUEMA ----------------
    esquema_dist = ta.groupby("ESQUEMA").size().reset_index(name="TABLAS")

    fig_esquema = px.bar(
        esquema_dist,
        x="TABLAS",
        y="ESQUEMA",
        orientation="h",
        text="TABLAS",
        title="Distribución de tablas por esquema"
    )
    st.plotly_chart(fig_esquema, use_container_width=True)

# =====================================================
# TAB 2 – ANÁLISIS TABLA POR TABLA
# =====================================================
with tab2:
    st.subheader(" Análisis dirigido y toma de decisiones")

    f1, f2, f3, f4 = st.columns(4)
    r_sel = f1.multiselect("Riesgo", ta["RIESGO"].unique(), ta["RIESGO"].unique())
    a_sel = f2.multiselect("Acción", ta["ACCION"].unique(), ta["ACCION"].unique())
    e_sel = f3.multiselect("Esquema", ta["ESQUEMA"].unique(), ta["ESQUEMA"].unique())
    u_sel = f4.multiselect("Uso", ta["USO"].unique(), ta["USO"].unique())

    taf = ta[
        ta["RIESGO"].isin(r_sel) &
        ta["ACCION"].isin(a_sel) &
        ta["ESQUEMA"].isin(e_sel) &
        ta["USO"].isin(u_sel)
    ]

    d1, d2, d3 = st.columns(3)
    d1.metric("Tablas seleccionadas", taf.shape[0])
    d2.metric("A eliminar", (taf["ACCION"] == "ELIMINAR").sum())
    d3.metric("A analizar", (taf["ACCION"] == "ANALIZAR").sum())

    st.dataframe(taf, use_container_width=True)

# =====================================================
#                TAB 3 – BENCHMARK
# =====================================================
# =====================================================
# CARGA DE BENCHMARK (OBLIGATORIO)
# =====================================================
if FILE_BENCH.exists():
    df_bench = pd.read_excel(FILE_BENCH)
else:
    df_bench = None


with tab3:

    st.subheader("Benchmark estructural 2024 vs 2026")
    st.markdown(
        "Este análisis muestra la evolución de la estructura "
        "de la base de datos entre los periodos evaluados."
    )

    # Segmentador por estado (CORRECTO)
    estado_sel = st.multiselect(
        "Filtrar por estado de tabla",
        options=sorted(df_bench["estado"].unique()),
        default=sorted(df_bench["estado"].unique())
    )

    # Aplicar filtro
    dfb = df_bench[df_bench["estado"].isin(estado_sel)]

    # KPI dinámico
    st.metric(
        "Tablas impactadas por el filtro",
        dfb.shape[0]
    )

    st.divider()

    # Layout: gráfico + leyenda
    col_graf, col_legend = st.columns([2, 1])

    # Preparar datos del gráfico
    estado_dist = (
        dfb["estado"]
        .value_counts()
        .reset_index()
    )
    estado_dist.columns = ["ESTADO", "TABLAS"]

    # Gráfico
    fig_bench = px.pie( #bar(
        estado_dist,
        names="ESTADO",  # Categorias
        values="TABLAS", # valores numéricos (en minúsculas)
        color="ESTADO",
        hole=0.5,        # Donut (0.0 = pie, >0 = donut)
        title="Distribución de tablas por estado",
        color_discrete_map={
            "Nueva": "#1f77b4",
            "Modificada": "#ff7f0e",
            "Eliminada": "#d62728",
            "Sin cambios": "#2ca02c"
        }
    )
    
    
    fig_bench.update_traces(
        texttemplate="%{value} <br>(%{percent})",
        textfont_size=14
    )


    col_graf.plotly_chart(fig_bench, use_container_width=True)

    # Leyenda explicativa
    col_legend.markdown("""
###  Leyenda de estados

- **🟦 Nueva**  
  Tablas que no existían en el periodo anterior.

- **🟧 Modificada**  
  Tablas con cambios estructurales.

- **🟥 Eliminada**  
  Tablas que desaparecieron del modelo.

- **🟩 Sin cambios**  
  Tablas que se mantienen iguales.

** Interpretación:**  
Permite entender crecimiento, limpieza o estabilidad del modelo.
""")

    st.divider()

    # Detalle
    st.subheader("Detalle completo del Benchmark")
    st.dataframe(dfb, use_container_width=True)
