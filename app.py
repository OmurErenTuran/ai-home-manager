import streamlit as st
import pandas as pd
import os
import hmac
from datetime import date, datetime
from backup import auto_backup_daily
from style import apply_style, hero, sidebar_brand, bottom_nav

from database import (
    create_tables,
    create_assets_table,

    add_payment,
    get_payments,
    delete_payment,
    update_payment,
    mark_payment_paid,
    mark_payment_pending,

    add_asset,
    get_assets,
    delete_asset,

    create_recurring_payments_table,
    add_recurring_payment,
    get_recurring_payments,
    delete_recurring_payment,
    toggle_recurring_payment,
    create_monthly_recurring_payments,

    create_installments_table,
    add_installment,
    get_installments,
    delete_installment,
    create_installment_payments,

    create_maintenance_table,
    get_asset_intervals,
    update_asset_maintenance_plan,
    add_maintenance_record,
    get_maintenance_records,
    delete_maintenance_record,
    add_paid_payment,
    create_income_table,
    add_income,
    get_incomes,
    delete_income,
    create_vehicles_tables,
    add_vehicle,
    get_vehicles,
    update_vehicle,
    delete_vehicle,
    add_vehicle_expense,
    get_vehicle_expenses,
    delete_vehicle_expense,
    count_vehicle_alerts,
    create_recurring_incomes_table,
    add_recurring_income,
    get_recurring_incomes,
    delete_recurring_income,
    toggle_recurring_income,
    mark_recurring_income_done,
    create_monthly_fixed_incomes,
    get_pending_variable_incomes,
    update_recurring_payment,
    create_calendar_events_table,
    add_calendar_event,
    get_calendar_events,
    delete_calendar_event,
    create_credit_cards_tables,
    add_card_installment,
    get_card_installments,
    get_card_installments_for_month,
    add_credit_card,
    get_credit_cards,
    update_credit_card,
    delete_credit_card,
    add_card_statement,
    get_card_statements,
    delete_card_statement,
    reset_all_data
    
)
from ai_invoice import analyze_invoice, analyze_bill
# BDDK 1 Ekim 2026 kararı: kart limiti 100.000 TL ve altındaysa
# dönem borcunun %20'si, üzerindeyse %40'ı asgari ödemedir.
# Yönetmelik değişirse sadece bu üç satırı güncelle.
MIN_PAY_LIMIT = 100_000
MIN_PAY_RATE_LOW = 0.20
MIN_PAY_RATE_HIGH = 0.40
def min_pay_rate(limit):
    return (
        MIN_PAY_RATE_HIGH if (limit or 0) > MIN_PAY_LIMIT
        else MIN_PAY_RATE_LOW
    )


# =====================================================
# AYARLAR
# =====================================================

st.set_page_config(
    page_title="AI Home Manager",
    page_icon="🏠",
    layout="wide"
)
apply_style()
def require_password():
    """APP_PASSWORD tanımlıysa şifre sorar; tanımlı değilse hiçbir şey yapmaz."""
    expected = os.getenv("APP_PASSWORD", "")

    if not expected or st.session_state.get("auth_ok"):
        return

    st.markdown("## 🔒 AI Home Manager")

    with st.form("login_form"):
        pw = st.text_input("Şifre", type="password")
        ok = st.form_submit_button("Giriş", type="primary")

    if ok:
        if hmac.compare_digest(pw.encode(), expected.encode()):
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Şifre yanlış.")

    st.stop()


require_password()
create_tables()
create_assets_table()
create_maintenance_table()
create_vehicles_tables()
auto_backup_daily()
create_recurring_payments_table()
create_monthly_recurring_payments()
create_installments_table()
create_income_table()
create_recurring_incomes_table()
create_monthly_fixed_incomes()
create_calendar_events_table()
create_credit_cards_tables()
# =====================================================
# YARDIMCI FONKSİYON
# =====================================================

def get_payment_status(payment):

    payment_id, name, amount, due_date, category, status = payment

    if status == "Ödendi":
        return "🟢 Ödendi"

    due = datetime.strptime(
        due_date,
        "%Y-%m-%d"
    ).date()

    today = date.today()

    if due < today:
        return "🔴 Gecikti"

    return "🟡 Bekliyor"
# =====================================================
# BİLDİRİM SİSTEMİ
# =====================================================

import time

NOTIFICATION_SECONDS = 5  # bildirim ekranda kaç saniye kalsın

if "notification_queue" not in st.session_state:
    st.session_state.notification_queue = []


def notify(message, icon="🔔"):
    st.session_state.notification_queue.append(
        {
            "message": message,
            "icon": icon,
            "created": time.time()
        }
    )


# Süresi dolmayan bildirimleri tekrar göster
now = time.time()

active_notifications = [
    n for n in st.session_state.notification_queue
    if now - n["created"] < NOTIFICATION_SECONDS
]

st.session_state.notification_queue = active_notifications

for n in active_notifications:

    remaining = max(
        1,
        int(NOTIFICATION_SECONDS - (now - n["created"]))
    )

    st.toast(
        n["message"],
        icon=n["icon"],
        duration=remaining
    )

# =====================================================
# BEKLEYEN DEĞİŞKEN GELİRLER
# =====================================================

def render_pending_incomes():

    for (rid, p_name, p_last, p_due, p_cat) in get_pending_variable_incomes():

        with st.container(border=True):

            st.markdown(f"💵 **{p_name}** için bu ayın geliri bekleniyor")
            st.caption(f"Tarih: {p_due} • Tutarı girin, gelirlerinize eklensin.")

            c1, c2, c3 = st.columns([2, 1, 1])

            with c1:
                p_amount = st.number_input(
                    "Kazanılan tutar (₺)",
                    min_value=0.0,
                    value=float(p_last or 0),
                    step=100.0,
                    key=f"pend_inc_amount_{rid}"
                )

            with c2:
                st.write("")
                if st.button(
                    "💾 Kaydet",
                    key=f"pend_inc_save_{rid}",
                    type="primary",
                    use_container_width=True
                ):
                    if p_amount <= 0:
                        st.error("Tutar 0'dan büyük olmalı.")
                    else:
                        add_income(p_name, p_amount, p_due, p_cat)
                        mark_recurring_income_done(rid, p_amount)
                        notify("Gelir kaydedildi!", "💵")
                        st.rerun()

            with c3:
                st.write("")
                if st.button(
                    "⏭️ Bu ay yok",
                    key=f"pend_inc_skip_{rid}",
                    use_container_width=True
                ):
                    mark_recurring_income_done(rid)
                    st.rerun()
# =====================================================
# SIDEBAR
# app.py içinde "# SIDEBAR" başlık yorumunun altındaki kodu,
# yani `st.sidebar.title("🏠 AI Home Manager")` satırından
# `st.sidebar.caption("AI Home Manager v0.2")` satırına
# (parantezi dahil) kadar olan kısmı bununla değiştir.
# `menu` değişkeni aynı değerleri üretmeye devam ediyor,
# bu yüzden sayfa bölümlerine (if/elif menu == ...) dokunma.
# =====================================================

# Sidebar menü butonlarının görünümü (sadece kozmetik)
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] .stButton > button {
        justify-content: flex-start;
        text-align: left;
        border-radius: 10px;
        padding: 0.55rem 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -------------------------------------------------
# MENÜ TANIMI: (sayfa anahtarı, ikon, görünen ad)
# Sayfa anahtarları if/elif menu == "..." ile aynı olmalı.
# -------------------------------------------------

NAV_ITEMS = [
    ("Dashboard", "🏠", "Ana Sayfa"),
    ("Takvim", "📅", "Takvim"),
    ("Finans Merkezi", "💰", "Finans Merkezi"),
    ("Ödemeler", "💳", "Ödemeler"),
    ("Kredi Kartları", "🏦", "Kredi Kartları"),
    ("Bakımlar", "🔧", "Bakımlar"),
    ("Ev Eşyalarım", "📦", "Ev Eşyalarım"),
    ("Harcamalar", "📊", "Harcamalar"),
    ("Araçlar", "🚗", "Araçlar"),
    ("Yedekleme", "💾", "Yedekleme"),
    ("🤖 AI Asistan", "🤖", "AI Asistan"),
]

if "menu" not in st.session_state:
    st.session_state.menu = "Dashboard"

# -------------------------------------------------
# ROZET VE ÖZET HESABI
# -------------------------------------------------

_nav_today = date.today()

_nav_overdue_payments = 0
_nav_upcoming_7 = 0
_nav_month_pending = 0.0

for (_pid, _pname, _pamount, _pdue, _pcat, _pstatus) in get_payments():

    if _pstatus == "Ödendi":
        continue

    try:
        _due = datetime.strptime(_pdue, "%Y-%m-%d").date()
    except ValueError:
        continue

    if _due < _nav_today:
        _nav_overdue_payments += 1
    elif (_due - _nav_today).days <= 7:
        _nav_upcoming_7 += 1

    if (_due.year, _due.month) == (_nav_today.year, _nav_today.month):
        _nav_month_pending += _pamount

_nav_overdue_maintenance = 0

for _asset in get_assets():

    _maint = _asset[7]

    if not _maint:
        continue

    try:
        if datetime.strptime(_maint, "%Y-%m-%d").date() < _nav_today:
            _nav_overdue_maintenance += 1
    except ValueError:
        continue

_nav_badges = {
    "Ödemeler": _nav_overdue_payments,
    "Bakımlar": _nav_overdue_maintenance,
    "Araçlar": count_vehicle_alerts(),
}

# -------------------------------------------------
# MARKA
# -------------------------------------------------

sidebar_brand()

st.sidebar.divider()

# -------------------------------------------------
# MENÜ
# -------------------------------------------------

for _i, (_key, _icon, _label) in enumerate(NAV_ITEMS):

    _badge = _nav_badges.get(_key, 0)

    _text = f"{_icon}  {_label}"

    if _badge:
        _text += f"   🔴 {_badge}"

    if st.sidebar.button(
        _text,
        key=f"nav_{_i}",
        type="primary" if st.session_state.menu == _key else "secondary",
        use_container_width=True
    ):
        st.session_state.menu = _key
        st.rerun()

menu = st.session_state.menu
bottom_nav(NAV_ITEMS, _nav_badges, st.session_state.menu)

st.sidebar.divider()

# -------------------------------------------------
# HIZLI ÖZET
# -------------------------------------------------

with st.sidebar.container(border=True):

    st.caption("BU AY BEKLEYEN")

    st.markdown(f"### ₺{_nav_month_pending:,.0f}")

    if _nav_overdue_payments:
        st.caption(f"🔴 {_nav_overdue_payments} gecikmiş ödeme")

    if _nav_upcoming_7:
        st.caption(f"🟡 {_nav_upcoming_7} ödeme 7 gün içinde")

    if not _nav_overdue_payments and not _nav_upcoming_7:
        st.caption("🟢 Acil ödeme yok")

# -------------------------------------------------
# ALT BİLGİ
# -------------------------------------------------

st.sidebar.caption(
    f"v0.3 • {_nav_today.day:02d}.{_nav_today.month:02d}.{_nav_today.year}"
)


# =====================================================
# VERİLER
# =====================================================

payments = get_payments()


# =====================================================
# DASHBOARD
# app.py içinde `if menu == "Dashboard":` bloğundan
# `elif menu == "Ödemeler":` satırına kadar olan kısmı
# bununla değiştir. (elif menu == "Ödemeler" satırı kalsın.)
# =====================================================

if menu == "Dashboard":

    from datetime import timedelta
    import plotly.express as px
    import plotly.graph_objects as go

    today = date.today()

    month_names = [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    ]

    # -------------------------------------------------
    # VERİYİ HAZIRLA
    # -------------------------------------------------

    rows = []

    for (payment_id, p_name, p_amount, p_due, p_category, p_status) in payments:
        rows.append(
            {
                "id": payment_id,
                "Ad": p_name,
                "Tutar": p_amount,
                "Tarih": datetime.strptime(p_due, "%Y-%m-%d").date(),
                "Kategori": p_category,
                "Durum": p_status
            }
        )

    df = pd.DataFrame(
        rows,
        columns=["id", "Ad", "Tutar", "Tarih", "Kategori", "Durum"]
    )

    df["Ay"] = df["Tarih"].apply(lambda d: d.strftime("%Y-%m"))

    this_month = today.strftime("%Y-%m")
    prev_month = (
        today.replace(day=1) - timedelta(days=1)
    ).strftime("%Y-%m")

    month_df = df[df["Ay"] == this_month]
    prev_df = df[df["Ay"] == prev_month]

    total = month_df["Tutar"].sum()
    paid_total = month_df[month_df["Durum"] == "Ödendi"]["Tutar"].sum()
    pending_total = total - paid_total
    prev_total = prev_df["Tutar"].sum()
    delta = total - prev_total

    unpaid_df = df[df["Durum"] != "Ödendi"]
    overdue_df = unpaid_df[unpaid_df["Tarih"] < today].sort_values("Tarih")
    upcoming_df = unpaid_df[
        (unpaid_df["Tarih"] >= today)
        & (unpaid_df["Tarih"] <= today + timedelta(days=14))
    ].sort_values("Tarih")

    # -------------------------------------------------
    # BAŞLIK
    # -------------------------------------------------

    hero(
        "🏠 Ev Özeti",
        "Ödemeleriniz, giderleriniz ve eşyalarınız tek bakışta.",
        f"{today.day} {month_names[today.month - 1]} {today.year}"
    )
    # -------------------------------------------------
    # GECİKMİŞ ÖDEME UYARISI
    # -------------------------------------------------

    if not overdue_df.empty:
        st.error(
            f"🔴 **{len(overdue_df)} gecikmiş ödemeniz var** — "
            f"toplam ₺{overdue_df['Tutar'].sum():,.2f}"
        )
    render_pending_incomes()

    # -------------------------------------------------
    # KPI KARTLARI
    # -------------------------------------------------

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        with st.container(border=True):
            st.metric(
                "Bu Ayın Gideri",
                f"₺{total:,.2f}",
                delta=(
                    f"₺{delta:,.2f} (geçen aya göre)"
                    if prev_total > 0 else None
                ),
                delta_color="inverse"
            )

    with k2:
        with st.container(border=True):
            st.metric("Ödenen", f"₺{paid_total:,.2f}")

    with k3:
        with st.container(border=True):
            st.metric("Bekleyen", f"₺{pending_total:,.2f}")

    with k4:
        with st.container(border=True):
            st.metric("Geciken", len(overdue_df))

    # -------------------------------------------------
    # İLERLEME ÇUBUĞU
    # -------------------------------------------------

    ratio = (paid_total / total) if total > 0 else 0

    st.progress(
        min(ratio, 1.0),
        text=(
            f"{month_names[today.month - 1]} ayı ödemelerinin "
            f"%{ratio * 100:.0f}'i tamamlandı"
        )
    )

    st.write("")

        # -------------------------------------------------
    # GELİR - GİDER ÖZETİ
    # -------------------------------------------------

    inc_rows = []

    for (inc_id, inc_name, inc_amount, inc_date, inc_cat) in get_incomes():
        try:
            inc_day = datetime.strptime(inc_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        inc_rows.append(
            {
                "Tutar": float(inc_amount),
                "Ay": inc_day.strftime("%Y-%m")
            }
        )

    inc_df = pd.DataFrame(inc_rows, columns=["Tutar", "Ay"])

    month_income = inc_df[inc_df["Ay"] == this_month]["Tutar"].sum()
    net_balance = month_income - total

    with st.container(border=True):

        st.subheader("💵 Gelir - Gider")

        if month_income <= 0:

            st.info(
                "Bu ay için gelir girilmemiş. 'Finans Merkezi' "
                "sayfasından gelir ekleyin."
            )

        else:

            spend_ratio = total / month_income

            g1, g2, g3 = st.columns(3)

            with g1:
                st.metric("Gelir", f"₺{month_income:,.2f}")

            with g2:
                st.metric("Gider (planlanan)", f"₺{total:,.2f}")

            with g3:
                st.metric(
                    "Net Bakiye",
                    f"₺{net_balance:,.2f}",
                    delta="Artıda" if net_balance >= 0 else "Ekside",
                    delta_color="normal" if net_balance >= 0 else "inverse"
                )

            st.progress(
                min(spend_ratio, 1.0),
                text=f"Gelirinin %{spend_ratio * 100:.0f}'i giderlere ayrıldı"
            )

            if spend_ratio > 1:
                st.error(
                    f"🔴 Bu ayın giderleri gelirini "
                    f"₺{total - month_income:,.2f} aşıyor."
                )
            elif spend_ratio > 0.85:
                st.warning(
                    "🟠 Gelirinin %85'inden fazlası giderlere gidiyor."
                )

    st.write("")

    # -------------------------------------------------
    # KREDİ KARTLARI DURUMU
    # -------------------------------------------------

    import calendar as cc_calendar

    cc_cards = get_credit_cards()

    if cc_cards:

        def cc_next_due(due_day):
            """Bugünden itibaren gelen ilk son ödeme günü."""
            d0 = date(
                today.year, today.month,
                min(due_day, cc_calendar.monthrange(today.year, today.month)[1])
            )
            if d0 >= today:
                return d0
            y0, m0 = (
                (today.year + 1, 1) if today.month == 12
                else (today.year, today.month + 1)
            )
            return date(
                y0, m0, min(due_day, cc_calendar.monthrange(y0, m0)[1])
            )

        cc_rows = []

        for (
            cc_id, cc_name, cc_last4, cc_limit, cc_stmt, cc_due_day
        ) in cc_cards:

            cc_unpaid = 0.0
            cc_min = 0.0
            cc_overdue = 0
            cc_nearest = None
            cc_periods = set()
            cc_rate = min_pay_rate(cc_limit)

            for (
                cc_sid, cc_period, cc_pid, cc_minp,
                cc_amount, cc_due_str, cc_status
            ) in get_card_statements(cc_id):

                cc_periods.add(cc_period)

                if cc_status is None or cc_status == "Ödendi":
                    continue

                try:
                    cc_due = datetime.strptime(cc_due_str, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    continue

                cc_amt = float(cc_amount or 0)

                cc_unpaid += cc_amt
                cc_min += cc_minp if cc_minp > 0 else cc_amt * cc_rate

                if cc_due < today:
                    cc_overdue += 1

                if cc_nearest is None or cc_due < cc_nearest:
                    cc_nearest = cc_due

            cc_next = cc_next_due(int(cc_due_day))
            cc_next_period = f"{cc_next.year}-{cc_next.month:02d}"

            if cc_nearest is not None:
                cc_days = (cc_nearest - today).days
                if cc_days < 0:
                    cc_badge = f"🔴 {abs(cc_days)} gün gecikti"
                elif cc_days == 0:
                    cc_badge = "🟠 Bugün son gün"
                elif cc_days <= 7:
                    cc_badge = f"🟡 {cc_days} gün kaldı"
                else:
                    cc_badge = f"🟢 {cc_days} gün kaldı"
            elif cc_next_period in cc_periods:
                cc_badge = "🟢 Bu dönem ödendi"
            else:
                cc_days = (cc_next - today).days
                cc_badge = (
                    "⚪ Ekstre girilmedi • son ödeme bugün"
                    if cc_days == 0
                    else f"⚪ Ekstre girilmedi • son ödeme {cc_days} gün sonra"
                )

            cc_inst = sum(
                m[1] for m in get_card_installments_for_month(
                    cc_id, today.year, today.month
                )
            )

            cc_rows.append(
                {
                    "name": cc_name,
                    "last4": cc_last4,
                    "limit": float(cc_limit or 0),
                    "unpaid": cc_unpaid,
                    "min": cc_min,
                    "overdue": cc_overdue,
                    "badge": cc_badge,
                    "inst": cc_inst
                }
            )

        with st.container(border=True):

            st.subheader("🏦 Kredi Kartlarım")

            cc_t1, cc_t2, cc_t3 = st.columns(3)

            with cc_t1:
                st.metric(
                    "Ödenmemiş Ekstre",
                    f"₺{sum(r['unpaid'] for r in cc_rows):,.2f}"
                )

            with cc_t2:
                st.metric(
                    "Toplam Asgari Ödeme",
                    f"₺{sum(r['min'] for r in cc_rows):,.2f}",
                    help=(
                        "Ekstreye banka rakamı girildiyse o, girilmediyse "
                        "limite göre hesaplanan tahmin kullanılır."
                    )
                )

            with cc_t3:
                st.metric(
                    "Bu Ay Kart Taksitleri",
                    f"₺{sum(r['inst'] for r in cc_rows):,.2f}",
                    help="Bu ayın ekstrelerine yansıyan taksit toplamı."
                )

            st.write("")

            for cc_r in cc_rows:

                cc_a, cc_b, cc_c = st.columns([3, 2.5, 3])

                with cc_a:
                    st.markdown(
                        f"**🏦 {cc_r['name']}**"
                        + (f" •••• {cc_r['last4']}" if cc_r["last4"] else "")
                    )
                    st.caption(
                        f"Limit: ₺{cc_r['limit']:,.0f}"
                        if cc_r["limit"] else "Limit girilmedi"
                    )

                with cc_b:
                    st.markdown(f"**₺{cc_r['unpaid']:,.2f}**")
                    st.caption(
                        f"Asgari: ₺{cc_r['min']:,.2f}"
                        if cc_r["unpaid"] > 0 else "Ödenmemiş ekstre yok"
                    )

                with cc_c:
                    st.write(cc_r["badge"])
                    if cc_r["inst"] > 0:
                        st.caption(f"Bu ay taksit: ₺{cc_r['inst']:,.2f}")

                if cc_r["limit"] > 0 and cc_r["unpaid"] > 0:
                    st.progress(
                        min(cc_r["unpaid"] / cc_r["limit"], 1.0),
                        text=(
                            f"Ekstre borcu limitin "
                            f"%{min(cc_r['unpaid'] / cc_r['limit'], 1.0) * 100:.0f}'i"
                        )
                    )

            st.caption(
                "Ekstre eklemek ve ödemek için 'Kredi Kartları' menüsüne bakın."
            )

        st.write("")

    # -------------------------------------------------
    # ORTA BÖLÜM: ÖDEMELER + KATEGORİ GRAFİĞİ
    # -------------------------------------------------

    left, right = st.columns([3, 2])

    with left:

        with st.container(border=True):

            st.subheader("📅 Ödeme Takvimi")

            if overdue_df.empty and upcoming_df.empty:

                st.success(
                    "Gecikmiş veya önümüzdeki 14 gün içinde "
                    "yaklaşan ödeme yok. 🎉"
                )

            else:

                shown = pd.concat(
                    [overdue_df, upcoming_df]
                ).head(8)

                for _, r in shown.iterrows():

                    days_left = (r["Tarih"] - today).days

                    if days_left < 0:
                        badge = f"🔴 {abs(days_left)} gün gecikti"
                    elif days_left == 0:
                        badge = "🟠 Bugün"
                    elif days_left == 1:
                        badge = "🟡 Yarın"
                    else:
                        badge = f"🟡 {days_left} gün kaldı"

                    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])

                    with c1:
                        st.markdown(f"**{r['Ad']}**")
                        st.caption(f"{r['Kategori']} • {r['Tarih']}")

                    with c2:
                        st.write(f"₺{r['Tutar']:,.2f}")

                    with c3:
                        st.write(badge)

                    with c4:
                        if st.button(
                            "✅ Ödendi",
                            key=f"dash_paid_{r['id']}",
                            use_container_width=True
                        ):
                            mark_payment_paid(int(r["id"]))
                            notify(
                                "Ödeme ödendi olarak işaretlendi!",
                                "✅"
                            )
                            st.rerun()

                if len(overdue_df) + len(upcoming_df) > 8:
                    st.caption(
                        "Tüm ödemeler için 'Ödemeler' menüsüne bakın."
                    )

    with right:

        with st.container(border=True):

            st.subheader("📊 Kategori Dağılımı")

            if month_df.empty:

                st.info("Bu ay için kategori verisi bulunmuyor.")

            else:

                chart_data = (
                    month_df.groupby("Kategori", as_index=False)["Tutar"]
                    .sum()
                    .sort_values("Tutar", ascending=False)
                )

                fig = px.pie(
                    chart_data,
                    names="Kategori",
                    values="Tutar",
                    hole=0.6
                )

                fig.update_traces(
                    textposition="inside",
                    textinfo="percent",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Tutar: ₺%{value:,.2f}<br>"
                        "Oran: %{percent}<extra></extra>"
                    ),
                    marker=dict(line=dict(color="white", width=2))
                )

                fig.update_layout(
                    height=340,
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.05,
                        xanchor="center",
                        x=0.5
                    ),
                    annotations=[
                        dict(
                            text=f"₺{total:,.0f}",
                            x=0.5,
                            y=0.5,
                            showarrow=False,
                            font=dict(size=22)
                        )
                    ]
                )

                st.plotly_chart(fig, use_container_width=True)

       # -------------------------------------------------
    # SON 6 AYLIK GELİR - GİDER
    # -------------------------------------------------

    with st.container(border=True):

        st.subheader("📈 Son 6 Ay Gelir - Gider")

        labels = []
        exp_values = []
        inc_values = []

        for i in range(5, -1, -1):

            y, m = today.year, today.month - i

            while m <= 0:
                m += 12
                y -= 1

            key = f"{y}-{m:02d}"

            labels.append(f"{month_names[m - 1][:3]} {y}")
            exp_values.append(df[df["Ay"] == key]["Tutar"].sum())
            inc_values.append(inc_df[inc_df["Ay"] == key]["Tutar"].sum())

        bar = go.Figure()

        bar.add_trace(
            go.Bar(
                name="Gelir",
                x=labels,
                y=inc_values,
                marker_color="#2ca02c",
                hovertemplate="%{x}<br>Gelir: ₺%{y:,.2f}<extra></extra>"
            )
        )

        bar.add_trace(
            go.Bar(
                name="Gider",
                x=labels,
                y=exp_values,
                marker_color="#d62728",
                hovertemplate="%{x}<br>Gider: ₺%{y:,.2f}<extra></extra>"
            )
        )

        bar.update_layout(
            barmode="group",
            height=320,
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis=dict(showgrid=True, title=None),
            xaxis=dict(title=None),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )

        st.plotly_chart(bar, use_container_width=True)
    # -------------------------------------------------
    # GARANTİ VE BAKIM UYARILARI
    # -------------------------------------------------

    with st.container(border=True):

        st.subheader("🛡️ Garanti ve Bakım Uyarıları")

        alerts = []

        for asset in get_assets():

            (
                a_id, a_name, a_brand, a_model, a_pdate,
                a_price, a_warranty, a_maint, a_notes
            ) = asset

            for label, value in (
                ("Garanti bitişi", a_warranty),
                ("Bakım", a_maint)
            ):

                if not value:
                    continue

                try:
                    d = datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    continue

                days = (d - today).days

                if days < 0 and label == "Garanti bitişi":
                    continue  # süresi dolmuş garantiyi tekrar uyarma

                if days <= 30:
                    alerts.append((a_name, label, value, days))

        if not alerts:

            st.success("Yaklaşan garanti veya bakım yok.")

        else:

            for a_name, label, value, days in sorted(
                alerts, key=lambda x: x[3]
            ):

                if days < 0:
                    st.error(
                        f"**{a_name}** — {label} {abs(days)} gün gecikti ({value})"
                    )
                else:
                    st.warning(
                        f"**{a_name}** — {label}: {days} gün kaldı ({value})"
                    )
