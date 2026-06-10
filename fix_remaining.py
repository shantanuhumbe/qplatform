#!/usr/bin/env python3
"""
Final targeted fix for all remaining broken vignettes.
Directly patches the JSON data for cases the renderer can't auto-fix.
"""
import json, re

INPUT_PATH = "questions_bank.json"

with open(INPUT_PATH, 'r') as f:
    data = json.load(f)

fixes_applied = 0

def fix_vignette(vi, fixer_fn):
    global fixes_applied
    old = data['vignettes'][vi]['case_study_text']
    new = fixer_fn(old)
    if new != old:
        data['vignettes'][vi]['case_study_text'] = new
        fixes_applied += 1
        print(f"  ✓ Fixed vignette {vi}: {data['vignettes'][vi].get('topic','')[:55]}")
    else:
        print(f"  ✗ No change vignette {vi}")

# ─── PATTERN 1: Oversized headers where ALL data is crammed into one row ────────
# e.g. vignette 16: | Title |  |  |  | ... |
#      then next row has ALL values: | Title | val1 | val2 ...all in one row
def fix_crammed_single_row(text):
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        # Detect: pipe row followed by separator followed by one giant row
        if s.startswith('|') and s.endswith('|'):
            block = []
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                block.append(lines[i].strip())
                i += 1
            # Check: header has many empty cols, only 1 data row, and that row is very long
            sep_rows = [r for r in block if re.match(r'^\|\s*:?-+', r)]
            data_rows = [r for r in block if not re.match(r'^\|\s*:?-+', r)]
            if len(sep_rows) == 1 and len(data_rows) == 2:  # header + 1 data row
                header = data_rows[0]
                data_row = data_rows[1]
                header_cols = [c.strip() for c in header.split('|') if c.strip()]
                data_cols = [c.strip() for c in data_row.split('|') if c.strip()]
                # If data row is extremely long (all data crammed in), try to parse it
                if len(data_row) > 200 and len(data_cols) <= 3:
                    # Try to split the crammed data row into proper KV pairs
                    raw = data_cols[0] if data_cols else data_row
                    # Pattern: "Label $val Label2 val2% Label3 val3%"
                    # Split on known separators: dollar amounts, percentages
                    parts = re.split(r'(?=\$[\d\.,]+)|(?<=\d%)\s+(?=[A-Z])|(?<=\d)\s{2,}(?=[A-Z])', raw)
                    if len(parts) >= 2:
                        new_rows = []
                        for part in parts:
                            part = part.strip()
                            # split label from value
                            m = re.match(r'^(.+?)\s+([\$\d][\d\.\,%\s–\-]+)$', part)
                            if m:
                                new_rows.append(f'| **{m.group(1).strip()}** | {m.group(2).strip()} |')
                            elif part:
                                new_rows.append(f'| {part} | |')
                        if new_rows:
                            result.append('| Item | Value |')
                            result.append('| :--- | :--- |')
                            result.extend(new_rows)
                            continue
            result.extend(block)
        else:
            result.append(lines[i])
            i += 1
    return '\n'.join(result)


# ─── PATTERN 2: Split row labels (label split across col1+col2) ─────────────────
# e.g. | **Most Recent** | Year | 3.15 | 1.77 |
# → should be: | **Most Recent Year** | 3.15 | 1.77 |
# Detect: col1 is bold short word, col2 is non-numeric short word, col3+ are numeric
def fix_split_row_labels(text):
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith('|') and s.endswith('|') and not re.match(r'^\|\s*:?-+', s):
            # Check if next line is separator or another pipe
            next_s = lines[i+1].strip() if i+1 < len(lines) else ''
            if re.match(r'^\|\s*:?-+', next_s):
                # This is a header row — skip
                result.append(lines[i])
                i += 1
                continue
            # Check if this is a data row with split label
            cols = [c.strip() for c in s.split('|') if c.strip()]
            if len(cols) >= 4:
                col0_clean = cols[0].replace('**', '').strip()
                col1_clean = cols[1].replace('**', '').strip()
                # col0: short word (1-3 words), col1: short non-numeric word, col2+: numeric
                col0_words = len(col0_clean.split())
                col1_words = len(col1_clean.split())
                col0_has_num = bool(re.search(r'\d', col0_clean))
                col1_has_num = bool(re.search(r'\d', col1_clean))
                col2_has_num = bool(re.search(r'\d', cols[2])) if len(cols) > 2 else False
                
                if (col0_words <= 3 and col1_words <= 2 and 
                    not col0_has_num and not col1_has_num and col2_has_num):
                    # Merge col0 + col1 as combined label
                    merged_label = f'**{col0_clean} {col1_clean}**'
                    rest = ' | '.join(cols[2:])
                    result.append(f'| {merged_label} | {rest} |')
                    i += 1
                    continue
        result.append(lines[i])
        i += 1
    return '\n'.join(result)


