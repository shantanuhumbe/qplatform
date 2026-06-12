import pdfplumber
import re
import json
import os
import sys

# Define CFA Reading/Module Name lookup
CFA_READING_NAMES = {
    1: "Multiple Regression",
    2: "Time Series Analysis",
    3: "Machine Learning",
    4: "Big Data Projects",
    5: "Currency Exchange Rates: Understanding Equilibrium Value",
    6: "Economic Growth",
    7: "Economics of Regulation",
    8: "Intercorporate Investments",
    9: "Employee Compensation: Post-Employment and Share-Based",
    10: "Multinational Operations",
    11: "Analysis of Financial Institutions",
    12: "Evaluating Quality of Financial Reports",
    13: "Integration of Financial Statement Analysis Techniques",
    14: "Industry and Company Analysis",
    15: "Analysis of Dividends and Share Repurchases",
    16: "Environmental, Social, and Governance (ESG) Considerations in Investment Analysis",
    17: "Cost of Capital: Advanced Topics",
    18: "Corporate Restructuring",
    19: "Equity Valuation: Applications and Processes",
    20: "Discounted Dividend Valuation",
    21: "Free Cash Flow Valuation",
    22: "Market-Based Valuation: Price and Enterprise Value",
    23: "Residual Income Valuation",
    24: "Private Company Valuation",
    25: "Valuation and Analysis of Bonds with Embedded Options",
    26: "The Term Structure and Interest Rate Dynamics",
    27: "The Arbitrage-Free Valuation Framework",
    28: "Credit Analysis Models",
    29: "Credit Default Swaps",
    30: "Pricing and Valuation of Forward Commitments",
    31: "Valuation and Analysis of Option Contracts",
    32: "Introduction to Commodities and Commodity Derivatives",
    33: "Overview of Types of Real Estate Investment",
    34: "Hedge Fund Strategies",
    35: "Exchange-Traded Funds: Mechanics and Applications",
    36: "Using Multifactor Models",
    37: "Measuring and Managing Market Risk",
    38: "Backtesting and Simulation",
    39: "Economics and Investment Markets",
    40: "Analysis of Active Portfolio Management",
    41: "Code of Ethics and Standards of Professional Conduct",
    42: "Guidance for Standards I-VII",
    43: "Guidance for Standards I-VII"
}

PDF_PATH = "/Users/shantanuhumbe/gemini/resume/qbank_merged.pdf"
OUTPUT_PATH = "/Users/shantanuhumbe/gemini/qplatform/qbank_merged.json"

def is_green(color):
    if not color:
        return False
    if len(color) == 3:
        r, g, b = color
        return abs(r - 0.4863) < 0.05 and abs(g - 0.7255) < 0.05 and b < 0.05
    return False

def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fix_ligatures(text):
    if not text:
        return text
    # Replace common words containing ligatures represented as \u0000
    text = text.replace('\u0000rm', 'firm')
    text = text.replace('\u0000rst', 'first')
    text = text.replace('\u0000t', 'fit')
    text = text.replace('\u0000gure', 'figure')
    text = text.replace('\u0000le', 'file')
    text = text.replace('\u0000ow', 'flow')
    text = text.replace('\u0000uid', 'fluid')
    
    # Common mid-word replacements
    text = re.sub(r'coe\u0000cient', 'coefficient', text, flags=re.IGNORECASE)
    text = re.sub(r'di\u0000erent', 'different', text, flags=re.IGNORECASE)
    text = re.sub(r'di\u0000icult', 'difficult', text, flags=re.IGNORECASE)
    text = re.sub(r'e\u0000icient', 'efficient', text, flags=re.IGNORECASE)
    text = re.sub(r'su\u0000icient', 'sufficient', text, flags=re.IGNORECASE)
    text = re.sub(r'de\u0000ned', 'defined', text, flags=re.IGNORECASE)
    text = re.sub(r'de\u0000ne', 'define', text, flags=re.IGNORECASE)
    text = re.sub(r'con\u0000lict', 'conflict', text, flags=re.IGNORECASE)
    text = re.sub(r'in\u0000uence', 'influence', text, flags=re.IGNORECASE)
    text = re.sub(r'in\u0000ation', 'inflation', text, flags=re.IGNORECASE)
    text = re.sub(r'e\u0000ect', 'effect', text, flags=re.IGNORECASE)
    text = re.sub(r'a\u0000ect', 'affect', text, flags=re.IGNORECASE)
    text = re.sub(r'o\u0000ice', 'office', text, flags=re.IGNORECASE)
    text = re.sub(r'bene\u0000t', 'benefit', text, flags=re.IGNORECASE)
    
    text = re.sub(r'signi\u0000cant', 'significant', text, flags=re.IGNORECASE)
    text = re.sub(r'insigni\u0000cant', 'insignificant', text, flags=re.IGNORECASE)
    text = re.sub(r'speci\u0000c', 'specific', text, flags=re.IGNORECASE)
    
    # Context-aware ligature replacements
    def repl_func(m):
        left, right = m.group(1), m.group(2)
        combined = (left + right).lower()
        if combined == 'ic': return left + 'fi' + right   # signi[fi]cant, speci[fi]c
        if combined == 'on': return left + 'fl' + right   # con[fl]ict
        if combined == 'ui': return left + 'ffi' + right  # su[ffi]cient
        if combined == 'ie': return left + 'ffi' + right  # coe[ffi]cient
        if combined == 'ia': return left + 'fi' + right   # bene[fi]ciary
        if combined == 'ir': return left + 'fi' + right   # [fi]rst, [fi]rm
        if combined == 'it': return left + 'fi' + right   # [fi]t, bene[fi]t
        if combined == 'ee': return left + 'ff' + right   # di[ff]erent
        if combined == 'lo': return left + 'i' + right    # portfol[i]o
        if combined == 'fl': return left + 'f' + right    # o[ff]line
        return left + 'f' + right
        
    text = re.sub(r'([a-zA-Z])\u0000([a-zA-Z])', repl_func, text)
    text = text.replace('\u0000', 'f')
    return text