# =====================================================
# ÖDEMELER
# app.py içinde `elif menu == "Ödemeler":` satırından
# `elif menu == "Bakımlar":` satırına kadar olan kısmı
# bununla değiştir. (elif menu == "Bakımlar" satırı kalsın.)
# =====================================================

elif menu == "Ödemeler":

    month_names = [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    ]

    categories = [
        "Elektrik", "Su", "Doğalgaz", "İnternet", "Kira",
        "Aidat", "Sigorta", "Cep Telefonu", "Taksit","Kredi Kartı", "Diğer"
    ]

    today = date.today()

    st.title("💳 Ödemeler")
    st.caption("Faturalarınızı, kira ve taksitlerinizi buradan yönetin.")

    # -------------------------------------------------
    # YENİ ÖDEME
    # -------------------------------------------------

    with st.expander("➕ Yeni Ödeme Ekle", expanded=False):

        with st.form("payment_form", clear_on_submit=True):

            f1, f2 = st.columns(2)

            with f1:
                new_name = st.text_input(
                    "Ödeme adı",
                    placeholder="Örn: Elektrik"
                )
                new_amount = st.number_input(
                    "Tutar (₺)",
                    min_value=0.0,
                    step=10.0
                )

            with f2:
                new_due_date = st.date_input("Son ödeme tarihi")
                new_category = st.selectbox("Kategori", categories)

            new_recurring = st.checkbox(
                "🔁 Her ay otomatik oluştur",
                help=(
                    "Sabit fiyatlı faturalar için kullanın. "
                    "Örneğin cep telefonu veya ev interneti."
                )
            )

            submitted = st.form_submit_button(
                "💾 Ödemeyi Kaydet",
                type="primary"
            )

            if submitted:

                if not new_name.strip():
                    st.error("Lütfen ödeme adını girin.")

                elif new_amount <= 0:
                    st.error("Tutar 0'dan büyük olmalı.")

                else:
                    add_payment(
                        new_name.strip(),
                        new_amount,
                        str(new_due_date),
                        new_category
                    )

                    if new_recurring:
                        add_recurring_payment(
                            new_name.strip(),
                            new_amount,
                            new_due_date.day,
                            new_category
                        )

                    notify("Ödeme başarıyla oluşturuldu!", "💳")
                    st.rerun()
        # -------------------------------------------------
    # FATURADAN ÖDEME EKLE (AI)
    # -------------------------------------------------

    with st.expander(
        "🤖 Faturadan Ödeme Ekle",
        expanded="bill_data" in st.session_state
    ):

        bn = st.session_state.get("bill_n", 0)

        bill_file = st.file_uploader(
            "Fatura PDF yükleyin (elektrik, su, doğalgaz, internet...)",
            type=["pdf"],
            key=f"bill_uploader_{bn}"
        )

        if bill_file is not None:

            if st.button(
                "🤖 Faturayı AI ile Analiz Et",
                key=f"bill_analyze_{bn}",
                use_container_width=True
            ):

                bill_ok = False

                with st.spinner("Fatura AI tarafından analiz ediliyor..."):

                    try:

                        bill = analyze_bill(bill_file)

                        for k in list(st.session_state.keys()):
                            if k.startswith("bill_f_"):
                                del st.session_state[k]

                        st.session_state["bill_data"] = {
                            "name": bill.bill_name,
                            "category": bill.category,
                            "amount": bill.amount,
                            "due_date": bill.due_date,
                            "note": bill.confidence_note
                        }

                        bill_ok = True

                    except Exception as e:

                        st.error(
                            f"❌ Fatura analiz edilirken hata oluştu: {e}"
                        )

                if bill_ok:
                    st.rerun()

        if "bill_data" in st.session_state:

            bd = st.session_state["bill_data"]

            st.info(
                "Tutarı ve son ödeme tarihini mutlaka kontrol edin, "
                "sonra kaydedin."
            )

            try:
                bill_due_default = datetime.strptime(
                    bd["due_date"], "%Y-%m-%d"
                ).date()
            except (ValueError, TypeError):
                bill_due_default = today

            b1, b2 = st.columns(2)

            with b1:
                bill_name = st.text_input(
                    "Ödeme adı",
                    value=bd["name"] or "",
                    key="bill_f_name"
                )
                bill_amount = st.number_input(
                    "Tutar (₺)",
                    min_value=0.0,
                    value=float(bd["amount"] or 0),
                    step=10.0,
                    key="bill_f_amount"
                )

            with b2:
                bill_due = st.date_input(
                    "Son ödeme tarihi",
                    value=bill_due_default,
                    key="bill_f_due"
                )
                bill_category = st.selectbox(
                    "Kategori",
                    categories,
                    index=(
                        categories.index(bd["category"])
                        if bd["category"] in categories
                        else len(categories) - 1
                    ),
                    key="bill_f_category"
                )

            bill_paid = st.checkbox(
                "Bu faturayı zaten ödedim",
                key="bill_f_paid"
            )

            st.caption(
                "🤖 **AI Güven Notu:** "
                + (bd["note"] or "AI tarafından not oluşturulmadı.")
            )

            if st.button(
                "💾 Ödemeyi Kaydet",
                type="primary",
                use_container_width=True,
                key="bill_f_save"
            ):

                if not bill_name.strip():
                    st.error("Lütfen ödeme adını girin.")

                elif bill_amount <= 0:
                    st.error("Tutar 0'dan büyük olmalı.")

                else:

                    if bill_paid:
                        add_paid_payment(
                            bill_name.strip(),
                            bill_amount,
                            str(bill_due),
                            bill_category
                        )
                    else:
                        add_payment(
                            bill_name.strip(),
                            bill_amount,
                            str(bill_due),
                            bill_category
                        )

                    del st.session_state["bill_data"]

                    for k in list(st.session_state.keys()):
                        if k.startswith("bill_f_"):
                            del st.session_state[k]

                    st.session_state["bill_n"] = bn + 1

                    notify("Fatura ödemesi eklendi!", "🧾")
                    st.rerun()

    # -------------------------------------------------
    # FİLTRELER
    # -------------------------------------------------

    st.write("")

    fc1, fc2, fc3, fc4, fc5 = st.columns([1.2, 1, 1.2, 1.3, 2])

    with fc1:
        selected_month = st.selectbox(
            "Ay",
            range(1, 13),
            index=today.month - 1,
            format_func=lambda x: month_names[x - 1],
            key="payment_month"
        )

    with fc2:
        selected_year = st.selectbox(
            "Yıl",
            range(today.year - 2, today.year + 6),
            index=2,
            key="payment_year"
        )

    with fc3:
        status_filter = st.selectbox(
            "Durum",
            ["Tümü", "Bekleyen", "Geciken", "Ödenen"],
            key="payment_status_filter"
        )

    with fc4:
        category_filter = st.selectbox(
            "Kategori",
            ["Tümü"] + categories,
            key="payment_category_filter"
        )

    with fc5:
        search_text = st.text_input(
            "Ara",
            placeholder="Ödeme adı ara...",
            key="payment_search"
        )

    # -------------------------------------------------
    # VERİYİ HAZIRLA
    # -------------------------------------------------

    month_items = []

    for (
        payment_id, p_name, p_amount, p_due, p_category, p_status
    ) in get_payments():

        due = datetime.strptime(p_due, "%Y-%m-%d").date()

        if due.month != selected_month or due.year != selected_year:
            continue

        if p_status == "Ödendi":
            state = "paid"
        elif due < today:
            state = "overdue"
        else:
            state = "pending"

        month_items.append(
            {
                "id": payment_id,
                "name": p_name,
                "amount": p_amount,
                "due_str": p_due,
                "due": due,
                "category": p_category,
                "state": state
            }
        )

    month_items.sort(key=lambda x: x["due"])

    # -------------------------------------------------
    # ÖZET KARTLARI (seçilen ay)
    # -------------------------------------------------

    m_total = sum(i["amount"] for i in month_items)
    m_paid = sum(i["amount"] for i in month_items if i["state"] == "paid")
    m_pending = m_total - m_paid
    m_overdue = sum(1 for i in month_items if i["state"] == "overdue")

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        with st.container(border=True):
            st.metric("Toplam", f"₺{m_total:,.2f}")

    with s2:
        with st.container(border=True):
            st.metric("Ödenen", f"₺{m_paid:,.2f}")

    with s3:
        with st.container(border=True):
            st.metric("Bekleyen", f"₺{m_pending:,.2f}")

    with s4:
        with st.container(border=True):
            st.metric("Geciken", m_overdue)

    if m_total > 0:
        ratio = m_paid / m_total
        st.progress(
            min(ratio, 1.0),
            text=f"Ödemelerin %{ratio * 100:.0f}'i tamamlandı"
        )

    st.divider()

    # -------------------------------------------------
    # FİLTRELERİ UYGULA
    # -------------------------------------------------

    status_map = {
        "Bekleyen": "pending",
        "Geciken": "overdue",
        "Ödenen": "paid"
    }

    filtered = month_items

    if status_filter != "Tümü":
        filtered = [
            i for i in filtered
            if i["state"] == status_map[status_filter]
        ]

    if category_filter != "Tümü":
        filtered = [
            i for i in filtered
            if i["category"] == category_filter
        ]

    if search_text.strip():
        q = search_text.strip().lower()
        filtered = [i for i in filtered if q in i["name"].lower()]

    # -------------------------------------------------
    # LİSTE BAŞLIĞI + CSV İNDİR
    # -------------------------------------------------

    lh1, lh2 = st.columns([4, 1])

    with lh1:
        st.subheader(
            f"📋 {month_names[selected_month - 1]} {selected_year} "
            f"({len(filtered)} ödeme)"
        )

    with lh2:
        if filtered:
            export_df = pd.DataFrame(
                [
                    {
                        "Ödeme": i["name"],
                        "Tutar": i["amount"],
                        "Son Ödeme Tarihi": i["due_str"],
                        "Kategori": i["category"],
                        "Durum": {
                            "paid": "Ödendi",
                            "overdue": "Gecikti",
                            "pending": "Bekliyor"
                        }[i["state"]]
                    }
                    for i in filtered
                ]
            )

            st.download_button(
                "⬇️ CSV indir",
                data=export_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=(
                    f"odemeler_{selected_year}_{selected_month:02d}.csv"
                ),
                mime="text/csv",
                use_container_width=True
            )

    # -------------------------------------------------
    # ÖDEME KARTLARI
    # -------------------------------------------------

    if not filtered:

        st.info("Bu filtrelere uyan ödeme bulunmuyor.")

    else:

        for item in filtered:

            pid = item["id"]
            days_left = (item["due"] - today).days

            if item["state"] == "paid":
                badge = "🟢 Ödendi"
            elif item["state"] == "overdue":
                badge = f"🔴 {abs(days_left)} gün gecikti"
            elif days_left == 0:
                badge = "🟠 Bugün son gün"
            elif days_left <= 7:
                badge = f"🟡 {days_left} gün kaldı"
            else:
                badge = "🟡 Bekliyor"

            with st.container(border=True):

                c1, c2, c3, c4 = st.columns([3, 1.5, 1.8, 1.5])

                with c1:
                    st.markdown(f"**{item['name']}**")
                    st.caption(
                        f"{item['category']} • Son ödeme: {item['due_str']}"
                    )

                with c2:
                    st.markdown(f"**₺{item['amount']:,.2f}**")

                with c3:
                    st.write(badge)

                with c4:
                    if item["state"] == "paid":
                        if st.button(
                            "↩️ Beklet",
                            key=f"pending_{pid}",
                            use_container_width=True
                        ):
                            mark_payment_pending(pid)
                            notify(
                                "Ödeme tekrar beklemeye alındı!",
                                "↩️"
                            )
                            st.rerun()
                    else:
                        if st.button(
                            "✅ Ödendi",
                            key=f"paid_{pid}",
                            type="primary",
                            use_container_width=True
                        ):
                            mark_payment_paid(pid)
                            notify(
                                "Ödeme ödendi olarak işaretlendi!",
                                "✅"
                            )
                            st.rerun()

                # ---------------------------------
                # DÜZENLE / SİL
                # ---------------------------------

                with st.expander("✏️ Düzenle / Sil"):

                    e1, e2 = st.columns(2)

                    with e1:
                        edit_name = st.text_input(
                            "Ödeme adı",
                            value=item["name"],
                            key=f"name_{pid}"
                        )

                        edit_amount = st.number_input(
                            "Tutar (₺)",
                            value=float(item["amount"]),
                            min_value=0.0,
                            key=f"amount_{pid}"
                        )

                    with e2:
                        edit_date = st.date_input(
                            "Tarih",
                            value=item["due"],
                            key=f"date_{pid}"
                        )

                        edit_category = st.selectbox(
                            "Kategori",
                            categories,
                            index=(
                                categories.index(item["category"])
                                if item["category"] in categories
                                else len(categories) - 1
                            ),
                            key=f"category_{pid}"
                        )

                    b1, b2 = st.columns(2)

                    with b1:
                        if st.button(
                            "💾 Değişiklikleri Kaydet",
                            key=f"save_{pid}",
                            use_container_width=True
                        ):
                            update_payment(
                                pid,
                                edit_name.strip(),
                                edit_amount,
                                str(edit_date),
                                edit_category
                            )
                            notify("Ödeme başarıyla güncellendi!", "✏️")
                            st.rerun()

                    with b2:
                        if st.button(
                            "🗑️ Sil",
                            key=f"delete_{pid}",
                            use_container_width=True
                        ):
                            delete_payment(pid)
                            notify("Ödeme başarıyla silindi!", "🗑️")
                            st.rerun()              
# =====================================================
# BAKIMLAR
# app.py içinde `elif menu == "Bakımlar":` satırından
# `elif menu == "Ev Eşyalarım":` satırına kadar olan kısmı
# bununla değiştir. (elif menu == "Ev Eşyalarım" satırı kalsın.)
# =====================================================

