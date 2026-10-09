import sqlite3
import calendar
from pathlib import Path
from datetime import date

DB_PATH = Path("home_manager.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


# =====================================================
# PAYMENTS
# =====================================================

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT DEFAULT 'Bekliyor'
        )
    """)

    conn.commit()
    conn.close()


def add_payment(name, amount, due_date, category):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO payments
        (name, amount, due_date, category, status)
        VALUES (?, ?, ?, ?, 'Bekliyor')
    """, (
        name,
        amount,
        due_date,
        category
    ))

    conn.commit()
    conn.close()


def get_payments():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            amount,
            due_date,
            category,
            status
        FROM payments
        ORDER BY due_date ASC
    """)

    payments = cursor.fetchall()

    conn.close()

    return payments


def delete_payment(payment_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM payments WHERE id = ?",
        (payment_id,)
    )

    conn.commit()
    conn.close()


def update_payment(
    payment_id,
    name,
    amount,
    due_date,
    category
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE payments
        SET name = ?,
            amount = ?,
            due_date = ?,
            category = ?
        WHERE id = ?
    """, (
        name,
        amount,
        due_date,
        category,
        payment_id
    ))

    conn.commit()
    conn.close()


def mark_payment_paid(payment_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE payments
        SET status = 'Ödendi'
        WHERE id = ?
    """, (payment_id,))

    conn.commit()
    conn.close()


def mark_payment_pending(payment_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE payments
        SET status = 'Bekliyor'
        WHERE id = ?
    """, (payment_id,))

    conn.commit()
    conn.close()


# =====================================================
# ASSETS / EV EŞYALARI
# =====================================================

def create_assets_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            model TEXT,
            purchase_date TEXT,
            purchase_price REAL DEFAULT 0,
            warranty_end TEXT,
            maintenance_date TEXT,
            notes TEXT
        )
    """)

    conn.commit()
    conn.close()


def add_asset(
    name,
    brand,
    model,
    purchase_date,
    purchase_price,
    warranty_end,
    maintenance_date,
    notes
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO assets (
            name,
            brand,
            model,
            purchase_date,
            purchase_price,
            warranty_end,
            maintenance_date,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        brand,
        model,
        purchase_date,
        purchase_price,
        warranty_end,
        maintenance_date,
        notes
    ))

    asset_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return asset_id

def get_assets():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            brand,
            model,
            purchase_date,
            purchase_price,
            warranty_end,
            maintenance_date,
            notes
        FROM assets
        ORDER BY warranty_end ASC
    """)

    assets = cursor.fetchall()

    conn.close()

    return assets


def delete_asset(asset_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM maintenance_records WHERE asset_id = ?",
        (asset_id,)
    )

    cursor.execute(
        "DELETE FROM assets WHERE id = ?",
        (asset_id,)
    )
    

    conn.commit()
    conn.close()
# =====================================================
# TEKRARLAYAN ÖDEMELER
# =====================================================

def create_recurring_payments_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recurring_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            due_day INTEGER NOT NULL,
            category TEXT NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()


def add_recurring_payment(
    name,
    amount,
    due_day,
    category
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO recurring_payments
        (name, amount, due_day, category, active)
        VALUES (?, ?, ?, ?, 1)
    """, (
        name,
        amount,
        due_day,
        category
    ))

    conn.commit()
    conn.close()


def get_recurring_payments():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            amount,
            due_day,
            category,
            active
        FROM recurring_payments
        ORDER BY due_day ASC
    """)

    payments = cursor.fetchall()

    conn.close()

    return payments


def delete_recurring_payment(recurring_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM recurring_payments
        WHERE id = ?
    """, (recurring_id,))

    conn.commit()
    conn.close()


def toggle_recurring_payment(
    recurring_id,
    active
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE recurring_payments
        SET active = ?
        WHERE id = ?
    """, (
        active,
        recurring_id
    ))

    conn.commit()
    conn.close()


