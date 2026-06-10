#!/usr/bin/env python3
"""
Batch re-process broken vignette tables through Gemini API.

Identifies vignettes with poorly formatted tables (plain text data,
garbled headers, broken pipe blocks) and sends each one to Gemini
to reformat the case_study_text with proper markdown tables.
"""

import json
import re
import os
import sys
import time
import urllib.request
import urllib.error
import ssl

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

INPUT_PATH = "questions_bank.json"
BACKUP_PATH = "questions_bank.pre_gemini_fix.json"
API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash"


REFORMAT_PROMPT = """You are a precise document formatter. Your task is to take the case study text below and reformat ONLY the tables/exhibits while preserving everything else exactly as-is.

RULES:
1. Convert ALL tabular data into proper markdown pipe tables with correct headers.
2. If a table title/label text was incorrectly split across table columns in the header row, reconstruct the proper column headers.
3. If table data exists as plain text (values separated by spaces without pipe formatting), convert it to a proper markdown pipe table.
4. If narrative/paragraph text was incorrectly placed inside a pipe table, extract it back as normal paragraph text.
5. Preserve ALL non-table text exactly as-is (paragraphs, bullet points, statements, bold formatting, etc.)
6. Keep exhibit labels (e.g., "**Exhibit 1:**") as-is, followed by the properly formatted table.
7. Every table MUST have:
   - A proper header row with meaningful column names
   - A separator row (| :--- | :--- |)
   - Data rows with values in correct columns
8. Use bold (**text**) for row labels in the first column of data rows.
9. DO NOT add, remove, or modify any narrative text, questions, or statements.
10. DO NOT add any explanation or commentary — return ONLY the reformatted case study text.

CASE STUDY TEXT TO REFORMAT:
"""


def identify_broken_vignettes(data):
    """Find vignettes with table formatting issues."""
    broken = []
    
    for i, v in enumerate(data['vignettes']):
        text = v.get('case_study_text', '')
        issues = []
        
        # Check 1: Plain text table data (multiple % or $ values on a line without pipes)
        lines = text.split('\n')
        for l in lines:
            s = l.strip()
            if not s.startswith('|') and not s.startswith('#') and not s.startswith('*'):
                pct_count = len(re.findall(r'\d+\.?\d*%', s))
                money_count = len(re.findall(r'[\$€£][\d,]+|CAD[\d,]+', s))
                if pct_count >= 2 or money_count >= 2:
                    issues.append('plain_text_table')
                    break
        
        # Check 2: Garbled pipe table headers (title split across columns)
        for li, l in enumerate(lines):
            s = l.strip()
            if s.startswith('|') and s.endswith('|') and not re.match(r'^\|\s*:?-', s):
                if li + 1 < len(lines) and re.match(r'^\|\s*:?-', lines[li+1].strip()):
                    cols = [c.strip() for c in s.split('|') if c.strip()]
                    # Too many empty columns
                    if len(cols) > 10:
                        issues.append('oversized_header')
                        break
                    # Check if header cols are just word fragments (not real headers)
                    if len(cols) >= 3:
                        has_numeric = any(re.search(r'\d', c) for c in cols)
                        is_generic = any(kw in ' '.join(cols).lower() for kw in 
                                        ['characteristic', 'value', 'item', 'year', 'maturity',
                                         'rate', 'price', 'return', 'cost', 'ratio'])
                        if not has_numeric and not is_generic:
                            # Join cols — if it reads like a sentence, it's garbled
                            joined = ' '.join(cols)
                            if len(joined) > 60:
                                issues.append('garbled_header')
                                break
        
        # Check 3: Pipe table with narrative text in data cells
        in_table = False
        block = []
        for li, l in enumerate(lines):
            s = l.strip()
            if s.startswith('|') and s.endswith('|'):
                in_table = True
                block.append(s)
            else:
                if in_table and block:
                    # Check for narrative rows
                    data_rows = [r for r in block if not re.match(r'^\|\s*:?-', r)]
                    for r in data_rows[1:]:  # skip header
                        cols = [c.strip() for c in r.split('|') if c.strip()]
                        if len(cols) >= 2:
                            val_cols = cols[1:]
                            all_short_words = all(
                                len(c.replace('**', '').split()) <= 2 and 
                                not re.search(r'\d', c) 
                                for c in val_cols
                            )
                            if all_short_words:
                                issues.append('narrative_in_table')
                                break
                    block = []
                in_table = False
        
        # Check 4: Exhibit reference but no nearby pipe table
        for m in re.finditer(r'\*\*Exhibit\s+\d+', text):
            after = text[m.end():m.end()+500]
            # If there's numeric data but no pipe table within 500 chars
            has_data = bool(re.search(r'\d+\.?\d*%', after))
            has_pipe = bool(re.search(r'\|.*\|', after))
            if has_data and not has_pipe:
                issues.append('exhibit_no_table')
                break
        
        if issues:
            broken.append((i, list(set(issues))))
    
    return broken