elif menu == "Bakımlar":

    import calendar
    import plotly.express as px

    today = date.today()

    # -------------------------------------------------
    # YARDIMCI FONKSİYONLAR
    # -------------------------------------------------

    def parse_date(value):
        if not value or not str(value).strip():
            return None
        try:
            return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    def add_months(d, months):
        total = d.month - 1 + months
        y = d.year + total // 12
        m = total % 12 + 1
        day = min(d.day, calendar.monthrange(y, m)[1])
        return date(y, m, day)

    def clear_keys(prefix):
        for k in list(st.session_state.keys()):
            if k.startswith(prefix):
                del st.session_state[k]

    interval_options = {
        "Tekrarlanmıyor": 0,
        "3 ayda bir": 3,
        "6 ayda bir": 6,
        "Yılda bir": 12,
        "2 yılda bir": 24
    }
    interval_labels = list(interval_options.keys())

    def interval_index(months):
        values = list(interval_options.values())
        return values.index(months) if months in values else 0

    def interval_text(months):
        for label, val in interval_options.items():
            if val == months:
                return label
        return f"{months} ayda bir"

    def status_badge(days):
        if days is None:
            return "⚪ Plan yok"
        if days < 0:
            return f"🔴 {abs(days)} gün gecikti"
        if days == 0:
            return "🟠 Bugün"
        if days <= 30:
            return f"🟠 {days} gün kaldı"
        return f"🟢 Planlı ({days} gün)"

    # -------------------------------------------------
    # VERİYİ HAZIRLA
    # -------------------------------------------------

    intervals = get_asset_intervals()
    records = get_maintenance_records()

    last_done = {}

    for (rid, r_asset_id, r_name, r_date, r_cost, r_notes) in records:
        if r_asset_id not in last_done:   # kayıtlar yeniden eskiye sıralı
            last_done[r_asset_id] = r_date

    items = []

    for (
        a_id, a_name, a_brand, a_model, a_pdate,
        a_price, a_warranty, a_maint, a_notes
    ) in get_assets():

        m_date = parse_date(a_maint)

        items.append(
            {
                "id": a_id,
                "name": a_name,
                "brand": a_brand,
                "model": a_model,
                "maint": a_maint,
                "m_date": m_date,
                "days": (m_date - today).days if m_date else None,
                "interval": intervals.get(a_id, 0),
                "last": last_done.get(a_id)
            }
        )

    # -------------------------------------------------
    # BAŞLIK + ÖZET KARTLARI
    # -------------------------------------------------

    st.title("🔧 Bakımlar")
    st.caption(
        "Cihazlarınızın bakım takvimini ve geçmişini takip edin."
    )

    if not items:
        st.info(
            "Henüz ev eşyası yok. Bakım takibi için önce "
            "'Ev Eşyalarım' sayfasından bir eşya ekleyin."
        )
        st.stop()

    planned = [i for i in items if i["days"] is not None]
    overdue = [i for i in planned if i["days"] < 0]
    soon = [i for i in planned if 0 <= i["days"] <= 30]
    total_cost = sum(r[4] for r in records)

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        with st.container(border=True):
            st.metric("Planlı Bakım", len(planned))

    with s2:
        with st.container(border=True):
            st.metric("Geciken", len(overdue))

    with s3:
        with st.container(border=True):
            st.metric("30 Gün İçinde", len(soon))

    with s4:
        with st.container(border=True):
            st.metric("Toplam Bakım Maliyeti", f"₺{total_cost:,.2f}")

    if overdue:
        st.error(
            f"🔴 {len(overdue)} eşyanın bakımı gecikmiş: "
            + ", ".join(i["name"] for i in overdue)
        )

    st.write("")

    tab_cal, tab_hist = st.tabs(
        ["🔧 Bakım Takvimi", "📜 Bakım Geçmişi"]
    )

    # =================================================
    # SEKME 1: BAKIM TAKVİMİ
    # =================================================

    with tab_cal:

        view = st.radio(
            "Göster",
            [
                "Tümü",
                "🔴 Gecikmiş",
                "🟠 30 gün içinde",
                "🟢 Planlı",
                "⚪ Planı olmayan"
            ],
            horizontal=True,
            key="maint_view"
        )

        shown = items

        if view == "🔴 Gecikmiş":
            shown = [i for i in items if i["days"] is not None and i["days"] < 0]
        elif view == "🟠 30 gün içinde":
            shown = [i for i in items if i["days"] is not None and 0 <= i["days"] <= 30]
        elif view == "🟢 Planlı":
            shown = [i for i in items if i["days"] is not None and i["days"] > 30]
        elif view == "⚪ Planı olmayan":
            shown = [i for i in items if i["days"] is None]

        shown = sorted(
            shown,
            key=lambda i: (i["days"] is None, i["days"] or 0)
        )

        if not shown:
            st.info("Bu görünüme uyan eşya yok.")

        for item in shown:

            iid = item["id"]

            with st.container(border=True):

                c1, c2 = st.columns([3, 3])

                with c1:
                    st.markdown(f"#### 🔧 {item['name']}")
                    st.caption(
                        f"{item['brand'] or '-'} • {item['model'] or '-'}"
                    )

                with c2:
                    st.write(
                        f"📅 Sonraki bakım: "
                        f"**{item['maint'] or 'Belirlenmedi'}**"
                    )
                    st.caption(
                        f"{status_badge(item['days'])} • "
                        f"{interval_text(item['interval'])}"
                    )
                    st.caption(
                        f"Son bakım: {item['last'] or 'kayıt yok'}"
                    )

                e1, e2 = st.columns(2)

                # ---------------- BAKIM YAPILDI ----------------

                with e1:

                    with st.expander("✅ Bakım Yapıldı"):

                        k = f"mdone_{iid}"

                        done_date = st.date_input(
                            "Bakım tarihi",
                            value=today,
                            key=f"{k}_date"
                        )

                        cost = st.number_input(
                            "Maliyet (₺)",
                            min_value=0.0,
                            step=50.0,
                            key=f"{k}_cost"
                        )

                        note = st.text_input(
                            "Not (opsiyonel)",
                            placeholder="Örn: Filtre değişti",
                            key=f"{k}_note"
                        )

                        next_label = st.selectbox(
                            "Bir sonraki bakım",
                            interval_labels,
                            index=interval_index(item["interval"]),
                            key=f"{k}_interval"
                        )

                        months = interval_options[next_label]

                        if months:
                            st.caption(
                                f"Sonraki bakım tarihi: "
                                f"**{add_months(done_date, months)}**"
                            )
                        else:
                            st.caption(
                                "Sonraki bakım tarihi temizlenecek."
                            )

                        add_expense = False

                        if cost > 0:
                            add_expense = st.checkbox(
                                "Maliyeti Ödemeler listesine "
                                "gider olarak ekle",
                                key=f"{k}_expense"
                            )

                        if st.button(
                            "💾 Kaydet",
                            key=f"{k}_save",
                            type="primary",
                            use_container_width=True
                        ):

                            add_maintenance_record(
                                iid,
                                str(done_date),
                                cost,
                                note.strip()
                            )

                            update_asset_maintenance_plan(
                                iid,
                                (
                                    str(add_months(done_date, months))
                                    if months else ""
                                ),
                                months
                            )

                            if add_expense:
                                add_paid_payment(
                                    f"{item['name']} Bakım",
                                    cost,
                                    str(done_date),
                                    "Diğer"
                                )

                            notify("Bakım kaydedildi!", "🔧")

                            clear_keys(k)
                            st.rerun()

                # ---------------- PLANI DÜZENLE ----------------

                with e2:

                    with st.expander("⚙️ Planı Düzenle"):

                        k2 = f"mplan_{iid}"

                        plan_date = st.date_input(
                            "Sonraki bakım tarihi",
                            value=item["m_date"],
                            key=f"{k2}_date"
                        )

                        plan_label = st.selectbox(
                            "Tekrar aralığı",
                            interval_labels,
                            index=interval_index(item["interval"]),
                            key=f"{k2}_interval"
                        )

                        if st.button(
                            "💾 Planı Kaydet",
                            key=f"{k2}_save",
                            use_container_width=True
                        ):

                            update_asset_maintenance_plan(
                                iid,
                                str(plan_date) if plan_date else "",
                                interval_options[plan_label]
                            )

                            notify("Bakım planı güncellendi!", "⚙️")
                            st.rerun()

    # =================================================
    # SEKME 2: BAKIM GEÇMİŞİ
    # =================================================

    with tab_hist:

        if not records:

            st.info(
                "Henüz bakım kaydı yok. Bakım Takvimi sekmesinde "
                "'Bakım Yapıldı' diyerek ilk kaydı oluşturabilirsiniz."
            )

        else:

            names = sorted({r[2] for r in records})

            sel_asset = st.selectbox(
                "Eşya",
                ["Tüm eşyalar"] + names,
                key="maint_hist_asset"
            )

            hist = (
                records if sel_asset == "Tüm eşyalar"
                else [r for r in records if r[2] == sel_asset]
            )

            h_total = sum(r[4] for r in hist)
            paid_records = [r[4] for r in hist if r[4] > 0]
            h_avg = (
                sum(paid_records) / len(paid_records)
                if paid_records else 0
            )

            h1, h2, h3 = st.columns(3)

            with h1:
                with st.container(border=True):
                    st.metric("Bakım Sayısı", len(hist))

            with h2:
                with st.container(border=True):
                    st.metric("Toplam Maliyet", f"₺{h_total:,.2f}")

            with h3:
                with st.container(border=True):
                    st.metric("Ortalama Maliyet", f"₺{h_avg:,.2f}")

            if sel_asset == "Tüm eşyalar" and h_total > 0:

                with st.container(border=True):

                    st.subheader("💰 Eşyaya Göre Bakım Maliyeti")

                    cost_df = pd.DataFrame(
                        [{"Eşya": r[2], "Maliyet": r[4]} for r in hist]
                    )
                    cost_df = (
                        cost_df.groupby("Eşya", as_index=False)["Maliyet"]
                        .sum()
                        .sort_values("Maliyet", ascending=False)
                    )

                    fig = px.bar(cost_df, x="Eşya", y="Maliyet")

                    fig.update_traces(
                        hovertemplate=(
                            "<b>%{x}</b><br>₺%{y:,.2f}<extra></extra>"
                        )
                    )

                    fig.update_layout(
                        height=300,
                        margin=dict(l=10, r=10, t=10, b=10),
                        xaxis_title=None,
                        yaxis_title=None
                    )

                    st.plotly_chart(fig, use_container_width=True)

            st.write("")

            for (rid, r_asset_id, r_name, r_date, r_cost, r_notes) in hist:

                with st.container(border=True):

                    a, b, c, d = st.columns([2.5, 1.5, 3, 1])

                    with a:
                        st.markdown(f"**{r_name}**")
                        st.caption(f"📅 {r_date}")

                    with b:
                        st.write(
                            f"₺{r_cost:,.2f}" if r_cost > 0 else "—"
                        )

                    with c:
                        st.caption(r_notes or "Not yok")

                    with d:
                        with st.popover("🗑️"):
                            st.write("Bu kayıt silinsin mi?")
                            st.caption(
                                "Eşyanın sonraki bakım tarihi değişmez."
                            )
                            if st.button(
                                "Evet, sil",
                                key=f"del_maint_{rid}",
                                type="primary"
                            ):
                                delete_maintenance_record(rid)
                                notify("Bakım kaydı silindi!", "🗑️")
                                st.rerun()# =====================================================
# EV EŞYALARIM
# app.py içinde `elif menu == "Ev Eşyalarım":` satırından
# `elif menu == "Harcamalar":` satırına kadar olan kısmı
# bununla değiştir. (elif menu == "Harcamalar" satırı kalsın.)
# =====================================================

elif menu == "Ev Eşyalarım":

    today = date.today()

    # -------------------------------------------------
    # YARDIMCI FONKSİYONLAR
    # -------------------------------------------------

    def parse_date(value):
        """YYYY-MM-DD metnini date'e çevirir, olmazsa None döner."""
        if not value or not str(value).strip():
            return None
        try:
            return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    def clear_keys(prefix):
        """Belirli bir önekle başlayan widget değerlerini temizler."""
        for k in list(st.session_state.keys()):
            if k.startswith(prefix):
                del st.session_state[k]

    def warranty_badge(days):
        if days is None:
            return "⚪ Belirtilmedi"
        if days < 0:
            return f"🔴 Süresi doldu ({abs(days)} gün önce)"
        if days <= 30:
            return f"🟠 {days} gün kaldı"
        return f"🟢 Aktif ({days} gün)"

    def maintenance_badge(days):
        if days is None:
            return "⚪ Belirlenmedi"
        if days < 0:
            return f"🔴 {abs(days)} gün gecikti"
        if days <= 30:
            return f"🟠 {days} gün kaldı"
        return f"🟢 Planlı ({days} gün)"

    def save_asset(
        name, brand, model, purchase_date, price,
        warranty_end, maintenance_date, notes,
        is_installment, installment_count, first_payment_date,
        card_id=None
    ):
        """Eşyayı kaydeder, taksitliyse ödeme planını da oluşturur.
        card_id verilirse taksit kartla alınmıştır: ayrı ödeme kaydı
        açılmaz, tutar kartın ekstresinin içinde sayılır."""

        asset_id = add_asset(
            name=name,
            brand=brand,
            model=model,
            purchase_date=purchase_date,
            purchase_price=price,
            warranty_end=warranty_end,
            maintenance_date=maintenance_date,
            notes=notes
        )

        notify("Ev eşyası başarıyla kaydedildi!", "📦")

        if is_installment:

            monthly = price / installment_count

            if card_id:

                add_card_installment(
                    asset_id,
                    card_id,
                    name,
                    price,
                    installment_count,
                    monthly,
                    str(first_payment_date)
                )

                notify(
                    f"{installment_count} taksit kartın ekstrelerine "
                    f"yansıyacak şekilde kaydedildi.",
                    "🏦"
                )

            else:

                add_installment(
                    asset_id=asset_id,
                    product_name=name,
                    total_amount=price,
                    installment_count=installment_count,
                    monthly_amount=monthly,
                    first_payment_date=first_payment_date
                )

                
            create_installment_payments(
                product_name=name,
                monthly_amount=monthly,
                installment_count=installment_count,
                first_payment_date=first_payment_date
            )

            notify(
                f"{installment_count} adet taksit ödeme planına eklendi.",
                "💳"
            )

    # -------------------------------------------------
    # VERİYİ HAZIRLA
    # -------------------------------------------------

    asset_items = []

    for (
        a_id, a_name, a_brand, a_model, a_pdate,
        a_price, a_warranty, a_maint, a_notes
    ) in get_assets():

        w_date = parse_date(a_warranty)
        m_date = parse_date(a_maint)

        asset_items.append(
            {
                "id": a_id,
                "name": a_name,
                "brand": a_brand,
                "model": a_model,
                "purchase_date": a_pdate,
                "price": a_price or 0,
                "warranty_end": a_warranty,
                "maintenance": a_maint,
                "notes": a_notes,
                "w_days": (w_date - today).days if w_date else None,
                "m_days": (m_date - today).days if m_date else None
            }
        )

    # -------------------------------------------------
    # BAŞLIK + ÖZET KARTLARI
    # -------------------------------------------------

    st.title("📦 Ev Eşyalarım")
    st.caption(
        "Cihazlarınızı, garanti süreleri ve bakım tarihleriyle takip edin."
    )

    total_value = sum(i["price"] for i in asset_items)

    active_warranty = sum(
        1 for i in asset_items
        if i["w_days"] is not None and i["w_days"] >= 0
    )

    alert_count = sum(
        1 for i in asset_items
        if (i["w_days"] is not None and 0 <= i["w_days"] <= 30)
        or (i["m_days"] is not None and i["m_days"] <= 30)
    )

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        with st.container(border=True):
            st.metric("Toplam Eşya", len(asset_items))

    with s2:
        with st.container(border=True):
            st.metric("Toplam Değer", f"₺{total_value:,.2f}")

    with s3:
        with st.container(border=True):
            st.metric("Garantisi Aktif", active_warranty)

    with s4:
        with st.container(border=True):
            st.metric("Yaklaşan Uyarı", alert_count)

    st.write("")

    tab_list, tab_ai, tab_manual = st.tabs(
        ["📦 Eşyalarım", "🤖 Faturadan Ekle", "➕ Manuel Ekle"]
    )

    # =================================================
    # SEKME 1: EŞYA LİSTESİ
    # =================================================

    with tab_list:

        if not asset_items:

            st.info(
                "Henüz kayıtlı ev eşyası yok. "
                "'Faturadan Ekle' veya 'Manuel Ekle' sekmesini kullanın."
            )

        else:

            f1, f2, f3 = st.columns([2, 1.5, 1.5])

            with f1:
                search_text = st.text_input(
                    "Ara",
                    placeholder="Ürün, marka veya model ara...",
                    key="asset_search"
                )

            with f2:
                asset_filter = st.selectbox(
                    "Filtre",
                    [
                        "Tümü",
                        "Garantisi aktif",
                        "Garantisi bitmiş",
                        "Bakımı yaklaşan / gecikmiş"
                    ],
                    key="asset_filter"
                )

            with f3:
                asset_sort = st.selectbox(
                    "Sırala",
                    [
                        "Kayıt sırası",
                        "Ada göre",
                        "Fiyat (yüksekten düşüğe)",
                        "Garanti bitimi (yakın önce)"
                    ],
                    key="asset_sort"
                )

            shown = asset_items

            if search_text.strip():
                q = search_text.strip().lower()
                shown = [
                    i for i in shown
                    if q in (i["name"] or "").lower()
                    or q in (i["brand"] or "").lower()
                    or q in (i["model"] or "").lower()
                ]

            if asset_filter == "Garantisi aktif":
                shown = [
                    i for i in shown
                    if i["w_days"] is not None and i["w_days"] >= 0
                ]
            elif asset_filter == "Garantisi bitmiş":
                shown = [
                    i for i in shown
                    if i["w_days"] is not None and i["w_days"] < 0
                ]
            elif asset_filter == "Bakımı yaklaşan / gecikmiş":
                shown = [
                    i for i in shown
                    if i["m_days"] is not None and i["m_days"] <= 30
                ]

            if asset_sort == "Ada göre":
                shown = sorted(shown, key=lambda i: (i["name"] or "").lower())
            elif asset_sort == "Fiyat (yüksekten düşüğe)":
                shown = sorted(shown, key=lambda i: i["price"], reverse=True)
            elif asset_sort == "Garanti bitimi (yakın önce)":
                shown = sorted(
                    shown,
                    key=lambda i: (
                        i["w_days"] is None,
                        i["w_days"] if i["w_days"] is not None else 0
                    )
                )

            st.caption(f"{len(shown)} eşya gösteriliyor")

            if not shown:
                st.info("Bu filtrelere uyan eşya bulunmuyor.")

            for item in shown:

                with st.container(border=True):

                    c1, c2, c3 = st.columns([2, 2, 2])

                    with c1:
                        st.markdown(f"#### 📦 {item['name']}")
                        st.caption(
                            f"{item['brand'] or '-'} • "
                            f"{item['model'] or '-'}"
                        )
                        st.caption(
                            f"📅 Satın alma: "
                            f"{item['purchase_date'] or '-'}"
                        )

                    with c2:
                        st.markdown(f"💰 **₺{item['price']:,.2f}**")
                        st.write(
                            f"🛡️ Garanti: "
                            f"{item['warranty_end'] or 'Belirtilmedi'}"
                        )
                        st.caption(warranty_badge(item["w_days"]))

                    with c3:
                        st.write(" ")
                        st.write(
                            f"🔧 Bakım: "
                            f"{item['maintenance'] or 'Belirlenmedi'}"
                        )
                        st.caption(maintenance_badge(item["m_days"]))

                    if item["notes"]:
                        st.caption(f"📝 {item['notes']}")

                    with st.popover("🗑️ Sil"):

                        st.write(
                            f"**{item['name']}** silinsin mi?"
                        )

                        if st.button(
                            "Evet, sil",
                            key=f"delete_asset_{item['id']}",
                            type="primary"
                        ):
                            delete_asset(item["id"])
                            notify(
                                "Ev eşyası başarıyla silindi!",
                                "🗑️"
                            )
                            st.rerun()

    # =================================================
    # SEKME 2: FATURADAN EKLE (AI)
    # =================================================

    with tab_ai:

        st.markdown("##### Fatura PDF'inizi yükleyin, bilgileri AI çıkarsın")

        invoice_file = st.file_uploader(
            "Fatura PDF yükleyin",
            type=["pdf"],
            key="invoice_uploader"
        )

        if invoice_file is not None:

            if st.button(
                "🤖 Faturayı AI ile Analiz Et",
                use_container_width=True,
                key="analyze_invoice_btn"
            ):

                analysis_ok = False

                with st.spinner("Fatura AI tarafından analiz ediliyor..."):

                    try:

                        result = analyze_invoice(invoice_file)

                        clear_keys("ai_")

                        st.session_state["invoice_data"] = {
                            "product_name": result.product_name,
                            "brand": result.brand,
                            "model": result.model,
                            "purchase_date": result.purchase_date,
                            "price": result.price,
                            "warranty_end": result.warranty_end,
                            "confidence_note": result.confidence_note
                        }

                        notify("Fatura başarıyla analiz edildi!", "🤖")
                        analysis_ok = True

                    except Exception as e:

                        st.error(
                            f"❌ Fatura analiz edilirken hata oluştu: {e}"
                        )

                if analysis_ok:
                    st.rerun()

        if "invoice_data" in st.session_state:

            data = st.session_state["invoice_data"]

            st.divider()
            st.subheader("📋 AI Tarafından Çıkarılan Bilgiler")

            st.info(
                "Bilgileri kontrol edin, gerekirse düzeltin. "
                "Kaydetmeden önce mutlaka gözden geçirin."
            )

            a1, a2 = st.columns(2)

            with a1:
                ai_name = st.text_input(
                    "Ürün Adı",
                    value=data.get("product_name") or "",
                    key="ai_product_name"
                )
                ai_brand = st.text_input(
                    "Marka",
                    value=data.get("brand") or "",
                    key="ai_brand"
                )
                ai_model = st.text_input(
                    "Model",
                    value=data.get("model") or "",
                    key="ai_model"
                )
                ai_purchase_date = st.text_input(
                    "Satın Alma Tarihi",
                    value=data.get("purchase_date") or "",
                    help="YYYY-MM-DD formatında",
                    key="ai_purchase_date"
                )

            with a2:
                ai_price = st.number_input(
                    "Satın Alma Fiyatı (₺)",
                    min_value=0.0,
                    value=float(data.get("price") or 0),
                    step=100.0,
                    key="ai_price"
                )
                ai_warranty_end = st.text_input(
                    "Garanti Bitiş Tarihi",
                    value=data.get("warranty_end") or "",
                    help="YYYY-MM-DD formatında",
                    key="ai_warranty_end"
                )
                ai_maintenance = st.text_input(
                    "Bir Sonraki Bakım Tarihi (Opsiyonel)",
                    value="",
                    help="YYYY-MM-DD formatında. Boş bırakabilirsiniz.",
                    key="ai_maintenance_date"
                )

            st.caption(
                "🤖 **AI Güven Notu:** "
                + (
                    data.get("confidence_note")
                    or "AI tarafından herhangi bir not oluşturulmadı."
                )
            )

            # ---------------- TAKSİT ----------------

            st.divider()
            st.subheader("💳 Taksit Bilgileri")

            ai_is_installment = st.checkbox(
                "🛒 Bu ürünü taksitli aldım",
                key="ai_is_installment"
            )

            ai_installment_count = 1
            ai_first_date = None
            ai_card_id = None

            if ai_is_installment:

                t1, t2 = st.columns(2)

                with t1:
                    ai_installment_count = int(
                        st.number_input(
                            "Taksit Sayısı",
                            min_value=2,
                            max_value=60,
                            value=6,
                            step=1,
                            key="ai_installment_count"
                        )
                    )

                with t2:
                    ai_first_date = st.date_input(
                        "İlk Taksit Tarihi",
                        value=parse_date(ai_purchase_date) or today,
                        key="ai_first_installment_date"
                    )

                st.info(
                    f"💳 Aylık taksit: "
                    f"**₺{ai_price / ai_installment_count:,.2f}**"
                )
                _cards = get_credit_cards()

                if _cards:

                    _opts = {0: "Kartla değil — ayrı taksit ödemeleri oluştur"}

                    for _c in _cards:
                        _opts[_c[0]] = (
                            f"🏦 {_c[1]}" + (f" •••• {_c[2]}" if _c[2] else "")
                        )

                    _pick = st.selectbox(
                        "Ödeme şekli",
                        list(_opts.keys()),
                        format_func=lambda x: _opts[x],
                        key="ai_card_id"
                    )

                    if _pick:
                        ai_card_id = _pick
                        st.caption(
                            "Kartla alındıysa 'İlk Taksit Tarihi', ilk "
                            "taksitin yansıyacağı ekstrenin SON ÖDEME "
                            "tarihi olmalı. Ayrı ödeme kaydı açılmaz; "
                            "tutar ekstrenin içinde sayılır."
                        )

            st.divider()

            if st.button(
                "📦 Ev Eşyalarıma Ekle",
                type="primary",
                use_container_width=True,
                key="ai_save_btn"
            ):

                errors = []

                if not ai_name.strip():
                    errors.append("Ürün adı boş bırakılamaz.")

                if ai_purchase_date.strip() and not parse_date(ai_purchase_date):
                    errors.append(
                        "Satın alma tarihi geçersiz (YYYY-MM-DD)."
                    )

                if ai_warranty_end.strip() and not parse_date(ai_warranty_end):
                    errors.append(
                        "Garanti bitiş tarihi geçersiz (YYYY-MM-DD)."
                    )

                if ai_maintenance.strip() and not parse_date(ai_maintenance):
                    errors.append("Bakım tarihi geçersiz (YYYY-MM-DD).")

                if ai_is_installment and ai_price <= 0:
                    errors.append(
                        "Taksit için fiyat 0'dan büyük olmalı."
                    )

                if errors:

                    for err in errors:
                        st.error(f"❌ {err}")

                else:

                    save_asset(
                        name=ai_name.strip(),
                        brand=ai_brand.strip(),
                        model=ai_model.strip(),
                        purchase_date=ai_purchase_date.strip(),
                        price=ai_price,
                        warranty_end=ai_warranty_end.strip(),
                        maintenance_date=ai_maintenance.strip(),
                        notes="AI tarafından faturadan çıkarıldı.",
                        is_installment=ai_is_installment,
                        installment_count=ai_installment_count,
                        first_payment_date=ai_first_date,
                        card_id=ai_card_id
                    )

                    del st.session_state["invoice_data"]
                    clear_keys("ai_")
                    st.rerun()

    # =================================================
    # SEKME 3: MANUEL EKLE
    # =================================================

    with tab_manual:

        st.markdown("##### Eşya bilgilerini kendiniz girin")

        m1, m2 = st.columns(2)

        with m1:
            man_name = st.text_input(
                "Ürün adı",
                placeholder="Örn: Buzdolabı",
                key="man_name"
            )
            man_brand = st.text_input(
                "Marka",
                placeholder="Örn: Bosch",
                key="man_brand"
            )
            man_model = st.text_input(
                "Model",
                placeholder="Örn: KGN56",
                key="man_model"
            )
            man_purchase_date = st.date_input(
                "Satın alma tarihi",
                value=today,
                key="man_purchase_date"
            )

        with m2:
            man_price = st.number_input(
                "Satın alma fiyatı (₺)",
                min_value=0.0,
                step=100.0,
                key="man_price"
            )
            man_warranty_end = st.date_input(
                "Garanti bitiş tarihi (opsiyonel)",
                value=None,
                key="man_warranty_end"
            )
            man_maintenance = st.date_input(
                "Bir sonraki bakım tarihi (opsiyonel)",
                value=None,
                key="man_maintenance"
            )
            man_notes = st.text_area(
                "Notlar",
                placeholder="Örn: Yıllık bakım gerekiyor.",
                key="man_notes"
            )

        # ---------------- TAKSİT ----------------

        st.divider()
        st.subheader("💳 Taksit Bilgileri")

        man_is_installment = st.checkbox(
            "🛒 Bu ürünü taksitli aldım",
            key="man_is_installment"
        )

        man_installment_count = 1
        man_first_date = None
        man_card_id = None

        if man_is_installment:

            t3, t4 = st.columns(2)

            with t3:
                man_installment_count = int(
                    st.number_input(
                        "Taksit Sayısı",
                        min_value=2,
                        max_value=60,
                        value=6,
                        step=1,
                        key="man_installment_count"
                    )
                )

            with t4:
                man_first_date = st.date_input(
                    "İlk Taksit Tarihi",
                    value=man_purchase_date,
                    key="man_first_installment_date"
                )

            st.info(
                f"💳 Aylık taksit: "
                f"**₺{man_price / man_installment_count:,.2f}**"
            )
            _cards = get_credit_cards()

            if _cards:

                _opts = {0: "Kartla değil — ayrı taksit ödemeleri oluştur"}

                for _c in _cards:
                    _opts[_c[0]] = (
                        f"🏦 {_c[1]}" + (f" •••• {_c[2]}" if _c[2] else "")
                    )

                _pick = st.selectbox(
                    "Ödeme şekli",
                    list(_opts.keys()),
                    format_func=lambda x: _opts[x],
                    key="man_card_id"
                )

                if _pick:
                    man_card_id = _pick
                    st.caption(
                        "Kartla alındıysa 'İlk Taksit Tarihi', ilk "
                        "taksitin yansıyacağı ekstrenin SON ÖDEME "
                        "tarihi olmalı. Ayrı ödeme kaydı açılmaz; "
                        "tutar ekstrenin içinde sayılır."
                    )

        st.divider()

        if st.button(
            "💾 Ev Eşyasını Kaydet",
            type="primary",
            use_container_width=True,
            key="man_save_btn"
        ):

            if not man_name.strip():

                st.error("❌ Lütfen ürün adını girin.")

            elif man_is_installment and man_price <= 0:

                st.error(
                    "❌ Taksit için satın alma fiyatı 0'dan büyük olmalı."
                )

            else:

                save_asset(
                    name=man_name.strip(),
                    brand=man_brand.strip(),
                    model=man_model.strip(),
                    purchase_date=str(man_purchase_date),
                    price=man_price,
                    warranty_end=(
                        str(man_warranty_end) if man_warranty_end else ""
                    ),
                    maintenance_date=(
                        str(man_maintenance) if man_maintenance else ""
                    ),
                    notes=man_notes.strip(),
                    is_installment=man_is_installment,
                    installment_count=man_installment_count,
                    first_payment_date=man_first_date,
                    card_id=man_card_id
                )

                clear_keys("man_")
                st.rerun()