def create_monthly_recurring_payments():
    """
    Aktif tekrarlayan ödemelerin
    içinde bulunduğumuz ay için
    henüz oluşturulmamışsa ödeme kaydını oluşturur.
    """

    today = date.today()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            amount,
            due_day,
            category
        FROM recurring_payments
        WHERE active = 1
    """)

    recurring_payments = cursor.fetchall()

    for recurring in recurring_payments:

        recurring_id, name, amount, due_day, category = recurring

        month_prefix = today.strftime("%Y-%m")

        cursor.execute("""
            SELECT id
            FROM payments
            WHERE name = ?
            AND due_date LIKE ?
        """, (
            name,
            f"{month_prefix}%"
        ))

        existing_payment = cursor.fetchone()

        if existing_payment:
            continue

        # Ayın geçerli gününü belirle
        import calendar

        last_day = calendar.monthrange(
            today.year,
            today.month
        )[1]

        actual_day = min(
            due_day,
            last_day
        )

        due_date = date(
            today.year,
            today.month,
            actual_day
        )

        cursor.execute("""
            INSERT INTO payments
            (name, amount, due_date, category, status)
            VALUES (?, ?, ?, ?, 'Bekliyor')
        """, (
            name,
            amount,
            str(due_date),
            category
        ))

    conn.commit()
    conn.close()
    # =====================================================
# TAKSİTLİ EV EŞYALARI
# =====================================================

def create_installments_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS installments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            total_amount REAL NOT NULL,
            installment_count INTEGER NOT NULL,
            monthly_amount REAL NOT NULL,
            first_payment_date TEXT NOT NULL,
            current_installment INTEGER DEFAULT 0,
            FOREIGN KEY (asset_id) REFERENCES assets(id)
        )
    """)

    conn.commit()
    conn.close()


def add_installment(
    asset_id,
    product_name,
    total_amount,
    installment_count,
    monthly_amount,
    first_payment_date
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO installments (
            asset_id,
            product_name,
            total_amount,
            installment_count,
            monthly_amount,
            first_payment_date,
            current_installment
        )
        VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (
        asset_id,
        product_name,
        total_amount,
        installment_count,
        monthly_amount,
        str(first_payment_date)
    ))

    conn.commit()
    conn.close()


def get_installments():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            asset_id,
            product_name,
            total_amount,
            installment_count,
            monthly_amount,
            first_payment_date,
            current_installment
        FROM installments
        ORDER BY first_payment_date ASC
    """)

    installments = cursor.fetchall()

    conn.close()

    return installments


def delete_installment(installment_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM installments
        WHERE id = ?
    """, (installment_id,))

    conn.commit()
    conn.close()
# =====================================================
# TAKSİT ÖDEMELERİNİ OLUŞTUR
# =====================================================

def create_installment_payments(
    product_name,
    monthly_amount,
    installment_count,
    first_payment_date
):
    conn = get_connection()
    cursor = conn.cursor()

    import calendar
    from datetime import date

    first_date = (
        first_payment_date
        if isinstance(first_payment_date, date)
        else date.fromisoformat(str(first_payment_date))
    )

    for i in range(installment_count):

        year = first_date.year
        month = first_date.month + i

        while month > 12:
            month -= 12
            year += 1

        last_day = calendar.monthrange(
            year,
            month
        )[1]

        actual_day = min(
            first_date.day,
            last_day
        )

        payment_date = date(
            year,
            month,
            actual_day
        )

        payment_name = (
            f"{product_name} "
            f"Taksit {i + 1}/{installment_count}"
        )

        cursor.execute("""
            INSERT INTO payments
            (name, amount, due_date, category, status)
            VALUES (?, ?, ?, ?, 'Bekliyor')
        """, (
            payment_name,
            monthly_amount,
            str(payment_date),
            "Taksit"
        ))

    conn.commit()
    conn.close()
