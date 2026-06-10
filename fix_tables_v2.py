#!/usr/bin/env python3
"""
Targeted deep fix for broken tables in questions_bank.json.

This script handles the harder cases that simple heuristics miss:
1. Multi-line plain text tables (header words split across lines)
2. Mixed tables where real data rows + narrative text are in the same pipe block
3. 3-column pipe blocks where col2+col3 are short fragments (broken narrative)
"""

import json
import re
import copy

INPUT_PATH = "questions_bank.json"


def fix_mixed_pipe_blocks(text: str) -> str:
    """
    Fix pipe-table blocks that mix real data rows and broken narrative rows.
    
    Pattern:
    | **Monte Carlo simulation** | 0.026% | 0.501% |   ← GOOD data row
    | **Hamilton elects to apply...** | risk | assessment | ← BAD narrative row
    
    Strategy: Split the block — keep good data rows as table, extract bad ones as text.
    """
    lines = text.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('|') and line.endswith('|'):
            # Collect full pipe block
            block = []
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                block.append(lines[i].strip())
                i += 1
            
            # Classify each row
            separator_rows = []
            data_rows = []
            narrative_rows = []
            header_row = None
            
            for j, row in enumerate(block):
                if re.match(r'^\|\s*:?-+', row):
                    separator_rows.append((j, row))
                    continue
                
                cols = [c.strip() for c in row.split('|')]
                cols = [c for c in cols if c]  # remove empty from leading/trailing |
                
                if j == 0:
                    header_row = (j, row)
                    continue
                
                # Classify: does this row have numeric data (%, $, numbers)?
                row_text = ' '.join(cols)
                has_pct = bool(re.search(r'\d+\.?\d*%', row_text))
                has_dollar = bool(re.search(r'[\$€£]|CAD', row_text))
                has_numbers = len(re.findall(r'\b\d+[\.,]?\d*\b', row_text)) >= 2
                
                # Check if second+ columns are short word fragments (narrative indicator)
                if len(cols) >= 2:
                    short_fragments = sum(1 for c in cols[1:] if len(c.replace('**','').split()) <= 2)
                    total_value_cols = len(cols) - 1
                    
                    if has_pct or has_dollar:
                        data_rows.append((j, row))
                    elif short_fragments == total_value_cols and not has_numbers:
                        narrative_rows.append((j, row))
                    else:
                        data_rows.append((j, row))
                else:
                    data_rows.append((j, row))
            
            # Rebuild: if there's a mix, separate them
            if narrative_rows and data_rows:
                # Output good data table first
                if header_row:
                    result.append(header_row[1])
                for _, row in separator_rows:
                    result.append(row)
                for _, row in data_rows:
                    result.append(row)
                result.append('')  # blank line
                
                # Output narrative as plain text
                narrative_text = []
                for _, row in narrative_rows:
                    cols = [c.strip().replace('**', '') for c in row.split('|') if c.strip()]
                    narrative_text.append(' '.join(cols))
                result.append(' '.join(narrative_text))
            elif narrative_rows and not data_rows:
                # All narrative — convert to plain text
                all_text = []
                if header_row:
                    cols = [c.strip().replace('**', '') for c in header_row[1].split('|') if c.strip()]
                    all_text.append(' '.join(cols))
                for _, row in narrative_rows:
                    cols = [c.strip().replace('**', '') for c in row.split('|') if c.strip()]
                    all_text.append(' '.join(cols))
                result.append(' '.join(all_text))
            else:
                # All data rows — keep as-is
                for row in block:
                    result.append(row)
        else:
            result.append(lines[i])
            i += 1
    
    return '\n'.join(result)


