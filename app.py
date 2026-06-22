"""Diagnóstico Inicial de Cartera - Plan de Acción de Cobranza."""
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from data_utils import guess_column, pct, read_any

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = px.colors.qualitative.Bold

st.set_page_config(page_title="Diagnóstico de Cartera", layout="wide")
st.title("Diagnóstico Inicial de Cartera")
st.caption(
    "Línea base de recuperación, contactabilidad y productividad operativa "
    "para el plan de acción de cobranza."
)

# ---------------------------------------------------------------------------
# Carga de bases
# ---------------------------------------------------------------------------
st.sidebar.header("1. Cargar bases")
remesa_file = st.sidebar.file_uploader("Remesa (Cartera Asignada)", type=["csv", "xlsx", "xls"])
pagos_file = st.sidebar.file_uploader("Pagos", type=["csv", "xlsx", "xls"])
vicidial_file = st.sidebar.file_uploader("Vicidial", type=["csv", "xlsx", "xls"])
sms_file = st.sidebar.file_uploader("SMS", type=["csv", "xlsx", "xls"])
reminder_file = st.sidebar.file_uploader("Reminder / IVR", type=["csv", "xlsx", "xls"])

if not remesa_file:
    st.info("Sube al menos la base **Remesa** para iniciar el diagnóstico.")
    st.stop()

remesa = read_any(remesa_file)
pagos = read_any(pagos_file) if pagos_file else None
vicidial = read_any(vicidial_file) if vicidial_file else None
sms = read_any(sms_file) if sms_file else None
reminder = read_any(reminder_file) if reminder_file else None

# ---------------------------------------------------------------------------
# Mapeo de columnas
# ---------------------------------------------------------------------------
st.sidebar.header("2. Mapear columnas")


def col_select(label, df, candidates, key):
    options = ["(ninguna)"] + list(df.columns)
    guess = guess_column(df.columns, candidates)
    idx = options.index(guess) if guess in options else 0
    return st.sidebar.selectbox(label, options, index=idx, key=key)


with st.sidebar.expander("Remesa", expanded=False):
    r_codigo = col_select("Código de cliente", remesa, ["codigo_de_cliente", "codigo_cliente"], "r_codigo")
    r_saldo = col_select("Saldo asignado", remesa, ["saldo_asignado", "saldo"], "r_saldo")
    r_aging = col_select("Aging de morosidad (temporalidad)", remesa, ["aging_de_morosidad", "aging", "temporalidad"], "r_aging")
    r_estado = col_select("Estado", remesa, ["estado"], "r_estado")
    r_estado_residencia = col_select(
        "Estado de residencia (geográfico)",
        remesa,
        ["direccion_de_residencia_estado", "estado_residencia", "estado_de_residencia"],
        "r_estado_residencia",
    )
    r_camino = col_select("Camino de crecimiento", remesa, ["camino_de_crecimiento", "camino_crecimiento"], "r_camino")
    r_segmento = col_select("Segmentación rep", remesa, ["segmentacion_rep", "segmentacion"], "r_segmento")

p_codigo = p_pago = None
if pagos is not None:
    with st.sidebar.expander("Pagos", expanded=False):
        p_codigo = col_select("Código de cliente", pagos, ["codigo_de_cliente", "codigo_cliente"], "p_codigo")
        p_pago = col_select("Pago aplicado", pagos, ["pago_aplicado", "monto_pagado", "pago"], "p_pago")

v_codigo = v_status = v_status_name = v_ejecutivo = v_fecha = v_contacto = None
if vicidial is not None:
    with st.sidebar.expander("Vicidial", expanded=False):
        v_codigo = col_select("Código de cliente", vicidial, ["codigo_de_cliente", "codigo_cliente"], "v_codigo")
        v_status = col_select("Status", vicidial, ["status"], "v_status")
        v_status_name = col_select("Status name", vicidial, ["status_name"], "v_status_name")
        v_ejecutivo = col_select("Ejecutivo / agente", vicidial, ["ejecutivo", "agente", "user", "usuario"], "v_ejecutivo")
        v_fecha = col_select("Fecha/hora de llamada", vicidial, ["fecha", "call_date", "fecha_llamada", "hora"], "v_fecha")
        v_contacto = col_select("Contactabilidad (columna AO)", vicidial, ["contactabilidad", "contacto"], "v_contacto")
        v_contact_statuses = st.multiselect(
            "Status considerados 'contacto efectivo'",
            sorted(vicidial[v_status_name].dropna().unique().tolist()) if v_status_name != "(ninguna)" else [],
            key="v_contact_statuses",
        )
        v_contacto_statuses = st.multiselect(
            "Valores de la columna de contactabilidad considerados 'contacto efectivo'",
            sorted(vicidial[v_contacto].dropna().unique().tolist()) if v_contacto != "(ninguna)" else [],
            key="v_contacto_statuses",
        )

s_codigo = s_estado = None
if sms is not None:
    with st.sidebar.expander("SMS", expanded=False):
        s_codigo = col_select("Código de cliente", sms, ["codigo_de_cliente", "codigo_cliente"], "s_codigo")
        s_estado = col_select("Estado de envío", sms, ["estado", "status", "resultado"], "s_estado")
        s_entregado_statuses = st.multiselect(
            "Status considerados 'entregado/contacto'",
            sorted(sms[s_estado].dropna().unique().tolist()) if s_estado != "(ninguna)" else [],
            key="s_entregado_statuses",
        )