# =====================================================
# FİNANS MERKEZİ
# =====================================================

elif menu == "Finans Merkezi":

    import plotly.express as px

    today = date.today()

    month_names = [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    ]

    st.title("💰 Finans Merkezi")

    st.caption(
        "Ev bütçenizi, ödemelerinizi, taksitlerinizi ve "
        "ekstra masraflarınızı tek yerden yönetin."
    )

    # =================================================
    # GELİR EKLE
    # =================================================

    with st.expander("➕ Yeni Gelir Ekle", expanded=False):

        with st.form("income_form", clear_on_submit=True):

            i1, i2 = st.columns(2)

            with i1:

                income_name = st.text_input(
                    "Gelir adı",
                    placeholder="Örn: Maaş"
                )

                income_amount = st.number_input(
                    "Tutar (₺)",
                    min_value=0.0,
                    step=100.0
                )

            with i2:

                income_date_input = st.date_input(
                    "Gelir tarihi",
                    value=today
                )

                income_category = st.selectbox(
                    "Gelir kategorisi",
                    [
                        "Maaş",
                        "Ek Gelir",
                        "Prim",
                        "Freelance",
                        "Diğer"
                    ]
                )

            income_submitted = st.form_submit_button(
                "💾 Geliri Kaydet",
                type="primary"
            )

            if income_submitted:

                if not income_name.strip():

                    st.error(
                        "Lütfen gelir adını girin."
                    )

                elif income_amount <= 0:

                    st.error(
                        "Gelir tutarı 0'dan büyük olmalı."
                    )

                else:

                    add_income(
                        income_name.strip(),
                        income_amount,
                        str(income_date_input),
                        income_category
                    )

                    notify(
                        "Gelir başarıyla eklendi!",
                        "💵"
                    )

                    st.rerun()

        render_pending_incomes()

    with st.expander("🔁 Tekrarlayan Gelir", expanded=False):

        r1, r2 = st.columns(2)

        with r1:
            rec_name = st.text_input(
                "Gelir adı",
                placeholder="Örn: Maaş",
                key="rec_inc_name"
            )
            rec_kind_label = st.radio(
                "Maaş türü",
                ["Sabit maaş", "Değişken maaş"],
                key="rec_inc_kind",
                help=(
                    "Sabit: her ay otomatik eklenir. "
                    "Değişken: maaş gününde tutarı sana sorar."
                )
            )

        with r2:
            rec_category = st.selectbox(
                "Kategori",
                ["Maaş", "Ek Gelir", "Prim", "Freelance","Kredi Kartı", "Diğer"],
                key="rec_inc_category"
            )
            rec_day = st.number_input(
                "Ayın kaçında yatıyor?",
                min_value=1,
                max_value=31,
                value=1,
                step=1,
                key="rec_inc_day"
            )

        rec_is_fixed = rec_kind_label == "Sabit maaş"

        if rec_is_fixed:
            rec_amount = st.number_input(
                "Aylık tutar (₺)",
                min_value=0.0,
                step=100.0,
                key="rec_inc_amount"
            )
        else:
            rec_amount = 0.0
            st.info(
                "Her ayın bu gününde tutarı girmeniz için "
                "Dashboard ve Finans Merkezi'nde bir kart çıkar."
            )

        rec_skip = st.checkbox(
            "Bu ayın gelirini zaten girdim, gelecek aydan başlasın",
            key="rec_inc_skip"
        )

        if st.button(
            "💾 Tekrarlayan Geliri Kaydet",
            type="primary",
            key="rec_inc_save"
        ):

            if not rec_name.strip():
                st.error("Lütfen gelir adını girin.")

            elif rec_is_fixed and rec_amount <= 0:
                st.error("Sabit maaş için tutar 0'dan büyük olmalı.")

            else:
                add_recurring_income(
                    rec_name.strip(),
                    rec_amount,
                    int(rec_day),
                    rec_category,
                    "fixed" if rec_is_fixed else "variable",
                    skip_current_month=rec_skip
                )

                create_monthly_fixed_incomes()

                for k in (
                    "rec_inc_name", "rec_inc_amount",
                    "rec_inc_day", "rec_inc_skip"
                ):
                    st.session_state.pop(k, None)

                notify("Tekrarlayan gelir tanımlandı!", "🔁")
                st.rerun()

        # ---------------- TANIMLI LİSTE ----------------

        defined_incomes = get_recurring_incomes()

        if defined_incomes:

            st.divider()
            st.markdown("**Tanımlı tekrarlayan gelirler**")

            for (
                rid, r_name, r_amount, r_day,
                r_cat, r_kind, r_active, r_last
            ) in defined_incomes:

                x1, x2, x3, x4 = st.columns([3, 2, 1.5, 1])

                with x1:
                    st.markdown(f"**{r_name}**")
                    st.caption(
                        f"{r_cat} • Her ayın {r_day}. günü"
                        + ("" if r_active else " • ⏸️ Durduruldu")
                    )

                with x2:
                    if r_kind == "fixed":
                        st.write(f"₺{float(r_amount or 0):,.2f} (sabit)")
                    else:
                        st.write("Değişken")

                with x3:
                    if st.button(
                        "⏸️ Durdur" if r_active else "▶️ Başlat",
                        key=f"rec_inc_toggle_{rid}",
                        use_container_width=True
                    ):
                        toggle_recurring_income(rid)
                        st.rerun()

                with x4:
                    if st.button("🗑️", key=f"rec_inc_del_{rid}"):
                        delete_recurring_income(rid)
                        notify("Tekrarlayan gelir silindi!", "🗑️")
                        st.rerun()
    # =================================================
    # VERİLER
    # =================================================

    payments = get_payments()
    recurring = get_recurring_payments()
    installments = get_installments()
    maintenance_records = get_maintenance_records()
    vehicles = get_vehicles()
    incomes = get_incomes()

    # =================================================
    # GELİR VERİLERİ
    # =================================================

    current_month_income = 0.0

    for (
        income_id,
        income_name,
        income_amount,
        income_date,
        income_category
    ) in incomes:

        try:

            income_day = datetime.strptime(
                income_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            continue

        if (
            income_day.year == today.year
            and income_day.month == today.month
        ):

            current_month_income += float(
                income_amount
            )

    # =================================================
    # ÖDEME VERİLERİ
    # =================================================

    current_month_payments = []

    paid_total = 0.0
    pending_total = 0.0
    overdue_total = 0.0
    month_total = 0.0

    for (
        payment_id,
        payment_name,
        payment_amount,
        payment_due,
        payment_category,
        payment_status
    ) in payments:

        try:

            due_date = datetime.strptime(
                payment_due,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            continue

        if (
            due_date.year == today.year
            and due_date.month == today.month
        ):

            amount = float(payment_amount)

            month_total += amount

            if payment_status == "Ödendi":

                paid_total += amount

            else:

                pending_total += amount

                if due_date < today:

                    overdue_total += amount

            current_month_payments.append(
                {
                    "Ad": payment_name,
                    "Tutar": amount,
                    "Tarih": due_date,
                    "Kategori": payment_category,
                    "Durum": payment_status
                }
            )

    # =================================================
    # NET BAKİYE
    # =================================================

    net_balance = (
        current_month_income
        - month_total
    )

    # =================================================
    # ÜST METRİKLER
    # =================================================
    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:
        with st.container(border=True):
            st.metric(
                "💵 Bu Ay Gelir",
                f"₺{current_month_income:,.2f}"
            )

    with k2:
        with st.container(border=True):
            st.metric(
                "💰 Planlanan Gider",
                f"₺{month_total:,.2f}"
            )

    with k3:
        with st.container(border=True):
            st.metric(
                "✅ Ödenen",
                f"₺{paid_total:,.2f}"
            )

    with k4:
        with st.container(border=True):
            st.metric(
                "⏳ Bekleyen",
                f"₺{pending_total:,.2f}"
            )

    with k5:
        with st.container(border=True):

            if net_balance >= 0:
                st.metric(
                    "📈 Net Bakiye",
                    f"₺{net_balance:,.2f}"
                )
            else:
                st.metric(
                    "📉 Net Bakiye",
                    f"-₺{abs(net_balance):,.2f}"
                )
    

    # =================================================
    # GELİRLER
    # =================================================

    st.subheader("💵 Gelirler")

    if incomes:

        income_rows = []

        for (
            inc_id,
            inc_name,
            inc_amount,
            inc_date,
            inc_category
        ) in incomes:

            income_rows.append(
                {
                    "ID": inc_id,
                    "Gelir": inc_name,
                    "Kategori": inc_category,
                    "Tarih": inc_date,
                    "Tutar": float(inc_amount)
                }
            )

        income_df = pd.DataFrame(income_rows)

        st.dataframe(
            income_df.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tutar": st.column_config.NumberColumn(
                    "Tutar",
                    format="₺%.2f"
                )
            }
        )

        st.write("")

        st.markdown("### 🗑️ Gelir Sil")

        delete_income_options = {
            f"{row['Gelir']} - ₺{row['Tutar']:,.2f} ({row['Tarih']})": row["ID"]
            for _, row in income_df.iterrows()
        }

        selected_income = st.selectbox(
            "Silmek istediğiniz geliri seçin",
            list(delete_income_options.keys()),
            key="delete_income_select"
        )

        if st.button(
            "🗑️ Seçili Geliri Sil",
            type="secondary",
            key="delete_income_button"
        ):

            delete_income(delete_income_options[selected_income])

            notify("Gelir başarıyla silindi!", "🗑️")

            st.rerun()

    else:

        st.info(
            "Henüz kayıtlı gelir bulunmuyor. "
            "Yukarıdaki 'Yeni Gelir Ekle' bölümünden gelir ekleyebilirsiniz."
        )

    st.write("")
# =================================================
# ÖDEME DURUMU
# =================================================

    left, right = st.columns([3, 2])

    with left:

        with st.container(border=True):

            st.subheader("📅 Bu Ayın Ödeme Planı")

            if current_month_payments:

                month_df = pd.DataFrame(
                    current_month_payments
                )

                month_df = month_df.sort_values(
                    "Tarih"
                )

                st.dataframe(
                    month_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Tutar": st.column_config.NumberColumn(
                            "Tutar",
                            format="₺%.2f"
                        ),
                        "Tarih": st.column_config.DateColumn(
                            "Tarih",
                            format="DD.MM.YYYY"
                        )
                    }
                )

            else:

                st.info(
                    "Bu ay için kayıtlı ödeme bulunmuyor."
                )

    with right:

        with st.container(border=True):

            st.subheader("📊 Ödeme Dağılımı")

            if current_month_payments:

                status_df = pd.DataFrame(
                    [
                        {
                            "Durum": "Ödendi",
                            "Tutar": paid_total
                        },
                        {
                            "Durum": "Bekleyen",
                            "Tutar": pending_total
                        }
                    ]
                )

                status_df = status_df[
                    status_df["Tutar"] > 0
                ]

                if not status_df.empty:

                    fig_status = px.pie(
                        status_df,
                        names="Durum",
                        values="Tutar",
                        hole=0.45
                    )

                    fig_status.update_layout(
                        height=320,
                        margin=dict(
                            l=10,
                            r=10,
                            t=10,
                            b=10
                        ),
                        showlegend=True
                    )

                    st.plotly_chart(
                        fig_status,
                        use_container_width=True
                    )

            else:

                st.info("Grafik için ödeme bulunmuyor.")

    st.write("")

    # =================================================
    # SON 6 AY
    # =================================================

    with st.container(border=True):

        st.subheader("📈 Son 6 Aylık Finansal Görünüm")

        six_months = []

        for i in range(5, -1, -1):

            month_number = today.month - i
            year_number = today.year

            while month_number <= 0:
                month_number += 12
                year_number -= 1

            total = 0
            paid = 0

            for (
                pid,
                name,
                amount,
                due,
                category,
                status
            ) in payments:

                try:
                    due_date = datetime.strptime(
                        due,
                        "%Y-%m-%d"
                    ).date()
                except ValueError:
                    continue

                if (
                    due_date.year == year_number
                    and due_date.month == month_number
                ):

                    total += float(amount)

                    if status == "Ödendi":
                        paid += float(amount)

            six_months.append(
                {
                    "Ay": (
                        f"{month_names[month_number - 1][:3]} "
                        f"{year_number}"
                    ),
                    "Planlanan": total,
                    "Ödenen": paid
                }
            )

        six_df = pd.DataFrame(six_months)

        fig_six = px.bar(
            six_df,
            x="Ay",
            y=["Planlanan", "Ödenen"],
            barmode="group"
        )

        fig_six.update_layout(
            height=400,
            margin=dict(
                l=10,
                r=10,
                t=10,
                b=10
            ),
            xaxis_title=None,
            yaxis_title="Tutar (₺)"
        )

        st.plotly_chart(
            fig_six,
            use_container_width=True
        )

    st.write("")

    # =================================================
    # ALT BÖLÜM
    # =================================================

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🏷️ Kategoriler",
            "🔄 Sabit Ödemeler",
            "💳 Taksitler",
            "🚗 Ek Masraflar"
        ]
    )

    # =================================================
    # KATEGORİLER
    # =================================================

    with tab1:

        category_data = []

        for (
            pid,
            name,
            amount,
            due,
            category,
            status
        ) in payments:

            try:
                due_date = datetime.strptime(
                    due,
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                continue

            if (
                due_date.year == today.year
                and due_date.month == today.month
            ):

                category_data.append(
                    {
                        "Kategori": category,
                        "Tutar": float(amount)
                    }
                )

        if category_data:

            category_df = pd.DataFrame(
                category_data
            )

            category_df = (
                category_df
                .groupby("Kategori", as_index=False)["Tutar"]
                .sum()
                .sort_values(
                    "Tutar",
                    ascending=False
                )
            )

            c1, c2 = st.columns([2, 3])

            with c1:

                fig_cat = px.pie(
                    category_df,
                    names="Kategori",
                    values="Tutar",
                    hole=0.4
                )

                fig_cat.update_layout(
                    height=350,
                    margin=dict(
                        l=10,
                        r=10,
                        t=10,
                        b=10
                    )
                )

                st.plotly_chart(
                    fig_cat,
                    use_container_width=True
                )

            with c2:

                st.dataframe(
                    category_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Tutar": st.column_config.NumberColumn(
                            "Tutar",
                            format="₺%.2f"
                        )
                    }
                )

        else:

            st.info(
                "Bu ay için kategori verisi bulunmuyor."
            )

     # =================================================
    # SABİT ÖDEMELER
    # =================================================

    with tab2:

        st.subheader("🔄 Aylık Sabit Ödemeler")

        rec_categories = [
            "Elektrik", "Su", "Doğalgaz", "İnternet", "Kira",
            "Aidat", "Sigorta", "Cep Telefonu", "Taksit", "Diğer"
        ]

        if recurring:

            active_count = sum(1 for r in recurring if r[5] == 1)
            active_total = sum(
                float(r[2]) for r in recurring if r[5] == 1
            )

            rm1, rm2 = st.columns(2)

            with rm1:
                st.metric("Aylık Sabit Gider", f"₺{active_total:,.2f}")

            with rm2:
                st.metric(
                    "Aktif / Toplam",
                    f"{active_count} / {len(recurring)}"
                )

            for (
                rid,
                r_name,
                r_amount,
                r_day,
                r_cat,
                r_active
            ) in recurring:

                with st.container(border=True):

                    c1, c2, c3 = st.columns([3, 1.5, 1.5])

                    with c1:
                        st.markdown(
                            f"**{r_name}**" + ("" if r_active else " ⏸️")
                        )
                        st.caption(
                            f"{r_cat} • Her ayın {r_day}. günü"
                            + ("" if r_active else " • Durduruldu")
                        )

                    with c2:
                        st.markdown(f"**₺{float(r_amount):,.2f}**")

                    with c3:
                        if st.button(
                            "⏸️ Durdur" if r_active else "▶️ Başlat",
                            key=f"rp_toggle_{rid}",
                            use_container_width=True
                        ):
                            toggle_recurring_payment(
                                rid,
                                0 if r_active else 1
                            )
                            notify(
                                "Sabit ödeme durduruldu!"
                                if r_active
                                else "Sabit ödeme tekrar başlatıldı!",
                                "⏸️" if r_active else "▶️"
                            )
                            st.rerun()

                    with st.expander("✏️ Düzenle / Sil"):

                        e1, e2 = st.columns(2)

                        with e1:
                            ed_name = st.text_input(
                                "Ödeme adı",
                                value=r_name,
                                key=f"rp_name_{rid}"
                            )
                            ed_amount = st.number_input(
                                "Aylık tutar (₺)",
                                min_value=0.0,
                                value=float(r_amount),
                                step=10.0,
                                key=f"rp_amount_{rid}"
                            )

                        with e2:
                            ed_day = st.number_input(
                                "Ayın kaçında?",
                                min_value=1,
                                max_value=31,
                                value=int(r_day),
                                step=1,
                                key=f"rp_day_{rid}"
                            )
                            ed_cat = st.selectbox(
                                "Kategori",
                                rec_categories,
                                index=(
                                    rec_categories.index(r_cat)
                                    if r_cat in rec_categories
                                    else len(rec_categories) - 1
                                ),
                                key=f"rp_cat_{rid}"
                            )

                        ed_current = st.checkbox(
                            "Bu ayın bekleyen ödemesini de güncelle",
                            value=True,
                            help=(
                                "Kapalıysa değişiklik sadece gelecek "
                                "aylar için geçerli olur. Ödenmiş "
                                "kayıtlara dokunulmaz."
                            ),
                            key=f"rp_current_{rid}"
                        )

                        b1, b2 = st.columns(2)

                        with b1:
                            if st.button(
                                "💾 Değişiklikleri Kaydet",
                                key=f"rp_save_{rid}",
                                type="primary",
                                use_container_width=True
                            ):
                                if not ed_name.strip():
                                    st.error("Ödeme adı boş olamaz.")
                                elif ed_amount <= 0:
                                    st.error("Tutar 0'dan büyük olmalı.")
                                else:
                                    update_recurring_payment(
                                        rid,
                                        ed_name.strip(),
                                        ed_amount,
                                        int(ed_day),
                                        ed_cat,
                                        update_current_month=ed_current
                                    )
                                    notify(
                                        "Sabit ödeme güncellendi!",
                                        "✏️"
                                    )
                                    st.rerun()

                        with b2:
                            with st.popover(
                                "🗑️ Sil",
                                use_container_width=True
                            ):
                                st.write(
                                    f"**{r_name}** sabit ödemesi silinsin mi?"
                                )
                                st.caption(
                                    "Daha önce oluşmuş aylık ödeme "
                                    "kayıtları silinmez."
                                )
                                if st.button(
                                    "Evet, sil",
                                    key=f"rp_delete_{rid}",
                                    type="primary"
                                ):
                                    delete_recurring_payment(rid)
                                    notify("Sabit ödeme silindi!", "🗑️")
                                    st.rerun()

        else:

            st.info(
                "Henüz sabit ödeme yok. 'Ödemeler' sayfasında yeni "
                "ödeme eklerken '🔁 Her ay otomatik oluştur' kutusunu "
                "işaretleyebilirsiniz."
            )
    # =================================================
    # TAKSİTLER
    # =================================================

    with tab3:
        card_billed = {r[0]: r[8] for r in get_card_installments()}
        st.subheader("💳 Taksitli Ödemeler")

        if installments:

            installment_rows = []

            for installment in installments:

                (
                    iid,
                    asset_id,
                    product_name,
                    total_amount,
                    installment_count,
                    monthly_amount,
                    first_payment_date,
                    current_installment
                ) = installment

                installment_rows.append(
                    {
                        "Ürün": product_name,
                        "Toplam": float(total_amount),
                        "Taksit": (
                            f"{card_billed.get(iid, current_installment)}/"
                            f"{installment_count}"
                        ),
                        "Aylık": float(monthly_amount),
                        "İlk Ödeme": first_payment_date
                    }
                )

            installment_df = pd.DataFrame(
                installment_rows
            )

            i1, i2 = st.columns(2)

            with i1:

                st.metric(
                    "Aktif Taksit",
                    len(installment_df)
                )

            with i2:

                st.metric(
                    "Aylık Taksit Yükü",
                    f"₺{installment_df['Aylık'].sum():,.2f}"
                )

            st.dataframe(
                installment_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Toplam": st.column_config.NumberColumn(
                        "Toplam",
                        format="₺%.2f"
                    ),
                    "Aylık": st.column_config.NumberColumn(
                        "Aylık",
                        format="₺%.2f"
                    )
                }
            )

        else:

            st.info(
                "Henüz taksitli ödeme bulunmuyor."
            )

    # =================================================
    # ARAÇ + BAKIM MASRAFLARI
    # =================================================

    with tab4:

        st.subheader("🚗 Araç ve Bakım Masrafları")

        extra_rows = []

        # -----------------------------
        # Bakım masrafları
        # -----------------------------

        for record in maintenance_records:

            (
                rid,
                asset_id,
                asset_name,
                maintenance_date,
                cost,
                notes
            ) = record

            try:
                expense_date = datetime.strptime(
                    maintenance_date,
                    "%Y-%m-%d"
                ).date()
            except ValueError:
                continue

            if expense_date.year == today.year:

                extra_rows.append(
                    {
                        "Tür": "Bakım",
                        "Ad": asset_name,
                        "Tarih": expense_date,
                        "Tutar": float(cost)
                    }
                )

        # -----------------------------
        # Araç masrafları
        # -----------------------------

        vehicle_map = {
            v[0]: f"{v[2]} {v[3]} ({v[1]})"
            for v in vehicles
        }

        for vehicle in vehicles:

            vehicle_id = vehicle[0]

            for expense in get_vehicle_expenses(
                vehicle_id
            ):

                (
                    eid,
                    vid,
                    expense_date,
                    expense_type,
                    amount,
                    km,
                    liters,
                    notes
                ) = expense

                try:
                    expense_date_obj = datetime.strptime(
                        expense_date,
                        "%Y-%m-%d"
                    ).date()
                except ValueError:
                    continue

                if expense_date_obj.year == today.year:

                    extra_rows.append(
                        {
                            "Tür": "Araç",
                            "Ad": (
                                f"{vehicle_map.get(vehicle_id, 'Araç')} "
                                f"- {expense_type}"
                            ),
                            "Tarih": expense_date_obj,
                            "Tutar": float(amount)
                        }
                    )

        if extra_rows:

            extra_df = pd.DataFrame(
                extra_rows
            )

            extra_total = extra_df[
                "Tutar"
            ].sum()

            st.metric(
                "Bu Yıl Ek Masraflar",
                f"₺{extra_total:,.2f}"
            )

            st.dataframe(
                extra_df.sort_values(
                    "Tarih",
                    ascending=False
                ),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tarih": st.column_config.DateColumn(
                        "Tarih",
                        format="DD.MM.YYYY"
                    ),
                    "Tutar": st.column_config.NumberColumn(
                        "Tutar",
                        format="₺%.2f"
                    )
                }
            )

        else:

            st.info(
                "Bu yıl için bakım veya araç masrafı bulunmuyor."
            )