# =====================================================
# BAKIM KAYITLARI
# Bu kodun TAMAMINI database.py dosyasının EN SONUNA ekle.
# (Mevcut hiçbir fonksiyonu değiştirmiyor.)
# =====================================================

def create_maintenance_table():
    """
    Bakım geçmişi tablosunu oluşturur ve assets tablosuna
    'maintenance_interval_months' sütununu (yoksa) ekler.
    create_assets_table() çağrısından SONRA çağrılmalı.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            maintenance_date TEXT NOT NULL,
            cost REAL DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (asset_id) REFERENCES assets(id)
        )
    """)

    cursor.execute("PRAGMA table_info(assets)")
    columns = [row[1] for row in cursor.fetchall()]

    if "maintenance_interval_months" not in columns:
        cursor.execute("""
            ALTER TABLE assets
            ADD COLUMN maintenance_interval_months INTEGER DEFAULT 0
        """)

    conn.commit()
    conn.close()


def get_asset_intervals():
    """{asset_id: bakım aralığı (ay)} sözlüğü döndürür. 0 = tekrarlanmaz."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, COALESCE(maintenance_interval_months, 0)
        FROM assets
    """)

    result = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return result


def update_asset_maintenance_plan(
    asset_id,
    maintenance_date,
    interval_months
):
    """Eşyanın sonraki bakım tarihini ve tekrar aralığını günceller."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE assets
        SET maintenance_date = ?,
            maintenance_interval_months = ?
        WHERE id = ?
    """, (
        maintenance_date,
        interval_months,
        asset_id
    ))

    conn.commit()
    conn.close()


def add_maintenance_record(
    asset_id,
    maintenance_date,
    cost,
    notes
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO maintenance_records
        (asset_id, maintenance_date, cost, notes)
        VALUES (?, ?, ?, ?)
    """, (
        asset_id,
        maintenance_date,
        cost,
        notes
    ))

    record_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return record_id


def get_maintenance_records():
    """
    Tüm bakım kayıtlarını yeniden eskiye döndürür:
    (id, asset_id, asset_name, maintenance_date, cost, notes)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            r.id,
            r.asset_id,
            COALESCE(a.name, 'Silinmiş eşya'),
            r.maintenance_date,
            COALESCE(r.cost, 0),
            COALESCE(r.notes, '')
        FROM maintenance_records r
        LEFT JOIN assets a ON a.id = r.asset_id
        ORDER BY r.maintenance_date DESC, r.id DESC
    """)

    records = cursor.fetchall()

    conn.close()

    return records


def delete_maintenance_record(record_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM maintenance_records WHERE id = ?",
        (record_id,)
    )

    conn.commit()
    conn.close()


def add_paid_payment(name, amount, due_date, category):
    """Doğrudan 'Ödendi' durumunda bir ödeme kaydı ekler."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO payments
        (name, amount, due_date, category, status)
        VALUES (?, ?, ?, ?, 'Ödendi')
    """, (
        name,
        amount,
        due_date,
        category
    ))

    conn.commit()
    conn.close()
# =====================================================
# ARAÇLAR
# Bu kodun TAMAMINI database.py dosyasının EN SONUNA ekle.
# (Mevcut hiçbir fonksiyonu değiştirmiyor.)
# =====================================================

def create_vehicles_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT NOT NULL,
            brand TEXT NOT NULL,
            model TEXT,
            year INTEGER,
            fuel_type TEXT,
            km INTEGER DEFAULT 0,
            inspection_date TEXT,
            traffic_insurance_end TEXT,
            kasko_end TEXT,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            expense_date TEXT NOT NULL,
            expense_type TEXT NOT NULL,
            amount REAL NOT NULL,
            km INTEGER,
            liters REAL,
            notes TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )
    """)

    conn.commit()
    conn.close()