rm_codigo = rm_estado = rm_duracion = None
if reminder is not None:
    with st.sidebar.expander("Reminder / IVR", expanded=False):
        rm_codigo = col_select("Nocodigo (código de cliente)", reminder, ["nocodigo", "codigo_de_cliente"], "rm_codigo")
        rm_estado = col_select("Estado de llamada", reminder, ["estado_llamada", "estado", "resultado"], "rm_estado")
        rm_duracion = col_select("Duración de llamada", reminder, ["duracion", "duracion_llamada", "duration"], "rm_duracion")
        rm_contestada_statuses = st.multiselect(
            "Estados considerados 'contestada'",
            sorted(reminder[rm_estado].dropna().unique().tolist()) if rm_estado != "(ninguna)" else [],
            key="rm_contestada_statuses",
        )

NA = "(ninguna)"


def col_or_none(value):
    return None if value == NA else value


r_codigo, r_saldo, r_aging, r_estado, r_estado_residencia, r_camino, r_segmento = (
    col_or_none(x) for x in (r_codigo, r_saldo, r_aging, r_estado, r_estado_residencia, r_camino, r_segmento)
)
p_codigo, p_pago = (col_or_none(x) for x in (p_codigo, p_pago)) if pagos is not None else (None, None)
if vicidial is not None:
    v_codigo, v_status, v_status_name, v_ejecutivo, v_fecha, v_contacto = (
        col_or_none(x) for x in (v_codigo, v_status, v_status_name, v_ejecutivo, v_fecha, v_contacto)
    )
if sms is not None:
    s_codigo, s_estado = (col_or_none(x) for x in (s_codigo, s_estado))
if reminder is not None:
    rm_codigo, rm_estado, rm_duracion = (col_or_none(x) for x in (rm_codigo, rm_estado, rm_duracion))

if not r_codigo:
    st.error("Debes mapear el código de cliente en Remesa para continuar.")
    st.stop()

remesa = remesa.copy()
remesa[r_codigo] = remesa[r_codigo].astype(str).str.strip()
if r_saldo:
    remesa[r_saldo] = pd.to_numeric(remesa[r_saldo], errors="coerce").fillna(0)

# ---------------------------------------------------------------------------
# Cruces de información
# ---------------------------------------------------------------------------
recupero_por_cliente = pd.DataFrame(columns=[r_codigo, "monto_recuperado"])
if pagos is not None and p_codigo and p_pago:
    pagos = pagos.copy()
    pagos[p_codigo] = pagos[p_codigo].astype(str).str.strip()
    pagos[p_pago] = pd.to_numeric(pagos[p_pago], errors="coerce").fillna(0)
    recupero_por_cliente = (
        pagos.groupby(p_codigo, as_index=False)[p_pago]
        .sum()
        .rename(columns={p_codigo: r_codigo, p_pago: "monto_recuperado"})
    )

gestion_vicidial_por_cliente = pd.DataFrame(columns=[r_codigo, "llamadas_vicidial"])
if vicidial is not None and v_codigo:
    vicidial = vicidial.copy()
    vicidial[v_codigo] = vicidial[v_codigo].astype(str).str.strip()
    gestion_vicidial_por_cliente = (
        vicidial.groupby(v_codigo, as_index=False).size()
        .rename(columns={v_codigo: r_codigo, "size": "llamadas_vicidial"})
    )

gestion_sms_por_cliente = pd.DataFrame(columns=[r_codigo, "sms_enviados"])
if sms is not None and s_codigo:
    sms = sms.copy()
    sms[s_codigo] = sms[s_codigo].astype(str).str.strip()
    gestion_sms_por_cliente = (
        sms.groupby(s_codigo, as_index=False).size()
        .rename(columns={s_codigo: r_codigo, "size": "sms_enviados"})
    )

gestion_reminder_por_cliente = pd.DataFrame(columns=[r_codigo, "envios_reminder"])
if reminder is not None and rm_codigo:
    reminder = reminder.copy()
    reminder[rm_codigo] = reminder[rm_codigo].astype(str).str.strip()
    gestion_reminder_por_cliente = (
        reminder.groupby(rm_codigo, as_index=False).size()
        .rename(columns={rm_codigo: r_codigo, "size": "envios_reminder"})
    )

base = remesa.merge(recupero_por_cliente, on=r_codigo, how="left")
base = base.merge(gestion_vicidial_por_cliente, on=r_codigo, how="left")
base = base.merge(gestion_sms_por_cliente, on=r_codigo, how="left")
base = base.merge(gestion_reminder_por_cliente, on=r_codigo, how="left")
base["monto_recuperado"] = base.get("monto_recuperado", 0).fillna(0)
base["llamadas_vicidial"] = base.get("llamadas_vicidial", 0).fillna(0)
base["sms_enviados"] = base.get("sms_enviados", 0).fillna(0)
base["envios_reminder"] = base.get("envios_reminder", 0).fillna(0)

