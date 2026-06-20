"""Carga y normalización de las bases del diagnóstico de cartera."""
import io
import unicodedata

import pandas as pd


def normalize_name(name: str) -> str:
    name = str(name).strip().lower()
    name = "".join(c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn")
    name = name.replace(" ", "_").replace("-", "_")
    while "__" in name:
        name = name.replace("__", "_")
    return name


CSV_ENCODINGS = ["utf-8", "utf-8-sig", "latin1", "cp1252"]


def read_any(uploaded_file) -> pd.DataFrame:
    """Lee un archivo subido (csv o excel) a un DataFrame."""
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".csv"):
        df = None
        last_error = None
        for encoding in CSV_ENCODINGS:
            try:
                df = pd.read_csv(io.BytesIO(data), sep=None, engine="python", encoding=encoding)
                break
            except UnicodeDecodeError as exc:
                last_error = exc
                continue
            except Exception:
                try:
                    df = pd.read_csv(io.BytesIO(data), sep=";", encoding=encoding)
                    break
                except UnicodeDecodeError as exc:
                    last_error = exc
                    continue
        if df is None:
            raise last_error
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
    if total in (0, None) or pd.isna(total):
        return 0.0
    return 100.0 * part / total