def call_gemini_reformat(api_key, case_study_text, vignette_idx, total):
    """Send case study text to Gemini for table reformatting."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    
    request_data = {
        "contents": [
            {
                "parts": [
                    {"text": REFORMAT_PROMPT + case_study_text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192
        }
    }
    
    headers = {"Content-Type": "application/json"}
    req_body = json.dumps(request_data).encode("utf-8")
    req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
    
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as response:
            res_data = response.read().decode("utf-8")
            res_json = json.loads(res_data)
            
            candidates = res_json.get("candidates", [])
            if not candidates:
                return None, "No candidates returned"
            
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return None, "No content parts returned"
            
            reformatted = parts[0].get("text", "")
            if not reformatted.strip():
                return None, "Empty response"
            
            return reformatted.strip(), None
            
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        return None, f"HTTP {e.code}: {error_msg[:200]}"
    except Exception as e:
        return None, str(e)


def validate_reformatted(original, reformatted):
    """Basic validation that reformatted text is reasonable."""
    if not reformatted:
        return False, "Empty"
    
    # Should be roughly similar length (not truncated or massively expanded)
    ratio = len(reformatted) / max(len(original), 1)
    if ratio < 0.3:
        return False, f"Too short (ratio: {ratio:.2f})"
    if ratio > 3.0:
        return False, f"Too long (ratio: {ratio:.2f})"
    
    # Should have pipe tables if original had table data
    if re.search(r'\d+\.?\d*%', original) or re.search(r'Exhibit \d', original):
        if '|' not in reformatted:
            return False, "No pipe tables in output"
    
    return True, "OK"


def main():
    if not API_KEY:
        print("Error: GEMINI_API_KEY not set.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading {INPUT_PATH}...")
    with open(INPUT_PATH, 'r') as f:
        data = json.load(f)
    
    # Create backup
    print(f"Creating backup at {BACKUP_PATH}...")
    with open(BACKUP_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Identify broken vignettes
    broken = identify_broken_vignettes(data)
    print(f"\nFound {len(broken)} vignettes with table issues:")
    for idx, issues in broken[:5]:
        print(f"  Vignette {idx}: {', '.join(issues)}")
    if len(broken) > 5:
        print(f"  ... and {len(broken) - 5} more")
    
    # Process each broken vignette
    fixed = 0
    failed = 0
    skipped = 0
    
    for batch_idx, (vi, issues) in enumerate(broken):
        topic = data['vignettes'][vi].get('topic', 'Unknown')[:60]
        print(f"\n[{batch_idx+1}/{len(broken)}] Vignette {vi}: {topic}")
        print(f"  Issues: {', '.join(issues)}")
        
        original_text = data['vignettes'][vi]['case_study_text']
        
        # Skip very short texts (likely no real tables)
        if len(original_text) < 100:
            print(f"  Skipped (too short)")
            skipped += 1
            continue
        
        # Call Gemini
        reformatted, error = call_gemini_reformat(
            API_KEY, original_text, batch_idx, len(broken)
        )
        
        if error:
            print(f"  ERROR: {error}")
            failed += 1
            continue
        
        # Validate
        is_valid, reason = validate_reformatted(original_text, reformatted)
        if not is_valid:
            print(f"  VALIDATION FAILED: {reason}")
            failed += 1
            continue
        
        # Update
        data['vignettes'][vi]['case_study_text'] = reformatted
        fixed += 1
        print(f"  ✓ Fixed ({len(original_text)} → {len(reformatted)} chars)")
        
        # Rate limiting: small delay between calls
        time.sleep(0.5)
        
        # Save periodically (every 10 fixes)
        if fixed % 10 == 0:
            with open(INPUT_PATH, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  [Checkpoint saved: {fixed} fixes so far]")
    
    # Final save
    print(f"\nSaving final results to {INPUT_PATH}...")
    with open(INPUT_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*50}")
    print(f"RESULTS:")
    print(f"  Total broken vignettes: {len(broken)}")
    print(f"  Successfully fixed:     {fixed}")
    print(f"  Failed:                 {failed}")
    print(f"  Skipped:                {skipped}")
    print(f"  Backup at:              {BACKUP_PATH}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
