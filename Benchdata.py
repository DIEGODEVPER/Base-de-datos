import pandas as pd
from pathlib import Path

# ===============================
# 1. Rutas de archivos (carpeta data)
# ===============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

file_2024 = DATA_DIR / "Extraccion_DB_SIFODS_2024.xlsx"
file_2026 = DATA_DIR / "Extraccion_DB_SIFODS_2026.xlsx"

# ===============================
# 2. Cargar archivos
# ===============================
df24 = pd.read_excel(file_2024, sheet_name=0, engine="openpyxl")
df26 = pd.read_excel(file_2026, sheet_name=0, engine="openpyxl")

# ===============================
# 3. Normalización
# ===============================
def normalize(df):
    df = df.copy()
    df["tabla_id"] = (
        df["Esquema"].astype(str).str.strip() + "." +
        df["Nombre_Tabla"].astype(str).str.strip()
    )
    return df

df24 = normalize(df24)
df26 = normalize(df26)

# ===============================
# 4. Agregación por tabla
# ===============================
tag24 = (
    df24
    .groupby("tabla_id")
    .agg(
        campos_2024=("Nombre_Campo", "count"),
        registros_2024=("Total_Registros", "max")
    )
    .reset_index()
)

tag26 = (
    df26
    .groupby("tabla_id")
    .agg(
        campos_2026=("Nombre_Campo", "count"),
        registros_2026=("Total_Registros", "max")
    )
    .reset_index()
)

# ===============================
# 5. Benchmarking
# ===============================
benchmark = tag24.merge(tag26, on="tabla_id", how="outer")

def estado_tabla(row):
    if pd.isna(row["campos_2024"]):
        return "Nueva"
    if pd.isna(row["campos_2026"]):
        return "Eliminada"
    if row["campos_2024"] == row["campos_2026"]:
        return "Sin cambios"
    return "Modificada"

benchmark["estado"] = benchmark.apply(estado_tabla, axis=1)

benchmark["delta_campos"] = (
    benchmark["campos_2026"].fillna(0)
    - benchmark["campos_2024"].fillna(0)
)

benchmark["delta_registros"] = (
    benchmark["registros_2026"].fillna(0)
    - benchmark["registros_2024"].fillna(0)
)

# ===============================
# 6. Exportar resultado
# ===============================
output_file = BASE_DIR / "Benchmark_SIFODS_2024_vs_2026.xlsx"
benchmark.to_excel(output_file, index=False, engine="openpyxl")

print("Benchmark ejecutado correctamente")
print(f"Archivo generado en: {output_file}")