# ---------------------------------------------------------------------------
# Etiquetas de temporalidad (Tem-1, Tem-2, Tem-3...)
# ---------------------------------------------------------------------------
AGING_MAP = {}
if r_aging:

    def _aging_sort_key(v):
        s = str(v)
        m = re.search(r"-?\d+(\.\d+)?", s)
        return (0, float(m.group())) if m else (1, s)

    _uniques = sorted(base[r_aging].dropna().unique(), key=_aging_sort_key)
    AGING_MAP = {v: f"Tem-{i + 1}" for i, v in enumerate(_uniques)}


def relabel_aging(df, col):
    """Reemplaza los valores crudos de aging_de_morosidad por Tem-1, Tem-2, etc."""
    if col == r_aging and AGING_MAP:
        df = df.copy()
        df[col] = df[col].map(AGING_MAP).fillna(df[col])
    return df


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tabs = st.tabs(
    [
        "Plan de Trabajo",
        "Dashboard Ejecutivo",
        "Inventario de Cartera",
        "Recuperación",
        "Gestión Telefónica",
        "Gestión Automática",
        "Oportunidades",
        "Efectividad por Canal",
        "Línea Base / Exportar",
    ]
)

total_cuentas = len(base)
total_saldo = base[r_saldo].sum() if r_saldo else 0
total_recuperado = base["monto_recuperado"].sum()


def dist_table(df, col, value_col=None):
    if value_col:
        g = df.groupby(col, dropna=False).agg(
            cuentas=(col, "size"), saldo=(value_col, "sum")
        ).reset_index()
        g["pct_cuentas"] = pct(g["cuentas"], g["cuentas"].sum())
        g["pct_saldo"] = pct(g["saldo"], g["saldo"].sum())
    else:
        g = df.groupby(col, dropna=False).size().reset_index(name="cuentas")
        g["pct_cuentas"] = pct(g["cuentas"], g["cuentas"].sum())
    return g.sort_values("cuentas", ascending=False)


MONEY_KEYWORDS = ("saldo", "monto", "recuperado")


def money_config(df):
    return {
        c: st.column_config.NumberColumn(format="%,.2f")
        for c in df.columns
        if any(k in c.lower() for k in MONEY_KEYWORDS)
    }


def is_pct_col(c):
    return "%" in c or c.lower().startswith("pct_")


def pct_config(df):
    return {c: st.column_config.NumberColumn(format="%.2f%%") for c in df.columns if is_pct_col(c)}


def table_config(df):
    return {**money_config(df), **pct_config(df)}


TABLE_COLUMN_ORDER = [
    "cuentas", "pct_cuentas",
    "saldo", "pct_saldo",
    "llamadas", "contactos", "% Contactabilidad",
    "saldo_asignado", "monto_recuperado", "pct_recuperacion",
]


def reorder_table(df, col):
    """Ordena: columna de categoría, cuentas, % cuentas, saldo, % saldo (y variantes)."""
    ordered = [col] + [c for c in TABLE_COLUMN_ORDER if c in df.columns]
    rest = [c for c in df.columns if c not in ordered]
    return df[ordered + rest]


def vicidial_contacto_mask(df):
    """Máscara de contacto efectivo: prioriza la columna de contactabilidad (AO) sobre status_name."""
    if v_contacto:
        return df[v_contacto].isin(st.session_state.get("v_contacto_statuses", []))
    if v_status_name:
        return df[v_status_name].isin(st.session_state.get("v_contact_statuses", []))
    return pd.Series(False, index=df.index)