def add_vehicle(
    plate,
    brand,
    model,
    year,
    fuel_type,
    km,
    inspection_date,
    traffic_insurance_end,
    kasko_end,
    notes
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO vehicles (
            plate, brand, model, year, fuel_type, km,
            inspection_date, traffic_insurance_end, kasko_end, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        plate, brand, model, year, fuel_type, km,
        inspection_date, traffic_insurance_end, kasko_end, notes
    ))

    vehicle_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return vehicle_id


def get_vehicles():
    """
    (id, plate, brand, model, year, fuel_type, km,
     inspection_date, traffic_insurance_end, kasko_end, notes)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id, plate, brand, model, year, fuel_type, km,
            inspection_date, traffic_insurance_end, kasko_end, notes
        FROM vehicles
        ORDER BY id ASC
    """)

    vehicles = cursor.fetchall()

    conn.close()

    return vehicles


def update_vehicle(
    vehicle_id,
    plate,
    brand,
    model,
    year,
    fuel_type,
    km,
    inspection_date,
    traffic_insurance_end,
    kasko_end,
    notes
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE vehicles
        SET plate = ?,
            brand = ?,
            model = ?,
            year = ?,
            fuel_type = ?,
            km = ?,
            inspection_date = ?,
            traffic_insurance_end = ?,
            kasko_end = ?,
            notes = ?
        WHERE id = ?
    """, (
        plate, brand, model, year, fuel_type, km,
        inspection_date, traffic_insurance_end, kasko_end, notes,
        vehicle_id
    ))

    conn.commit()
    conn.close()


def delete_vehicle(vehicle_id):
    """Aracı ve ona ait tüm masraf kayıtlarını siler."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM vehicle_expenses WHERE vehicle_id = ?",
        (vehicle_id,)
    )

    cursor.execute(
        "DELETE FROM vehicles WHERE id = ?",
        (vehicle_id,)
    )

    conn.commit()
    conn.close()


def add_vehicle_expense(
    vehicle_id,
    expense_date,
    expense_type,
    amount,
    km,
    liters,
    notes
):
    """
    Masraf ekler. km girildiyse ve aracın mevcut km'sinden
    büyükse aracın km bilgisi de güncellenir.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO vehicle_expenses
        (vehicle_id, expense_date, expense_type, amount, km, liters, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        vehicle_id, expense_date, expense_type, amount, km, liters, notes
    ))

    expense_id = cursor.lastrowid

    if km:
        cursor.execute("""
            UPDATE vehicles
            SET km = ?
            WHERE id = ?
            AND (km IS NULL OR km < ?)
        """, (km, vehicle_id, km))

    conn.commit()
    conn.close()

    return expense_id


def get_vehicle_expenses(vehicle_id):
    """
    Yeniden eskiye sıralı:
    (id, vehicle_id, expense_date, expense_type, amount, km, liters, notes)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id, vehicle_id, expense_date, expense_type,
            amount, km, liters, COALESCE(notes, '')
        FROM vehicle_expenses
        WHERE vehicle_id = ?
        ORDER BY expense_date DESC, id DESC
    """, (vehicle_id,))

    expenses = cursor.fetchall()

    conn.close()

    return expenses


def delete_vehicle_expense(expense_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM vehicle_expenses WHERE id = ?",
        (expense_id,)
    )

    conn.commit()
    conn.close()


def count_vehicle_alerts(days=30):
    """
    Muayene / trafik sigortası / kasko tarihi geçmiş veya
    'days' gün içinde dolacak belge sayısını döndürür.
    (Sidebar rozeti için kullanılır.)
    """
    from datetime import datetime, date

    today = date.today()
    count = 0

    for v in get_vehicles():
        for value in (v[7], v[8], v[9]):

            if not value:
                continue

            try:
                d = datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                continue

            if (d - today).days <= days:
                count += 1

    return count
# =====================================================
# GELİRLER
# =====================================================

def create_income_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL NOT NULL,
            income_date TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def add_income(name, amount, income_date, category):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO incomes
        (name, amount, income_date, category)
        VALUES (?, ?, ?, ?)
    """, (
        name,
        amount,
        income_date,
        category
    ))

    conn.commit()
    conn.close()