# ─── PATTERN 3: Plain text rows below a pipe table (same exhibit) ──────────────
# e.g. after pipe table rows, suddenly:
#   Required rate of return on common equity 8.84% --- 10.48% ---
#   Risk-free rate 2.94%
# These should be additional table rows
def fix_orphan_data_rows(text):
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        # Check: last result line was a pipe row, this line is plain text with numbers
        if result and result[-1].strip().startswith('|') and result[-1].strip().endswith('|'):
            if s and not s.startswith('|') and not s.startswith('**') and not s.startswith('#'):
                pct_count = len(re.findall(r'\d+\.?\d*%', s))
                num_count = len(re.findall(r'\b\d+[\.,]\d+\b', s))
                if pct_count >= 1 or num_count >= 1:
                    # Convert plain text row to pipe row
                    m = re.match(r'^(.+?)\s{2,}([\d\$€£\-–].*)$', s)
                    if not m:
                        m = re.match(r'^(.+?)\s+([\d][\d\.\,%\s\-–]+.*)$', s)
                    if m:
                        label = m.group(1).strip()
                        vals = re.split(r'\s{2,}', m.group(2).strip())
                        vals = [v.strip() for v in vals if v.strip()]
                        # Match column count of table above
                        result.append('| **' + label + '** | ' + ' | '.join(vals) + ' |')
                        i += 1
                        continue
        result.append(lines[i])
        i += 1
    return '\n'.join(result)


# ─── Apply fixes to all vignettes ──────────────────────────────────────────────
print("Applying targeted fixes to all vignettes...")
for vi in range(len(data['vignettes'])):
    old_text = data['vignettes'][vi]['case_study_text']
    
    # Apply pattern fixes in order
    text = fix_split_row_labels(old_text)
    text = fix_orphan_data_rows(text)
    text = fix_crammed_single_row(text)
    
    if text != old_text:
        data['vignettes'][vi]['case_study_text'] = text
        fixes_applied += 1

print(f"\nTotal vignettes fixed: {fixes_applied}")

# ─── Direct fix for vignette 16 specifically ──────────────────────────────────
v16 = data['vignettes'][16]
t16 = v16['case_study_text']
old_block = '| Information About High Growth Stock |  |  |  |  |  |  |  |\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |'
if old_block in t16:
    # Find the giant data row and extract key-value pairs
    giant_row_match = re.search(r'\| Information About High Growth Stock \| Current dividend \| (\$[\d\.]+) Growth rate expected years \| ([\d–\-]+) \| (\d+%) Growth rate expected after year \| (\d+) \| (\d+%) Required rate of return \| (\d+%)', t16)
    if giant_row_match:
        d1, yr, gr1, yr2, gr2, req = giant_row_match.groups()
        new_table = f'''| Item | Value |
| :--- | :--- |
| **Current dividend** | {d1} |
| **Growth rate expected years {yr}** | {gr1} |
| **Growth rate expected after year {yr2}** | {gr2} |
| **Required rate of return** | {req} |'''
        # Replace from old_block through end of giant row
        start_idx = t16.find(old_block)
        # Find end of the giant row
        giant_row_start = t16.find('| Information About High Growth Stock | Current dividend |')
        if giant_row_start != -1:
            giant_row_end = t16.find('\n', giant_row_start)
            if giant_row_end == -1:
                giant_row_end = len(t16)
            # Extract narrative text from inside the giant row
            giant_row_content = t16[giant_row_start:giant_row_end]
            narrative_match = re.search(r'Jackson has been.*$', giant_row_content)
            narrative = narrative_match.group(0).rstrip('|').strip() if narrative_match else ''
            
            new_content = new_table
            if narrative:
                new_content += '\n\n' + narrative
            
            t16_new = t16[:start_idx] + new_content + t16[giant_row_end:]
            data['vignettes'][16]['case_study_text'] = t16_new
            fixes_applied += 1
            print("  ✓ Fixed vignette 16 (crammed data row)")

with open(INPUT_PATH, 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"\nTotal applied: {fixes_applied} fixes. Saved.")
