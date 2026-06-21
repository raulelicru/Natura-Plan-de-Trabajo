"""Diagnóstico Inicial de Cartera - Plan de Acción de Cobranza."""
import pandas as pd
import plotly.express as px
import streamlit as st

from data_utils import guess_column, pct, read_any

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

v_codigo = v_status = v_status_name = v_ejecutivo = v_fecha = None
if vicidial is not None:
    with st.sidebar.expander("Vicidial", expanded=False):
        v_codigo = col_select("Código de cliente", vicidial, ["codigo_de_cliente", "codigo_cliente"], "v_codigo")
        v_status = col_select("Status", vicidial, ["status"], "v_status")
        v_status_name = col_select("Status name", vicidial, ["status_name"], "v_status_name")
        v_ejecutivo = col_select("Ejecutivo / agente", vicidial, ["ejecutivo", "agente", "user", "usuario"], "v_ejecutivo")
        v_fecha = col_select("Fecha/hora de llamada", vicidial, ["fecha", "call_date", "fecha_llamada", "hora"], "v_fecha")
        v_contact_statuses = st.multiselect(
            "Status considerados 'contacto efectivo'",
            sorted(vicidial[v_status_name].dropna().unique().tolist()) if v_status_name != "(ninguna)" else [],
            key="v_contact_statuses",
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
    v_codigo, v_status, v_status_name, v_ejecutivo, v_fecha = (
        col_or_none(x) for x in (v_codigo, v_status, v_status_name, v_ejecutivo, v_fecha)
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
# Tabs
# ---------------------------------------------------------------------------
tabs = st.tabs(
    [
        "Dashboard Ejecutivo",
        "Inventario de Cartera",
        "Temporalidad",
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


# --- Dashboard Ejecutivo ---------------------------------------------------
with tabs[0]:
    st.subheader("Resumen Ejecutivo")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cuentas asignadas", f"{total_cuentas:,}")
    c2.metric("Saldo asignado", f"${total_saldo:,.0f}")
    c3.metric("Recuperado", f"${total_recuperado:,.0f}")
    c4.metric("% Recuperación", f"{pct(total_recuperado, total_saldo):.1f}%")

    if r_estado_residencia:
        top_estados = dist_table(base, r_estado_residencia, r_saldo).sort_values("saldo", ascending=False).head(15)
        fig = px.bar(
            top_estados, x=r_estado_residencia, y="saldo", title="Saldo asignado por estado (top 15)"
        )
        fig.update_xaxes(categoryorder="total descending")
        st.plotly_chart(fig, use_container_width=True)
    elif r_estado:
        fig = px.bar(dist_table(base, r_estado, r_saldo), x=r_estado, y="saldo", title="Saldo asignado por estado")
        st.plotly_chart(fig, use_container_width=True)
    if r_aging:
        fig2 = px.pie(dist_table(base, r_aging, r_saldo), names=r_aging, values="saldo", title="Saldo por temporalidad")
        st.plotly_chart(fig2, use_container_width=True)

# --- Inventario --------------------------------------------------------
with tabs[1]:
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
            t_dist = dist_table(base, col, r_saldo)
            st.dataframe(t_dist, use_container_width=True, column_config=money_config(t_dist))

# --- Temporalidad --------------------------------------------------------
with tabs[2]:
    st.subheader("Análisis de Temporalidad (Aging de Morosidad)")
    if r_aging:
        t = dist_table(base, r_aging, r_saldo).rename(
            columns={r_aging: "Temporalidad", "cuentas": "Número de cuentas", "saldo": "Saldo asignado", "pct_saldo": "% Participación"}
        )
        t_show = t[["Temporalidad", "Número de cuentas", "Saldo asignado", "% Participación"]]
        st.dataframe(t_show, use_container_width=True, column_config=money_config(t_show))
        t_chart = t.copy()
        t_chart["Etiqueta"] = t_chart["% Participación"].map(lambda v: f"{v:.2f}%")
        st.plotly_chart(
            px.bar(t_chart, x="Temporalidad", y="Saldo asignado", text="Etiqueta"), use_container_width=True
        )
    else:
        st.warning("Mapea la columna de aging de morosidad en Remesa.")

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
            g = base.groupby(col, dropna=False).agg(
                saldo_asignado=(r_saldo, "sum") if r_saldo else (col, "size"),
                monto_recuperado=("monto_recuperado", "sum"),
            ).reset_index()
            g["pct_recuperacion"] = pct(g["monto_recuperado"], g["saldo_asignado"])
            st.markdown(f"**{label}**")
            g_show = g.sort_values("monto_recuperado", ascending=False)
            st.dataframe(g_show, use_container_width=True, column_config=money_config(g_show))

# --- Gestión Telefónica (Vicidial) --------------------------------------
with tabs[4]:
    st.subheader("Análisis de Gestión Telefónica (Vicidial)")
    if vicidial is None:
        st.info("Sube la base Vicidial para ver este análisis.")
    else:
        total_llamadas = len(vicidial)
        cuentas_gestionadas = vicidial[v_codigo].nunique() if v_codigo else 0
        contactadas = (
            vicidial[v_status_name].isin(st.session_state.get("v_contact_statuses", [])).sum()
            if v_status_name
            else 0
        )
        c1, c2, c3 = st.columns(3)
        c1.metric("Total de llamadas", f"{total_llamadas:,}")
        c2.metric("Cuentas gestionadas", f"{cuentas_gestionadas:,}")
        c3.metric("Contactabilidad", f"{pct(contactadas, total_llamadas):.1f}%")

        if v_ejecutivo:
            st.markdown("**Gestiones por ejecutivo**")
            st.dataframe(dist_table(vicidial, v_ejecutivo), use_container_width=True)
        if v_status_name:
            st.markdown("**Resultados de llamada por status_name**")
            st.dataframe(dist_table(vicidial, v_status_name), use_container_width=True)
        if v_fecha:
            try:
                horas = pd.to_datetime(vicidial[v_fecha], errors="coerce").dt.hour
                dist_horario = horas.value_counts().sort_index().reset_index()
                dist_horario.columns = ["Hora", "Llamadas"]
                st.markdown("**Distribución de llamadas por horario**")
                st.plotly_chart(px.bar(dist_horario, x="Hora", y="Llamadas"), use_container_width=True)
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
            st.dataframe(dist_table(reminder, rm_estado), use_container_width=True)

# --- Oportunidades --------------------------------------------------------
with tabs[6]:
    st.subheader("Identificación de Oportunidades")

    def lowest_recovery(col):
        g = base.groupby(col, dropna=False).agg(
            saldo_asignado=(r_saldo, "sum") if r_saldo else (col, "size"),
            monto_recuperado=("monto_recuperado", "sum"),
        ).reset_index()
        g["pct_recuperacion"] = pct(g["monto_recuperado"], g["saldo_asignado"])
        return g.sort_values("pct_recuperacion")

    if r_estado:
        st.markdown("**Estados con menor recuperación**")
        t_low = lowest_recovery(r_estado).head(10)
        st.dataframe(t_low, use_container_width=True, column_config=money_config(t_low))
    if r_aging:
        st.markdown("**Temporalidades con menor recuperación**")
        t_low = lowest_recovery(r_aging).head(10)
        st.dataframe(t_low, use_container_width=True, column_config=money_config(t_low))
    if r_segmento:
        g = lowest_recovery(r_segmento)
        st.markdown("**Segmentos con mayor potencial de recuperación** (alto saldo, baja recuperación)")
        t_seg = g[g["saldo_asignado"] > g["saldo_asignado"].median()].sort_values("pct_recuperacion").head(10)
        st.dataframe(t_seg, use_container_width=True, column_config=money_config(t_seg))
    if vicidial is not None and v_ejecutivo and v_status_name:
        st.markdown("**Ejecutivos con mejor desempeño** (mayor contactabilidad)")
        contact_set = st.session_state.get("v_contact_statuses", [])
        perf = vicidial.groupby(v_ejecutivo, dropna=False).agg(
            llamadas=(v_ejecutivo, "size"),
            contactos=(v_status_name, lambda s: s.isin(contact_set).sum()),
        ).reset_index()
        perf["pct_contactabilidad"] = pct(perf["contactos"], perf["llamadas"])
        st.dataframe(perf.sort_values("pct_contactabilidad", ascending=False).head(10), use_container_width=True)

    canales_disponibles = []
    if vicidial is not None:
        canal_v = pct(
            vicidial[v_status_name].isin(st.session_state.get("v_contact_statuses", [])).sum() if v_status_name else 0,
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
        contactos_v = (
            vicidial[v_status_name].isin(st.session_state.get("v_contact_statuses", [])).sum()
            if v_status_name
            else 0
        )
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
        st.plotly_chart(
            px.bar(canal_df, x="Canal", y="% Efectividad", text="% Efectividad", title="% Efectividad por canal"),
            use_container_width=True,
        )

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
        if v_status_name:
            resumen["% Contactabilidad Vicidial"] = pct(
                vicidial[v_status_name].isin(st.session_state.get("v_contact_statuses", [])).sum(), len(vicidial)
            )
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
