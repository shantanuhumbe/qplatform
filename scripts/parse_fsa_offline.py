import re
import json
import os
import sys
import shutil
import pypdf

# Setup paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
PDF_PATH = os.path.join(BASE_DIR, "CFAL2 Combined_FSA QB 2.pdf")
OUTPUT_PATH = os.path.join(BASE_DIR, "questions_bank.json")
BACKUP_PATH = os.path.join(BASE_DIR, "questions_bank.json.bak")

FSA_MODULES = {
    1: ("Intercorporate Investments", 1, 37),
    2: ("Employee Compensation: Post-Employment and Share-Based", 38, 51),
    3: ("Multinational Operations", 52, 103),
    4: ("Analysis of Financial Institutions", 104, 135),
    5: ("Evaluating Quality of Financial Reports", 136, 161),
    6: ("Integration of Financial Statement Analysis Techniques", 162, 177)
}

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
    for m_id, (name, _, _) in FSA_MODULES.items():
        text = re.sub(rf'\n\s*{re.escape(name)}\s*\n', '\n', text, flags=re.IGNORECASE)
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
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF not found at {PDF_PATH}")
        return
        
    # 1. Create database backup
    if os.path.exists(OUTPUT_PATH):
        print(f"Creating backup at: {BACKUP_PATH}")
        shutil.copy2(OUTPUT_PATH, BACKUP_PATH)
        
    print(f"Opening PDF: {PDF_PATH}...")
    reader = pypdf.PdfReader(PDF_PATH)
    
    all_new_vignettes = []
    for m_id in sorted(FSA_MODULES.keys()):
        name, start, end = FSA_MODULES[m_id]
        vignettes = parse_module(reader, m_id, name, start, end)
        all_new_vignettes.extend(vignettes)
        
    # 2. Merge with existing database
    from quizapp.utils.data_manager import load_questions_bank, save_questions_bank, merge_vignettes
    existing_data = load_questions_bank(OUTPUT_PATH)
    
    # Load default format
    existing_vignettes = existing_data
    
    # Merge vignettes
    merged_vignettes, added = merge_vignettes(existing_vignettes, all_new_vignettes)
    
    # Save final Q-bank
    save_questions_bank(OUTPUT_PATH, merged_vignettes)
    print(f"\nMigration complete! Successfully added {added} new FSA vignettes. Total: {len(merged_vignettes)}")

if __name__ == "__main__":
    main()
