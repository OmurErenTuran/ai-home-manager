"""
ai_assistant.py

AI Home Manager için Gemini tabanlı ev asistanı.
app.py ile aynı klasöre koy (database.py ve ai_invoice.py'nin yanına).

Kurulum (ai_invoice.py için zaten kurduysan gerek yok):
    pip install google-genai python-dotenv

API anahtarı: GEMINI_API_KEY ortam değişkeni (veya .env dosyası).
"""

import os
import time
from datetime import date, datetime, timedelta

from google import genai
from google.genai import types

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ai_invoice.py'de farklı bir model kullanıyorsan aynısını yaz.
MODEL_NAME = "gemini-3.8-flash"
# Ana model yoğunsa (503) denenecek yedek model
FALLBACK_MODEL = "gemini-3.7-flash"

SYSTEM_PROMPT = """Sen "AI Home Manager" uygulamasının ev asistanısın.
Kullanıcının ev ödemeleri, gelirleri, taksitleri, sabit ödemeleri, ev eşyaları,
bakım kayıtları ve araçları (belgeler, masraflar, yakıt tüketimi) hakkındaki
soruları cevaplıyorsun.

Kurallar:
- Yalnızca aşağıda verilen verilere dayan. Veride olmayan bir şeyi uydurma;
  bilmiyorsan "Kayıtlarında bu bilgi yok" de.
- Toplam, fark ve oran hesaplarını dikkatle yap. Gerekirse adım adım topla.
- Para tutarlarını ₺ ile ve binlik ayraçlı yaz (örn. ₺1.250,00).
- Kısa, net ve samimi cevap ver. Gereksiz uzatma.
- Liste gerektiğinde madde işareti kullan.
- Hukuki veya finansal tavsiye verme; sadece kayıtları özetle ve yorumla.
- Cevabı her zaman Türkçe yaz.
"""


def _get_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Gemini API anahtarı bulunamadı. GEMINI_API_KEY ortam "
            "değişkenini veya .env dosyasını kontrol edin."
        )

    return genai.Client(api_key=api_key)


def _parse(value):
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def build_context(payments, assets):
    """Veritabanındaki verileri modele verilecek metne çevirir."""

    today = date.today()
    lines = [f"BUGÜNÜN TARİHİ: {today.isoformat()}", ""]

    # -------------------------------------------------
    # ÖDEMELER
    # -------------------------------------------------

    items = []

    for (pid, name, amount, due_str, category, status) in payments:

        due = _parse(due_str)

        if due is None:
            continue

        if status == "Ödendi":
            state = "ÖDENDİ"
        elif due < today:
            state = f"GECİKTİ ({(today - due).days} gün)"
        else:
            state = f"BEKLİYOR ({(due - today).days} gün kaldı)"

        items.append((due, name, amount, category, state, status))

    items.sort(key=lambda x: x[0])

    # Aylık toplamlar
    monthly = {}

    for due, name, amount, category, state, status in items:
        key = due.strftime("%Y-%m")
        m = monthly.setdefault(key, {"total": 0.0, "paid": 0.0})
        m["total"] += amount
        if status == "Ödendi":
            m["paid"] += amount

    lines.append("AYLIK ÖZET (toplam / ödenen / bekleyen):")

    if monthly:
        for key in sorted(monthly):
            m = monthly[key]
            lines.append(
                f"- {key}: toplam ₺{m['total']:,.2f} / "
                f"ödenen ₺{m['paid']:,.2f} / "
                f"bekleyen ₺{m['total'] - m['paid']:,.2f}"
            )
    else:
        lines.append("- Kayıtlı ödeme yok.")

    # Bu ayın kategori dağılımı
    this_month = today.strftime("%Y-%m")
    cats = {}

    for due, name, amount, category, state, status in items:
        if due.strftime("%Y-%m") == this_month:
            cats[category] = cats.get(category, 0.0) + amount

    lines.append("")
    lines.append(f"BU AYIN ({this_month}) KATEGORİ DAĞILIMI:")

    if cats:
        for cat, total in sorted(cats.items(), key=lambda x: -x[1]):
            lines.append(f"- {cat}: ₺{total:,.2f}")
    else:
        lines.append("- Bu ay için ödeme yok.")

    # Ödeme listesi (bugünden ±12 ay)
    lo = today - timedelta(days=365)
    hi = today + timedelta(days=365)

    lines.append("")
    lines.append("ÖDEME LİSTESİ (tarih | ad | tutar | kategori | durum):")

    listed = [i for i in items if lo <= i[0] <= hi]

    if listed:
        for due, name, amount, category, state, status in listed[:250]:
            lines.append(
                f"- {due.isoformat()} | {name} | "
                f"₺{amount:,.2f} | {category} | {state}"
            )
    else:
        lines.append("- Yok.")

    # -------------------------------------------------
    # EV EŞYALARI
    # -------------------------------------------------

    lines.append("")
    lines.append(
        "EV EŞYALARI (ad | marka | model | satın alma | fiyat | "
        "garanti | bakım):"
    )

    if not assets:
        lines.append("- Kayıtlı eşya yok.")

    for (
        aid, name, brand, model, pdate,
        price, warranty_end, maint, notes
    ) in assets:

        w = _parse(warranty_end)
        m = _parse(maint)

        if w is None:
            w_text = "belirtilmemiş"
        elif (w - today).days < 0:
            w_text = f"{warranty_end} (süresi dolmuş)"
        else:
            w_text = f"{warranty_end} ({(w - today).days} gün kaldı)"

        if m is None:
            m_text = "belirlenmemiş"
        elif (m - today).days < 0:
            m_text = f"{maint} ({abs((m - today).days)} gün gecikmiş)"
        else:
            m_text = f"{maint} ({(m - today).days} gün kaldı)"

        lines.append(
            f"- {name} | {brand or '-'} | {model or '-'} | "
            f"{pdate or '-'} | ₺{(price or 0):,.2f} | "
            f"garanti: {w_text} | bakım: {m_text}"
        )

    return "\n".join(lines)