# --- Plan de Trabajo (resumen ejecutivo / metodología) ---------------------
with tabs[0]:
    st.subheader("Plan de Trabajo de Cobranza — Diagnóstico Basado en Datos")
    st.markdown(
        """
Este diagnóstico integra **toda la cartera asignada** con cada canal de gestión
(llamadas, SMS, recordatorios automáticos y pagos) en un solo modelo de datos,
conectado por el código único de cliente. El objetivo es contar con evidencia
verificable para sustentar las decisiones del plan de acción y dar seguimiento
a su impacto semana a semana.
"""
    )

    st.markdown("#### Metodología")
    st.markdown(
        """
1. **Una sola fuente de verdad.** Remesa, Pagos, Vicidial, SMS y Reminder/IVR se
   cruzan automáticamente por código de cliente — sin reconciliación manual.
2. **Indicadores accionables.** Cada cifra (recuperación, contactabilidad,
   efectividad por canal) está diseñada para activar una decisión específica,
   no solo para reportar.
3. **Línea base y seguimiento.** Los mismos indicadores se vuelven a medir cada
   semana durante 4 semanas, lo que permite demostrar el impacto real de cada
   ajuste operativo.
"""
    )

    st.markdown("#### Lo que la cartera actual demuestra")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cuentas bajo gestión", f"{total_cuentas:,}")
    k2.metric("Saldo bajo diagnóstico", f"${total_saldo:,.0f}")
    k3.metric("Recuperado a la fecha", f"${total_recuperado:,.0f}")
    k4.metric("% Recuperación", f"{pct(total_recuperado, total_saldo):.2f}%")

    fortalezas, oportunidades = [], []

    if r_aging:
        g_aging = relabel_aging(base, r_aging).groupby(r_aging, dropna=False).agg(
            saldo=(r_saldo, "sum") if r_saldo else (r_aging, "size"),
            recuperado=("monto_recuperado", "sum"),
        ).reset_index()
        g_aging["pct_rec"] = pct(g_aging["recuperado"], g_aging["saldo"])
        if len(g_aging):
            best = g_aging.sort_values("pct_rec", ascending=False).iloc[0]
            worst = g_aging.sort_values("pct_rec", ascending=True).iloc[0]
            fortalezas.append(
                f"**{best[r_aging]}** es la temporalidad con mejor recuperación "
                f"({best['pct_rec']:.2f}%) — evidencia de que la estrategia de gestión "
                f"actual funciona cuando se aplica de forma oportuna."
            )
            if worst[r_aging] != best[r_aging]:
                oportunidades.append(
                    f"Replicar ese mismo enfoque en **{worst[r_aging]}** representa la "
                    f"siguiente oportunidad de mayor retorno del plan."
                )

    if vicidial is not None and v_codigo and (v_contacto or v_status_name):
        contacto_pct = pct(vicidial_contacto_mask(vicidial).sum(), len(vicidial))
        fortalezas.append(
            f"La gestión telefónica alcanza **{contacto_pct:.2f}%** de contactabilidad "
            f"medida directamente desde Vicidial, con trazabilidad por ejecutivo, estado y "
            f"segmentación."
        )

    canal_candidatos = []
    if vicidial is not None and v_codigo:
        canal_candidatos.append(("Llamadas (Vicidial)", pct(vicidial_contacto_mask(vicidial).sum(), len(vicidial)) if (v_contacto or v_status_name) else None))
    if sms is not None and s_estado:
        canal_candidatos.append(("SMS", pct(sms[s_estado].isin(st.session_state.get("s_entregado_statuses", [])).sum(), len(sms))))
    if reminder is not None and rm_estado:
        canal_candidatos.append(("Reminder/IVR", pct(reminder[rm_estado].isin(st.session_state.get("rm_contestada_statuses", [])).sum(), len(reminder))))
    canal_candidatos = [c for c in canal_candidatos if c[1] is not None]
    if canal_candidatos:
        mejor_canal = max(canal_candidatos, key=lambda c: c[1])
        fortalezas.append(
            f"**{mejor_canal[0]}** es hoy el canal más efectivo ({mejor_canal[1]:.2f}%), "
            f"una base sólida para priorizar la asignación de presupuesto y horas de gestión."
        )

    if r_segmento and r_saldo:
        g_seg = base.groupby(r_segmento, dropna=False).agg(
            saldo=(r_saldo, "sum"), recuperado=("monto_recuperado", "sum")
        ).reset_index()
        g_seg["pct_rec"] = pct(g_seg["recuperado"], g_seg["saldo"])
        alto_saldo = g_seg[g_seg["saldo"] > g_seg["saldo"].median()]
        if len(alto_saldo):
            oportunidad_seg = alto_saldo.sort_values("pct_rec").iloc[0]
            oportunidades.append(
                f"El segmento **{oportunidad_seg[r_segmento]}** concentra saldo "
                f"significativo con recuperación aún por capturar — siguiente paso "
                f"recomendado del plan de acción."
            )

    c_fort, c_op = st.columns(2)
    with c_fort:
        st.markdown("##### Fortalezas demostradas con datos")
        if fortalezas:
            for f in fortalezas:
                st.markdown(f"- {f}")
        else:
            st.caption("Sube las bases de Pagos y Vicidial para ver fortalezas cuantificadas.")
    with c_op:
        st.markdown("##### Próximos pasos del plan (oportunidades)")
        if oportunidades:
            for o in oportunidades:
                st.markdown(f"- {o}")
        else:
            st.caption("Aún no hay suficiente información cruzada para priorizar siguientes pasos.")

    st.markdown("#### Por qué este modelo es replicable")
    st.markdown(
        """
El mismo proceso de cruce de bases, cálculo de indicadores y línea base se aplica
a **cualquier remesa nueva, en cualquier periodo**, con resultados comparables.
Esto convierte el diagnóstico en una capacidad permanente del equipo — no en un
ejercicio aislado — y es la base para sostener la mejora de recuperación de
forma consistente, periodo tras periodo. El detalle completo de cada análisis
está disponible en las pestañas siguientes, y la línea base exportable en
**Línea Base / Exportar**.
"""
    )