# =====================================================
# HARCAMALAR
# app.py içinde `elif menu == "Harcamalar":` satırından
# `elif menu == "🤖 AI Asistan":` satırına kadar olan kısmı
# bununla değiştir. (elif menu == "🤖 AI Asistan" satırı kalsın.)
# =====================================================

elif menu == "Harcamalar":

    import plotly.express as px

    today = date.today()

    month_names = [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    ]
    short = [m[:3] for m in month_names]

    st.title("📊 Harcamalar")
    st.caption("Aylık ve yıllık gider analizleriniz.")

    # -------------------------------------------------
    # ÜST FİLTRELER
    # -------------------------------------------------

    top1, top2 = st.columns([1, 2])

    with top1:
        year = st.selectbox(
            "Yıl",
            range(today.year - 3, today.year + 3),
            index=3,
            key="exp_year"
        )

    with top2:
        st.write("")
        paid_only = st.toggle(
            "Sadece ödenen ödemeleri say",
            value=False,
            help=(
                "Kapalıyken bekleyen ve gelecek ödemeler de "
                "gider olarak hesaplanır."
            ),
            key="exp_paid_only"
        )

    # -------------------------------------------------
    # VERİYİ HAZIRLA
    # -------------------------------------------------

    rows = []

    for (pid, p_name, p_amount, p_due, p_category, p_status) in get_payments():

        if paid_only and p_status != "Ödendi":
            continue

        due = datetime.strptime(p_due, "%Y-%m-%d").date()

        rows.append(
            {
                "Ad": p_name,
                "Tutar": p_amount,
                "Tarih": due,
                "Kategori": p_category,
                "Yıl": due.year,
                "Ay": due.month
            }
        )

    df = pd.DataFrame(
        rows,
        columns=["Ad", "Tutar", "Tarih", "Kategori", "Yıl", "Ay"]
    )

    if df.empty:
        st.info("Analiz için henüz ödeme kaydı yok.")
        st.stop()

    year_df = df[df["Yıl"] == year]
    prev_year_df = df[df["Yıl"] == year - 1]

    tab_year, tab_month, tab_cat = st.tabs(
        [
            "📅 Yıllık Genel Bakış",
            "🗓️ Aylık Detay",
            "🏷️ Kategori Analizi"
        ]
    )

    # =================================================
    # SEKME 1: YILLIK
    # =================================================

    with tab_year:

        if year_df.empty:

            st.info(f"{year} yılı için kayıt bulunmuyor.")

        else:

            year_total = year_df["Tutar"].sum()
            prev_total = prev_year_df["Tutar"].sum()

            monthly = (
                year_df.groupby("Ay")["Tutar"].sum()
                .reindex(range(1, 13), fill_value=0)
            )

            active_months = monthly[monthly > 0]
            avg_month = active_months.mean() if len(active_months) else 0
            peak_month = int(monthly.idxmax())

            cat_totals = (
                year_df.groupby("Kategori")["Tutar"].sum()
                .sort_values(ascending=False)
            )

            k1, k2, k3, k4 = st.columns(4)

            with k1:
                with st.container(border=True):
                    delta = None
                    if prev_total > 0:
                        pct = (year_total - prev_total) / prev_total * 100
                        delta = f"{pct:+.1f}% (geçen yıla göre)"
                    st.metric(
                        f"{year} Toplam Gider",
                        f"₺{year_total:,.2f}",
                        delta=delta,
                        delta_color="inverse"
                    )

            with k2:
                with st.container(border=True):
                    st.metric("Aylık Ortalama", f"₺{avg_month:,.2f}")

            with k3:
                with st.container(border=True):
                    st.metric(
                        "En Yüksek Ay",
                        month_names[peak_month - 1],
                        delta=f"₺{monthly[peak_month]:,.2f}",
                        delta_color="off"
                    )

            with k4:
                with st.container(border=True):
                    st.metric(
                        "En Büyük Kategori",
                        cat_totals.index[0],
                        delta=f"₺{cat_totals.iloc[0]:,.2f}",
                        delta_color="off"
                    )
                                # ---------------- GELİR - GİDER ----------------

            inc_monthly = {m: 0.0 for m in range(1, 13)}

            for (inc_id, inc_name, inc_amount, inc_date, inc_cat) in get_incomes():
                try:
                    inc_day = datetime.strptime(inc_date, "%Y-%m-%d").date()
                except ValueError:
                    continue
                if inc_day.year == year:
                    inc_monthly[inc_day.month] += float(inc_amount)

            year_income = sum(inc_monthly.values())

            if year_income > 0:

                year_net = year_income - year_total
                saving_rate = year_net / year_income * 100

                st.write("")

                i1, i2, i3 = st.columns(3)

                with i1:
                    with st.container(border=True):
                        st.metric(f"{year} Toplam Gelir", f"₺{year_income:,.2f}")

                with i2:
                    with st.container(border=True):
                        st.metric(
                            "Net (Gelir - Gider)",
                            f"₺{year_net:,.2f}",
                            delta="Artıda" if year_net >= 0 else "Ekside",
                            delta_color="normal" if year_net >= 0 else "inverse"
                        )

                with i3:
                    with st.container(border=True):
                        st.metric("Tasarruf Oranı", f"%{saving_rate:.1f}")

                with st.container(border=True):

                    st.subheader("💵 Aylık Gelir - Gider")

                    ig_rows = []

                    for m in range(1, 13):
                        ig_rows.append(
                            {"Ay": short[m - 1], "Tür": "Gelir",
                             "Tutar": inc_monthly[m]}
                        )
                        ig_rows.append(
                            {"Ay": short[m - 1], "Tür": "Gider",
                             "Tutar": float(monthly[m])}
                        )

                    fig_ig = px.bar(
                        pd.DataFrame(ig_rows),
                        x="Ay",
                        y="Tutar",
                        color="Tür",
                        barmode="group",
                        category_orders={"Ay": short},
                        color_discrete_map={
                            "Gelir": "#2ca02c",
                            "Gider": "#d62728"
                        }
                    )

                    fig_ig.update_traces(
                        hovertemplate="<b>%{x}</b><br>₺%{y:,.2f}<extra></extra>"
                    )

                    fig_ig.update_layout(
                        height=350,
                        margin=dict(l=10, r=10, t=10, b=10),
                        xaxis_title=None,
                        yaxis_title=None,
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.15,
                            xanchor="center",
                            x=0.5,
                            title=None
                        )
                    )

                    st.plotly_chart(fig_ig, use_container_width=True)

            st.write("")

            with st.container(border=True):

                st.subheader("📈 Aylık Gider (kategoriye göre)")

                month_cat = (
                    year_df.groupby(["Ay", "Kategori"], as_index=False)["Tutar"]
                    .sum()
                )
                month_cat["Ay Adı"] = month_cat["Ay"].map(
                    lambda m: short[m - 1]
                )

                fig = px.bar(
                    month_cat,
                    x="Ay Adı",
                    y="Tutar",
                    color="Kategori",
                    category_orders={"Ay Adı": short}
                )

                fig.update_traces(
                    hovertemplate=(
                        "<b>%{x}</b><br>₺%{y:,.2f}<extra></extra>"
                    )
                )

                fig.update_layout(
                    height=400,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_title=None,
                    yaxis_title=None,
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.15,
                        xanchor="center",
                        x=0.5,
                        title=None
                    )
                )

                st.plotly_chart(fig, use_container_width=True)

            with st.expander("📋 Ay × Kategori tablosu"):

                pivot = year_df.pivot_table(
                    index="Kategori",
                    columns="Ay",
                    values="Tutar",
                    aggfunc="sum",
                    fill_value=0
                ).reindex(columns=range(1, 13), fill_value=0)

                pivot.columns = short
                pivot["Toplam"] = pivot.sum(axis=1)
                pivot = pivot.sort_values("Toplam", ascending=False)

                st.dataframe(
                    pivot.round(2),
                    use_container_width=True
                )

    # =================================================
    # SEKME 2: AYLIK
    # =================================================

    with tab_month:

        sel_month = st.selectbox(
            "Ay",
            range(1, 13),
            index=today.month - 1,
            format_func=lambda x: month_names[x - 1],
            key="exp_month"
        )

        if sel_month == 1:
            prev_y, prev_m = year - 1, 12
        else:
            prev_y, prev_m = year, sel_month - 1

        cur_df = df[(df["Yıl"] == year) & (df["Ay"] == sel_month)]
        prev_df = df[(df["Yıl"] == prev_y) & (df["Ay"] == prev_m)]

        if cur_df.empty:

            st.info(
                f"{month_names[sel_month - 1]} {year} için kayıt yok."
            )

        else:

            cur_total = cur_df["Tutar"].sum()
            prev_month_total = prev_df["Tutar"].sum()
            biggest = cur_df.loc[cur_df["Tutar"].idxmax()]

            m1, m2, m3, m4 = st.columns(4)

            with m1:
                with st.container(border=True):
                    delta = None
                    if prev_month_total > 0:
                        diff = cur_total - prev_month_total
                        delta = (
                            f"₺{diff:+,.2f} "
                            f"({month_names[prev_m - 1]} ayına göre)"
                        )
                    st.metric(
                        "Toplam Gider",
                        f"₺{cur_total:,.2f}",
                        delta=delta,
                        delta_color="inverse"
                    )

            with m2:
                with st.container(border=True):
                    st.metric("Ödeme Sayısı", len(cur_df))

            with m3:
                with st.container(border=True):
                    st.metric(
                        "Ortalama Ödeme",
                        f"₺{cur_df['Tutar'].mean():,.2f}"
                    )

            with m4:
                with st.container(border=True):
                    st.metric(
                        "En Büyük Ödeme",
                        f"₺{biggest['Tutar']:,.2f}",
                        delta=biggest["Ad"],
                        delta_color="off"
                    )

            st.write("")

            left, right = st.columns([3, 2])

            with left:

                with st.container(border=True):

                    st.subheader("🔀 Önceki Ayla Karşılaştırma")

                    cur_cat = cur_df.groupby("Kategori")["Tutar"].sum()
                    prev_cat = prev_df.groupby("Kategori")["Tutar"].sum()

                    cats = sorted(set(cur_cat.index) | set(prev_cat.index))

                    cur_label = f"{month_names[sel_month - 1]} {year}"
                    prev_label = f"{month_names[prev_m - 1]} {prev_y}"

                    cmp_df = pd.DataFrame(
                        [
                            {
                                "Kategori": c,
                                "Dönem": cur_label,
                                "Tutar": float(cur_cat.get(c, 0))
                            }
                            for c in cats
                        ]
                        + [
                            {
                                "Kategori": c,
                                "Dönem": prev_label,
                                "Tutar": float(prev_cat.get(c, 0))
                            }
                            for c in cats
                        ]
                    )

                    fig2 = px.bar(
                        cmp_df,
                        x="Kategori",
                        y="Tutar",
                        color="Dönem",
                        barmode="group"
                    )

                    fig2.update_traces(
                        hovertemplate=(
                            "<b>%{x}</b><br>₺%{y:,.2f}<extra></extra>"
                        )
                    )

                    fig2.update_layout(
                        height=350,
                        margin=dict(l=10, r=10, t=10, b=10),
                        xaxis_title=None,
                        yaxis_title=None,
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.2,
                            xanchor="center",
                            x=0.5,
                            title=None
                        )
                    )

                    st.plotly_chart(fig2, use_container_width=True)

            with right:

                with st.container(border=True):

                    st.subheader("🏆 En Büyük 10 Ödeme")

                    top_df = (
                        cur_df.sort_values("Tutar", ascending=False)
                        .head(10)[["Ad", "Kategori", "Tutar", "Tarih"]]
                    )

                    st.dataframe(
                        top_df,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Tutar": st.column_config.NumberColumn(
                                "Tutar",
                                format="₺%.2f"
                            )
                        }
                    )

    # =================================================
    # SEKME 3: KATEGORİ
    # =================================================

    with tab_cat:

        if year_df.empty:

            st.info(f"{year} yılı için kayıt bulunmuyor.")

        else:

            cat_list = (
                year_df.groupby("Kategori")["Tutar"].sum()
                .sort_values(ascending=False)
                .index.tolist()
            )

            sel_cat = st.selectbox(
                "Kategori",
                cat_list,
                key="exp_category"
            )

            cat_df = year_df[year_df["Kategori"] == sel_cat]

            cat_total = cat_df["Tutar"].sum()

            cat_monthly = (
                cat_df.groupby("Ay")["Tutar"].sum()
                .reindex(range(1, 13), fill_value=0)
            )

            cat_active = cat_monthly[cat_monthly > 0]
            cat_avg = cat_active.mean() if len(cat_active) else 0
            cat_peak = int(cat_monthly.idxmax())
            share = cat_total / year_df["Tutar"].sum() * 100

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                with st.container(border=True):
                    st.metric(f"{sel_cat} Toplam", f"₺{cat_total:,.2f}")

            with c2:
                with st.container(border=True):
                    st.metric("Aylık Ortalama", f"₺{cat_avg:,.2f}")

            with c3:
                with st.container(border=True):
                    st.metric(
                        "En Yüksek Ay",
                        month_names[cat_peak - 1],
                        delta=f"₺{cat_monthly[cat_peak]:,.2f}",
                        delta_color="off"
                    )

            with c4:
                with st.container(border=True):
                    st.metric("Yıllık Payı", f"%{share:.1f}")

            st.write("")

            left, right = st.columns([3, 2])

            with left:

                with st.container(border=True):

                    st.subheader(f"📈 {sel_cat} — Aylık Seyir")

                    trend = pd.DataFrame(
                        {
                            "Ay": short,
                            "Tutar": cat_monthly.values
                        }
                    )

                    fig3 = px.line(
                        trend,
                        x="Ay",
                        y="Tutar",
                        markers=True,
                        category_orders={"Ay": short}
                    )

                    fig3.update_traces(
                        hovertemplate=(
                            "<b>%{x}</b><br>₺%{y:,.2f}<extra></extra>"
                        )
                    )

                    fig3.update_layout(
                        height=350,
                        margin=dict(l=10, r=10, t=10, b=10),
                        xaxis_title=None,
                        yaxis_title=None
                    )

                    st.plotly_chart(fig3, use_container_width=True)

            with right:

                with st.container(border=True):

                    st.subheader("🥧 Yıllık Dağılım")

                    share_df = (
                        year_df.groupby("Kategori", as_index=False)["Tutar"]
                        .sum()
                    )

                    fig4 = px.pie(
                        share_df,
                        names="Kategori",
                        values="Tutar",
                        hole=0.55
                    )

                    fig4.update_traces(
                        textposition="inside",
                        textinfo="percent",
                        hovertemplate=(
                            "<b>%{label}</b><br>"
                            "₺%{value:,.2f}<br>%{percent}<extra></extra>"
                        ),
                        marker=dict(line=dict(color="white", width=2))
                    )

                    fig4.update_layout(
                        height=350,
                        margin=dict(l=10, r=10, t=10, b=10),
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.05,
                            xanchor="center",
                            x=0.5
                        )
                    )

                    st.plotly_chart(fig4, use_container_width=True)

# =====================================================
# AI ASİSTAN
# app.py içinde `elif menu == "🤖 AI Asistan":` satırından
# dosyanın sonuna kadar olan kısmı bununla değiştir.
# (Bu bölüm dosyanın en sonunda olduğu için altında
#  başka bir elif kalmaz.)
# =====================================================
# =====================================================
# ARAÇLAR
# Bu bloğu app.py içinde `elif menu == "🤖 AI Asistan":`
# satırının HEMEN ÜSTÜNE yeni bir elif bloğu olarak yapıştır.
# (Diğer elif bloklarıyla aynı girintide, en solda başlamalı.)
# =====================================================