def build_extra_context(assets):
    """Bakım geçmişi, bakım aralıkları ve araç verilerini metne çevirir."""

    # database'i burada içe aktarıyoruz; modül yüklenirken döngü olmasın.
    from database import (
        get_maintenance_records,
        get_asset_intervals,
        get_vehicles,
        get_vehicle_expenses,
    )

    today = date.today()
    lines = []

    # -------------------------------------------------
    # BAKIM GEÇMİŞİ VE ARALIKLAR
    # -------------------------------------------------

    try:
        records = get_maintenance_records()    # yeniden eskiye
        intervals = get_asset_intervals()
    except Exception:
        records, intervals = [], {}

    lines.append("")
    lines.append("BAKIM ARALIKLARI (eşya | tekrar | sonraki bakım):")

    any_interval = False

    for a in assets:
        a_id, a_name, maint = a[0], a[1], a[7]
        months = intervals.get(a_id, 0)

        if not maint and not months:
            continue

        any_interval = True
        repeat = f"{months} ayda bir" if months else "tekrarlanmıyor"
        lines.append(f"- {a_name} | {repeat} | sonraki: {maint or 'belirlenmemiş'}")

    if not any_interval:
        lines.append("- Bakım planı olan eşya yok.")

    lines.append("")
    lines.append("BAKIM GEÇMİŞİ (eşya | tarih | maliyet | not), en yeni önce:")

    if records:
        for (rid, aid, name, rdate, cost, notes) in records[:100]:
            lines.append(
                f"- {name} | {rdate} | ₺{cost:,.2f} | {notes or '-'}"
            )
        lines.append(
            f"Toplam bakım maliyeti: ₺{sum(r[4] for r in records):,.2f}"
        )
    else:
        lines.append("- Bakım kaydı yok.")

    # -------------------------------------------------
    # ARAÇLAR
    # -------------------------------------------------

    try:
        vehicles = get_vehicles()
    except Exception:
        vehicles = []

    lines.append("")
    lines.append("ARAÇLAR:")

    if not vehicles:
        lines.append("- Kayıtlı araç yok.")

    for v in vehicles:

        (
            v_id, plate, brand, model, year, fuel, km,
            inspection, traffic, kasko, notes
        ) = v

        lines.append(
            f"- {plate} | {brand} {model or ''} | {year or '-'} | "
            f"yakıt: {fuel or '-'} | km: {(km or 0):,}"
        )

        for label, value in (
            ("Muayene bitiş", inspection),
            ("Trafik sigortası bitiş", traffic),
            ("Kasko bitiş", kasko),
        ):
            d = _parse(value)

            if d is None:
                lines.append(f"    {label}: girilmemiş")
            elif (d - today).days < 0:
                lines.append(
                    f"    {label}: {value} (süresi {abs((d - today).days)} gün önce doldu)"
                )
            else:
                lines.append(
                    f"    {label}: {value} ({(d - today).days} gün kaldı)"
                )

        try:
            exps = get_vehicle_expenses(v_id)   # yeniden eskiye
        except Exception:
            exps = []

        if not exps:
            lines.append("    Masraf kaydı yok.")
            continue

        this_year = [e for e in exps if str(e[2]).startswith(str(today.year))]
        this_month = [
            e for e in exps
            if str(e[2]).startswith(today.strftime("%Y-%m"))
        ]

        lines.append(
            f"    Masraf toplamı: bu ay ₺{sum(e[4] for e in this_month):,.2f}, "
            f"{today.year} yılı ₺{sum(e[4] for e in this_year):,.2f}, "
            f"tüm zamanlar ₺{sum(e[4] for e in exps):,.2f}"
        )

        by_type = {}
        for e in this_year:
            by_type[e[3]] = by_type.get(e[3], 0.0) + e[4]

        if by_type:
            parts = ", ".join(
                f"{t}: ₺{a:,.2f}"
                for t, a in sorted(by_type.items(), key=lambda x: -x[1])
            )
            lines.append(f"    {today.year} türe göre: {parts}")

        # Ortalama yakıt tüketimi (ardışık dolumlar, depo full varsayımı)
        fills = sorted(
            [e for e in exps if e[3] == "Yakıt" and e[5] and e[6]],
            key=lambda e: e[5]
        )

        if len(fills) >= 2 and fills[-1][5] > fills[0][5]:
            distance = fills[-1][5] - fills[0][5]
            liters = sum(e[6] for e in fills[1:])
            unit = "kWh" if fuel == "Elektrik" else "L"
            lines.append(
                f"    Ortalama tüketim: {liters / distance * 100:.1f} {unit}/100 km"
            )

        lines.append("    Son masraflar (tarih | tür | tutar | km | miktar | not):")

        for e in exps[:40]:
            lines.append(
                f"      {e[2]} | {e[3]} | ₺{e[4]:,.2f} | "
                f"{e[5] or '-'} | {e[6] or '-'} | {e[7] or '-'}"
            )

    return "\n".join(lines)