# --- Dashboard Ejecutivo ---------------------------------------------------
with tabs[1]:
    st.subheader("Resumen Ejecutivo")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cuentas asignadas", f"{total_cuentas:,}")
    c2.metric("Saldo asignado", f"${total_saldo:,.0f}")
    c3.metric("Recuperado", f"${total_recuperado:,.0f}")
    c4.metric("% Recuperación", f"{pct(total_recuperado, total_saldo):.1f}%")

    if r_estado_residencia:
        top_estados = dist_table(base, r_estado_residencia, r_saldo).sort_values("saldo", ascending=True).tail(10)
        top_estados[r_estado_residencia] = top_estados[r_estado_residencia].astype(str)
        fig = px.bar(
            top_estados,
            x="saldo",
            y=r_estado_residencia,
            orientation="h",
            color="saldo",
            color_continuous_scale="Sunset",
            text="saldo",
            title="Saldo asignado por estado (top 10)",
        )
        fig.update_traces(texttemplate="$%{text:,.0f}")
        fig.update_layout(yaxis_title="", xaxis_title="Saldo asignado", coloraxis_showscale=False)
        fig.update_yaxes(type="category")
        st.plotly_chart(fig, use_container_width=True)
    elif r_estado:
        d = dist_table(base, r_estado, r_saldo).sort_values("saldo", ascending=True)
        d[r_estado] = d[r_estado].astype(str)
        fig = px.bar(
            d, x="saldo", y=r_estado, orientation="h", color="saldo",
            color_continuous_scale="Sunset", title="Saldo asignado por estado",
        )
        fig.update_layout(coloraxis_showscale=False)
        fig.update_yaxes(type="category")
        st.plotly_chart(fig, use_container_width=True)
    if r_aging:
        fig2 = px.pie(
            dist_table(relabel_aging(base, r_aging), r_aging, r_saldo),
            names=r_aging,
            values="saldo",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Vivid,
            title="Saldo por temporalidad",
        )
        fig2.update_traces(textinfo="percent+label", pull=0.02)
        st.plotly_chart(fig2, use_container_width=True)

