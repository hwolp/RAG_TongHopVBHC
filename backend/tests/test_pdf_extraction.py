"""
Script kiểm tra chất lượng đọc PDF và chunking.
Chạy: python tests/test_pdf_extraction.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import PyMuPDFLoader
import fitz  # PyMuPDF trực tiếp

PDF_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                        "uploads", "personal", "464-ttg.signed.pdf")

print("=" * 80)
print(f"PDF PATH: {PDF_PATH}")
print(f"FILE EXISTS: {os.path.exists(PDF_PATH)}")
print("=" * 80)

# ── 1. Đọc trực tiếp bằng PyMuPDF (fitz) ─────────────────────────────────
print("\n[1] ĐỌC TRỰC TIẾP BẰNG PyMuPDF (fitz)")
print("-" * 60)
try:
    doc = fitz.open(PDF_PATH)
    print(f"Số trang: {doc.page_count}")
    total_chars_fitz = 0
    for i, page in enumerate(doc):
        text = page.get_text()
        total_chars_fitz += len(text)
        print(f"\n--- Trang {i+1} ({len(text)} chars) ---")
        preview = text[:500] if text else "(TRỐNG)"
        print(preview)
        if len(text) > 500:
            print(f"... (còn {len(text)-500} chars)")
    print(f"\nTổng ký tự (fitz): {total_chars_fitz}")
    doc.close()
except Exception as e:
    print(f"LỖI fitz: {e}")

# ── 2. Đọc bằng PyMuPDFLoader (LangChain) ─────────────────────────────────
print("\n\n[2] ĐỌC BẰNG PyMuPDFLoader (LangChain)")
print("-" * 60)
try:
    loader = PyMuPDFLoader(PDF_PATH)
    pages = loader.load()
    print(f"Số pages (LangChain): {len(pages)}")
    total_chars_lc = 0
    empty_pages = []
    short_pages = []
    for i, page in enumerate(pages):
        total_chars_lc += len(page.page_content)
        if len(page.page_content) == 0:
            empty_pages.append(i + 1)
        elif len(page.page_content) < 50:
            short_pages.append((i + 1, page.page_content.strip()))
        
        print(f"\n--- Page {i+1} ({len(page.page_content)} chars) ---")
        print(f"Metadata: {page.metadata}")
        preview = page.page_content[:300] if page.page_content else "(TRỐNG)"
        print(preview)
    
    print(f"\n\nTổng ký tự (LangChain): {total_chars_lc}")
    if empty_pages:
        print(f"⚠ TRANG TRỐNG: {empty_pages}")
    if short_pages:
        print(f"⚠ TRANG ÍT NỘI DUNG (<50 chars): {short_pages}")
except Exception as e:
    print(f"LỖI PyMuPDFLoader: {e}")

# ── 3. Kiểm tra chunking ──────────────────────────────────────────────────
print("\n\n[3] KIỂM TRA CHUNKING")
print("-" * 60)
try:
    from rag_engine.chroma_manager import _is_administrative_text, _split_administrative, _split_normal
    
    loader = PyMuPDFLoader(PDF_PATH)
    pages = loader.load()
    
    full_text = "\n".join(p.page_content for p in pages)
    is_admin = _is_administrative_text(full_text)
    print(f"Nhận diện là văn bản hành chính: {is_admin}")
    
    # Thử cả 2 phương pháp chunking
    admin_chunks = _split_administrative(pages)
    normal_chunks = _split_normal(pages)
    
    print(f"\n--- Chunking hành chính ---")
    print(f"Số chunks: {len(admin_chunks)}")
    total_admin_chars = sum(len(c.page_content) for c in admin_chunks)
    print(f"Tổng ký tự: {total_admin_chars}")
    for i, chunk in enumerate(admin_chunks[:5]):
        print(f"\n  Chunk {i+1} ({len(chunk.page_content)} chars):")
        print(f"  {chunk.page_content[:200]}...")
    
    print(f"\n--- Chunking thường ---")
    print(f"Số chunks: {len(normal_chunks)}")
    total_normal_chars = sum(len(c.page_content) for c in normal_chunks)
    print(f"Tổng ký tự: {total_normal_chars}")
    for i, chunk in enumerate(normal_chunks[:5]):
        print(f"\n  Chunk {i+1} ({len(chunk.page_content)} chars):")
        print(f"  {chunk.page_content[:200]}...")
    
    # So sánh tỉ lệ mất mát nội dung
    print(f"\n\n[4] SO SÁNH MẤT MÁT NỘI DUNG")
    print("-" * 60)
    print(f"Full text length: {len(full_text)}")
    print(f"Admin chunks tổng chars: {total_admin_chars} ({total_admin_chars/len(full_text)*100:.1f}%)")
    print(f"Normal chunks tổng chars: {total_normal_chars} ({total_normal_chars/len(full_text)*100:.1f}%)")

    # Kiểm tra chunks trùng/rỗng
    empty_admin = [i for i, c in enumerate(admin_chunks) if len(c.page_content.strip()) < 10]
    empty_normal = [i for i, c in enumerate(normal_chunks) if len(c.page_content.strip()) < 10]
    print(f"\nAdmin chunks rỗng/quá ngắn: {len(empty_admin)}")
    print(f"Normal chunks rỗng/quá ngắn: {len(empty_normal)}")

except Exception as e:
    import traceback
    print(f"LỖI: {e}")
    traceback.print_exc()

# ── 5. Kiểm tra OCR khả năng ───────────────────────────────────────────────
print("\n\n[5] KIỂM TRA CÓ CẦN OCR KHÔNG")
print("-" * 60)
try:
    doc = fitz.open(PDF_PATH)
    for i, page in enumerate(doc):
        text = page.get_text()
        images = page.get_images()
        has_text = len(text.strip()) > 0
        has_images = len(images) > 0
        
        status = ""
        if has_text and not has_images:
            status = "✓ Text-only (OK)"
        elif has_text and has_images:
            status = "⚠ Text + Images (có thể có nội dung trong ảnh)"
        elif not has_text and has_images:
            status = "✗ Image-only (CẦN OCR!)"
        elif not has_text and not has_images:
            status = "✗ Trang trống"
        
        if not has_text or has_images:
            print(f"  Trang {i+1}: {status} | text={len(text)} chars, images={len(images)}")
    
    doc.close()
except Exception as e:
    print(f"LỖI: {e}")

print("\n" + "=" * 80)
print("XONG!")