elif menu == "Araçlar":

    import plotly.express as px

    today = date.today()

    expense_types = [
        "Yakıt", "Bakım / Servis", "Sigorta", "Muayene", "Lastik",
        "Tamir", "Otopark / Otoyol", "Vergi (MTV)", "Diğer"
    ]

    fuel_types = ["Benzin", "Dizel", "LPG", "Hibrit", "Elektrik"]

    # -------------------------------------------------
    # YARDIMCI FONKSİYONLAR
    # -------------------------------------------------

    def parse_date(value):
        if not value or not str(value).strip():
            return None
        try:
            return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    def clear_keys(prefix):
        for k in list(st.session_state.keys()):
            if k.startswith(prefix):
                del st.session_state[k]

    def doc_badge(days):
        if days is None:
            return "⚪ Girilmedi"
        if days < 0:
            return f"🔴 {abs(days)} gün önce doldu"
        if days == 0:
            return "🟠 Bugün doluyor"
        if days <= 30:
            return f"🟠 {days} gün kaldı"
        return f"🟢 Geçerli ({days} gün)"

    # -------------------------------------------------
    # BAŞLIK
    # -------------------------------------------------

    st.title("🚗 Araçlar")
    st.caption(
        "Aracınızın belgelerini, masraflarını ve yakıt tüketimini takip edin."
    )

    vehicles = get_vehicles()

    # -------------------------------------------------
    # YENİ ARAÇ EKLE
    # -------------------------------------------------

    with st.expander("➕ Yeni Araç Ekle", expanded=not vehicles):

        with st.form("vehicle_form", clear_on_submit=True):

            f1, f2 = st.columns(2)

            with f1:
                new_plate = st.text_input("Plaka", placeholder="34 ABC 123")
                new_brand = st.text_input("Marka", placeholder="Örn: Renault")
                new_model = st.text_input("Model", placeholder="Örn: Clio")
                new_year = st.number_input(
                    "Model yılı",
                    min_value=1980,
                    max_value=today.year + 1,
                    value=today.year,
                    step=1
                )
                new_fuel = st.selectbox("Yakıt türü", fuel_types)

            with f2:
                new_km = st.number_input(
                    "Güncel kilometre",
                    min_value=0,
                    value=0,
                    step=1000
                )
                new_inspection = st.date_input(
                    "Muayene bitiş tarihi (opsiyonel)",
                    value=None
                )
                new_traffic = st.date_input(
                    "Trafik sigortası bitiş (opsiyonel)",
                    value=None
                )
                new_kasko = st.date_input(
                    "Kasko bitiş (opsiyonel)",
                    value=None
                )
                new_notes = st.text_area("Notlar")

            if st.form_submit_button("💾 Aracı Kaydet", type="primary"):

                if not new_plate.strip() or not new_brand.strip():

                    st.error("Plaka ve marka boş bırakılamaz.")

                else:

                    add_vehicle(
                        new_plate.strip().upper(),
                        new_brand.strip(),
                        new_model.strip(),
                        int(new_year),
                        new_fuel,
                        int(new_km),
                        str(new_inspection) if new_inspection else "",
                        str(new_traffic) if new_traffic else "",
                        str(new_kasko) if new_kasko else "",
                        new_notes.strip()
                    )

                    notify("Araç başarıyla eklendi!", "🚗")
                    st.rerun()

    if not vehicles:
        st.info("Henüz kayıtlı araç yok. Yukarıdan aracınızı ekleyin.")
        st.stop()

    # -------------------------------------------------
    # ARAÇ SEÇİMİ
    # -------------------------------------------------

    labels = {v[0]: f"{v[1]} — {v[2]} {v[3] or ''}".strip() for v in vehicles}

    if len(vehicles) > 1:
        sel_id = st.selectbox(
            "Araç",
            list(labels.keys()),
            format_func=lambda x: labels[x],
            key="veh_selected"
        )
    else:
        sel_id = vehicles[0][0]

    vehicle = next(v for v in vehicles if v[0] == sel_id)

    (
        v_id, v_plate, v_brand, v_model, v_year, v_fuel, v_km,
        v_inspection, v_traffic, v_kasko, v_notes
    ) = vehicle

    energy_unit = "kWh" if v_fuel == "Elektrik" else "L"

    # -------------------------------------------------
    # ARAÇ KARTI
    # -------------------------------------------------

    with st.container(border=True):

        h1, h2, h3 = st.columns([3, 2, 2])

        with h1:
            st.markdown(f"### 🚗 {v_plate}")
            st.caption(f"{v_brand} {v_model or ''} • {v_year or '-'}")

        with h2:
            st.metric("Kilometre", f"{(v_km or 0):,} km")

        with h3:
            st.metric("Yakıt", v_fuel or "-")

    # -------------------------------------------------
    # BELGELER VE SÜRELER
    # -------------------------------------------------

    st.subheader("📄 Belgeler ve Süreler")

    doc_cols = st.columns(3)

    for col, (label, value) in zip(
        doc_cols,
        [
            ("🛠️ Muayene", v_inspection),
            ("🛡️ Trafik Sigortası", v_traffic),
            ("🚘 Kasko", v_kasko)
        ]
    ):

        d = parse_date(value)
        days = (d - today).days if d else None

        with col:
            with st.container(border=True):
                st.caption(label)
                st.markdown(f"**{value or 'Girilmedi'}**")
                st.caption(doc_badge(days))

    # -------------------------------------------------
    # DÜZENLE / SİL
    # -------------------------------------------------

    ec1, ec2 = st.columns([4, 1])

    with ec1:

        with st.expander("✏️ Araç Bilgilerini Düzenle"):

            ek = f"veh_edit_{v_id}"

            e1, e2 = st.columns(2)

            with e1:
                ed_plate = st.text_input("Plaka", value=v_plate, key=f"{ek}_plate")
                ed_brand = st.text_input("Marka", value=v_brand, key=f"{ek}_brand")
                ed_model = st.text_input("Model", value=v_model or "", key=f"{ek}_model")
                ed_year = st.number_input(
                    "Model yılı",
                    min_value=1980,
                    max_value=today.year + 1,
                    value=int(v_year or today.year),
                    step=1,
                    key=f"{ek}_year"
                )
                ed_fuel = st.selectbox(
                    "Yakıt türü",
                    fuel_types,
                    index=fuel_types.index(v_fuel) if v_fuel in fuel_types else 0,
                    key=f"{ek}_fuel"
                )

            with e2:
                ed_km = st.number_input(
                    "Güncel kilometre",
                    min_value=0,
                    value=int(v_km or 0),
                    step=1000,
                    key=f"{ek}_km"
                )
                ed_inspection = st.date_input(
                    "Muayene bitiş",
                    value=parse_date(v_inspection),
                    key=f"{ek}_inspection"
                )
                ed_traffic = st.date_input(
                    "Trafik sigortası bitiş",
                    value=parse_date(v_traffic),
                    key=f"{ek}_traffic"
                )
                ed_kasko = st.date_input(
                    "Kasko bitiş",
                    value=parse_date(v_kasko),
                    key=f"{ek}_kasko"
                )
                ed_notes = st.text_area(
                    "Notlar",
                    value=v_notes or "",
                    key=f"{ek}_notes"
                )

            if st.button(
                "💾 Değişiklikleri Kaydet",
                key=f"{ek}_save",
                type="primary"
            ):

                if not ed_plate.strip() or not ed_brand.strip():

                    st.error("Plaka ve marka boş bırakılamaz.")

                else:

                    update_vehicle(
                        v_id,
                        ed_plate.strip().upper(),
                        ed_brand.strip(),
                        ed_model.strip(),
                        int(ed_year),
                        ed_fuel,
                        int(ed_km),
                        str(ed_inspection) if ed_inspection else "",
                        str(ed_traffic) if ed_traffic else "",
                        str(ed_kasko) if ed_kasko else "",
                        ed_notes.strip()
                    )

                    notify("Araç bilgileri güncellendi!", "✏️")
                    st.rerun()

    with ec2:

        with st.popover("🗑️ Aracı Sil", use_container_width=True):

            st.write(f"**{v_plate}** ve tüm masraf kayıtları silinsin mi?")

            if st.button(
                "Evet, sil",
                key=f"veh_delete_{v_id}",
                type="primary"
            ):
                delete_vehicle(v_id)
                st.session_state.pop("veh_selected", None)
                notify("Araç silindi!", "🗑️")
                st.rerun()

    # -------------------------------------------------
    # MASRAF VERİSİ
    # -------------------------------------------------

    expenses = get_vehicle_expenses(v_id)

    df = pd.DataFrame(
        [
            {
                "id": e[0],
                "Tarih": parse_date(e[2]) or today,
                "Tür": e[3],
                "Tutar": e[4],
                "Km": e[5] if e[5] else None,
                "Litre": e[6] if e[6] else None,
                "Not": e[7]
            }
            for e in expenses
        ],
        columns=["id", "Tarih", "Tür", "Tutar", "Km", "Litre", "Not"]
    )

    df["Km"] = pd.to_numeric(df["Km"], errors="coerce")
    df["Litre"] = pd.to_numeric(df["Litre"], errors="coerce")

    # Yakıt tüketimi: ardışık dolumlar arasındaki km'ye göre
    # (depo her seferinde doldurulduğu varsayılır)
    fuel_df = df[
        (df["Tür"] == "Yakıt")
        & df["Km"].notna()
        & df["Litre"].notna()
        & (df["Litre"] > 0)
    ].sort_values("Km")

    consumption_rows = []
    prev_km = None

    for _, r in fuel_df.iterrows():
        if prev_km is not None and r["Km"] > prev_km:
            consumption_rows.append(
                {
                    "Tarih": r["Tarih"],
                    "Tüketim": r["Litre"] / (r["Km"] - prev_km) * 100
                }
            )
        prev_km = r["Km"]

    avg_consumption = None

    if len(fuel_df) >= 2:
        distance = fuel_df["Km"].max() - fuel_df["Km"].min()
        if distance > 0:
            avg_consumption = (
                fuel_df.iloc[1:]["Litre"].sum() / distance * 100
            )

    # Km başı yaklaşık maliyet (tüm masraflar / km aralığı)
    km_values = df["Km"].dropna()
    cost_per_km = None

    if len(km_values) >= 2 and km_values.max() > km_values.min():
        cost_per_km = df["Tutar"].sum() / (km_values.max() - km_values.min())

    month_total = float(
        sum(
            amount
            for d, amount in zip(df["Tarih"], df["Tutar"])
            if (d.year, d.month) == (today.year, today.month)
        )
    )

    year_total = float(
        sum(
            amount
            for d, amount in zip(df["Tarih"], df["Tutar"])
            if d.year == today.year
        )
    )
    # -------------------------------------------------
    # ÖZET KARTLARI
    # -------------------------------------------------

    st.write("")

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        with st.container(border=True):
            st.metric("Bu Ay Masraf", f"₺{month_total:,.2f}")

    with k2:
        with st.container(border=True):
            st.metric(f"{today.year} Masraf", f"₺{year_total:,.2f}")

    with k3:
        with st.container(border=True):
            st.metric(
                "Ort. Tüketim",
                (
                    f"{avg_consumption:.1f} {energy_unit}/100 km"
                    if avg_consumption else "—"
                ),
                help="En az iki yakıt kaydında km ve litre girilmiş olmalı."
            )

    with k4:
        with st.container(border=True):
            st.metric(
                "Km Başı Maliyet",
                f"₺{cost_per_km:,.2f}" if cost_per_km else "—",
                help=(
                    "Tüm masrafların, kayıtlardaki km aralığına bölümü. "
                    "Yaklaşık bir değerdir."
                )
            )

    st.write("")

    tab_add, tab_hist, tab_analysis = st.tabs(
        ["➕ Masraf Ekle", "📜 Masraf Geçmişi", "📊 Analiz"]
    )

    # =================================================
    # SEKME 1: MASRAF EKLE
    # =================================================

    with tab_add:

        xk = f"vexp_{v_id}"

        x1, x2 = st.columns(2)

        with x1:
            x_date = st.date_input("Tarih", value=today, key=f"{xk}_date")
            x_type = st.selectbox("Masraf türü", expense_types, key=f"{xk}_type")
            x_amount = st.number_input(
                "Tutar (₺)",
                min_value=0.0,
                step=50.0,
                key=f"{xk}_amount"
            )

        with x2:
            x_km = st.number_input(
                "Kilometre (opsiyonel)",
                min_value=0,
                value=int(v_km or 0),
                step=100,
                key=f"{xk}_km"
            )

            x_liters = 0.0

            if x_type == "Yakıt":
                x_liters = st.number_input(
                    f"Alınan miktar ({energy_unit})",
                    min_value=0.0,
                    step=1.0,
                    key=f"{xk}_liters"
                )

                if x_liters > 0 and x_amount > 0:
                    st.caption(
                        f"Birim fiyat: ₺{x_amount / x_liters:,.2f} / "
                        f"{energy_unit}"
                    )

            x_note = st.text_input(
                "Not (opsiyonel)",
                placeholder="Örn: Shell, depo full",
                key=f"{xk}_note"
            )

        x_pay = st.checkbox(
            "Ödemeler listesine ödenmiş gider olarak ekle",
            help=(
                "İşaretlersen bu masraf Ödemeler, Harcamalar ve "
                "Dashboard'a da yansır."
            ),
            key=f"{xk}_pay"
        )

        if x_type == "Yakıt":
            st.caption(
                "💡 Tüketim hesabı için yakıt kayıtlarında km ve miktarı "
                "girin ve depoyu her seferinde doldurun."
            )

        if st.button(
            "💾 Masrafı Kaydet",
            type="primary",
            use_container_width=True,
            key=f"{xk}_save"
        ):

            if x_amount <= 0:

                st.error("Tutar 0'dan büyük olmalı.")

            else:

                add_vehicle_expense(
                    v_id,
                    str(x_date),
                    x_type,
                    x_amount,
                    int(x_km) if x_km > 0 else None,
                    x_liters if x_liters > 0 else None,
                    x_note.strip()
                )

                if x_pay:
                    add_paid_payment(
                        f"{v_plate} {x_type}",
                        x_amount,
                        str(x_date),
                        "Diğer"
                    )

                notify("Masraf kaydedildi!", "🚗")

                clear_keys(xk)
                st.rerun()

    # =================================================
    # SEKME 2: MASRAF GEÇMİŞİ
    # =================================================

    with tab_hist:

        if df.empty:

            st.info("Bu araç için henüz masraf kaydı yok.")

        else:

            type_filter = st.selectbox(
                "Tür",
                ["Tümü"] + expense_types,
                key="veh_hist_type"
            )

            hist = df if type_filter == "Tümü" else df[df["Tür"] == type_filter]

            st.caption(
                f"{len(hist)} kayıt • Toplam ₺{hist['Tutar'].sum():,.2f}"
            )

            if not hist.empty:
                st.download_button(
                    "⬇️ CSV indir",
                    data=hist.drop(columns=["id"])
                    .to_csv(index=False)
                    .encode("utf-8-sig"),
                    file_name=f"arac_masraflari_{v_plate.replace(' ', '')}.csv",
                    mime="text/csv"
                )

            for _, r in hist.iterrows():

                with st.container(border=True):

                    a, b, c, d = st.columns([2, 1.5, 3, 1])

                    with a:
                        st.markdown(f"**{r['Tür']}**")
                        st.caption(f"📅 {r['Tarih']}")

                    with b:
                        st.markdown(f"**₺{r['Tutar']:,.2f}**")

                    with c:
                        details = []

                        if pd.notna(r["Km"]):
                            details.append(f"{int(r['Km']):,} km")

                        if pd.notna(r["Litre"]):
                            details.append(f"{r['Litre']:.1f} {energy_unit}")

                        if r["Not"]:
                            details.append(r["Not"])

                        st.caption(" • ".join(details) or "—")

                    with d:
                        with st.popover("🗑️"):
                            st.write("Bu kayıt silinsin mi?")
                            st.caption(
                                "Ödemeler listesine eklenmişse oradaki "
                                "kayıt silinmez."
                            )
                            if st.button(
                                "Evet, sil",
                                key=f"veh_exp_del_{int(r['id'])}",
                                type="primary"
                            ):
                                delete_vehicle_expense(int(r["id"]))
                                notify("Masraf silindi!", "🗑️")
                                st.rerun()

    # =================================================
    # SEKME 3: ANALİZ
    # =================================================

    with tab_analysis:

        if df.empty:

            st.info("Analiz için önce masraf ekleyin.")

        else:

            # Son 12 ay
            months = []

            for i in range(11, -1, -1):
                y, m = today.year, today.month - i
                while m <= 0:
                    m += 12
                    y -= 1
                months.append((y, m))

            month_labels = [f"{m:02d}/{y}" for y, m in months]

            last12 = df[
                df["Tarih"].apply(lambda d: (d.year, d.month) in months)
            ].copy()

            last12["Ay"] = last12["Tarih"].apply(
                lambda d: f"{d.month:02d}/{d.year}"
            )

            left, right = st.columns([3, 2])

            with left:

                with st.container(border=True):

                    st.subheader("📈 Son 12 Ay Masraf")

                    if last12.empty:

                        st.info("Son 12 ayda masraf yok.")

                    else:

                        grouped = (
                            last12.groupby(["Ay", "Tür"], as_index=False)["Tutar"]
                            .sum()
                        )

                        fig = px.bar(
                            grouped,
                            x="Ay",
                            y="Tutar",
                            color="Tür",
                            category_orders={"Ay": month_labels}
                        )

                        fig.update_traces(
                            hovertemplate=(
                                "<b>%{x}</b><br>₺%{y:,.2f}<extra></extra>"
                            )
                        )

                        fig.update_layout(
                            height=360,
                            margin=dict(l=10, r=10, t=10, b=10),
                            xaxis_title=None,
                            yaxis_title=None,
                            legend=dict(
                                orientation="h",
                                yanchor="top",
                                y=-0.2,
                                xanchor="center",
                                x=0.5,
                                title=None
                            )
                        )

                        st.plotly_chart(fig, use_container_width=True)

            with right:

                with st.container(border=True):

                    st.subheader("🥧 Türe Göre Dağılım")

                    type_totals = (
                        df.groupby("Tür", as_index=False)["Tutar"].sum()
                    )

                    fig2 = px.pie(
                        type_totals,
                        names="Tür",
                        values="Tutar",
                        hole=0.55
                    )

                    fig2.update_traces(
                        textposition="inside",
                        textinfo="percent",
                        hovertemplate=(
                            "<b>%{label}</b><br>₺%{value:,.2f}"
                            "<br>%{percent}<extra></extra>"
                        ),
                        marker=dict(line=dict(color="white", width=2))
                    )

                    fig2.update_layout(
                        height=360,
                        margin=dict(l=10, r=10, t=10, b=10),
                        legend=dict(
                            orientation="h",
                            yanchor="top",
                            y=-0.05,
                            xanchor="center",
                            x=0.5
                        )
                    )

                    st.plotly_chart(fig2, use_container_width=True)

            # ---------------- YAKIT ----------------

            with st.container(border=True):

                st.subheader(f"⛽ Yakıt Takibi ({energy_unit})")

                f_left, f_right = st.columns(2)

                with f_left:

                    st.caption(f"Tüketim ({energy_unit}/100 km)")

                    if consumption_rows:

                        cons_df = pd.DataFrame(consumption_rows)

                        fig3 = px.line(
                            cons_df,
                            x="Tarih",
                            y="Tüketim",
                            markers=True
                        )

                        fig3.update_traces(
                            hovertemplate=(
                                "%{x}<br>%{y:.1f}<extra></extra>"
                            )
                        )

                        fig3.update_layout(
                            height=280,
                            margin=dict(l=10, r=10, t=10, b=10),
                            xaxis_title=None,
                            yaxis_title=None
                        )

                        st.plotly_chart(fig3, use_container_width=True)

                    else:

                        st.info(
                            "En az iki yakıt kaydında km ve miktar girilince "
                            "tüketim grafiği çıkar."
                        )

                with f_right:

                    st.caption(f"Birim fiyat (₺/{energy_unit})")

                    price_df = df[
                        (df["Tür"] == "Yakıt")
                        & df["Litre"].notna()
                        & (df["Litre"] > 0)
                    ].copy()

                    if len(price_df) >= 2:

                        price_df["Birim Fiyat"] = (
                            price_df["Tutar"] / price_df["Litre"]
                        )

                        fig4 = px.line(
                            price_df.sort_values("Tarih"),
                            x="Tarih",
                            y="Birim Fiyat",
                            markers=True
                        )

                        fig4.update_traces(
                            hovertemplate=(
                                "%{x}<br>₺%{y:.2f}<extra></extra>"
                            )
                        )

                        fig4.update_layout(
                            height=280,
                            margin=dict(l=10, r=10, t=10, b=10),
                            xaxis_title=None,
                            yaxis_title=None
                        )

                        st.plotly_chart(fig4, use_container_width=True)

                    else:

                        st.info(
                            "Birim fiyat grafiği için en az iki yakıt "
                            "kaydında miktar girilmeli."
                        )
# =====================================================
# TAKVİM
# =====================================================