# --- Inventario --------------------------------------------------------
with tabs[2]:
    st.subheader("Inventario General de Cartera")
    c1, c2, c3 = st.columns(3)
    c1.metric("Número de cuentas", f"{total_cuentas:,}")
    c2.metric("Saldo total asignado", f"${total_saldo:,.0f}")
    c3.metric("Saldo promedio por cuenta", f"${(total_saldo / total_cuentas if total_cuentas else 0):,.0f}")

    for label, col in [
        ("Distribución por temporalidad", r_aging),
        ("Distribución por estado", r_estado),
        ("Distribución por estado de residencia", r_estado_residencia),
        ("Distribución por camino de crecimiento", r_camino),
        ("Distribución por segmentación rep", r_segmento),
    ]:
        if col:
            st.markdown(f"**{label}**")
            base_rel = relabel_aging(base, col)
            t_dist = dist_table(base_rel, col, r_saldo).sort_values("saldo", ascending=False)
            if col in (r_estado, r_estado_residencia):
                t_dist = t_dist.head(10)
            st.dataframe(reorder_table(t_dist, col), use_container_width=True, column_config=table_config(t_dist))

            recup = base_rel.groupby(col, dropna=False)["monto_recuperado"].sum().reset_index()
            t_chart = t_dist.merge(recup, on=col, how="left")
            t_chart["monto_recuperado"] = t_chart["monto_recuperado"].fillna(0)
            t_chart = t_chart.sort_values("saldo", ascending=False).copy()
            t_chart[col] = t_chart[col].astype(str)
            t_melt = t_chart.melt(
                id_vars=col,
                value_vars=["saldo", "monto_recuperado"],
                var_name="Concepto",
                value_name="Monto",
            )
            t_melt["Concepto"] = t_melt["Concepto"].map(
                {"saldo": "Saldo asignado", "monto_recuperado": "Monto recuperado"}
            )
            fig = px.bar(
                t_melt,
                x="Monto",
                y=col,
                color="Concepto",
                orientation="h",
                barmode="group",
                text="Monto",
                color_discrete_sequence=["#636EFA", "#00CC96"],
                title=f"Inventario vs. recuperación — {label}"
                + (" (top 10)" if col in (r_estado, r_estado_residencia) else ""),
                category_orders={col: t_chart[col].tolist()},
            )
            fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside", textfont_size=13)
            fig.update_yaxes(type="category", autorange="reversed", tickfont_size=14)
            fig.update_xaxes(tickfont_size=13)
            fig.update_layout(
                yaxis_title="",
                xaxis_title="Monto ($)",
                height=max(420, 70 * t_chart[col].nunique()),
                font=dict(size=14),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=10, r=10, t=80, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

# --- Recuperación --------------------------------------------------------
with tabs[3]:
    st.subheader("Análisis de Recuperación")
    c1, c2 = st.columns(2)
    c1.metric("Recuperación total", f"${total_recuperado:,.0f}")
    c2.metric("Recuperación %", f"{pct(total_recuperado, total_saldo):.1f}%")

    for label, col in [
        ("Recuperación por temporalidad", r_aging),
        ("Recuperación por estado", r_estado),
        ("Recuperación por camino de crecimiento", r_camino),
        ("Recuperación por segmentación rep", r_segmento),
    ]:
        if col:
            g = relabel_aging(base, col).groupby(col, dropna=False).agg(
                saldo_asignado=(r_saldo, "sum") if r_saldo else (col, "size"),
                monto_recuperado=("monto_recuperado", "sum"),
            ).reset_index()
            g["pct_recuperacion"] = pct(g["monto_recuperado"], g["saldo_asignado"])
            st.markdown(f"**{label}**")
            g_show = g.sort_values("pct_recuperacion", ascending=False)
            if col in (r_estado, r_estado_residencia):
                g_show = g_show.head(10)
            st.dataframe(reorder_table(g_show, col), use_container_width=True, column_config=table_config(g_show))

            g_chart = g_show.copy()
            g_chart[col] = g_chart[col].astype(str)
            fig_pct = px.bar(
                g_chart,
                x="pct_recuperacion",
                y=col,
                orientation="h",
                color="pct_recuperacion",
                color_continuous_scale="Tealgrn",
                text="pct_recuperacion",
                title=f"% de recuperación — {label}",
                category_orders={col: g_chart[col].tolist()},
            )
            fig_pct.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            fig_pct.update_yaxes(type="category", tickfont_size=14)
            fig_pct.update_layout(
                yaxis_title="",
                xaxis_title="% Recuperación",
                coloraxis_showscale=False,
                height=max(380, 60 * g_chart[col].nunique()),
                font=dict(size=13),
                margin=dict(l=10, r=10, t=60, b=10),
            )
            st.plotly_chart(fig_pct, use_container_width=True)
            st.caption("La gráfica de saldo asignado vs. recuperado está en la pestaña **Inventario de Cartera**.")

# --- Gestión Telefónica (Vicidial) --------------------------------------
with tabs[4]:
    st.subheader("Análisis de Gestión Telefónica (Vicidial)")
    if vicidial is None:
        st.info("Sube la base Vicidial para ver este análisis.")
    else:
        total_llamadas = len(vicidial)
        cuentas_gestionadas = vicidial[v_codigo].nunique() if v_codigo else 0
        contacto_mask = vicidial_contacto_mask(vicidial)
        contactadas = contacto_mask.sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de llamadas", f"{total_llamadas:,}")
        c2.metric("Cuentas gestionadas", f"{cuentas_gestionadas:,}")
        c3.metric("Contactabilidad", f"{pct(contactadas, total_llamadas):.1f}%")

        st.markdown("**Contactación (Contacto vs. No contacto)**")
        contacto_df = pd.DataFrame(
            {
                "Resultado": ["Contacto", "No contacto"],
                "Llamadas": [contactadas, total_llamadas - contactadas],
            }
        )
        fig_contacto = px.pie(
            contacto_df,
            names="Resultado",
            values="Llamadas",
            hole=0.45,
            color="Resultado",
            color_discrete_map={"Contacto": "#00CC96", "No contacto": "#EF553B"},
            title="% de contactación",
        )
        fig_contacto.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_contacto, use_container_width=True)

        if v_status_name:
            st.markdown("**Resultados por status_name**")
            d_status = vicidial.groupby(v_status_name, dropna=False).size().reset_index(name="cantidad_llamadas")
            contactos_status = (
                vicidial.assign(__contactado__=contacto_mask)
                .groupby(v_status_name, dropna=False)["__contactado__"]
                .sum()
                .reset_index(name="contactos")
            )
            d_status = d_status.merge(contactos_status, on=v_status_name, how="left")
            d_status["% Contacto"] = pct(d_status["contactos"], d_status["cantidad_llamadas"])
            d_status = d_status.sort_values("cantidad_llamadas", ascending=False).drop(columns="contactos")
            st.dataframe(d_status, use_container_width=True, column_config=table_config(d_status))

        if v_fecha:
            try:
                horas = pd.to_datetime(vicidial[v_fecha], errors="coerce").dt.hour
                dist_horario = pd.DataFrame({"Hora": horas, "__contactado__": contacto_mask}).dropna(subset=["Hora"])
                g_hora = dist_horario.groupby("Hora").agg(
                    Llamadas=("__contactado__", "size"), Contactos=("__contactado__", "sum")
                ).reset_index()
                g_hora["% Contactación"] = pct(g_hora["Contactos"], g_hora["Llamadas"])
                g_hora = g_hora.sort_values("Hora")
                st.markdown("**Llamadas por hora del día**")
                fig_hora = make_subplots(specs=[[{"secondary_y": True}]])
                fig_hora.add_trace(
                    go.Bar(x=g_hora["Hora"], y=g_hora["Llamadas"], name="Llamadas", marker_color="#636EFA"),
                    secondary_y=False,
                )
                fig_hora.add_trace(
                    go.Scatter(
                        x=g_hora["Hora"],
                        y=g_hora["% Contactación"],
                        name="% Contactación",
                        mode="lines+markers",
                        line=dict(color="#EF553B", width=3),
                        marker=dict(size=8),
                    ),
                    secondary_y=True,
                )
                fig_hora.update_layout(title="Llamadas por hora del día y % de contactación", xaxis_title="Hora")
                fig_hora.update_yaxes(title_text="Llamadas", secondary_y=False)
                fig_hora.update_yaxes(title_text="% Contactación", ticksuffix="%", secondary_y=True)
                st.plotly_chart(fig_hora, use_container_width=True)
            except Exception:
                st.warning("No se pudo interpretar la columna de fecha/hora.")