def merge_floating_labels(all_lines):
    pages_dict = {}
    for line in all_lines:
        p = line["page"]
        if p not in pages_dict:
            pages_dict[p] = []
        pages_dict[p].append(line)
        
    merged_all_lines = []
    
    for p_num in sorted(pages_dict.keys()):
        lines = pages_dict[p_num]
        i = 0
        merged_page_lines = []
        
        while i < len(lines):
            text = lines[i]["text"].strip()
            is_label = re.match(r'^([A-C])\s*[\)\.]\s*$', text, re.IGNORECASE)
            
            if is_label and i > 0 and i < len(lines) - 1:
                prev_line = lines[i-1]
                next_line = lines[i+1]
                
                prev_text = prev_line["text"].strip()
                next_text = next_line["text"].strip()
                
                is_prev_header = (
                    prev_text.startswith("Question") or
                    prev_text.startswith("Explanation") or
                    re.match(r'^[A-C][\)\.]', prev_text, re.IGNORECASE)
                )
                is_next_header = (
                    next_text.startswith("Question") or
                    next_text.startswith("Explanation") or
                    re.match(r'^[A-C][\)\.]', next_text, re.IGNORECASE)
                )
                
                if (prev_line.get("min_x0", 0) >= 95 and 
                    next_line.get("min_x0", 0) >= 95 and
                    not is_prev_header and 
                    not is_next_header):
                    
                    has_green = prev_line["has_green"] or lines[i]["has_green"] or next_line["has_green"]
                    
                    merged_page_lines[-1] = {
                        "text": lines[i]["text"] + " " + prev_text + " " + next_text,
                        "has_green": has_green,
                        "page": p_num,
                        "top": prev_line["top"],
                        "min_x0": lines[i]["min_x0"]
                    }
                    i += 2
                    continue
                    
            merged_page_lines.append(lines[i])
            i += 1
            
        merged_all_lines.extend(merged_page_lines)
        
    return merged_all_lines