elif menu == "Takvim":

    import calendar
    import html as html_lib
    from datetime import timedelta

    today = date.today()

    month_names = [
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
    ]
    weekday_names = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

    # tür: (ikon, ad, renk)
    KIND_INFO = {
        "payment": ("💳", "Ödemeler", "#f59e0b"),
        "maintenance": ("🔧", "Bakımlar", "#3b82f6"),
        "warranty": ("🛡️", "Garanti bitişleri", "#14b8a6"),
        "vehicle": ("🚗", "Araç belgeleri", "#6366f1"),
        "tax": ("🏛️", "Vergi / Resmi", "#a855f7"),
        "custom": ("📌", "Hatırlatıcılar", "#ec4899"),
    }
    KIND_ORDER = list(KIND_INFO.keys())

    COLOR_DONE = "#22c55e"
    COLOR_BAD = "#ef4444"
    COLOR_PAST = "#9ca3af"

    TAX_OPTIONS = {
        "mtv": "MTV (Ocak, Temmuz)",
        "emlak": "Emlak vergisi (Mayıs, Kasım)",
        "gelir": "Gelir vergisi taksitleri (Mart, Temmuz)",
    }

    # (ay, gün, başlık)
    TAX_DATES = {
        "mtv": [
            (1, 31, "MTV 1. taksit son gün"),
            (7, 31, "MTV 2. taksit son gün"),
        ],
        "emlak": [
            (5, 31, "Emlak vergisi 1. taksit son gün"),
            (11, 30, "Emlak vergisi 2. taksit son gün"),
        ],
        "gelir": [
            (3, 31, "Gelir vergisi 1. taksit son gün"),
            (7, 31, "Gelir vergisi 2. taksit son gün"),
        ],
    }

    # -------------------------------------------------
    # YARDIMCI FONKSİYONLAR
    # -------------------------------------------------

    def parse_date(value):
        if not value or not str(value).strip():
            return None
        try:
            return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
        except ValueError:
            return None

    def safe_date(year, month, day):
        """Günü ayın uzunluğuna sığdırır (31 -> Şubat'ta 28/29)."""
        return date(
            year, month,
            min(day, calendar.monthrange(year, month)[1])
        )

    def shift_month(delta):
        m = st.session_state["cal_month"] - 1 + delta
        st.session_state["cal_year"] += m // 12
        st.session_state["cal_month"] = m % 12 + 1

    def go_today():
        st.session_state["cal_year"] = today.year
        st.session_state["cal_month"] = today.month

    def sort_key(e):
        return (
            e["state"] != "bad",
            KIND_ORDER.index(e["kind"]),
            e["title"]
        )

    def chip_color(e):
        if e["state"] == "done":
            return COLOR_DONE
        if e["state"] == "bad":
            return COLOR_BAD
        if e["state"] == "past":
            return COLOR_PAST
        return KIND_INFO[e["kind"]][2]

    def status_text(e):
        days = (e["date"] - today).days
        if e["state"] == "done":
            return "✅ Ödendi"
        if e["state"] == "proj":
            return "🔮 Tahmini"
        if e["state"] == "bad":
            return f"🔴 {abs(days)} gün gecikti"
        if e["state"] == "past":
            return "—"
        if days == 0:
            return "🟠 Bugün"
        if days == 1:
            return "🟡 Yarın"
        if days <= 7:
            return f"🟡 {days} gün kaldı"
        return f"{days} gün kaldı"

    # -------------------------------------------------
    # BAŞLIK VE AY GEZİNME
    # -------------------------------------------------

    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = today.year
        st.session_state["cal_month"] = today.month

    cy = st.session_state["cal_year"]
    cm = st.session_state["cal_month"]

    st.title("📅 Takvim")
    st.caption(
        "Ödeme, bakım, garanti, araç belgesi ve vergi tarihleriniz "
        "tek takvimde."
    )

    nav1, nav2, nav3, nav4 = st.columns([1, 4, 1, 1.5])

    with nav1:
        st.button(
            "◀", key="cal_prev",
            on_click=shift_month, args=(-1,),
            use_container_width=True
        )

    with nav2:
        st.markdown(
            f"<h3 style='text-align:center; margin:0;'>"
            f"{month_names[cm - 1]} {cy}</h3>",
            unsafe_allow_html=True
        )

    with nav3:
        st.button(
            "▶", key="cal_next",
            on_click=shift_month, args=(1,),
            use_container_width=True
        )

    with nav4:
        st.button(
            "📍 Bugün", key="cal_today",
            on_click=go_today,
            use_container_width=True
        )

    # -------------------------------------------------
    # FİLTRELER
    # -------------------------------------------------

    f1, f2, f3 = st.columns([3, 2.5, 1.5])

    with f1:
        sel_kinds = st.multiselect(
            "Göster",
            KIND_ORDER,
            default=KIND_ORDER,
            format_func=lambda k: f"{KIND_INFO[k][0]} {KIND_INFO[k][1]}",
            key="cal_kinds"
        )

    with f2:
        tax_picks = st.multiselect(
            "Vergi tarihleri",
            list(TAX_OPTIONS.keys()),
            default=["mtv", "emlak"],
            format_func=lambda k: TAX_OPTIONS[k],
            key="cal_tax_picks"
        )

    with f3:
        st.write("")
        show_paid = st.toggle(
            "Ödenenleri göster",
            value=True,
            key="cal_show_paid"
        )

    # -------------------------------------------------
    # ETKİNLİKLERİ TOPLA
    # -------------------------------------------------

    def collect_events(start, end):
        """start-end (dahil) aralığındaki tüm etkinlikler.
        state: normal / bad (gecikmiş) / done (ödendi) /
               past (geçmiş, uyarı değil) / proj (tahmini)"""

        events = []

        def add(d, kind, title, detail="", state="normal",
                pid=None, amount=None):
            if d is None or d < start or d > end:
                return
            events.append(
                {
                    "date": d,
                    "kind": kind,
                    "title": title,
                    "detail": detail,
                    "state": state,
                    "pid": pid,
                    "amount": amount
                }
            )

        # ---------------- ÖDEMELER ----------------

        names_by_month = {}

        for (pid, p_name, p_amount, p_due, p_cat, p_status) in get_payments():

            d = parse_date(p_due)

            if d is None:
                continue

            names_by_month.setdefault((d.year, d.month), set()).add(p_name)

            if p_status == "Ödendi":
                state = "done"
            elif d < today:
                state = "bad"
            else:
                state = "normal"

            add(
                d, "payment",
                f"{p_name} • ₺{float(p_amount):,.0f}",
                p_cat, state,
                pid=pid, amount=float(p_amount)
            )

        # Henüz oluşmamış gelecek ayların sabit ödemeleri (tahmini)
        recurring_all = get_recurring_payments()

        cur = date(start.year, start.month, 1)

        while cur <= end:

            if (cur.year, cur.month) > (today.year, today.month):

                existing = names_by_month.get((cur.year, cur.month), set())

                for (
                    rid, r_name, r_amount, r_day, r_cat, r_active
                ) in recurring_all:

                    if r_active != 1 or r_name in existing:
                        continue

                    add(
                        safe_date(cur.year, cur.month, int(r_day)),
                        "payment",
                        f"{r_name} • ₺{float(r_amount):,.0f}",
                        f"{r_cat} • tahmini (sabit ödeme)",
                        "proj",
                        amount=float(r_amount)
                    )

            cur = date(cur.year + cur.month // 12, cur.month % 12 + 1, 1)

        # ---------------- KREDİ KARTI SON ÖDEME GÜNLERİ ----------------
        # Ekstre girilmemiş aylar için kartın son ödeme gününü tahmini
        # olarak gösterir. Ekstre girilince gerçek ödeme kaydı görünür,
        # bu tahmini kayıt kaybolur.

        for (
            k_id, k_name, k_last4, k_limit, k_stmt_day, k_due_day
        ) in get_credit_cards():

            entered_periods = {s[1] for s in get_card_statements(k_id)}

            k_cur = date(start.year, start.month, 1)

            while k_cur <= end:

                k_period = f"{k_cur.year}-{k_cur.month:02d}"

                k_date = safe_date(k_cur.year, k_cur.month, int(k_due_day))

                if k_period not in entered_periods and k_date >= today:
                    add(
                        k_date,
                        "payment",
                        f"{k_name} son ödeme",
                        "Kredi kartı • ekstre henüz girilmedi",
                        "proj"
                    )

                k_cur = date(
                    k_cur.year + k_cur.month // 12,
                    k_cur.month % 12 + 1,
                    1
                )

        # ---------------- BAKIM VE GARANTİ ----------------

        for (
            a_id, a_name, a_brand, a_model, a_pdate,
            a_price, a_warranty, a_maint, a_notes
        ) in get_assets():

            m_date = parse_date(a_maint)

            if m_date:
                add(
                    m_date, "maintenance", f"{a_name} bakımı",
                    a_brand or "",
                    "bad" if m_date < today else "normal"
                )

            w_date = parse_date(a_warranty)

            if w_date:
                add(
                    w_date, "warranty", f"{a_name} garanti bitişi",
                    a_brand or "",
                    "past" if w_date < today else "normal"
                )

        # ---------------- ARAÇ BELGELERİ ----------------

        for (
            v_id, v_plate, v_brand, v_model, v_year, v_fuel, v_km,
            v_insp, v_traf, v_kasko, v_notes
        ) in get_vehicles():

            for label, value in (
                ("Muayene", v_insp),
                ("Trafik sigortası", v_traf),
                ("Kasko", v_kasko)
            ):

                d = parse_date(value)

                if d:
                    add(
                        d, "vehicle", f"{v_plate} {label} bitişi",
                        f"{v_brand} {v_model or ''}".strip(),
                        "bad" if d < today else "normal"
                    )

        # ---------------- VERGİ TARİHLERİ ----------------

        for year in range(start.year, end.year + 1):

            for key in tax_picks:

                for (mm, dd, label) in TAX_DATES[key]:

                    d = safe_date(year, mm, dd)

                    add(
                        d, "tax", label,
                        "Resmi son tarih (genel kural)",
                        "past" if d < today else "normal"
                    )

        # ---------------- KENDİ ETKİNLİKLERİM ----------------

        for (
            ev_id, ev_title, ev_date, ev_kind, ev_repeat, ev_notes
        ) in get_calendar_events():

            base = parse_date(ev_date)

            if base is None:
                continue

            kind = "tax" if ev_kind == "tax" else "custom"

            if ev_repeat:
                for year in range(
                    max(start.year, base.year), end.year + 1
                ):
                    d = safe_date(year, base.month, base.day)
                    add(
                        d, kind, ev_title, ev_notes,
                        "past" if d < today else "normal"
                    )
            else:
                add(
                    base, kind, ev_title, ev_notes,
                    "past" if base < today else "normal"
                )

        return events

    def in_kinds(items):
        return [e for e in items if e["kind"] in sel_kinds]
    full_weekdays = [
        "Pazartesi", "Salı", "Çarşamba", "Perşembe",
        "Cuma", "Cumartesi", "Pazar"
    ]

    @st.dialog("📅 Gün Detayı", width="large")
    def show_day_dialog(day_iso):

        day = date.fromisoformat(day_iso)

        day_events = sorted(
            [
                e for e in in_kinds(collect_events(day, day))
                if show_paid or e["state"] != "done"
            ],
            key=sort_key
        )

        st.markdown(
            f"### {day.day} {month_names[day.month - 1]} {day.year}, "
            f"{full_weekdays[day.weekday()]}"
        )

        if not day_events:
            st.info("Bu güne ait etkinlik yok.")
            return

        pay_events = [e for e in day_events if e["amount"] is not None]

        if pay_events:

            day_total = sum(e["amount"] for e in pay_events)
            day_pending = sum(
                e["amount"] for e in pay_events if e["state"] != "done"
            )

            m1, m2, m3 = st.columns(3)

            with m1:
                st.metric("Etkinlik", len(day_events))

            with m2:
                st.metric("Ödeme Toplamı", f"₺{day_total:,.2f}")

            with m3:
                st.metric("Bekleyen", f"₺{day_pending:,.2f}")

        else:

            st.metric("Etkinlik", len(day_events))

        st.write("")

        for e in day_events:

            icon = "✅" if e["state"] == "done" else KIND_INFO[e["kind"]][0]

            with st.container(border=True):

                c1, c2, c3 = st.columns([4, 2, 2])

                with c1:
                    st.markdown(f"**{icon} {e['title']}**")
                    st.caption(
                        KIND_INFO[e["kind"]][1]
                        + (f" • {e['detail']}" if e["detail"] else "")
                    )

                with c2:
                    st.write(status_text(e))

                with c3:
                    if e["pid"] is not None and e["state"] in ("normal", "bad"):
                        if st.button(
                            "✅ Ödendi",
                            key=f"dlg_paid_{e['pid']}",
                            type="primary",
                            use_container_width=True
                        ):
                            mark_payment_paid(int(e["pid"]))
                            notify(
                                "Ödeme ödendi olarak işaretlendi!",
                                "✅"
                            )
                            st.rerun()

    # -------------------------------------------------
    # AY IZGARASI İÇİN VERİ
    # -------------------------------------------------

    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(cy, cm)
    grid_start, grid_end = weeks[0][0], weeks[-1][-1]

    visible = [
        e for e in in_kinds(collect_events(grid_start, grid_end))
        if show_paid or e["state"] != "done"
    ]

    by_day = {}

    for e in visible:
        by_day.setdefault(e["date"], []).append(e)

    month_events = [
        e for e in visible
        if e["date"].year == cy and e["date"].month == cm
    ]

    # -------------------------------------------------
    # ÖZET KARTLARI
    # -------------------------------------------------

    overdue_events = [
        e for e in in_kinds(
            collect_events(
                date(today.year - 2, 1, 1),
                today - timedelta(days=1)
            )
        )
        if e["state"] == "bad"
    ]

    next7 = [
        e for e in in_kinds(
            collect_events(today, today + timedelta(days=7))
        )
        if e["state"] in ("normal", "proj")
    ]

    next30 = [
        e for e in in_kinds(
            collect_events(today, today + timedelta(days=30))
        )
        if e["state"] in ("normal", "proj")
    ]

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        with st.container(border=True):
            st.metric(f"{month_names[cm - 1]} Etkinlikleri", len(month_events))

    with s2:
        with st.container(border=True):
            st.metric("7 Gün İçinde", len(next7))

    with s3:
        with st.container(border=True):
            st.metric("30 Gün İçinde", len(next30))

    with s4:
        with st.container(border=True):
            st.metric("Geciken", len(overdue_events))

    st.write("")

    tab_cal, tab_my = st.tabs(["🗓️ Takvim", "📌 Kendi Etkinliklerim"])

    # =================================================
    # SEKME 1: TAKVİM
    # =================================================

    with tab_cal:

        css = (
            "<style>"
            ".cal-head{text-align:center;font-weight:600;"
            "font-size:.8rem;opacity:.7;}"
            ".cal-chip{font-size:.68rem;line-height:1.25;padding:1px 4px;"
            "margin-top:2px;border-radius:4px;white-space:nowrap;"
            "overflow:hidden;text-overflow:ellipsis;"
            "border-left:3px solid;max-width:100%;box-sizing:border-box;}"
            ".cal-more{font-size:.68rem;opacity:.7;margin-top:2px;}"
            "</style>"
        )

        st.markdown(css, unsafe_allow_html=True)

        head_cols = st.columns(7)

        for i, wd in enumerate(weekday_names):
            with head_cols[i]:
                st.markdown(
                    f"<div class='cal-head'>{wd}</div>",
                    unsafe_allow_html=True
                )

        for week in weeks:

            week_cols = st.columns(7)

            for i, d in enumerate(week):

                in_month = d.month == cm

                day_events = (
                    sorted(by_day.get(d, []), key=sort_key)
                    if in_month else []
                )

                with week_cols[i]:

                    with st.container(border=True, height=150):

                        label = str(d.day)

                        

                        if st.button(
                            label,
                            key=f"cal_day_{d.isoformat()}",
                            type="primary" if d == today else "secondary",
                            disabled=not in_month,
                            use_container_width=True
                        ):
                            show_day_dialog(d.isoformat())

                        if day_events:

                            chips = []

                            for e in day_events[:2]:

                                color = chip_color(e)
                                icon = (
                                    "✅" if e["state"] == "done"
                                    else KIND_INFO[e["kind"]][0]
                                )

                                extra = ""

                                if e["state"] == "done":
                                    extra = (
                                        "text-decoration:line-through;"
                                        "opacity:.7;"
                                    )
                                elif e["state"] == "proj":
                                    extra = (
                                        "border-style:dashed;"
                                        "font-style:italic;"
                                    )

                                short = (
                                    e["title"] if len(e["title"]) <= 22
                                    else e["title"][:21] + "…"
                                )

                                chips.append(
                                    f'<div class="cal-chip" '
                                    f'style="background:{color}26;'
                                    f'border-color:{color};{extra}">'
                                    f'{icon} {html_lib.escape(short)}</div>'
                                )

                            if len(day_events) > 2:
                                chips.append(
                                    f'<div class="cal-more">'
                                    f'+{len(day_events) - 2} daha</div>'
                                )

                            st.markdown(
                                "".join(chips),
                                unsafe_allow_html=True
                            )
        st.caption(
            "🔴 gecikmiş • 🟢 ödenmiş • kesik çizgili: henüz oluşmamış "
            "sabit ödeme (tahmini) • bir güne tıklayınca o günün tüm "
            "etkinlikleri açılır"
        )

        # ---------------- AYIN LİSTESİ ----------------

        st.write("")
        st.subheader(f"📋 {month_names[cm - 1]} {cy} Etkinlikleri")

        if not month_events:

            st.info("Bu ay için etkinlik yok.")

        else:

            rows = [
                {
                    "Tarih": e["date"],
                    "Tür": f"{KIND_INFO[e['kind']][0]} {KIND_INFO[e['kind']][1]}",
                    "Etkinlik": e["title"],
                    "Detay": e["detail"],
                    "Durum": status_text(e)
                }
                for e in sorted(
                    month_events,
                    key=lambda e: (e["date"],) + sort_key(e)
                )
            ]

            st.dataframe(
                pd.DataFrame(rows),
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Tarih": st.column_config.DateColumn(
                        "Tarih",
                        format="DD.MM.YYYY"
                    )
                }
            )

    # =================================================
    # SEKME 2: KENDİ ETKİNLİKLERİM
    # =================================================

    with tab_my:

        with st.form("cal_event_form", clear_on_submit=True):

            c1, c2 = st.columns(2)

            with c1:
                ev_title = st.text_input(
                    "Etkinlik adı",
                    placeholder="Örn: Kombi bakım randevusu"
                )
                ev_date = st.date_input("Tarih", value=today)

            with c2:
                ev_kind = st.selectbox(
                    "Tür",
                    ["custom", "tax"],
                    format_func=lambda k: (
                        "📌 Hatırlatıcı" if k == "custom"
                        else "🏛️ Vergi / Resmi"
                    )
                )
                ev_repeat = st.checkbox("🔁 Her yıl tekrarla")

            ev_notes = st.text_input("Not (opsiyonel)")

            if st.form_submit_button("💾 Etkinliği Kaydet", type="primary"):

                if not ev_title.strip():

                    st.error("Lütfen etkinlik adını girin.")

                else:

                    add_calendar_event(
                        ev_title.strip(),
                        str(ev_date),
                        ev_kind,
                        1 if ev_repeat else 0,
                        ev_notes.strip()
                    )

                    notify("Etkinlik eklendi!", "📌")
                    st.rerun()

        my_events = get_calendar_events()

        if not my_events:

            st.info(
                "Henüz kendi eklediğiniz etkinlik yok. Yukarıdan vergi "
                "tarihi, randevu ya da hatırlatıcı ekleyebilirsiniz."
            )

        else:

            st.markdown("**Eklediğim etkinlikler**")

            for (
                my_id, my_title, my_date, my_kind, my_repeat, my_notes
            ) in my_events:

                with st.container(border=True):

                    a, b, c = st.columns([4, 2, 1])

                    with a:
                        st.markdown(f"**{my_title}**")
                        st.caption(my_notes or "Not yok")

                    with b:
                        d_obj = parse_date(my_date)
                        st.write(
                            d_obj.strftime("%d.%m.%Y") if d_obj else my_date
                        )
                        st.caption(
                            ("🔁 Her yıl • " if my_repeat else "")
                            + KIND_INFO["tax" if my_kind == "tax" else "custom"][1]
                        )

                    with c:
                        with st.popover("🗑️"):
                            st.write("Bu etkinlik silinsin mi?")
                            if st.button(
                                "Evet, sil",
                                key=f"cal_del_{my_id}",
                                type="primary"
                            ):
                                delete_calendar_event(my_id)
                                notify("Etkinlik silindi!", "🗑️")
                                st.rerun()

# =====================================================
# YEDEKLEME
# Bu bloğu app.py içinde `elif menu == "🤖 AI Asistan":`
# satırının HEMEN ÜSTÜNE yeni bir elif bloğu olarak yapıştır.
# (Diğer elif bloklarıyla aynı girintide, en solda başlamalı.)
# =====================================================

elif menu == "Yedekleme":

    from datetime import datetime as _dt
    from backup import (
        BACKUP_DIR,
        KIND_LABELS,
        KNOWN_TABLES,
        create_backup_bytes,
        create_backup_file,
        get_current_counts,
        inspect_backup_bytes,
        list_backups,
        restore_from_bytes,
    )

    st.title("💾 Yedekleme")
    st.caption(
        "Verilerinizi yedekleyin, gerektiğinde geri yükleyin."
    )
    if st.session_state.pop("reset_done", False):
        st.success(
            "✅ Tüm veriler silindi. Uygulama sıfırdan başlamaya hazır. "
            "Geri dönmek isterseniz 'Yerel Yedekler' sekmesinden, "
            "silmeden hemen önce alınan 'Manuel' yedeği geri yükleyebilirsiniz."
        )

    current_counts = get_current_counts()
    local_backups = list_backups()

    def fmt_size(num_bytes):
        if num_bytes < 1024:
            return f"{num_bytes} B"
        if num_bytes < 1024 * 1024:
            return f"{num_bytes / 1024:.1f} KB"
        return f"{num_bytes / (1024 * 1024):.1f} MB"

    # -------------------------------------------------
    # ÖZET KARTLARI
    # -------------------------------------------------

    last_backup_text = (
        local_backups[0]["mtime"].strftime("%d.%m.%Y %H:%M")
        if local_backups else "Yok"
    )

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        with st.container(border=True):
            st.metric("Ödeme Kaydı", current_counts.get("payments", 0))

    with s2:
        with st.container(border=True):
            st.metric("Ev Eşyası", current_counts.get("assets", 0))

    with s3:
        with st.container(border=True):
            st.metric("Yerel Yedek", len(local_backups))

    with s4:
        with st.container(border=True):
            st.metric("Son Yerel Yedek", last_backup_text)

    st.write("")

    tab_dl, tab_restore, tab_local, tab_reset = st.tabs(
        [
            "⬇️ Yedek Al",
            "⬆️ Geri Yükle",
            "🗂️ Yerel Yedekler",
            "🗑️ Verileri Sıfırla"
        ]
    )

    # =================================================
    # SEKME 1: YEDEK AL
    # =================================================

    with tab_dl:

        with st.container(border=True):

            st.subheader("Yedeği bilgisayarına indir")

            st.write(
                "Tüm verilerin (ödemeler, eşyalar, bakımlar, araçlar) "
                "tek bir `.db` dosyası olarak iner."
            )

            st.download_button(
                "⬇️ Yedeği İndir (.db)",
                data=create_backup_bytes(),
                file_name=(
                    f"home_manager_yedek_{_dt.now():%Y-%m-%d_%H%M}.db"
                ),
                mime="application/octet-stream",
                type="primary",
                use_container_width=True,
                key="backup_download"
            )

            st.info(
                "💡 İndirdiğin dosyayı bilgisayarın dışında bir yerde de "
                "sakla (USB bellek, bulut depolama). Yerel yedekler bu "
                "bilgisayardaki diskte durduğu için disk bozulursa "
                "onlar da gider."
            )

    # =================================================
    # SEKME 2: GERİ YÜKLE
    # =================================================

    with tab_restore:

        n = st.session_state.get("restore_n", 0)

        uploaded = st.file_uploader(
            "Yedek dosyasını seçin (.db)",
            type=["db", "sqlite", "sqlite3"],
            key=f"restore_upload_{n}"
        )

        if uploaded is not None:

            data = uploaded.getvalue()
            info = inspect_backup_bytes(data)

            if not info["valid"]:

                st.error(f"❌ {info['error']}")

            else:

                st.subheader("📋 Yedek İçeriği")

                compare = pd.DataFrame(
                    [
                        {
                            "Kayıt türü": label,
                            "Şu an": current_counts.get(table, 0),
                            "Yedekte": info["counts"].get(table, 0)
                        }
                        for table, label in KNOWN_TABLES.items()
                        if table in info["counts"]
                        or table in current_counts
                    ]
                )

                st.dataframe(
                    compare,
                    hide_index=True,
                    use_container_width=True
                )

                st.warning(
                    "⚠️ Geri yükleme, şu anki **tüm verilerinin yerine** "
                    "bu yedeği koyar. İşlemden önce mevcut verilerin "
                    "otomatik olarak 'Yerel Yedekler' sekmesine "
                    "kaydedilir."
                )

                confirmed = st.checkbox(
                    "Mevcut verilerin yedekle değiştirileceğini anlıyorum",
                    key=f"restore_confirm_{n}"
                )

                if st.button(
                    "♻️ Yedeği Geri Yükle",
                    type="primary",
                    disabled=not confirmed,
                    use_container_width=True,
                    key=f"restore_btn_{n}"
                ):

                    try:
                        safety = restore_from_bytes(data)

                    except Exception as e:
                        st.error(f"❌ Geri yükleme başarısız: {e}")

                    else:
                        st.session_state["restore_n"] = n + 1

                        notify(
                            "Yedek başarıyla geri yüklendi!",
                            "♻️"
                        )

                        if safety is not None:
                            notify(
                                f"Önceki verilerin kaydedildi: {safety.name}",
                                "🛡️"
                            )

                        st.rerun()

    # =================================================
    # SEKME 3: YEREL YEDEKLER
    # =================================================

    with tab_local:

        top_l, top_r = st.columns([3, 1])

        with top_l:
            st.caption(
                f"Her gün uygulamanın ilk açılışında otomatik yedek alınır. "
                f"Son 14 otomatik, 10 manuel ve 5 geri yükleme öncesi yedek "
                f"saklanır. Klasör: `{BACKUP_DIR}`"
            )

        with top_r:
            if st.button(
                "📌 Şimdi Yedek Al",
                use_container_width=True,
                key="manual_local_backup"
            ):
                create_backup_file("manuel")
                notify("Yerel yedek alındı!", "📌")
                st.rerun()

        if not local_backups:

            st.info("Henüz yerel yedek yok.")

        for b in local_backups[:30]:

            with st.container(border=True):

                c1, c2, c3, c4 = st.columns([3, 1.2, 1.3, 1.3])

                with c1:
                    st.markdown(f"**{KIND_LABELS[b['kind']]}**")
                    st.caption(
                        f"{b['mtime']:%d.%m.%Y %H:%M} • {b['name']}"
                    )

                with c2:
                    st.write(fmt_size(b["size"]))

                with c3:
                    st.download_button(
                        "⬇️ İndir",
                        data=b["path"].read_bytes(),
                        file_name=b["name"],
                        mime="application/octet-stream",
                        key=f"dl_{b['name']}",
                        use_container_width=True
                    )

                with c4:
                    with st.popover(
                        "♻️ Geri yükle",
                        use_container_width=True
                    ):
                        st.write("Bu yedek geri yüklensin mi?")
                        st.caption(
                            "Şu anki verilerin önce ayrı bir yedeğe "
                            "kaydedilir."
                        )

                        if st.button(
                            "Evet, geri yükle",
                            type="primary",
                            key=f"restore_local_{b['name']}"
                        ):

                            try:
                                safety = restore_from_bytes(
                                    b["path"].read_bytes()
                                )

                            except Exception as e:
                                st.error(f"❌ Geri yükleme başarısız: {e}")

                            else:
                                notify("Yedek geri yüklendi!", "♻️")
                                st.rerun()
# =================================================
    # SEKME 4: VERİLERİ SIFIRLA
    # =================================================

    with tab_reset:

        st.error(
            "⚠️ **Tehlikeli bölge.** Bu işlem uygulamadaki bütün kayıtları "
            "kalıcı olarak siler."
        )

        total_records = sum(current_counts.values())

        with st.container(border=True):

            st.subheader("Silinecek kayıtlar")

            reset_df = pd.DataFrame(
                [
                    {
                        "Kayıt türü": label,
                        "Adet": current_counts.get(table, 0)
                    }
                    for table, label in KNOWN_TABLES.items()
                ]
            )

            st.dataframe(
                reset_df,
                hide_index=True,
                use_container_width=True
            )

            st.caption(f"Toplam {total_records} kayıt.")

        with st.container(border=True):

            st.subheader("1) Önce kendi bilgisayarına yedekle (önerilir)")

            st.download_button(
                "⬇️ Yedeği İndir (.db)",
                data=create_backup_bytes(),
                file_name=(
                    f"home_manager_sifirlama_oncesi_{_dt.now():%Y-%m-%d_%H%M}.db"
                ),
                mime="application/octet-stream",
                use_container_width=True,
                key="reset_backup_download"
            )

            st.caption(
                "Sıfırlama sırasında ayrıca otomatik bir yerel yedek de "
                "alınır. Ama o yedek bu bilgisayardaki diskte durur; "
                "indirdiğin dosya ise sende kalır."
            )

        with st.container(border=True):

            st.subheader("2) Onayla")

            wipe_backups = st.checkbox(
                "Yerel yedekleri de sil (geri dönüş olmaz)",
                key="reset_wipe_backups",
                help=(
                    "İşaretlenirse sıfırlamadan önce güvenlik yedeği "
                    "ALINMAZ ve 'Yerel Yedekler' sekmesindeki tüm "
                    "yedekler silinir."
                )
            )

            if wipe_backups:
                st.warning(
                    "Yerel yedekler de silinecek ve güvenlik yedeği "
                    "alınmayacak. İndirdiğin dosya tek kurtuluş yolun olur."
                )

            confirm_text = st.text_input(
                "Onaylamak için SIFIRLA yazın",
                key="reset_confirm_text"
            )

            confirmed = confirm_text.strip().upper() == "SIFIRLA"

            if st.button(
                "🗑️ Tüm Verilerimi Sil ve Baştan Başla",
                type="primary",
                disabled=not confirmed,
                use_container_width=True,
                key="reset_all_btn"
            ):

                try:

                    if not wipe_backups:
                        create_backup_file("manuel")

                    reset_all_data()

                    if wipe_backups:
                        for old_backup in list_backups():
                            try:
                                old_backup["path"].unlink()
                            except OSError:
                                pass

                except Exception as e:

                    st.error(f"❌ Sıfırlama başarısız: {e}")

                else:

                    st.session_state.clear()
                    st.session_state["auth_ok"] = True
                    st.session_state["menu"] = "Yedekleme"
                    st.session_state["reset_done"] = True
                    st.rerun()  