# --- Gestión Automática (Reminder) --------------------------------------
with tabs[5]:
    st.subheader("Análisis de Gestión Automática (Reminder / IVR)")
    if reminder is None:
        st.info("Sube la base Reminder/IVR para ver este análisis.")
    else:
        total_enviados = len(reminder)
        contestadas = (
            reminder[rm_estado].isin(st.session_state.get("rm_contestada_statuses", [])).sum()
            if rm_estado
            else 0
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Registros enviados", f"{total_enviados:,}")
        c2.metric("Llamadas contestadas", f"{contestadas:,}")
        c3.metric("Tasa de contacto", f"{pct(contestadas, total_enviados):.1f}%")

        if rm_duracion:
            dur = pd.to_numeric(reminder[rm_duracion], errors="coerce")
            st.metric("Duración promedio de llamadas", f"{dur.mean():.1f}")
        if rm_estado:
            st.markdown("**Resultados por estado de llamada**")
            d_rm = dist_table(reminder, rm_estado)
            st.dataframe(d_rm, use_container_width=True)
            fig_rm = px.pie(
                d_rm,
                names=rm_estado,
                values="cuentas",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
                title="Resultados por estado de llamada (Reminder/IVR)",
            )
            fig_rm.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_rm, use_container_width=True)

# --- Oportunidades --------------------------------------------------------
with tabs[6]:
    st.subheader("Identificación de Oportunidades")

    def lowest_recovery(col):
        g = relabel_aging(base, col).groupby(col, dropna=False).agg(
            saldo_asignado=(r_saldo, "sum") if r_saldo else (col, "size"),
            monto_recuperado=("monto_recuperado", "sum"),
        ).reset_index()
        g["pct_recuperacion"] = pct(g["monto_recuperado"], g["saldo_asignado"])
        return g.sort_values("pct_recuperacion")

    if r_estado:
        st.markdown("**Estados con menor recuperación**")
        t_low = lowest_recovery(r_estado).head(10)
        st.dataframe(reorder_table(t_low, r_estado), use_container_width=True, column_config=table_config(t_low))
    if r_aging:
        st.markdown("**Temporalidades con menor recuperación**")
        t_low = lowest_recovery(r_aging).head(10)
        st.dataframe(reorder_table(t_low, r_aging), use_container_width=True, column_config=table_config(t_low))
    if r_segmento:
        g = lowest_recovery(r_segmento)
        st.markdown("**Segmentos con mayor potencial de recuperación** (alto saldo, baja recuperación)")
        t_seg = g[g["saldo_asignado"] > g["saldo_asignado"].median()].sort_values("pct_recuperacion").head(10)
        st.dataframe(reorder_table(t_seg, r_segmento), use_container_width=True, column_config=table_config(t_seg))
    if vicidial is not None and v_ejecutivo and (v_contacto or v_status_name):
        st.markdown("**Ejecutivos con mejor desempeño** (mayor contactabilidad)")
        vic_perf = vicidial.copy()
        vic_perf["__contactado__"] = vicidial_contacto_mask(vicidial)
        perf = vic_perf.groupby(v_ejecutivo, dropna=False).agg(
            llamadas=(v_ejecutivo, "size"),
            contactos=("__contactado__", "sum"),
        ).reset_index()
        perf["pct_contactabilidad"] = pct(perf["contactos"], perf["llamadas"])
        st.dataframe(perf.sort_values("pct_contactabilidad", ascending=False).head(10), use_container_width=True)

    canales_disponibles = []
    if vicidial is not None:
        canal_v = pct(
            vicidial_contacto_mask(vicidial).sum() if (v_contacto or v_status_name) else 0,
            len(vicidial),
        )
        canales_disponibles.append({"Canal": "Vicidial", "% Contactabilidad": canal_v})
    if sms is not None:
        canal_s = pct(
            sms[s_estado].isin(st.session_state.get("s_entregado_statuses", [])).sum() if s_estado else 0,
            len(sms),
        )
        canales_disponibles.append({"Canal": "SMS", "% Contactabilidad": canal_s})
    if reminder is not None:
        canal_r = pct(
            reminder[rm_estado].isin(st.session_state.get("rm_contestada_statuses", [])).sum() if rm_estado else 0,
            len(reminder),
        )
        canales_disponibles.append({"Canal": "Reminder/IVR", "% Contactabilidad": canal_r})
    if canales_disponibles:
        st.markdown("**Canales con mayor efectividad**")
        st.dataframe(
            pd.DataFrame(canales_disponibles).sort_values("% Contactabilidad", ascending=False),
            use_container_width=True,
        )