def get_incomes():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            amount,
            income_date,
            category
        FROM incomes
        ORDER BY income_date DESC, id DESC
    """)

    incomes = cursor.fetchall()

    conn.close()

    return incomes


def delete_income(income_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM incomes
        WHERE id = ?
    """, (income_id,))

    conn.commit()
    conn.close()


# =====================================================
# TEKRARLAYAN GELİRLER
# =====================================================

def _month_day(year, month, day):
    """Günü ayın uzunluğuna sığdırır (31 -> Şubat'ta 28/29)."""
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def create_recurring_incomes_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recurring_incomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            amount REAL,
            day INTEGER NOT NULL,
            category TEXT NOT NULL,
            kind TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            last_month TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_recurring_income(
    name, amount, day, category, kind, skip_current_month=False
):
    """kind: 'fixed' (sabit) veya 'variable' (değişken)."""
    last_month = date.today().strftime("%Y-%m") if skip_current_month else None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO recurring_incomes
            (name, amount, day, category, kind, active, last_month)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        """,
        (name, amount if kind == "fixed" else None, day, category, kind, last_month)
    )
    conn.commit()
    conn.close()


def get_recurring_incomes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, amount, day, category, kind, active, last_month "
        "FROM recurring_incomes ORDER BY name"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_recurring_income(income_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recurring_incomes WHERE id = ?", (income_id,))
    conn.commit()
    conn.close()


def toggle_recurring_income(income_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE recurring_incomes SET active = 1 - active WHERE id = ?",
        (income_id,)
    )
    conn.commit()
    conn.close()


def mark_recurring_income_done(income_id, amount=None):
    """Bu ay için işlendi olarak işaretler. Değişken maaşta son tutarı
    bir sonraki ay için öneri olarak saklar."""
    this_month = date.today().strftime("%Y-%m")
    conn = get_connection()
    cursor = conn.cursor()
    if amount is not None:
        cursor.execute(
            "UPDATE recurring_incomes SET last_month = ?, amount = ? WHERE id = ?",
            (this_month, amount, income_id)
        )
    else:
        cursor.execute(
            "UPDATE recurring_incomes SET last_month = ? WHERE id = ?",
            (this_month, income_id)
        )
    conn.commit()
    conn.close()


def create_monthly_fixed_incomes():
    """Sabit maaşları bu ay için bir kez oluşturur."""
    today = date.today()
    this_month = today.strftime("%Y-%m")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name, amount, day, category FROM recurring_incomes
        WHERE active = 1 AND kind = 'fixed'
          AND (last_month IS NULL OR last_month != ?)
        """,
        (this_month,)
    )
    rows = cursor.fetchall()
    conn.close()

    for rid, name, amount, day, category in rows:
        income_date = _month_day(today.year, today.month, day)
        add_income(name, amount, str(income_date), category)
        mark_recurring_income_done(rid)


