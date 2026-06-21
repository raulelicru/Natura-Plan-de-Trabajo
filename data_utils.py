"""Carga y normalización de las bases del diagnóstico de cartera."""
import io
import unicodedata

import numpy as np
import pandas as pd


def normalize_name(name: str) -> str:
    name = str(name).strip().lower()
    name = "".join(c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn")
    name = name.replace(" ", "_").replace("-", "_")
    while "__" in name:
        name = name.replace("__", "_")
    return name


CSV_ENCODINGS = ["utf-8-sig", "utf-8", "cp1252", "latin1"]


def decode_bytes(data: bytes) -> str:
    """Decodifica bytes a texto probando varias codificaciones comunes en Latinoamérica."""
    for encoding in CSV_ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin1", errors="replace")


def read_any(uploaded_file) -> pd.DataFrame:
    """Lee un archivo subido (csv o excel) a un DataFrame."""
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".csv"):
        text = decode_bytes(data)
        try:
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
        except Exception:
            df = pd.read_csv(io.StringIO(text), sep=";")
    else:
        df = pd.read_excel(io.BytesIO(data))
    df.columns = [str(c).strip() for c in df.columns]
    return df


def guess_column(columns, candidates):
    """Busca en `columns` la primera coincidencia (normalizada) con alguno de `candidates`."""
    norm_map = {normalize_name(c): c for c in columns}
    for cand in candidates:
        cand_n = normalize_name(cand)
        if cand_n in norm_map:
            return norm_map[cand_n]
    for cand in candidates:
        cand_n = normalize_name(cand)
        for n, original in norm_map.items():
            if cand_n in n or n in cand_n:
                return original
    return None


def pct(part, total):
    if isinstance(total, pd.Series) or isinstance(part, pd.Series):
        part_arr = part.to_numpy(dtype=float) if isinstance(part, pd.Series) else np.asarray(part, dtype=float)
        total_arr = total.to_numpy(dtype=float) if isinstance(total, pd.Series) else np.asarray(total, dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            result = np.where((total_arr == 0) | np.isnan(total_arr), 0.0, 100.0 * part_arr / total_arr)
        if isinstance(part, pd.Series):
            return pd.Series(result, index=part.index)
        return result
    if total in (0, None) or pd.isna(total):
        return 0.0
    return 100.0 * part / total