# --- Efectividad por Canal -----------------------------------------------
with tabs[7]:
    st.subheader("Efectividad por Canal (Llamadas, SMS, Reminder)")

    canal_rows = []
    if vicidial is not None:
        contactos_v = vicidial_contacto_mask(vicidial).sum() if (v_contacto or v_status_name) else 0
        canal_rows.append({
            "Canal": "Llamadas (Vicidial)",
            "Gestiones/Envíos": len(vicidial),
            "Cuentas alcanzadas": vicidial[v_codigo].nunique() if v_codigo else None,
            "Contactos efectivos": contactos_v,
            "% Efectividad": pct(contactos_v, len(vicidial)),
        })
    if sms is not None:
        entregados_s = (
            sms[s_estado].isin(st.session_state.get("s_entregado_statuses", [])).sum()
            if s_estado
            else 0
        )
        canal_rows.append({
            "Canal": "SMS",
            "Gestiones/Envíos": len(sms),
            "Cuentas alcanzadas": sms[s_codigo].nunique() if s_codigo else None,
            "Contactos efectivos": entregados_s,
            "% Efectividad": pct(entregados_s, len(sms)),
        })
    if reminder is not None:
        contestadas_r = (
            reminder[rm_estado].isin(st.session_state.get("rm_contestada_statuses", [])).sum()
            if rm_estado
            else 0
        )
        canal_rows.append({
            "Canal": "Reminder / IVR",
            "Gestiones/Envíos": len(reminder),
            "Cuentas alcanzadas": reminder[rm_codigo].nunique() if rm_codigo else None,
            "Contactos efectivos": contestadas_r,
            "% Efectividad": pct(contestadas_r, len(reminder)),
        })

    if canal_rows:
        canal_df = pd.DataFrame(canal_rows)
        st.dataframe(canal_df, use_container_width=True)
        try:
            fig_canal = px.funnel(
                canal_df.sort_values("% Efectividad", ascending=False),
                x="% Efectividad",
                y="Canal",
                color="Canal",
                color_discrete_sequence=px.colors.qualitative.Bold,
                title="% Efectividad por canal",
            )
            st.plotly_chart(fig_canal, use_container_width=True)
        except Exception:
            fig_canal = px.bar(
                canal_df.sort_values("% Efectividad", ascending=True),
                x="% Efectividad", y="Canal", orientation="h", color="Canal",
                color_discrete_sequence=px.colors.qualitative.Bold,
                title="% Efectividad por canal",
            )
            st.plotly_chart(fig_canal, use_container_width=True)

        st.markdown("**Recuperación asociada a cuentas gestionadas por canal**")
        rec_rows = []
        for canal_col, label in [("llamadas_vicidial", "Llamadas (Vicidial)"), ("sms_enviados", "SMS"), ("envios_reminder", "Reminder / IVR")]:
            if canal_col in base.columns and base[canal_col].sum() > 0:
                gestionados = base[base[canal_col] > 0]
                rec_rows.append({
                    "Canal": label,
                    "Cuentas gestionadas": len(gestionados),
                    "Saldo asignado": gestionados[r_saldo].sum() if r_saldo else None,
                    "Monto recuperado": gestionados["monto_recuperado"].sum(),
                    "% Recuperación": pct(gestionados["monto_recuperado"].sum(), gestionados[r_saldo].sum() if r_saldo else 0),
                })
        if rec_rows:
            rec_df = pd.DataFrame(rec_rows)
            st.dataframe(rec_df, use_container_width=True, column_config=money_config(rec_df))
            rec_melt = rec_df.melt(
                id_vars="Canal", value_vars=["Saldo asignado", "Monto recuperado"],
                var_name="Concepto", value_name="Monto",
            )
            fig_rec = px.bar(
                rec_melt,
                x="Canal",
                y="Monto",
                color="Concepto",
                barmode="group",
                color_discrete_sequence=["#636EFA", "#00CC96"],
                title="Saldo asignado vs. recuperado por canal",
            )
            st.plotly_chart(fig_rec, use_container_width=True)
    else:
        st.info("Sube al menos una base de Vicidial, SMS o Reminder/IVR para comparar canales.")

# --- Línea base / Exportar -----------------------------------------------
with tabs[8]:
    st.subheader("Línea Base de Indicadores")
    st.caption("Indicadores a comparar durante las próximas 4 semanas del plan de acción.")
    resumen = {
        "Cuentas asignadas": total_cuentas,
        "Saldo total asignado": total_saldo,
        "Monto recuperado": total_recuperado,
        "% Recuperación": pct(total_recuperado, total_saldo),
    }
    if vicidial is not None:
        resumen["Llamadas Vicidial"] = len(vicidial)
        resumen["Cuentas gestionadas (Vicidial)"] = vicidial[v_codigo].nunique() if v_codigo else None
        if v_contacto or v_status_name:
            resumen["% Contactabilidad Vicidial"] = pct(vicidial_contacto_mask(vicidial).sum(), len(vicidial))
    if sms is not None:
        resumen["SMS enviados"] = len(sms)
        if s_estado:
            resumen["% Efectividad SMS"] = pct(
                sms[s_estado].isin(st.session_state.get("s_entregado_statuses", [])).sum(), len(sms)
            )
    if reminder is not None:
        resumen["Registros Reminder"] = len(reminder)
        if rm_estado:
            resumen["% Tasa de contacto Reminder"] = pct(
                reminder[rm_estado].isin(st.session_state.get("rm_contestada_statuses", [])).sum(), len(reminder)
            )

    resumen_df = pd.DataFrame(list(resumen.items()), columns=["Indicador", "Valor"])
    st.dataframe(resumen_df, use_container_width=True)
    st.download_button(
        "Descargar línea base (CSV)",
        resumen_df.to_csv(index=False).encode("utf-8"),
        file_name="linea_base_indicadores.csv",
        mime="text/csv",
    )
    st.download_button(
        "Descargar base cruzada completa (CSV)",
        base.to_csv(index=False).encode("utf-8"),
        file_name="cartera_diagnostico.csv",
        mime="text/csv",
    )