def get_pending_variable_incomes():
    """Günü gelmiş ama bu ay tutarı girilmemiş değişken maaşlar.
    Dönüş: (id, ad, son_tutar, bu_ayki_tarih, kategori)"""
    today = date.today()
    this_month = today.strftime("%Y-%m")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name, amount, day, category FROM recurring_incomes
        WHERE active = 1 AND kind = 'variable'
          AND (last_month IS NULL OR last_month != ?)
        """,
        (this_month,)
    )
    rows = cursor.fetchall()
    conn.close()

    pending = []
    for rid, name, amount, day, category in rows:
        due = _month_day(today.year, today.month, day)
        if today >= due:
            pending.append((rid, name, amount, str(due), category))
    return pending


# =====================================================
# TEKRARLAYAN ÖDEMEYİ GÜNCELLE
# =====================================================

def update_recurring_payment(
    recurring_id,
    name,
    amount,
    due_day,
    category,
    update_current_month=True
):
    """Sabit ödemeyi günceller.
    - İsim değiştiyse bu ayki kaydı da yeniden adlandırır
      (aksi halde isim eşleşmediği için çift kayıt oluşurdu).
    - update_current_month=True ise bu ayın ÖDENMEMİŞ kaydının
      tutar, gün ve kategorisi de güncellenir."""

    today = date.today()
    month_prefix = f"{today.strftime('%Y-%m')}%"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM recurring_payments WHERE id = ?",
        (recurring_id,)
    )
    row = cursor.fetchone()
    old_name = row[0] if row else name

    cursor.execute("""
        UPDATE recurring_payments
        SET name = ?, amount = ?, due_day = ?, category = ?
        WHERE id = ?
    """, (name, amount, due_day, category, recurring_id))

    if old_name != name:
        cursor.execute("""
            UPDATE payments
            SET name = ?
            WHERE name = ? AND due_date LIKE ?
        """, (name, old_name, month_prefix))

    if update_current_month:
        last_day = calendar.monthrange(today.year, today.month)[1]
        new_due = date(today.year, today.month, min(due_day, last_day))

        cursor.execute("""
            UPDATE payments
            SET amount = ?, due_date = ?, category = ?
            WHERE name = ? AND due_date LIKE ? AND status != 'Ödendi'
        """, (amount, str(new_due), category, name, month_prefix))

    conn.commit()
    conn.close()


# =====================================================
# TAKVİM ETKİNLİKLERİ
# =====================================================

def create_calendar_events_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'custom',
            repeat_yearly INTEGER NOT NULL DEFAULT 0,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_calendar_event(title, event_date, kind, repeat_yearly, notes):
    """kind: 'custom' (hatırlatıcı) veya 'tax' (vergi / resmi)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO calendar_events
            (title, event_date, kind, repeat_yearly, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, event_date, kind, repeat_yearly, notes)
    )
    conn.commit()
    conn.close()


def get_calendar_events():
    """(id, title, event_date, kind, repeat_yearly, notes)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, title, event_date, kind, repeat_yearly,
               COALESCE(notes, '')
        FROM calendar_events
        ORDER BY event_date ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_calendar_event(event_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM calendar_events WHERE id = ?",
        (event_id,)
    )
    conn.commit()
    conn.close()
# =====================================================
# KREDİ KARTLARI (hafif sürüm)
# Bu kodun TAMAMINI database.py dosyasının EN SONUNA ekle.
# Mevcut hiçbir fonksiyonu değiştirmiyor.
# =====================================================

def create_credit_cards_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            last4 TEXT,
            card_limit REAL DEFAULT 0,
            statement_day INTEGER,
            due_day INTEGER NOT NULL
        )
    """)

    # Tutar ve durum burada TUTULMAZ; payments tablosundan okunur.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_statements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id INTEGER NOT NULL,
            period TEXT NOT NULL,
            payment_id INTEGER,
            min_payment REAL DEFAULT 0,
            FOREIGN KEY (card_id) REFERENCES credit_cards(id)
        )
    """)
    _migrate_installments_card_column(cursor)

    conn.commit()
    conn.close()


def add_credit_card(name, last4, card_limit, statement_day, due_day):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO credit_cards
        (name, last4, card_limit, statement_day, due_day)
        VALUES (?, ?, ?, ?, ?)
    """, (name, last4, card_limit, statement_day, due_day))

    conn.commit()
    conn.close()


def get_credit_cards():
    """(id, name, last4, card_limit, statement_day, due_day)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, COALESCE(last4, ''), COALESCE(card_limit, 0),
               statement_day, due_day
        FROM credit_cards
        ORDER BY id ASC
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows


def update_credit_card(card_id, name, last4, card_limit, statement_day, due_day):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE credit_cards
        SET name = ?, last4 = ?, card_limit = ?,
            statement_day = ?, due_day = ?
        WHERE id = ?
    """, (name, last4, card_limit, statement_day, due_day, card_id))

    conn.commit()
    conn.close()


