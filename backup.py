"""
backup.py

AI Home Manager yedekleme işlemleri.
app.py, database.py ve ai_assistant.py ile aynı klasöre koy.

- Yedek alırken SQLite'ın kendi yedekleme yöntemi kullanılır; dosya
  o sırada açık olsa bile tutarlı bir kopya çıkar.
- Geri yüklemeden önce mevcut veriler otomatik olarak yedeklenir.
- Yerel yedekler, veritabanının yanındaki "backups" klasöründe tutulur.
"""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from database import DB_PATH


BACKUP_DIR = Path(DB_PATH).parent / "backups"

# Yedek türü -> saklanacak son yedek sayısı
KEEP_LAST = {
    "otomatik": 14,
    "manuel": 10,
    "geri_yukleme_oncesi": 5,
}

KIND_LABELS = {
    "otomatik": "🤖 Otomatik",
    "manuel": "📌 Manuel",
    "geri_yukleme_oncesi": "🛡️ Geri yükleme öncesi",
}

# Geçerli bir AI Home Manager yedeğinde en az bu tablolar olmalı
REQUIRED_TABLES = {"payments", "assets"}

# Tablo adı -> ekranda gösterilecek ad
KNOWN_TABLES = {
    "payments": "Ödeme",
    "recurring_payments": "Tekrarlayan ödeme",
    "installments": "Taksit planı",
    "assets": "Ev eşyası",
    "maintenance_records": "Bakım kaydı",
    "vehicles": "Araç",
    "vehicle_expenses": "Araç masrafı",
    "recurring_incomes": "Tekrarlayan Gelir",
}


# =====================================================
# İÇ YARDIMCILAR
# =====================================================

def _copy_db(src_path, dst_path):
    """SQLite yedekleme API'siyle src veritabanını dst'nin üzerine kopyalar."""
    src = sqlite3.connect(str(src_path))
    dst = sqlite3.connect(str(dst_path))

    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _table_counts(conn):
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }

    counts = {}

    for table in KNOWN_TABLES:
        if table in tables:
            counts[table] = conn.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

    return tables, counts


def _prune(prefix):
    keep = KEEP_LAST.get(prefix)

    if keep is None or not BACKUP_DIR.exists():
        return

    files = sorted(BACKUP_DIR.glob(f"{prefix}_*.db"), reverse=True)

    for old in files[keep:]:
        try:
            old.unlink()
        except OSError:
            pass


# =====================================================
# YEDEK ALMA
# =====================================================

def create_backup_bytes():
    """Güncel veritabanının tutarlı bir kopyasını bayt olarak döndürür."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        target = Path(tmp) / "backup.db"
        _copy_db(DB_PATH, target)
        return target.read_bytes()


def create_backup_file(prefix="manuel"):
    """backups klasörüne yeni bir yedek yazar ve yolunu döndürür."""
    if not Path(DB_PATH).exists():
        return None

    BACKUP_DIR.mkdir(exist_ok=True)

    name = f"{prefix}_{datetime.now():%Y-%m-%d_%H%M%S}.db"
    path = BACKUP_DIR / name

    _copy_db(DB_PATH, path)
    _prune(prefix)

    return path


def auto_backup_daily():
    """
    Bugün henüz otomatik yedek alınmadıysa alır.
    Uygulama her açıldığında/yenilendiğinde güvenle çağrılabilir;
    hata olursa uygulamayı durdurmaz.
    """
    try:
        if not Path(DB_PATH).exists():
            return None

        BACKUP_DIR.mkdir(exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")

        if any(BACKUP_DIR.glob(f"otomatik_{today}_*.db")):
            return None

        return create_backup_file("otomatik")

    except Exception:
        return None


def list_backups():
    """Yerel yedekleri yeniden eskiye döndürür."""
    if not BACKUP_DIR.exists():
        return []

    result = []

    for path in BACKUP_DIR.glob("*.db"):

        kind = next(
            (k for k in KEEP_LAST if path.name.startswith(f"{k}_")),
            None
        )

        if kind is None:
            continue

        stat = path.stat()

        result.append(
            {
                "name": path.name,
                "path": path,
                "kind": kind,
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime),
            }
        )

    result.sort(key=lambda b: b["mtime"], reverse=True)

    return result


# =====================================================
# KONTROL VE GERİ YÜKLEME
# =====================================================

def get_current_counts():
    """Mevcut veritabanındaki kayıt sayıları {tablo: sayı}."""
    if not Path(DB_PATH).exists():
        return {}

    conn = sqlite3.connect(str(DB_PATH))

    try:
        return _table_counts(conn)[1]
    except sqlite3.DatabaseError:
        return {}
    finally:
        conn.close()


def inspect_backup_bytes(data):
    """
    Yüklenen dosyanın geçerli bir yedek olup olmadığını kontrol eder.
    Döner: {"valid": bool, "error": str|None, "counts": {tablo: sayı}}
    """
    result = {"valid": False, "error": None, "counts": {}}

    if not data:
        result["error"] = "Dosya boş."
        return result

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:

        path = Path(tmp) / "upload.db"
        path.write_bytes(data)

        conn = None

        try:
            conn = sqlite3.connect(str(path))

            check = conn.execute("PRAGMA integrity_check").fetchone()

            if not check or check[0] != "ok":
                result["error"] = "Veritabanı dosyası bozuk görünüyor."
                return result

            tables, counts = _table_counts(conn)

            if not REQUIRED_TABLES <= tables:
                result["error"] = (
                    "Bu dosya bir AI Home Manager yedeği gibi görünmüyor."
                )
                return result

            result["valid"] = True
            result["counts"] = counts

        except sqlite3.DatabaseError:
            result["error"] = "Bu dosya geçerli bir veritabanı değil."

        finally:
            if conn is not None:
                conn.close()

    return result


def restore_from_bytes(data):
    """
    Veritabanını verilen yedekle değiştirir.
    Önce mevcut verilerin güvenlik yedeğini alır ve o yedeğin yolunu döndürür.
    """
    info = inspect_backup_bytes(data)

    if not info["valid"]:
        raise ValueError(info["error"])

    safety = create_backup_file("geri_yukleme_oncesi")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path = Path(tmp) / "restore.db"
        path.write_bytes(data)
        _copy_db(path, DB_PATH)

    return safety