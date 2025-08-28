# Import required modules for file operations and document processing
import os
import fitz  # PyMuPDF for PDF text extraction
from docx import Document  # For reading .docx files
import pandas as pd  # For CSV/XLSX reading

def extract_text_from_document(file_path: str) -> str:
    """
    Extract full text from supported document types (.pdf, .docx, .txt, .csv, .xlsx)
    without truncation for complete review.
    """
    import os
    import fitz  # PyMuPDF for PDFs
    from docx import Document
    import pandas as pd

    ext = os.path.splitext(file_path)[1].lower()

    try:
        # PDF: read all pages
        if ext == ".pdf":
            text = ""
            with fitz.open(file_path) as pdf:
                for page in pdf:
                    text += page.get_text()
            return text.strip() or "[No readable text in PDF]"

        # DOCX: join all non-empty paragraphs
        elif ext == ".docx":
            doc = Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return text or "[No readable text in DOCX]"

        # TXT: read entire file
        elif ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read().strip()
            return text or "[Empty TXT file]"

        # CSV: load entire file and convert to string
        elif ext == ".csv":
            df = pd.read_csv(file_path)
            return f"[CSV Content - {len(df)} rows]\n{df.to_string(index=False)}"

        # XLSX: load entire file and convert to string
        elif ext == ".xlsx":
            df = pd.read_excel(file_path)
            return f"[Excel Content - {len(df)} rows]\n{df.to_string(index=False)}"

        else:
            return "[Unsupported file type: only PDF, DOCX, TXT, CSV, XLSX allowed]"

    except Exception as e:
        return f"[Error extracting text: {str(e)}]"
