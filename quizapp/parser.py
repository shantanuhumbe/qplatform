import os
import json
import urllib.request
import urllib.error
import ssl
import pypdf

# Bypasses local SSL certificate issues common on macOS
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass
from quizapp.config import PARSER_SYSTEM_INSTRUCTION
from quizapp.models import VignetteList

def extract_text_from_pdf(pdf_path, start_page, end_page):
    """Extracts text from a range of pages (1-indexed, inclusive) from PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")
        
    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    # Adjust to 0-indexed bounds
    start_idx = max(0, start_page - 1)
    end_idx = min(total_pages, end_page)
    
    print(f"  Extracting PDF pages {start_page} to {end_page} (Total pages in doc: {total_pages})...")
    
    extracted_text = []
    for idx in range(start_idx, end_idx):
        page_text = reader.pages[idx].extract_text()
        if page_text:
            extracted_text.append(f"--- Page {idx + 1} ---\n{page_text}")
            
    return "\n\n".join(extracted_text)

def call_gemini_parser_api(api_key, model, text_to_parse, module_name):
    """Sends the extracted text to the Gemini API generateContent REST endpoint with structured outputs."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    prompt = (
        f"Please extract all vignettes and multiple-choice questions from the following text belonging to the module: '{module_name}'.\n"
        "Remember to convert all tabular data to markdown tables, formatting equations as LaTeX, and completely discarding "
        "any vignette or question that is cut off or incomplete at the bounds."
    )
    
    # Build schema payload from Pydantic schema model dynamically
    schema = {
        "type": "OBJECT",
        "properties": {
            "vignettes": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "module": {"type": "STRING"},
                        "topic": {"type": "STRING"},
                        "case_study_text": {"type": "STRING"},
                        "questions": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "question_text": {"type": "STRING"},
                                    "options": {
                                        "type": "ARRAY",
                                        "items": {"type": "STRING"}
                                    },
                                    "correct_answer": {"type": "STRING"},
                                    "official_explanation": {"type": "STRING"}
                                },
                                "required": ["question_text", "options", "correct_answer", "official_explanation"]
                            }
                        }
                    },
                    "required": ["module", "topic", "case_study_text", "questions"]
                }
            }
        },
        "required": ["vignettes"]
    }
    
    request_data = {
        "contents": [
            {
                "parts": [
                    {"text": f"{prompt}\n\nText:\n{text_to_parse}"}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": PARSER_SYSTEM_INSTRUCTION}
            ]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }
    
    headers = {"Content-Type": "application/json"}
    req_body = json.dumps(request_data).encode("utf-8")
    
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            res_data = response.read().decode("utf-8")
            res_json = json.loads(res_data)
            
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini API.")
                
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("No content parts returned from Gemini API.")
                
            raw_text = parts[0].get("text", "")
            parsed_json = json.loads(raw_text)
            
            # Basic validation
            validated = VignetteList(**parsed_json)
            return validated.model_dump().get("vignettes", [])
            
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"API HTTP Error {e.code}: {e.reason}\nDetails: {error_msg}")
        raise e
    except Exception as e:
        print(f"API call failure: {e}")
        raise e

def generate_page_chunks(start_page, end_page, chunk_size, overlap):
    """Generates overlapping page ranges from start_page to end_page."""
    chunks = []
    current_start = start_page
    
    while current_start <= end_page:
        current_end = min(current_start + chunk_size - 1, end_page)
        chunks.append((current_start, current_end))
        if current_end == end_page:
            break
        current_start = current_end - overlap + 1
        
    return chunks

def run_pdf_parsing_pipeline(pdf_path, start_page, end_page, api_key, model, chunk_size, overlap, module_name="Generic Module"):
    """Slices, extracts, calls Gemini API, and aggregates vignettes."""
    chunks = generate_page_chunks(start_page, end_page, chunk_size, overlap)
    print(f"Splitting page range {start_page}-{end_page} into {len(chunks)} overlapping chunks...")
    
    all_vignettes = []
    
    for idx, (c_start, c_end) in enumerate(chunks):
        print(f"Processing chunk {idx + 1}/{len(chunks)} (Pages {c_start} to {c_end})...")
        try:
            chunk_text = extract_text_from_pdf(pdf_path, c_start, c_end)
            if not chunk_text.strip():
                print(f"  Empty chunk text on pages {c_start}-{c_end}, skipping.")
                continue
                
            vignettes = call_gemini_parser_api(api_key, model, chunk_text, module_name)
            print(f"  Successfully parsed {len(vignettes)} vignettes from chunk.")
            
            # Post-process to ensure correct module tag
            for v in vignettes:
                if not v.get("module") or v["module"].lower() == "string":
                    v["module"] = module_name
                    
            all_vignettes.extend(vignettes)
            
        except Exception as e:
            print(f"  Error parsing chunk {c_start}-{c_end}: {e}. Continuing pipeline...")
            
    return all_vignettes
