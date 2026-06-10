#!/usr/bin/env python3
"""
Final pass: clean remaining broken narrative rows from pipe tables.

Strategy: In each pipe block, identify rows where ALL value columns 
(cols after the first) contain only word fragments (no numbers, no %, no $).
Extract those rows as plain text, keep the rest as table.
"""

import json
import re

INPUT_PATH = "questions_bank.json"


def has_data_value(col_text: str) -> bool:
    """Check if a column value looks like actual data (numbers, %, $, etc.)."""
    clean = col_text.replace('**', '').strip()
    if not clean:
        return False
    # Contains percentage
    if re.search(r'\d+\.?\d*%', clean):
        return True
    # Contains dollar/currency amount
    if re.search(r'[\$€£]|CAD|USD|GBP', clean):
        return True
    # Contains a number (standalone or with decimals)
    if re.search(r'\b\d+\.?\d*\b', clean):
        return True
    # Is a year
    if re.match(r'^(19|20)\d{2}$', clean):
        return True
    # Is n/a or similar
    if clean.lower() in ('n/a', 'n/a*', 'na', 'n.a.', '—', '–', '-'):
        return True
    return False


def clean_pipe_blocks(text: str) -> str:
    """Process all pipe blocks, extracting narrative rows as text."""
    lines = text.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('|') and line.endswith('|'):
            # Collect full block
            block = []
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                block.append(lines[i].strip())
                i += 1
            
            # Separate: separator rows, header, data rows, narrative rows
            sep_rows = []
            header = None
            good_rows = []
            bad_rows = []
            
            for j, row in enumerate(block):
                if re.match(r'^\|\s*:?-+', row):
                    sep_rows.append(row)
                    continue
                
                cols = [c.strip() for c in row.split('|')]
                cols = [c for c in cols if c != '']  # strip empty from |...|
                
                if j == 0 and not header:
                    # Check if header itself looks narrative
                    if len(cols) >= 2:
                        val_cols = cols[1:]
                        if all(not has_data_value(c) for c in val_cols):
                            # Header has no data — could be narrative header or table title
                            # Keep as header for now
                            pass
                    header = row
                    continue
                
                # For data rows: check if value columns have actual data
                if len(cols) >= 2:
                    val_cols = cols[1:]
                    if any(has_data_value(c) for c in val_cols):
                        good_rows.append(row)
                    else:
                        bad_rows.append(row)
                else:
                    good_rows.append(row)
            
            # Decide how to output
            if good_rows:
                # Keep good table
                if header:
                    result.append(header)
                for sr in sep_rows:
                    result.append(sr)
                for gr in good_rows:
                    result.append(gr)
                
                # Convert bad rows to text
                if bad_rows:
                    result.append('')
                    narrative_parts = []
                    for br in bad_rows:
                        cols = [c.strip().replace('**', '') for c in br.split('|') if c.strip()]
                        narrative_parts.append(' '.join(cols))
                    result.append(' '.join(narrative_parts))
            elif bad_rows:
                # All narrative — join everything as text
                all_parts = []
                if header:
                    cols = [c.strip().replace('**', '') for c in header.split('|') if c.strip()]
                    all_parts.append(' '.join(cols))
                for br in bad_rows:
                    cols = [c.strip().replace('**', '') for c in br.split('|') if c.strip()]
                    all_parts.append(' '.join(cols))
                result.append(' '.join(all_parts))
            else:
                # Only header + separator (empty table) — keep
                if header:
                    result.append(header)
                for sr in sep_rows:
                    result.append(sr)
        else:
            result.append(lines[i])
            i += 1
    
    return '\n'.join(result)


def main():
    print(f"Loading {INPUT_PATH}...")
    with open(INPUT_PATH, 'r') as f:
        data = json.load(f)
    
    fixed = 0
    for i in range(len(data['vignettes'])):
        original = data['vignettes'][i].get('case_study_text', '')
        fixed_text = clean_pipe_blocks(original)
        if fixed_text != original:
            fixed += 1
        data['vignettes'][i]['case_study_text'] = fixed_text
    
    print(f"Saving to {INPUT_PATH}...")
    with open(INPUT_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults:")
    print(f"  Total vignettes: {len(data['vignettes'])}")
    print(f"  Fixed vignettes: {fixed}")


if __name__ == '__main__':
    main()