def delete_credit_card(card_id):
    """Kartı, ekstre kayıtlarını ve ÖDENMEMİŞ ekstre ödemelerini siler.
    Ödenmiş ekstre ödemeleri geçmiş olarak payments'ta kalır."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM payments
        WHERE status != 'Ödendi'
        AND id IN (
            SELECT payment_id FROM card_statements WHERE card_id = ?
        )
    """, (card_id,))

    cursor.execute(
        "DELETE FROM card_statements WHERE card_id = ?", (card_id,)
    )
    cursor.execute(
        "DELETE FROM credit_cards WHERE id = ?", (card_id,)
    )

    conn.commit()
    conn.close()


def add_card_statement(card_id, card_name, amount, due_date, min_payment=0):
    """Ekstre ekler ve payments'a 'Kredi Kartı' ödemesi açar.
    Aynı kart + aynı ay için ekstre varsa None döner (eklenmez)."""

    period = str(due_date)[:7]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM card_statements WHERE card_id = ? AND period = ?",
        (card_id, period)
    )

    if cursor.fetchone():
        conn.close()
        return None

    cursor.execute("""
        INSERT INTO payments
        (name, amount, due_date, category, status)
        VALUES (?, ?, ?, 'Kredi Kartı', 'Bekliyor')
    """, (f"{card_name} Ekstre", amount, str(due_date)))

    payment_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO card_statements
        (card_id, period, payment_id, min_payment)
        VALUES (?, ?, ?, ?)
    """, (card_id, period, payment_id, min_payment))

    statement_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return statement_id


def get_card_statements(card_id):
    """Yeniden eskiye:
    (id, period, payment_id, min_payment, amount, due_date, status)
    Ödeme kaydı Ödemeler sayfasından silinmişse amount/due_date/status None."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id, s.period, s.payment_id, COALESCE(s.min_payment, 0),
               p.amount, p.due_date, p.status
        FROM card_statements s
        LEFT JOIN payments p ON p.id = s.payment_id
        WHERE s.card_id = ?
        ORDER BY s.period DESC, s.id DESC
    """, (card_id,))

    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_card_statement(statement_id):
    """Ekstre kaydını ve bağlı ödeme kaydını siler."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT payment_id FROM card_statements WHERE id = ?",
        (statement_id,)
    )
    row = cursor.fetchone()

    if row and row[0]:
        cursor.execute("DELETE FROM payments WHERE id = ?", (row[0],))

    cursor.execute(
        "DELETE FROM card_statements WHERE id = ?", (statement_id,)
    )

    conn.commit()
    conn.close()


def update_card_statement_min(statement_id, min_payment):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE card_statements SET min_payment = ? WHERE id = ?",
        (min_payment, statement_id)
    )

    conn.commit()
    conn.close()
# =====================================================
# KARTLA TAKSİT
# Bu kodun TAMAMINI database.py dosyasının EN SONUNA ekle.
# Ayrıca daha önce eklediğin create_credit_cards_tables()
# fonksiyonunun EN SONUNA (conn.commit() satırından ÖNCE)
# şu çağrıyı ekle:
#
#     _migrate_installments_card_column(cursor)
#
# Mevcut hiçbir fonksiyonu değiştirmiyor.
# =====================================================