def build_finance_context():
    """Gelirleri, aylık net durumu, taksitleri ve tekrarlayan
    kayıtları metne çevirir."""

    from database import (
        get_incomes,
        get_payments,
        get_installments,
        get_recurring_payments,
        get_recurring_incomes,
        get_card_installments,
        get_card_installment_ids,
        get_credit_cards,
    )

    today = date.today()
    lines = []

    try:
        incomes = get_incomes()
        payments = get_payments()
    except Exception:
        incomes, payments = [], []

    # -------------------------------------------------
    # GELİRLER VE AYLIK NET DURUM
    # -------------------------------------------------

    inc_monthly = {}

    for (iid, name, amount, idate, cat) in incomes:
        d = _parse(idate)
        if d is None:
            continue
        key = d.strftime("%Y-%m")
        inc_monthly[key] = inc_monthly.get(key, 0.0) + float(amount)

    exp_monthly = {}

    for (pid, name, amount, due, cat, status) in payments:
        d = _parse(due)
        if d is None:
            continue
        key = d.strftime("%Y-%m")
        exp_monthly[key] = exp_monthly.get(key, 0.0) + float(amount)

    lines.append("")
    lines.append(
        "AYLIK GELİR - GİDER (sadece geliri girilmiş aylar; "
        "ay | gelir | planlanan gider | net):"
    )

    if inc_monthly:
        for key in sorted(inc_monthly)[-18:]:
            inc = inc_monthly[key]
            exp = exp_monthly.get(key, 0.0)
            lines.append(
                f"- {key}: gelir ₺{inc:,.2f} | gider ₺{exp:,.2f} | "
                f"net ₺{inc - exp:,.2f}"
            )
    else:
        lines.append("- Kayıtlı gelir yok.")

    lines.append("")
    lines.append("GELİR KAYITLARI (tarih | ad | tutar | kategori), en yeni önce:")

    if incomes:
        for (iid, name, amount, idate, cat) in incomes[:40]:
            lines.append(f"- {idate} | {name} | ₺{float(amount):,.2f} | {cat}")
    else:
        lines.append("- Yok.")

    # -------------------------------------------------
    # TAKSİTLER
    # (kalan taksit sayısı, ödeme kayıtlarından hesaplanır)
    # -------------------------------------------------

    try:
        installments = get_installments()
        card_ids = get_card_installment_ids()
        card_inst = get_card_installments()
        card_names = {c[0]: c[1] for c in get_credit_cards()}
    except Exception:
        installments, card_ids, card_inst, card_names = [], set(), [], {}

    normal_inst = [i for i in installments if i[0] not in card_ids]

    lines.append("")
    lines.append(
        "TAKSİTLER (kartsız; ürün | toplam | aylık | ödenen/toplam taksit | "
        "kalan borç | sıradaki taksit):"
    )

    if not normal_inst:
        lines.append("- Kartsız taksitli ödeme yok.")

    total_remaining = 0.0

    for (
        iid, asset_id, pname, total, count, monthly_amt, first_date, cur
    ) in normal_inst:

        prefix = f"{pname} Taksit "

        related = [
            p for p in payments
            if str(p[1]).startswith(prefix) and p[4] == "Taksit"
        ]
        paid = [p for p in related if p[5] == "Ödendi"]
        remaining = [p for p in related if p[5] != "Ödendi"]

        remaining_amount = sum(float(p[2]) for p in remaining)
        total_remaining += remaining_amount

        due_dates = [
            d for d in (_parse(p[3]) for p in remaining) if d is not None
        ]
        next_due = min(due_dates).isoformat() if due_dates else "yok"

        lines.append(
            f"- {pname} | ₺{float(total):,.2f} | ₺{float(monthly_amt):,.2f} | "
            f"{len(paid)}/{count} ödendi | kalan ₺{remaining_amount:,.2f} | "
            f"sıradaki: {next_due}"
        )

    lines.append("")
    lines.append(
        "KARTLA TAKSİTLER (ürün | kart | aylık | ekstreye yansıyan/toplam | "
        "gelecek aylarda kalan). Bu taksitlerin aylık tutarı kartın ekstre "
        "ödemesinin İÇİNDEDİR, ayrı ödeme kaydı yoktur; gider hesabında "
        "ikinci kez sayma:"
    )

    if not card_inst:
        lines.append("- Yok.")

    for (
        iid, aid, cid, pname, total, count, monthly_amt, first, billed
    ) in card_inst:

        remaining_amount = (count - billed) * float(monthly_amt)
        total_remaining += remaining_amount

        lines.append(
            f"- {pname} | {card_names.get(cid, 'kart')} | "
            f"₺{float(monthly_amt):,.2f} | {billed}/{count} yansıdı | "
            f"kalan ₺{remaining_amount:,.2f}"
        )

    if normal_inst or card_inst:
        lines.append(f"Toplam kalan taksit borcu: ₺{total_remaining:,.2f}")
    # -------------------------------------------------
    # SABİT ÖDEMELER
    # -------------------------------------------------

    try:
        rec_payments = get_recurring_payments()
        rec_incomes = get_recurring_incomes()
    except Exception:
        rec_payments, rec_incomes = [], []

    lines.append("")
    lines.append("SABİT AYLIK ÖDEMELER (ad | tutar | ayın günü | kategori | durum):")

    if rec_payments:
        for (rid, name, amount, day, cat, active) in rec_payments:
            lines.append(
                f"- {name} | ₺{float(amount):,.2f} | {day}. gün | {cat} | "
                f"{'aktif' if active else 'durdurulmuş'}"
            )
        lines.append(
            "Aktif sabit ödemeler toplamı: ₺"
            f"{sum(float(r[2]) for r in rec_payments if r[5] == 1):,.2f}"
        )
    else:
        lines.append("- Yok.")

    lines.append("")
    lines.append("TEKRARLAYAN GELİRLER (ad | tür | ayın günü | durum):")

    if rec_incomes:
        for (rid, name, amount, day, cat, kind, active, last) in rec_incomes:
            kind_text = (
                f"sabit ₺{float(amount or 0):,.2f}"
                if kind == "fixed"
                else "değişken (her ay tutar elle girilir)"
            )
            lines.append(
                f"- {name} | {kind_text} | {day}. gün | "
                f"{'aktif' if active else 'durdurulmuş'}"
            )
    else:
        lines.append("- Yok.")

    return "\n".join(lines)

