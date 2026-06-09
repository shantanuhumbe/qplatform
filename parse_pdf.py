import os
import sys
import json
import argparse
import pypdf
import urllib.request
import urllib.error

# Mapping of the 30 modules to their starting and ending pages in the PDF (1-indexed)
MODULE_PAGES = {
    1: ("Equity Valuation: Applications and Processes", 1, 16),
    2: ("Discounted Dividend Valuation", 17, 63),
    3: ("Free Cash Flow Valuation", 64, 101),
    4: ("Market-Based Valuation: Price and Enterprise Value", 102, 135),
    5: ("Residual Income Valuation", 136, 167),
    6: ("Private Company Valuation", 168, 196),
    7: ("Code of Ethics and Standards of Professional Conduct", 197, 208),
    8: ("Guidance for Standards I–VII", 209, 274),
    9: ("Application of the Code and Standards: Level II", 275, 282),
    10: ("The Term Structure and Interest Rate Dynamics", 283, 318),
    11: ("The Arbitrage-Free Valuation Framework", 319, 353),
    12: ("Valuation and Analysis of Bonds with Embedded Options", 354, 400),
    13: ("Credit Analysis Models", 401, 452),
    14: ("Credit Default Swaps", 453, 474),
    15: ("Economics and Investment Markets", 475, 502),
    16: ("Analysis of Active Portfolio Management", 503, 538),
    17: ("Exchange-Traded Funds: Mechanics and Applications", 539, 556),
    18: ("Using Multifactor Models", 557, 585),
    19: ("Measuring and Managing Market Risk", 586, 620),
    20: ("Backtesting and Simulation", 621, 637),
    21: ("Introduction to Commodities and Commodity Derivatives", 638, 665),
    22: ("Overview of Types of Real Estate Investment", 666, 677),
    23: ("Investments in Real Estate through Publicly Traded", 678, 696),
    24: ("Hedge Fund Strategies", 697, 727),
    25: ("Analysis of Dividends and Share Repurchases", 728, 754),
    26: ("Environmental, Social, and Governance (ESG)", 755, 768),
    27: ("Cost of Capital: Advanced Topics", 769, 780),
    28: ("Corporate Restructuring", 781, 894),
    29: ("Currency Exchange Rates: Understanding Equilibrium Value", 895, 943),
    30: ("Economic Growth", 944, 980),
}

