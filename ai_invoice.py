import os
import time

from google import genai
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


# Geçici yoğunluk/kapasite hatasında sıradaki modele geçilir.
MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
]

RETRIES_PER_MODEL = 2

BILL_CATEGORIES = [
    "Elektrik", "Su", "Doğalgaz", "İnternet", "Kira",
    "Aidat", "Sigorta", "Cep Telefonu", "Taksit","Kredi Kartı", "Diğer"
]


class InvoiceData(BaseModel):
    product_name: str
    brand: str
    model: str
    purchase_date: str
    price: float
    warranty_end: str
    confidence_note: str


class BillData(BaseModel):
    bill_name: str
    category: str
    amount: float
    due_date: str
    confidence_note: str


def _is_temporary(error):
    text = str(error)
    return any(
        code in text
        for code in ("503", "UNAVAILABLE", "500", "429")
    )


def _generate(pdf_file, prompt, schema):
    """PDF'i Gemini'ye yükler, şemaya uygun sonucu döndürür.
    Geçici hatalarda tekrar dener, gerekirse yedek modele geçer."""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY bulunamadı. "
            ".env dosyanızı kontrol edin."
        )

    client = genai.Client(api_key=api_key)

    temp_path = "temp_invoice.pdf"

    with open(temp_path, "wb") as f:
        f.write(pdf_file.getbuffer())

    try:

        uploaded_file = client.files.upload(file=temp_path)

        last_error = None

        for model_name in MODELS:

            for attempt in range(RETRIES_PER_MODEL):

                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[uploaded_file, prompt],
                        config={
                            "response_mime_type": "application/json",
                            "response_schema": schema
                        }
                    )

                    if response.parsed is None:
                        raise RuntimeError(
                            "AI cevabı okunamadı, lütfen tekrar deneyin."
                        )

                    return response.parsed

                except Exception as e:
                    last_error = e

                    # API key, model adı, schema vb. kalıcı hatalarda
                    # başka modele geçmek yerine hatayı doğrudan göster.
                    if not _is_temporary(e):
                        raise

                    if attempt < RETRIES_PER_MODEL - 1:
                        wait_time = 2 ** attempt

                        print(
                            f"{model_name} geçici hata verdi. "
                            f"{wait_time} saniye sonra tekrar deneniyor..."
                        )

                        time.sleep(wait_time)

            print(
                f"{model_name} kullanılamıyor. "
                "Sıradaki Gemini modeline geçiliyor..."
            )

        if last_error is not None:
            raise last_error

        raise RuntimeError("Fatura analiz edilemedi.")

    finally:

        if os.path.exists(temp_path):
            os.remove(temp_path)


# =====================================================
# EV EŞYASI FATURASI
# =====================================================

def analyze_invoice(pdf_file):

    prompt = """
Sen bir fatura bilgi çıkarma asistanısın.

Yüklenen faturayı analiz et.

Aşağıdaki bilgileri faturadan mümkün olduğunca
doğru şekilde çıkar:

1. Ürün adı
2. Marka
3. Model
4. Satın alma tarihi
5. Toplam ödenen tutar
6. Garanti bitiş tarihi

Faturada garanti bitiş tarihi açıkça yazmıyorsa
boş string döndür.

Bir bilgi faturada bulunmuyorsa tahmin etme.
Boş string döndür.

Tarihleri YYYY-MM-DD formatında döndür.

Tutarı sadece sayı olarak döndür.

confidence_note alanında hangi bilgilerin
faturadan açıkça bulunduğunu ve hangilerinin
bulunamadığını kısaca belirt.
"""

    return _generate(pdf_file, prompt, InvoiceData)


# =====================================================
# AYLIK FATURA (elektrik, su, doğalgaz, internet...)
# =====================================================

def analyze_bill(pdf_file):

    categories = ", ".join(BILL_CATEGORIES)

    prompt = f"""
Sen bir fatura bilgi çıkarma asistanısın.

Yüklenen belge elektrik, su, doğalgaz, internet, cep telefonu,
aidat gibi aylık bir fatura. Şu bilgileri çıkar:

1. bill_name: Kurum ve fatura türü, kısa (örn. "Elektrik Faturası",
   "Doğalgaz Faturası"). Dönem belliyse ekle (örn. "Elektrik - Eylül").
2. category: Şu listeden TAM OLARAK birini seç: {categories}.
   Hiçbiri uymuyorsa "Diğer".
3. amount: Ödenecek toplam tutar (TL). Önceki dönemlerden devreden
   borç varsa ve belgede "ödenecek tutar" ayrıca yazıyorsa onu al.
   Sadece sayı olarak döndür (örn. 1250.75).
4. due_date: Son ödeme tarihi, YYYY-MM-DD formatında.

Bir bilgi belgede açıkça yoksa tahmin etme; metin alanlarını boş
string, tutarı 0 döndür.

confidence_note alanında hangi bilgilerin belgeden açıkça bulunduğunu
ve hangilerinin bulunamadığını (ya da emin olmadığını) kısaca belirt.
"""

    return _generate(pdf_file, prompt, BillData)