def parse_pdf():
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF not found at {PDF_PATH}")
        sys.exit(1)
        
    print(f"Opening PDF: {PDF_PATH}...", flush=True)
    
    all_lines = []
    
    with pdfplumber.open(PDF_PATH) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages: {total_pages}", flush=True)
        
        for p_idx in range(total_pages):
            if (p_idx + 1) % 100 == 0 or p_idx == total_pages - 1:
                print(f"  Reading page {p_idx + 1}/{total_pages}...", flush=True)
                
            page = pdf.pages[p_idx]
            
            # Extract green coordinates
            green_y_coords = []
            for c in page.curves:
                if is_green(c.get("non_stroking_color")):
                    y_center = (c["top"] + c["bottom"]) / 2
                    green_y_coords.append(y_center)
            
            # Extract characters and group into lines
            chars = page.chars
            lines_dict = {}
            for char in chars:
                y_val = round(char["top"], 1)
                matched_y = None
                for existing_y in lines_dict.keys():
                    if abs(existing_y - y_val) < 2:
                        matched_y = existing_y
                        break
                if matched_y is None:
                    matched_y = y_val
                    lines_dict[matched_y] = []
                lines_dict[matched_y].append(char)
                
            for y_val, char_list in sorted(lines_dict.items()):
                char_list.sort(key=lambda x: x["x0"])
                line_text = "".join(c["text"] for c in char_list)
                min_top = min(c["top"] for c in char_list)
                max_bottom = max(c["bottom"] for c in char_list)
                min_x0 = min(c["x0"] for c in char_list)
                
                has_green = False
                for gy in green_y_coords:
                    if min_top - 2 <= gy <= max_bottom + 2:
                        has_green = True
                        break
                        
                all_lines.append({
                    "text": line_text,
                    "has_green": has_green,
                    "page": p_idx + 1,
                    "top": min_top,
                    "min_x0": min_x0
                })
                
    all_lines = merge_floating_labels(all_lines)
    print(f"Extracted {len(all_lines)} lines of text after merging floating labels. Parsing questions...", flush=True)
    
    # State Machine to parse lines into questions
    q_header_re = re.compile(r'^Question\s*#\s*(\d+)(?:\s*-\s*(\d+))?\s+of\s+(\d+)', re.IGNORECASE)
    q_id_re = re.compile(r'Question\s*ID:\s*(\d+)', re.IGNORECASE)
    opt_re = re.compile(r'^([A-C])[\)\.]\s*(.*)', re.IGNORECASE)
    mod_re = re.compile(r'\(Module\s+(\d+)\.(\d+)', re.IGNORECASE)
    
    questions = []
    current_question = None
    accumulated_vignette_lines = []
    
    resets = [
        (1, 1), (91, 2), (154, 3), (166, 4), (172, 5), (222, 7), (289, 9), (310, 10), 
        (405, 11), (416, 12), (476, 13), (497, 14), (518, 15), (549, 16), (557, 17), 
        (568, 18), (576, 19), (596, 20), (682, 21), (756, 22), (829, 23), (909, 25), 
        (948, 26), (969, 27), (1013, 28), (1033, 29), (1046, 30), (1094, 31), (1169, 32), 
        (1176, 33), (1191, 34), (1221, 35), (1231, 36), (1254, 37), (1265, 38), (1273, 39), 
        (1289, 40), (1317, 41), (1327, 42), (1352, 42), (1379, 42), (1420, 42), (1448, 42), 
        (1492, 43)
    ]
    
    def get_fallback_module(page_num):
        fallback_mod = 1
        for start_p, mod_num in resets:
            if page_num >= start_p:
                fallback_mod = mod_num
        return fallback_mod

    for line in all_lines:
        text = line["text"]
        header_match = q_header_re.search(text)
        
        if header_match:
            # Save current question if exists
            if current_question:
                questions.append(current_question)
                
            q_num = int(header_match.group(1))
            start_v = q_num
            end_v = q_num
            if header_match.group(2):
                end_v = int(header_match.group(2))
                
            current_question = {
                "q_num": q_num,
                "start_v": start_v,
                "end_v": end_v,
                "q_id": None,
                "question_text_lines": [],
                "options": {"A": [], "B": [], "C": []},
                "explanation_lines": [],
                "correct_answer": None,
                "module_num": None,
                "page": line["page"],
                "vignette_context_text": "\n".join(accumulated_vignette_lines).strip()
            }
            
            accumulated_vignette_lines = []
            
            id_match = q_id_re.search(text)
            if id_match:
                current_question["q_id"] = id_match.group(1)
                
            continue
            
        if current_question:
            id_match = q_id_re.search(text)
            if id_match and not current_question["q_id"]:
                current_question["q_id"] = id_match.group(1)
                continue
                
            opt_match = opt_re.search(text)
            if opt_match:
                opt_letter = opt_match.group(1).upper()
                opt_text = opt_match.group(2)
                current_question["options"][opt_letter].append(opt_text)
                current_question["last_option"] = opt_letter
                
                if line["has_green"]:
                    current_question["correct_answer"] = opt_letter
                continue
                
            if text.strip().lower() == "explanation":
                current_question["last_option"] = None
                current_question["in_explanation"] = True
                continue
                
            if current_question.get("in_explanation"):
                current_question["explanation_lines"].append(text)
                
                # Check for module reference which marks the end of explanation
                mod_match = mod_re.search(text)
                if mod_match:
                    current_question["module_num"] = int(mod_match.group(1))
                    
                    # Reference marks the final line. Set current_question to None
                    questions.append(current_question)
                    current_question = None
            elif current_question.get("last_option"):
                opt_letter = current_question["last_option"]
                current_question["options"][opt_letter].append(text)
                if line["has_green"]:
                    current_question["correct_answer"] = opt_letter
            else:
                if text.strip() and not q_id_re.search(text):
                    current_question["question_text_lines"].append(text)
        else:
            clean_l = text.strip()
            if clean_l and not clean_l.startswith("Question ID:") and not q_header_re.search(clean_l):
                accumulated_vignette_lines.append(text)
                
    if current_question:
        questions.append(current_question)
        
    print(f"Parsed {len(questions)} questions raw. Post-processing and grouping...", flush=True)
    
    # Post-process questions and clean fields
    for q in questions:
        q["question_text"] = fix_ligatures(clean_text(" ".join(q["question_text_lines"])))
        
        # Clean options
        options_list = []
        for letter in ["A", "B", "C"]:
            opt_body = fix_ligatures(clean_text(" ".join(q["options"][letter])))
            options_list.append(f"{letter}. {opt_body}")
        q["options"] = options_list
        
        # Clean explanation
        q["official_explanation"] = fix_ligatures(clean_text(" ".join(q["explanation_lines"])))
        
        # Determine module number
        if not q["module_num"]:
            q["module_num"] = get_fallback_module(q["page"])
            
        # Determine correct answer letter (default to A if not detected)
        if not q["correct_answer"]:
            exp_text = q["official_explanation"].lower()
            if "a is correct" in exp_text or "choice a is correct" in exp_text:
                q["correct_answer"] = "A"
            elif "b is correct" in exp_text or "choice b is correct" in exp_text:
                q["correct_answer"] = "B"
            elif "c is correct" in exp_text or "choice c is correct" in exp_text:
                q["correct_answer"] = "C"
            else:
                q["correct_answer"] = "A"
                
        q.pop("question_text_lines", None)
        q.pop("explanation_lines", None)
        q.pop("last_option", None)
        q.pop("in_explanation", None)
        
    # Sequential grouping of questions
    grouped_items = []
    current_group = []
    current_group_end_v = None
    current_group_module = None

    for q in questions:
        is_same_vignette = (
            current_group and
            q["module_num"] == current_group_module and
            q["end_v"] == current_group_end_v
        )
        
        if is_same_vignette:
            current_group.append(q)
        else:
            if current_group:
                # Determine if group is vignette based on length or context
                longest_context = ""
                for gq in current_group:
                    ctx = gq.get("vignette_context_text", "")
                    if len(ctx) > len(longest_context):
                        longest_context = ctx
                is_vignette = (len(current_group) > 1 or len(longest_context) > 100) and len(longest_context.strip()) > 10
                
                grouped_items.append({
                    "type": "vignette" if is_vignette else "standalone",
                    "module": current_group_module,
                    "questions": current_group
                })
            current_group = [q]
            current_group_end_v = q["end_v"]
            current_group_module = q["module_num"]

    if current_group:
        longest_context = ""
        for gq in current_group:
            ctx = gq.get("vignette_context_text", "")
            if len(ctx) > len(longest_context):
                longest_context = ctx
        is_vignette = (len(current_group) > 1 or len(longest_context) > 100) and len(longest_context.strip()) > 10
        grouped_items.append({
            "type": "vignette" if is_vignette else "standalone",
            "module": current_group_module,
            "questions": current_group
        })

    vignettes_list = []
    from collections import defaultdict
    module_standalones = defaultdict(list)

    for item in grouped_items:
        m_num = item["module"]
        module_name = CFA_READING_NAMES.get(m_num, f"Module {m_num}")
        
        if item["type"] == "vignette":
            group = item["questions"]
            longest_context = ""
            for q in group:
                ctx = q.get("vignette_context_text", "")
                if len(ctx) > len(longest_context):
                    longest_context = ctx
                    
            v_questions = []
            for q in group:
                v_questions.append({
                    "question_text": q["question_text"],
                    "options": q["options"],
                    "correct_answer": q["correct_answer"],
                    "official_explanation": q["official_explanation"]
                })
                
            case_study = fix_ligatures(longest_context)
            case_study = re.sub(
                r'\b(Statement\s+\d+|Reason\s+\d+|Slide\s+\d+|Exhibit\s+\d+|Scenario\s+\d+):\s*\n?',
                r'**\1:**\n',
                case_study,
                flags=re.IGNORECASE
            )
            
            start_v = group[0]["q_num"]
            end_v = group[-1]["q_num"]
            topic = f"{module_name} - Vignette Questions {start_v}-{end_v}" if start_v != end_v else f"{module_name} - Vignette Question {start_v}"
            
            vignettes_list.append({
                "module": module_name,
                "topic": topic,
                "case_study_text": case_study,
                "questions": v_questions
            })
        else:
            for q in item["questions"]:
                module_standalones[module_name].append({
                    "question_text": q["question_text"],
                    "options": q["options"],
                    "correct_answer": q["correct_answer"],
                    "official_explanation": q["official_explanation"]
                })

    for module_name, standalone_qs in sorted(module_standalones.items()):
        if standalone_qs:
            vignettes_list.append({
                "module": module_name,
                "topic": f"{module_name} - Standalone Practice Questions",
                "case_study_text": "The following are standalone practice questions for this learning module.",
                "questions": standalone_qs
            })
            
    print(f"Saving {len(vignettes_list)} grouped vignettes to {OUTPUT_PATH}...", flush=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"vignettes": vignettes_list}, f, indent=2, ensure_ascii=False)
        
    print("Parsing and extraction complete!", flush=True)

if __name__ == "__main__":
    parse_pdf()