RESPONSE_SCHEMA = {
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

def extract_text_from_pdf(pdf_path, start_page, end_page):
    """Extracts text from a range of pages (1-indexed, inclusive)"""
    reader = pypdf.PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    # Adjust to 0-indexed bounds
    start_idx = max(0, start_page - 1)
    end_idx = min(total_pages, end_page)
    
    print(f"Reading pages {start_page} to {end_page} from PDF...")
    extracted_text = []
    for idx in range(start_idx, end_idx):
        page_text = reader.pages[idx].extract_text()
        if page_text:
            extracted_text.append(f"--- Page {idx + 1} ---\n{page_text}")
            
    return "\n\n".join(extracted_text)

def call_gemini_api(api_key, model, prompt, text_to_parse):
    """Calls the Gemini API generateContent endpoint with Structured Outputs JSON schema"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    system_instruction = (
        "You are an expert CFA curriculum content parser. Extract all vignettes (case studies) and "
        "their associated multiple-choice questions from the following text extracted from the CFA question bank.\n"
        "Each vignette starts with background information (typically 'Vignette (The following information relates to questions X-Y)').\n"
        "Ensure that every question has exactly 3 options (A, B, C) as per CFA Level II/III format, a correct letter answer (A, B, or C), "
        "and the official explanation or answer rationale.\n"
        "Generate a structured JSON response matching the provided schema."
    )
    
    full_prompt = f"{prompt}\n\nText to parse:\n{text_to_parse}"
    
    request_data = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ],
        "systemInstruction": {
            "parts": [
                {"text": system_instruction}
            ]
        },
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA
        }
    }
    
    headers = {"Content-Type": "application/json"}
    req_body = json.dumps(request_data).encode("utf-8")
    
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode("utf-8")
            res_json = json.loads(res_data)
            
            # Extract text content from response
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini API.")
                
            candidate = candidates[0]
            parts = candidate.get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("No text content returned from Gemini API.")
                
            raw_text = parts[0].get("text", "")
            return json.loads(raw_text)
            
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"HTTP Error: {e.code} - {e.reason}\nDetails: {error_msg}", file=sys.stderr)
        raise e
    except Exception as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        raise e

def save_to_questions_bank(output_path, new_vignettes):
    """Loads existing questions bank if it exists, merges new vignettes, and saves"""
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Warning: Could not read existing questions bank ({e}). Starting fresh.")
            data = {"vignettes": []}
    else:
        data = {"vignettes": []}
        
    existing_topics = {v["topic"].strip().lower() for v in data["vignettes"]}
    
    merged_count = 0
    for vignette in new_vignettes:
        # Avoid duplicate topics
        topic_key = vignette["topic"].strip().lower()
        if topic_key not in existing_topics:
            data["vignettes"].append(vignette)
            existing_topics.add(topic_key)
            merged_count += 1
            
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved. Added {merged_count} new vignettes. Total in bank: {len(data['vignettes'])}")

def main():
    parser = argparse.ArgumentParser(description="Parse CFA PDF questions using Gemini Structured Outputs")
    parser.add_argument("--pdf", default="/Users/shantanuhumbe/gemini/qplatform/CFA Combined QB (1).pdf", help="Path to PDF")
    parser.add_argument("--output", default="/Users/shantanuhumbe/gemini/qplatform/questions_bank.json", help="Path to output JSON")
    parser.add_argument("--module", type=int, choices=range(1, 31), help="Parse a specific learning module (1 to 30)")
    parser.add_argument("--pages", help="Parse specific page range (e.g. 1-16)")
    parser.add_argument("--api-key", help="Gemini API Key (overrides GEMINI_API_KEY environment variable)")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model to use (default: gemini-2.5-flash)")
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: Gemini API Key is required. Set GEMINI_API_KEY environment variable or pass --api-key.", file=sys.stderr)
        sys.exit(1)
        
    # Resolve page range
    module_name = "Custom Page Range"
    if args.module:
        module_name, start_page, end_page = MODULE_PAGES[args.module]
        print(f"Selected Module {args.module}: {module_name} (Pages {start_page} to {end_page})")
    elif args.pages:
        try:
            start_page, end_page = map(int, args.pages.split("-"))
        except ValueError:
            print("Error: Invalid pages format. Use 'start-end', e.g., '1-16'.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: You must specify either --module [1-30] or --pages [start-end].", file=sys.stderr)
        sys.exit(1)
        
    # Extract text from PDF
    try:
        text_to_parse = extract_text_from_pdf(args.pdf, start_page, end_page)
    except Exception as e:
        print(f"Error reading PDF: {e}", file=sys.stderr)
        sys.exit(1)
        
    if not text_to_parse.strip():
        print("Error: No text extracted from PDF page range.", file=sys.stderr)
        sys.exit(1)
        
    prompt = (
        f"Please extract all vignettes and multiple-choice questions from the following text belonging to the module: '{module_name}'.\n"
        "Ensure all details like question text, multiple choice options (A, B, C), the correct option, and explanation are fully captured."
    )
    
    print(f"Sending text to Gemini API ({args.model})...")
    try:
        parsed_result = call_gemini_api(api_key, args.model, prompt, text_to_parse)
        vignettes = parsed_result.get("vignettes", [])
        print(f"Successfully parsed {len(vignettes)} vignettes from Gemini.")
        
        # Inject the module name if missing or generic
        for v in vignettes:
            if not v.get("module") or v["module"].lower() == "string":
                v["module"] = module_name
                
        # Save to database
        save_to_questions_bank(args.output, vignettes)
        
    except Exception as e:
        print(f"Failed to parse and save content: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