def _migrate_installments_card_column(cursor):
    """installments tablosuna card_id sütununu (yoksa) ekler.
    card_id dolu olan taksitler karttandır: payments'a ödeme açılmaz,
    tutar kartın ekstresinin içinde sayılır."""

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS installments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            total_amount REAL NOT NULL,
            installment_count INTEGER NOT NULL,
            monthly_amount REAL NOT NULL,
            first_payment_date TEXT NOT NULL,
            current_installment INTEGER DEFAULT 0,
            FOREIGN KEY (asset_id) REFERENCES assets(id)
        )
    """)

    cursor.execute("PRAGMA table_info(installments)")
    columns = [row[1] for row in cursor.fetchall()]

    if "card_id" not in columns:
        cursor.execute("ALTER TABLE installments ADD COLUMN card_id INTEGER")


def _installment_number(first_date_str, count, year, month):
    """Verilen ayın kaçıncı taksit olduğunu döndürür (1..count),
    taksit o ayda yoksa None."""
    try:
        fy, fm = int(str(first_date_str)[:4]), int(str(first_date_str)[5:7])
    except (ValueError, TypeError):
        return None

    n = (year - fy) * 12 + (month - fm) + 1

    return n if 1 <= n <= count else None


def add_card_installment(
    asset_id,
    card_id,
    product_name,
    total_amount,
    installment_count,
    monthly_amount,
    first_payment_date
):
    """Kartla taksit kaydı. payments'a ödeme AÇMAZ.
    asset_id: ev eşyasıysa eşyanın id'si, değilse 0.
    first_payment_date: ilk taksitin yansıyacağı ekstrenin SON ÖDEME
    tarihi (sadece yıl-ay kullanılır)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO installments (
            asset_id, product_name, total_amount, installment_count,
            monthly_amount, first_payment_date, current_installment,
            card_id
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    """, (
        asset_id,
        product_name,
        total_amount,
        installment_count,
        monthly_amount,
        str(first_payment_date),
        card_id
    ))

    conn.commit()
    conn.close()


def get_card_installments(card_id=None):
    """Kartla alınan taksitler (card_id verilmezse tüm kartlar).
    (id, asset_id, card_id, product_name, total, count, monthly,
     first_date, billed)
    billed: bu ay dahil ekstrelere yansıyan taksit sayısı."""

    today = date.today()

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, asset_id, card_id, product_name, total_amount,
               installment_count, monthly_amount, first_payment_date
        FROM installments
        WHERE card_id IS NOT NULL
    """
    params = ()

    if card_id is not None:
        query += " AND card_id = ?"
        params = (card_id,)

    query += " ORDER BY first_payment_date ASC, id ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    result = []

    for (iid, aid, cid, pname, total, count, monthly, first) in rows:

        try:
            fy, fm = int(first[:4]), int(first[5:7])
            billed = (today.year - fy) * 12 + (today.month - fm) + 1
        except (ValueError, TypeError):
            billed = 0

        billed = max(0, min(count, billed))

        result.append(
            (iid, aid, cid, pname, total, count, monthly, first, billed)
        )

    return result


def get_card_installments_for_month(card_id, year, month):
    """O ayın ekstresine yansıyan taksitler:
    [(ürün, aylık tutar, kaçıncı taksit, toplam taksit), ...]"""

    result = []

    for (iid, aid, cid, pname, total, count, monthly, first, billed) \
            in get_card_installments(card_id):

        n = _installment_number(first, count, year, month)

        if n is not None:
            result.append((pname, float(monthly), n, count))

    return result


def get_card_installment_ids():
    """Kartla alınan taksitlerin id kümesi (AI asistan ve raporlarda
    bunları normal taksitlerden ayırmak için)."""
    return {row[0] for row in get_card_installments()}
# =====================================================
# TÜM VERİLERİ SIFIRLA
# =====================================================

def reset_all_data():
    """Veritabanındaki TÜM tabloların içini boşaltır (tablolar kalır,
    uygulama yeniden kullanıma hazır olur) ve id sayaçlarını sıfırlar.
    Silinen tabloların adlarını döndürür.
    Not: Yerel yedek dosyalarına dokunmaz."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
    """)

    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        cursor.execute(f'DELETE FROM "{table}"')

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE name = 'sqlite_sequence'"
    )

    if cursor.fetchone():
        cursor.execute("DELETE FROM sqlite_sequence")

    conn.commit()

    # Boşalan alanı dosyadan geri alır
    cursor.execute("VACUUM")

    conn.close()

    return tables