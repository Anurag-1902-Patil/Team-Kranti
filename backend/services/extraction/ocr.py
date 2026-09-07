"""
OCR service — extracts text from images and PDFs.

Two deliberately different OCR engines for two different accuracy profiles
(documented in .ai/ARCHITECTURE.md — this is intentional, not redundant):

  1. Typed/printed content (typed DPRs, spreadsheet renders, printed forms)
     → Tesseract (pytesseract) — fast, lightweight, excellent on clean printed text.

  2. Handwritten site diaries (photos of handwritten diary pages)
     → PP-OCRv5 via PaddleOCR — 0.07B params, CPU-only, no GPU required.
       Baidu benchmarks claim it outperforms Qwen2.5-VL and GPT-4o on handwritten
       text specifically. Validate against data/synthetic/site_diary_photo.png.

PDF handling:
  - Text-layer PDFs → pdfplumber (fast, preserves structure)
  - Scanned PDFs (no text layer) → rasterize with pdf2image → typed OCR path (Tesseract)

Spreadsheets (XLSX/CSV) are handled separately via extract_text_from_spreadsheet()
using pandas — no image OCR needed for native spreadsheet files.
"""

import io
import structlog

from backend.core.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

# PP-OCRv5 singleton (lazy-loaded, CPU only)
_ppocr_v5 = None


def _get_ppocr_v5():
    """
    Lazy-load PP-OCRv5 via PaddleOCR.

    Uses PP-OCRv5's recognition model which is specifically tuned for
    handwritten text. CPU inference is sufficient for demo-scale input.
    """
    global _ppocr_v5
    if _ppocr_v5 is None:
        from paddleocr import PaddleOCR

        log.info("ocr.loading_ppocr_v5")
        # lang="en" activates PP-OCRv5 English recognition weights
        # use_angle_cls=True handles rotated/tilted diary pages
        # use_gpu=False — explicit CPU-only (no GPU service in compose)
        _ppocr_v5 = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            show_log=False,
            use_gpu=False,
        )
        log.info("ocr.ppocr_v5_ready")
    return _ppocr_v5


def extract_text_printed(image_bytes: bytes) -> str:
    """
    Extract text from a typed/printed image using Tesseract.

    Used for: typed DPRs, rendered spreadsheet images, printed forms.
    Engine: pytesseract (Tesseract 4+ LSTM mode).

    Returns: extracted text as a single string.
    """
    import pytesseract
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # PSM 3 = fully automatic page segmentation (default, works well for DPRs)
    # OEM 3 = LSTM + legacy (best accuracy on typed text)
    custom_config = "--oem 3 --psm 3"

    extracted = pytesseract.image_to_string(image, config=custom_config).strip()
    log.info("ocr.printed_extracted_tesseract", chars=len(extracted))
    return extracted


def extract_text_handwritten(image_bytes: bytes) -> str:
    """
    Extract handwritten text from a site diary photo using PP-OCRv5.

    Used for: scanned/photographed handwritten daily progress diaries.
    Engine: PP-OCRv5 via PaddleOCR — 0.07B params, CPU-only.

    This replaces the earlier Groq vision approach — PP-OCRv5 runs locally,
    no API key or network needed, and is specifically tuned for handwritten OCR.

    Returns: extracted text as a single string.
    """
    import numpy as np
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(image)

    ocr = _get_ppocr_v5()
    results = ocr.ocr(img_array, cls=True)

    if not results or results[0] is None:
        log.warning("ocr.ppocr_v5_no_results")
        return ""

    lines = []
    for line in results[0]:
        text_info = line[1]  # (text, confidence)
        text, confidence = text_info[0], text_info[1]
        # PP-OCRv5 is generally more confident than v4; keep threshold at 0.4
        # for handwritten text where even 0.5 can exclude valid but messy glyphs
        if confidence > 0.4:
            lines.append(text)

    extracted = "\n".join(lines)
    log.info("ocr.handwritten_extracted_ppocr_v5", lines=len(lines), chars=len(extracted))
    return extracted


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF.
    Tries pdfplumber first (text-layer PDFs).
    Falls back to rasterize + Tesseract for scanned/image PDFs.
    """
    import pdfplumber

    text_parts = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
    except Exception as exc:
        log.warning("ocr.pdfplumber_failed", error=str(exc))

    if text_parts:
        result = "\n\n".join(text_parts)
        log.info("ocr.pdf_text_layer", pages=len(text_parts), chars=len(result))
        return result

    # No text layer — rasterize and run Tesseract on each page
    log.info("ocr.pdf_no_text_layer_rasterizing")
    try:
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(pdf_bytes, dpi=200)
        page_texts = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            page_text = extract_text_printed(buf.getvalue())
            page_texts.append(page_text)
        result = "\n\n".join(page_texts)
        log.info("ocr.pdf_ocr_fallback_tesseract", pages=len(images), chars=len(result))
        return result
    except Exception as exc:
        log.error("ocr.pdf_rasterize_failed", error=str(exc))
        return ""


def extract_text_from_spreadsheet(file_bytes: bytes, filename: str = "") -> str:
    """
    Convert an XLSX/CSV spreadsheet to a structured text representation
    suitable for LLM extraction.

    Returns each sheet as a pipe-delimited text block.
    Note: this uses pandas directly — no image OCR needed for native files.
    """
    import pandas as pd

    text_parts = []
    filename_lower = filename.lower()

    try:
        if filename_lower.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes), dtype=str, keep_default_na=False)
            text_parts.append(f"[Sheet: CSV Data]\n{df.to_csv(index=False)}")
        else:
            # XLSX — process all sheets
            xf = pd.ExcelFile(io.BytesIO(file_bytes))
            for sheet_name in xf.sheet_names:
                df = pd.read_excel(
                    io.BytesIO(file_bytes),
                    sheet_name=sheet_name,
                    dtype=str,
                    keep_default_na=False,
                )
                if df.empty:
                    continue
                # Drop fully-empty rows/columns
                df = df.dropna(how="all").dropna(axis=1, how="all")
                text_parts.append(
                    f"[Sheet: {sheet_name}]\n"
                    + df.to_csv(index=False, sep="|")
                )
    except Exception as exc:
        log.error("ocr.spreadsheet_failed", error=str(exc), filename=filename)
        return ""

    result = "\n\n".join(text_parts)
    log.info("ocr.spreadsheet_extracted", sheets=len(text_parts), chars=len(result))
    return result
