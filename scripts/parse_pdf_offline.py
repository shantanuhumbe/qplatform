import re
import json
import os
import pypdf

# Define module page mappings
CFA_MODULES = {
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

DEFAULT_PDF_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CFA Combined QB (1).pdf")
DEFAULT_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "questions_bank.json")

def clean_extracted_text(text):
    # Remove page boundary headers
    text = re.sub(r'=== PAGE \d+ ===', '', text)
    # Remove Vikas Vohra page markers
    text = re.sub(r'Faculty:\s*Vikas\s*Vohra\s+Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
    # Remove Learning Module headers
    text = re.sub(r'Learning\s+Module:\s*.*?\n', '', text, flags=re.IGNORECASE)
    # Remove Disclaimer headers
    text = re.sub(r'Disclaimer:\s*Following\s+are\s+the\s+questions.*?\n', '', text, flags=re.IGNORECASE)
    
    # Remove stand-alone line occurrences of any module name
    for m_id, (name, _, _) in CFA_MODULES.items():
        text = re.sub(rf'\n\s*{re.escape(name)}\s*\n', '\n', text, flags=re.IGNORECASE)
        clean_name = name.replace('–', '-').replace('—', '-')
        if clean_name != name:
            text = re.sub(rf'\n\s*{re.escape(clean_name)}\s*\n', '\n', text, flags=re.IGNORECASE)
    return text

def parse_module(reader, m_id, name, start, end):
    print(f"\nProcessing Module {m_id}: {name} (Pages {start}-{end})...", flush=True)
    
    # Extract text from the page range (0-indexed)
    module_text = ""
    for idx in range(start - 1, min(end, len(reader.pages))):
        module_text += f"\n=== PAGE {idx + 1} ===\n" + reader.pages[idx].extract_text()
        
    module_text = module_text.replace('\r', '\n')
    
    # Find Solutions section
    sol_marker_re = re.compile(r'\n\s*(?:Solutions|Answers)\s*\n', re.IGNORECASE)
    sol_match = sol_marker_re.search(module_text)
    
    if sol_match:
        questions_text = module_text[:sol_match.start()]
        solutions_text = "\n" + module_text[sol_match.end():]
    else:
        questions_text = module_text
        solutions_text = ""
        print(f"  Warning: No 'Solutions' section found for Module {m_id}!", flush=True)

    # 1. Parse Vignette headers & ranges
    vignette_re = re.compile(
        r'Vignette\s*\(\s*The\s+following\s+information\s+relates\s+to\s+questions?\s+(\d+)(?:\s*(?:–|—|-|to)\s*(\d+))?\s*\)',
        re.IGNORECASE
    )
    
    raw_vignettes = []
    for match in vignette_re.finditer(questions_text):
        start_q = int(match.group(1))
        end_q = int(match.group(2)) if match.group(2) else start_q
        header = match.group(0)
        start_idx = match.start()
        raw_vignettes.append((start_q, end_q, header, start_idx))
        
    raw_vignettes.sort(key=lambda x: x[3])
    
    vignettes = []
    for idx, (start_q, end_q, header, start_idx) in enumerate(raw_vignettes):
        q_pattern = re.compile(rf'\n\s*{start_q}\.\s+', re.MULTILINE)
        q_match = q_pattern.search(questions_text, start_idx)
        if q_match:
            body_start = start_idx + len(header)
            body_end = q_match.start()
            v_text = questions_text[body_start:body_end].strip()
            
            v_text_clean = clean_extracted_text(v_text)
            v_text_clean = re.sub(r'\n{3,}', '\n\n', v_text_clean).strip()
            
            # Statement formatting: Make bold and put on next line
            v_text_clean = re.sub(
                r'\b(Statement\s+\d+|Reason\s+\d+|Slide\s+\d+|Exhibit\s+\d+|Scenario\s+\d+):\s*\n?',
                r'**\1:**\n',
                v_text_clean,
                flags=re.IGNORECASE
            )
            
            vignettes.append({
                "module": name,
                "topic": f"{name} - Vignette Questions {start_q}-{end_q}" if start_q != end_q else f"{name} - Vignette Question {start_q}",
                "case_study_text": v_text_clean,
                "start_q": start_q,
                "end_q": end_q,
                "questions": []
            })

    # 2. Parse questions
    questions = {}
    q_markers = list(re.finditer(r'\n\s*(\d+)\.\s+', questions_text))
    for idx, q_match in enumerate(q_markers):
        q_num = int(q_match.group(1))
        start_pos = q_match.end()
        end_pos = len(questions_text)
        if idx + 1 < len(q_markers):
            end_pos = q_markers[idx + 1].start()
            
        q_block = questions_text[start_pos:end_pos].strip()
        
        # Parse options
        opt_re = re.compile(r'\n\s*([A-C])\.\s+(.*)')
        opts = opt_re.findall(q_block)
        
        first_opt_match = opt_re.search(q_block)
        if first_opt_match:
            q_text = q_block[:first_opt_match.start()].strip()
        else:
            q_text = q_block
            
        q_text = clean_extracted_text(q_text)
        q_text = re.sub(r'\s+', ' ', q_text).strip()
        
        options_list = []
        for opt_letter, opt_val in opts:
            opt_val = clean_extracted_text(opt_val)
            opt_val = re.sub(r'\s+', ' ', opt_val).strip()
            options_list.append(f"{opt_letter}. {opt_val}")
            
        if options_list:
            questions[q_num] = {
                "question_text": q_text,
                "options": options_list
            }

    # 3. Parse solutions
    solutions = {}
    if solutions_text:
        sol_markers = list(re.finditer(r'\n\s*(\d+)\.\s+([A-C])\s+is\s+correct', solutions_text, re.IGNORECASE))
        for idx, s_match in enumerate(sol_markers):
            s_num = int(s_match.group(1))
            ans_letter = s_match.group(2).upper()
            start_pos = s_match.end()
            end_pos = len(solutions_text)
            if idx + 1 < len(sol_markers):
                end_pos = sol_markers[idx + 1].start()
                
            sol_text = solutions_text[start_pos:end_pos].strip()
            sol_text = re.sub(r'^[\s\.:,]+', '', sol_text).strip()
            
            sol_text = clean_extracted_text(sol_text)
            sol_text = re.sub(r'\s+', ' ', sol_text).strip()
            
            solutions[s_num] = {
                "correct_answer": ans_letter,
                "official_explanation": f"{ans_letter} is correct. {sol_text}"
            }

    # 4. Group questions into vignettes
    used_questions = set()
    for v in vignettes:
        for q_num in range(v["start_q"], v["end_q"] + 1):
            if q_num in questions and q_num in solutions:
                q_data = {
                    "question_text": questions[q_num]["question_text"],
                    "options": questions[q_num]["options"],
                    "correct_answer": solutions[q_num]["correct_answer"],
                    "official_explanation": solutions[q_num]["official_explanation"]
                }
                v["questions"].append(q_data)
                used_questions.add(q_num)
                
    # 5. Handle Standalone questions
    standalone_questions = []
    for q_num in sorted(questions.keys()):
        if q_num not in used_questions and q_num in solutions:
            q_data = {
                "question_text": questions[q_num]["question_text"],
                "options": questions[q_num]["options"],
                "correct_answer": solutions[q_num]["correct_answer"],
                "official_explanation": solutions[q_num]["official_explanation"]
            }
            standalone_questions.append(q_data)
            
    if standalone_questions:
        vignettes.append({
            "module": name,
            "topic": f"{name} - Standalone Practice Questions",
            "case_study_text": "The following are standalone practice questions for this learning module.",
            "questions": standalone_questions
        })
        
    for v in vignettes:
        if "start_q" in v:
            del v["start_q"]
        if "end_q" in v:
            del v["end_q"]
            
    return vignettes

def main():
    pdf = DEFAULT_PDF_PATH
    output = DEFAULT_OUTPUT_PATH
    
    if not os.path.exists(pdf):
        print(f"Error: PDF not found at {pdf}")
        return
        
    print(f"Opening PDF: {pdf}...")
    reader = pypdf.PdfReader(pdf)
    
    all_vignettes = []
    for m_id in sorted(CFA_MODULES.keys()):
        name, start, end = CFA_MODULES[m_id]
        vignettes = parse_module(reader, m_id, name, start, end)
        all_vignettes.extend(vignettes)
        
    print(f"\nSaving {len(all_vignettes)} total vignettes to {output}...")
    with open(output, "w", encoding="utf-8") as f:
        json.dump({"vignettes": all_vignettes}, f, indent=2, ensure_ascii=False)
        
    print("Parsing and extraction complete!")

if __name__ == "__main__":
    main()