def fix_multiline_plain_tables(text: str) -> str:
    """
    Fix plain text exhibit tables where headers and data are split across lines.
    
    Pattern:
        **Exhibit 1:**
        Title
        <blank>
        HeaderWord1
        HeaderWord2
        ...
        Label1 Val1 Val2 Val3
        Label2 (multiline)
        continuation
        Val1 Val2 Val3
    """
    lines = text.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for exhibit pattern followed by plain text data
        if re.match(r'\*?\*?Exhibit\s+\d+\*?\*?\s*:?\*?\*?\s*$', line, re.IGNORECASE):
            result.append(lines[i])
            exhibit_start = i
            i += 1
            
            # Collect lines until we hit another section or pipe table
            collect = []
            while i < len(lines):
                next_line = lines[i].strip()
                # Stop at: another exhibit, a pipe table, or a very long narrative paragraph
                if re.match(r'\*?\*?Exhibit\s+\d+', next_line, re.IGNORECASE) and i > exhibit_start + 1:
                    break
                if next_line.startswith('|'):
                    break
                # Stop if we hit a long narrative sentence (>100 chars without numbers)
                if len(next_line) > 100 and not re.search(r'\d+\.?\d*%', next_line):
                    break
                collect.append(lines[i])
                i += 1
            
            # Analyze collected lines: try to find data rows
            data_line_indices = []
            for j, cl in enumerate(collect):
                stripped = cl.strip()
                pct_count = len(re.findall(r'\d+\.?\d*%', stripped))
                money_count = len(re.findall(r'[\$€£][\d,]+|CAD[\d,]+', stripped))
                num_count = len(re.findall(r'\b\d+[\.,]\d+\b', stripped))
                
                if pct_count >= 2 or money_count >= 1 or (pct_count >= 1 and num_count >= 1):
                    data_line_indices.append(j)
            
            if len(data_line_indices) >= 2:
                # We have data rows — try to build a table
                # Everything before first data row is header/title
                first_data = data_line_indices[0]
                header_lines = [cl.strip() for cl in collect[:first_data] if cl.strip()]
                
                # Parse data rows
                parsed = []
                for j in data_line_indices:
                    dl = collect[j].strip()
                    # Handle multi-line labels: check if previous line is a label fragment
                    label_prefix = ''
                    if j > 0 and j-1 not in data_line_indices:
                        prev = collect[j-1].strip()
                        if prev and not re.search(r'\d+\.?\d*%', prev):
                            label_prefix = prev + ' '
                    
                    match = re.match(r'^(.+?)\s{2,}([\d\$€£C].*)', dl)
                    if not match:
                        match = re.match(r'^(.+?)\s+([\d][\d\.\,\$%\s]+)$', dl)
                    
                    if match:
                        label = label_prefix + match.group(1).strip()
                        vals = re.split(r'\s{2,}|\s+(?=\d)', match.group(2).strip())
                        vals = [v.strip() for v in vals if v.strip()]
                        parsed.append([label] + vals)
                    else:
                        parsed.append([label_prefix + dl])
                
                if parsed:
                    max_cols = max(len(r) for r in parsed)
                    if max_cols >= 2:
                        # Build markdown table
                        # Use header lines as title context
                        title = ' '.join(header_lines) if header_lines else ''
                        if title:
                            result.append(title)
                            result.append('')
                        
                        # Create header
                        headers = [''] * max_cols
                        headers[0] = 'Item'
                        for hi in range(1, max_cols):
                            headers[hi] = f'Value {hi}' if max_cols > 2 else 'Value'
                        
                        result.append('| ' + ' | '.join(headers) + ' |')
                        result.append('| ' + ' | '.join([':---'] * max_cols) + ' |')
                        
                        for row in parsed:
                            while len(row) < max_cols:
                                row.append('')
                            result.append('| ' + ' | '.join(row) + ' |')
                        result.append('')
                        continue
            
            # Couldn't parse as table — keep original lines
            result.extend(collect)
        else:
            result.append(lines[i])
            i += 1
    
    return '\n'.join(result)


def remove_duplicate_text_blocks(text: str) -> str:
    """
    Remove duplicate paragraphs that sometimes appear when narrative was
    extracted from broken tables but the original text also remains.
    """
    lines = text.split('\n')
    result = []
    seen_blocks = set()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # For long lines (likely extracted narrative), check for near-duplicates
        if len(line) > 150:
            # Normalize for comparison
            normalized = re.sub(r'\s+', ' ', line.lower().strip())
            # Check if this content already appears in previous lines
            is_dup = False
            # Check if a significant portion appears in nearby previous content
            for prev_line in result[-20:]:
                prev_norm = re.sub(r'\s+', ' ', prev_line.lower().strip())
                if len(prev_norm) > 50:
                    # Check overlap
                    overlap = len(set(normalized.split()) & set(prev_norm.split()))
                    min_words = min(len(normalized.split()), len(prev_norm.split()))
                    if min_words > 0 and overlap / min_words > 0.7:
                        is_dup = True
                        break
            
            if is_dup:
                i += 1
                continue
        
        result.append(lines[i])
        i += 1
    
    return '\n'.join(result)


def main():
    print(f"Loading {INPUT_PATH}...")
    with open(INPUT_PATH, 'r') as f:
        data = json.load(f)
    
    fixed_mixed = 0
    fixed_plain = 0
    fixed_dup = 0
    total = len(data['vignettes'])
    
    for i in range(total):
        original = data['vignettes'][i].get('case_study_text', '')
        
        # Pass 1: Fix mixed pipe blocks (data + narrative in same table)
        text = fix_mixed_pipe_blocks(original)
        if text != original:
            fixed_mixed += 1
        
        # Pass 2: Fix multi-line plain text tables
        text2 = fix_multiline_plain_tables(text)
        if text2 != text:
            fixed_plain += 1
        
        # Pass 3: Remove duplicate text blocks
        text3 = remove_duplicate_text_blocks(text2)
        if text3 != text2:
            fixed_dup += 1
        
        data['vignettes'][i]['case_study_text'] = text3
    
    print(f"Saving to {INPUT_PATH}...")
    with open(INPUT_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults:")
    print(f"  Total vignettes: {total}")
    print(f"  Fixed mixed pipe blocks: {fixed_mixed}")
    print(f"  Fixed multi-line plain tables: {fixed_plain}")
    print(f"  Removed duplicate blocks: {fixed_dup}")


if __name__ == '__main__':
    main()