def ask_assistant(question, history, payments, assets):
    """
    question : kullanıcının yeni sorusu
    history  : önceki mesajlar [{"role": "user"|"assistant", "content": str}]
               (yeni soru dahil DEĞİL)
    payments : get_payments() çıktısı
    assets   : get_assets() çıktısı
    """

    client = _get_client()

    system_instruction = (
        SYSTEM_PROMPT + "\n\nKULLANICININ GÜNCEL VERİLERİ:\n"
        + build_context(payments, assets)
        + "\n" + build_extra_context(assets)
        + "\n" + build_finance_context()
    )

    contents = []

    for msg in history[-10:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            )
        )

    contents.append(
        types.Content(role="user", parts=[types.Part(text=question)])
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction
    )

    def is_temporary(error):
        text = str(error)
        return any(
            code in text
            for code in ("503", "UNAVAILABLE", "500", "429")
        )

    last_error = None

    # (model, deneme sayısı): önce ana model, olmazsa yedek model
    for model_name, max_tries in ((MODEL_NAME, 4), (FALLBACK_MODEL, 2)):

        for attempt in range(max_tries):

            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
                return response.text or (
                    "Cevap oluşturulamadı, lütfen tekrar deneyin."
                )

            except Exception as e:
                last_error = e

                if not is_temporary(e):
                    # Yedek modelde 404 gibi hatalar sessizce geçilir
                    if model_name == FALLBACK_MODEL:
                        break
                    raise

                if attempt < max_tries - 1:
                    time.sleep(2 ** attempt)

    raise RuntimeError(
        "Gemini şu an çok yoğun, birkaç dakika sonra tekrar deneyin. "
        f"(Son hata: {last_error})"
    )