# =====================================================
# KREDİ KARTLARI (hafif sürüm)
# Bu bloğu app.py içinde `elif menu == "🤖 AI Asistan":`
# satırının HEMEN ÜSTÜNE yapıştır (en solda başlamalı).
# =====================================================

elif menu == "Kredi Kartları":

    import calendar

    today = date.today()

    # -------------------------------------------------
    # YARDIMCI FONKSİYONLAR
    # -------------------------------------------------

    def safe_day(year, month, day):
        return date(year, month, min(day, calendar.monthrange(year, month)[1]))

    def next_due(due_day):
        """Bugünden itibaren gelen ilk son ödeme günü."""
        d = safe_day(today.year, today.month, due_day)
        if d >= today:
            return d
        y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        return safe_day(y, m, due_day)

    def statement_state(due_str, status):
        """paid / overdue / pending / missing"""
        if status is None:
            return "missing"
        if status == "Ödendi":
            return "paid"
        try:
            due = datetime.strptime(due_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return "pending"
        return "overdue" if due < today else "pending"

    def clear_keys(prefix):
        for k in list(st.session_state.keys()):
            if k.startswith(prefix):
                del st.session_state[k]
            

    def min_pay_rate(limit):
        return (
            MIN_PAY_RATE_HIGH if (limit or 0) > MIN_PAY_LIMIT
            else MIN_PAY_RATE_LOW
        )

    # -------------------------------------------------
    # BAŞLIK
    # -------------------------------------------------

    st.title("🏦 Kredi Kartları")
    st.caption(
        "Kartlarınızın ekstre ve son ödeme tarihlerini takip edin. "
        "Her ekstre Ödemeler listesine otomatik eklenir."
    )

    cards = get_credit_cards()

    # -------------------------------------------------
    # YENİ KART
    # -------------------------------------------------

    with st.expander("➕ Yeni Kart Ekle", expanded=not cards):

        with st.form("card_form", clear_on_submit=True):

            f1, f2 = st.columns(2)

            with f1:
                new_name = st.text_input(
                    "Kart adı", placeholder="Örn: Garanti Bonus"
                )
                new_last4 = st.text_input(
                    "Son 4 hane (opsiyonel)", max_chars=4, placeholder="1234"
                )
                new_limit = st.number_input(
                    "Kart limiti (₺)", min_value=0.0, step=1000.0
                )

            with f2:
                new_stmt_day = st.number_input(
                    "Hesap kesim günü",
                    min_value=1, max_value=31, value=1, step=1
                )
                new_due_day = st.number_input(
                    "Son ödeme günü",
                    min_value=1, max_value=31, value=10, step=1
                )

            if st.form_submit_button("💾 Kartı Kaydet", type="primary"):

                if not new_name.strip():
                    st.error("Lütfen kart adını girin.")
                else:
                    add_credit_card(
                        new_name.strip(),
                        new_last4.strip(),
                        new_limit,
                        int(new_stmt_day),
                        int(new_due_day)
                    )
                    notify("Kart eklendi!", "🏦")
                    st.rerun()

    if not cards:
        st.info("Henüz kayıtlı kart yok. Yukarıdan ilk kartınızı ekleyin.")
        st.stop()

    # -------------------------------------------------
    # TÜM KARTLAR İÇİN ÖZET
    # -------------------------------------------------

    all_unpaid = 0.0
    all_overdue = 0
    unpaid_by_card = {}
    unpaid_min_by_card = {}

    for c in cards:
        card_unpaid = 0.0
        card_min = 0.0
        rate = min_pay_rate(c[3])
        for (sid, period, pid, min_p, amount, due_str, status) in get_card_statements(c[0]):
            state = statement_state(due_str, status)
            if state in ("pending", "overdue"):
                card_unpaid += float(amount or 0)
                # Ekstredeki rakam girildiyse o, yoksa oran ile tahmin
                card_min += (
                    min_p if min_p > 0 else float(amount or 0) * rate
                )
            if state == "overdue":
                all_overdue += 1
        unpaid_by_card[c[0]] = card_unpaid
        unpaid_min_by_card[c[0]] = card_min
        all_unpaid += card_unpaid

    s1, s2, s3 = st.columns(3)

    with s1:
        with st.container(border=True):
            st.metric("Kart Sayısı", len(cards))

    with s2:
        with st.container(border=True):
            st.metric("Ödenmemiş Ekstre Toplamı", f"₺{all_unpaid:,.2f}")

    with s3:
        with st.container(border=True):
            st.metric("Geciken Ekstre", all_overdue)

    if all_overdue:
        st.error(f"🔴 {all_overdue} ekstre ödemeniz gecikmiş.")

    st.write("")

    # -------------------------------------------------
    # KART SEÇİMİ
    # -------------------------------------------------

    labels = {
        c[0]: f"{c[1]}" + (f" •••• {c[2]}" if c[2] else "")
        for c in cards
    }

    if len(cards) > 1:
        sel_id = st.selectbox(
            "Kart",
            list(labels.keys()),
            format_func=lambda x: labels[x],
            key="card_selected"
        )
    else:
        sel_id = cards[0][0]

    card = next(c for c in cards if c[0] == sel_id)
    c_id, c_name, c_last4, c_limit, c_stmt_day, c_due_day = card

    c_unpaid = unpaid_by_card.get(c_id, 0.0)
    c_unpaid_min = unpaid_min_by_card.get(c_id, 0.0)
    c_rate = min_pay_rate(c_limit)

    # -------------------------------------------------
    # KART BİLGİSİ
    # -------------------------------------------------

    with st.container(border=True):

        h1, h2, h3, h4, h5 = st.columns([2.6, 1.6, 1.8, 1.8, 1.8])

        with h1:
            st.markdown(f"### 🏦 {c_name}")
            st.caption(
                (f"•••• {c_last4} • " if c_last4 else "")
                + f"Kesim: her ayın {c_stmt_day or '-'}. günü • "
                f"Son ödeme: her ayın {c_due_day}. günü"
            )

        with h2:
            st.metric("Limit", f"₺{c_limit:,.0f}" if c_limit else "—")

        with h3:
            st.metric("Ödenmemiş Ekstre", f"₺{c_unpaid:,.2f}")

        with h4:
            st.metric(
                "Asgari Ödeme",
                f"₺{c_unpaid_min:,.2f}",
                help=(
                    "Ödenmemiş ekstrelerin asgari toplamı. Ekstreye banka "
                    "rakamını girdiyseniz o, girmediyseniz limitinize göre "
                    "hesaplanan tahmin kullanılır."
                )
            )

        with h5:
            st.metric(
                "Sıradaki Son Ödeme",
                next_due(c_due_day).strftime("%d.%m.%Y")
            )

        st.caption(
            f"Asgari ödeme oranı: **%{c_rate * 100:.0f}** "
            + (
                f"(limit ₺{MIN_PAY_LIMIT:,.0f} üzerinde)"
                if (c_limit or 0) > MIN_PAY_LIMIT
                else (
                    f"(limit ₺{MIN_PAY_LIMIT:,.0f} ve altında)"
                    if c_limit
                    else "(limit girilmediği için %20 varsayıldı)"
                )
            )
            + " • BDDK 1 Ekim 2026 kararı. Bankanızın ekstredeki rakamı esastır."
        )

        if c_limit and c_limit > 0:
            usage = min(c_unpaid / c_limit, 1.0)
            st.progress(
                usage,
                text=f"Ekstre borcu limitin %{usage * 100:.0f}'i "
                     f"(güncel dönem harcamaları dahil değil)"
            )
    # -------------------------------------------------
    # DÜZENLE / SİL
    # -------------------------------------------------

    ec1, ec2 = st.columns([4, 1])

    with ec1:

        with st.expander("✏️ Kart Bilgilerini Düzenle"):

            ek = f"card_edit_{c_id}"

            e1, e2 = st.columns(2)

            with e1:
                ed_name = st.text_input("Kart adı", value=c_name, key=f"{ek}_name")
                ed_last4 = st.text_input(
                    "Son 4 hane", value=c_last4, max_chars=4, key=f"{ek}_last4"
                )
                ed_limit = st.number_input(
                    "Kart limiti (₺)",
                    min_value=0.0,
                    value=float(c_limit or 0),
                    step=1000.0,
                    key=f"{ek}_limit"
                )

            with e2:
                ed_stmt = st.number_input(
                    "Hesap kesim günü",
                    min_value=1, max_value=31,
                    value=int(c_stmt_day or 1), step=1,
                    key=f"{ek}_stmt"
                )
                ed_due = st.number_input(
                    "Son ödeme günü",
                    min_value=1, max_value=31,
                    value=int(c_due_day), step=1,
                    key=f"{ek}_due"
                )

            if st.button(
                "💾 Değişiklikleri Kaydet",
                key=f"{ek}_save",
                type="primary"
            ):
                if not ed_name.strip():
                    st.error("Kart adı boş olamaz.")
                else:
                    update_credit_card(
                        c_id,
                        ed_name.strip(),
                        ed_last4.strip(),
                        ed_limit,
                        int(ed_stmt),
                        int(ed_due)
                    )
                    notify("Kart güncellendi!", "✏️")
                    st.rerun()

    with ec2:

        with st.popover("🗑️ Kartı Sil", use_container_width=True):

            st.write(f"**{c_name}** silinsin mi?")
            st.caption(
                "Kartın ekstre kayıtları ve ödenmemiş ekstre ödemeleri "
                "silinir. Ödenmiş ekstreler Ödemeler geçmişinde kalır."
            )

            if st.button(
                "Evet, sil",
                key=f"card_delete_{c_id}",
                type="primary"
            ):
                delete_credit_card(c_id)
                st.session_state.pop("card_selected", None)
                notify("Kart silindi!", "🗑️")
                st.rerun()

    st.write("")

    tab_add, tab_list, tab_inst = st.tabs(
        ["➕ Ekstre Ekle", "📜 Ekstreler", "🧾 Kart Taksitleri"]
    )

    # =================================================
    # SEKME 1: EKSTRE EKLE
    # =================================================

    with tab_add:

        xk = f"stmt_{c_id}"

        x1, x2 = st.columns(2)

        with x1:
            x_amount = st.number_input(
                "Ekstre tutarı (₺)",
                min_value=0.0,
                step=100.0,
                key=f"{xk}_amount"
            )
            x_min = st.number_input(
                "Asgari ödeme (₺) — ekstredeki rakam, boşsa tahmin edilir",
                min_value=0.0,
                step=50.0,
                key=f"{xk}_min"
            )

            if x_amount > 0:
                st.caption(
                    f"Tahmini asgari ödeme: "
                    f"₺{x_amount * min_pay_rate(c_limit):,.2f} "
                    f"(%{min_pay_rate(c_limit) * 100:.0f})"
                )

        with x2:
            x_due = st.date_input(
                "Son ödeme tarihi",
                value=next_due(c_due_day),
                key=f"{xk}_due"
            )
            st.caption(
                "Aynı kart için her ay yalnızca bir ekstre eklenebilir."
            )

        month_inst = get_card_installments_for_month(
            c_id, x_due.year, x_due.month
        )

        if month_inst:

            inst_sum = sum(m[1] for m in month_inst)

            st.info(
                f"🧾 Bu ekstreye yansıyan kart taksitleri: "
                f"**₺{inst_sum:,.2f}**\n\n"
                + "\n".join(
                    f"- {pn}: ₺{pa:,.2f} ({pk}/{pc})"
                    for (pn, pa, pk, pc) in month_inst
                )
                + "\n\nBankanın ekstre tutarı bunları zaten içerir; "
                "ayrıca eklemeyin."
            )
        if st.button(
            "💾 Ekstreyi Kaydet",
            type="primary",
            use_container_width=True,
            key=f"{xk}_save"
        ):

            if x_amount <= 0:
                st.error("Tutar 0'dan büyük olmalı.")

            elif x_min > x_amount:
                st.error("Asgari ödeme ekstre tutarından büyük olamaz.")

            else:

                result = add_card_statement(
                    c_id, c_name, x_amount, str(x_due), x_min
                )

                if result is None:
                    st.error(
                        f"{x_due.strftime('%m.%Y')} dönemi için bu kartta "
                        f"zaten bir ekstre var."
                    )
                else:
                    notify("Ekstre eklendi, Ödemeler listesine düştü!", "🏦")
                    clear_keys(f"{xk}_")
                    st.rerun()

    # =================================================
    # SEKME 2: EKSTRELER
    # =================================================

    with tab_list:

        statements = get_card_statements(c_id)

        if not statements:

            st.info("Bu kart için henüz ekstre yok.")

        for (sid, period, pid, min_p, amount, due_str, status) in statements:

            state = statement_state(due_str, status)

            with st.container(border=True):

                a, b, c, d = st.columns([2.5, 1.8, 2, 1.7])

                with a:
                    st.markdown(f"**{period} Ekstresi**")
                    if state == "missing":
                        st.caption("Ödeme kaydı Ödemeler'den silinmiş")
                    else:
                        st.caption(f"Son ödeme: {due_str}")

                with b:
                    if state == "missing":
                        st.write("—")
                    else:
                        st.markdown(f"**₺{float(amount):,.2f}**")
                        if min_p > 0:
                            st.caption(f"Asgari: ₺{min_p:,.2f}")
                        else:
                            st.caption(
                                f"Asgari (tahmini): "
                                f"₺{float(amount) * min_pay_rate(c_limit):,.2f}"
                            )

                with c:
                    if state == "paid":
                        st.write("🟢 Ödendi")
                    elif state == "overdue":
                        days = (today - datetime.strptime(due_str, "%Y-%m-%d").date()).days
                        st.write(f"🔴 {days} gün gecikti")
                    elif state == "pending":
                        days = (datetime.strptime(due_str, "%Y-%m-%d").date() - today).days
                        st.write("🟠 Bugün son gün" if days == 0 else f"🟡 {days} gün kaldı")
                    else:
                        st.write("⚪ —")

                with d:
                    if state in ("pending", "overdue"):
                        if st.button(
                            "✅ Ödendi",
                            key=f"stmt_paid_{sid}",
                            type="primary",
                            use_container_width=True
                        ):
                            mark_payment_paid(int(pid))
                            notify("Ekstre ödendi olarak işaretlendi!", "✅")
                            st.rerun()
                    elif state == "paid":
                        if st.button(
                            "↩️ Beklet",
                            key=f"stmt_pending_{sid}",
                            use_container_width=True
                        ):
                            mark_payment_pending(int(pid))
                            notify("Ekstre tekrar beklemeye alındı!", "↩️")
                            st.rerun()

                    with st.popover("🗑️", use_container_width=True):
                        st.write("Bu ekstre silinsin mi?")
                        st.caption("Ödemeler listesindeki kaydı da silinir.")
                        if st.button(
                            "Evet, sil",
                            key=f"stmt_del_{sid}",
                            type="primary"
                        ):
                            delete_card_statement(sid)
                            notify("Ekstre silindi!", "🗑️")
                            st.rerun()

        # =================================================
    # SEKME 3: KART TAKSİTLERİ
    # =================================================

    with tab_inst:

        ik = f"cinst_{c_id}"

        card_inst = get_card_installments(c_id)

        this_month_inst = get_card_installments_for_month(
            c_id, today.year, today.month
        )

        future_total = sum(
            (i[5] - i[8]) * float(i[6]) for i in card_inst
        )

        m1, m2, m3 = st.columns(3)

        with m1:
            with st.container(border=True):
                st.metric("Taksit Kaydı", len(card_inst))

        with m2:
            with st.container(border=True):
                st.metric(
                    "Bu Ay Ekstreye Yansıyan",
                    f"₺{sum(m[1] for m in this_month_inst):,.2f}"
                )

        with m3:
            with st.container(border=True):
                st.metric(
                    "Gelecek Aylarda Kalan",
                    f"₺{future_total:,.2f}",
                    help="Bu ay dahil yansıyanlar düşüldükten sonra kalan."
                )

        st.write("")

        if not card_inst:
            st.info(
                "Bu kartta kartla alınmış taksit yok. Ev Eşyalarım'da "
                "'Ödeme şekli' olarak bu kartı seçebilir ya da aşağıdan "
                "ekleyebilirsiniz."
            )

        for (
                iid, aid, cid, pname, total, count, monthly_amt, first, billed
            ) in card_inst:

            left = count - billed

            with st.container(border=True):

                a1, a2, a3, a4 = st.columns([3, 2, 2, 1])

                with a1:
                    st.markdown(f"**{pname}**")
                    st.caption(
                        f"İlk ekstre: {str(first)[:7]} • "
                        f"Toplam ₺{float(total):,.2f}"
                    )

                with a2:
                    st.markdown(f"**₺{float(monthly_amt):,.2f}** / ay")
                    st.caption(f"{billed}/{count} ekstreye yansıdı")

                with a3:
                    if left > 0:
                        st.write(f"Kalan: ₺{left * float(monthly_amt):,.2f}")
                        st.caption(f"{left} taksit")
                    else:
                        st.write("🟢 Tamamlandı")

                with a4:
                    with st.popover("🗑️"):
                        st.write("Bu taksit kaydı silinsin mi?")
                        st.caption(
                            "Sadece taksit takibi silinir. Girdiğiniz "
                            "ekstreler ve ödemeler değişmez."
                        )
                        if st.button(
                            "Evet, sil",
                            key=f"cinst_del_{iid}",
                            type="primary"
                        ):
                            delete_installment(iid)
                            notify("Taksit kaydı silindi!", "🗑️")
                            st.rerun()

                st.progress(min(billed / count, 1.0) if count else 0)

    with st.expander("➕ Ev eşyası dışı kart taksiti ekle (telefon, tatil...)"):

            n1, n2 = st.columns(2)

            with n1:
                ni_name = st.text_input(
                    "Ürün / harcama adı",
                    placeholder="Örn: Telefon",
                    key=f"{ik}_name"
                )
                ni_total = st.number_input(
                    "Toplam tutar (₺)",
                    min_value=0.0,
                    step=100.0,
                    key=f"{ik}_total"
                )

            with n2:
                ni_count = int(
                    st.number_input(
                        "Taksit sayısı",
                        min_value=2,
                        max_value=60,
                        value=6,
                        step=1,
                        key=f"{ik}_count"
                    )
                )
                ni_first = st.date_input(
                    "İlk taksitin yansıyacağı ekstrenin son ödeme tarihi",
                    value=next_due(c_due_day),
                    key=f"{ik}_first"
                )

            if ni_total > 0:
                st.caption(
                    f"Aylık taksit: ₺{ni_total / ni_count:,.2f}"
                )

            if st.button(
                "💾 Taksiti Kaydet",
                type="primary",
                use_container_width=True,
                key=f"{ik}_save"
            ):

                if not ni_name.strip():
                    st.error("Lütfen ürün adını girin.")

                elif ni_total <= 0:
                    st.error("Toplam tutar 0'dan büyük olmalı.")

                else:
                    add_card_installment(
                        0,
                        c_id,
                        ni_name.strip(),
                        ni_total,
                        ni_count,
                        ni_total / ni_count,
                        str(ni_first)
                    )
                    notify("Kart taksiti eklendi!", "🧾")
                    clear_keys(f"{ik}_")
                    st.rerun()
                          
elif menu == "🤖 AI Asistan":

    from ai_assistant import ask_assistant

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # -------------------------------------------------
    # BAŞLIK
    # -------------------------------------------------

    h1, h2 = st.columns([4, 1])

    with h1:
        st.title("🤖 AI Ev Asistanı")
        st.caption(
            "Ödemeleriniz, taksitleriniz ve ev eşyalarınız hakkında "
            "soru sorun. Asistan güncel kayıtlarınıza göre cevap verir."
        )

    with h2:
        st.write("")
        st.write("")
        if st.session_state.chat_messages:
            if st.button("🧹 Sohbeti Temizle", use_container_width=True):
                st.session_state.chat_messages = []
                st.rerun()

    # Önerilen soruya tıklanınca gelen soru
    pending_question = st.session_state.pop("pending_question", None)

    # -------------------------------------------------
    # ÖNERİLEN SORULAR (sohbet boşken)
    # -------------------------------------------------

    if not st.session_state.chat_messages and not pending_question:

        st.markdown("##### 💡 Şunları sorabilirsiniz")

        suggestions = [
            "Bu ay ev giderim ne kadar?",
            "Gecikmiş ödemelerim var mı?",
            "Önümüzdeki 7 günde hangi ödemelerim var?",
            "Geçen aya göre giderlerim arttı mı?",
            "Garantisi yakında bitecek eşyalarım hangileri?",
            "Bu yıl arabaya ne kadar harcadım?",
            "Gelirim giderlerimi karşılıyor mu?",
            "Toplam kalan taksit borcum ne kadar?",
            "Bu ay en çok hangi kategoriye harcadım?"
        ]

        cols = st.columns(2)

        for idx, text in enumerate(suggestions):
            with cols[idx % 2]:
                if st.button(
                    text,
                    key=f"suggestion_{idx}",
                    use_container_width=True
                ):
                    st.session_state["pending_question"] = text
                    st.rerun()

    # -------------------------------------------------
    # GEÇMİŞ MESAJLAR
    # -------------------------------------------------

    for msg in st.session_state.chat_messages:
        with st.chat_message(
            msg["role"],
            avatar="🧑" if msg["role"] == "user" else "🤖"
        ):
            st.markdown(msg["content"])

    # -------------------------------------------------
    # YENİ SORU
    # -------------------------------------------------

    prompt = st.chat_input("Sorunuzu yazın...") or pending_question

    if prompt:

        history = list(st.session_state.chat_messages)

        st.session_state.chat_messages.append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user", avatar="🧑"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🤖"):

            with st.spinner("Düşünüyorum..."):

                try:

                    answer = ask_assistant(
                        question=prompt,
                        history=history,
                        payments=get_payments(),
                        assets=get_assets()
                    )

                except Exception as e:

                    answer = (
                        f"❌ Şu an cevap veremiyorum: {e}"
                    )

            st.markdown(answer)

        st.session_state.chat_messages.append(
            {"role": "assistant", "content": answer}
        )