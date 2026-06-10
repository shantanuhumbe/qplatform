#!/usr/bin/env python3
"""
Fix broken table formatting in questions_bank.json.

Two issues are addressed:
1. Narrative text incorrectly forced into markdown pipe tables
   → Convert back to plain paragraph text.
2. Actual tabular exhibit data left as unformatted plain text
   → Convert into proper markdown pipe tables.
"""

import json
import re
import copy
import os

INPUT_PATH = "questions_bank.json"
BACKUP_PATH = "questions_bank.backup.json"


def fix_broken_pipe_narrative(text: str) -> str:
    """
    Fix #1: Detect pipe-table blocks where narrative text was incorrectly
    shoved into a 2-column table. Convert back to plain paragraphs.
    
    Heuristic: A pipe-table row is "broken narrative" if:
      - It has exactly 2 data columns
      - The first column is very long (>60 chars) or starts with bold narrative
      - The second column is short (a sentence fragment like "the", "risk.", "-average")
    """
    lines = text.split('\n')
    result_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if we're entering a pipe table block
        if line.startswith('|') and line.endswith('|'):
            # Collect the full table block
            table_block = []
            block_start = i
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                table_block.append(lines[i].strip())
                i += 1
            
            # Analyze: is this a broken narrative table?
            if is_broken_narrative_table(table_block):
                # Convert back to paragraph text
                paragraph = extract_narrative_from_pipes(table_block)
                result_lines.append(paragraph)
            else:
                # Keep the table as-is
                result_lines.extend(table_block)
        else:
            result_lines.append(lines[i])
            i += 1
    
    return '\n'.join(result_lines)


def is_broken_narrative_table(table_block: list) -> bool:
    """Check if a pipe table block is actually narrative text incorrectly formatted."""
    if len(table_block) < 3:
        return False
    
    # Skip separator row (| :--- | :--- |)
    data_rows = [r for r in table_block if not re.match(r'^\|\s*:?-+:?\s*\|', r)]
    
    if not data_rows:
        return False
    
    # Check the first row (header) — if it has very long content, it's likely narrative
    first_row = data_rows[0]
    cols = [c.strip() for c in first_row.split('|') if c.strip()]
    
    # If 2 columns and first column is very long (>70 chars) → likely narrative
    if len(cols) == 2:
        narrative_indicators = 0
        for row in data_rows[1:]:  # Skip header
            row_cols = [c.strip() for c in row.split('|') if c.strip()]
            if len(row_cols) == 2:
                col1 = row_cols[0].replace('**', '').strip()
                col2 = row_cols[1].strip()
                # Second column is a short fragment (1-3 words)
                if len(col2.split()) <= 3 and len(col1) > 40:
                    narrative_indicators += 1
        
        # If most rows look like broken narrative
        if narrative_indicators >= len(data_rows) * 0.5:
            return True
    
    return False


def extract_narrative_from_pipes(table_block: list) -> str:
    """Extract narrative text from a broken pipe table, joining columns back."""
    parts = []
    for row in table_block:
        # Skip separator rows
        if re.match(r'^\|\s*:?-+', row):
            continue
        cols = [c.strip().replace('**', '') for c in row.split('|') if c.strip()]
        joined = ' '.join(cols)
        parts.append(joined)
    
    return ' '.join(parts)


def fix_plain_text_exhibits(text: str) -> str:
    """
    Fix #2: Find exhibit data that is unformatted plain text and convert
    to proper markdown tables.
    
    Pattern detected:
        **Exhibit N:**
        Title Line
        Header1
        Header2  
        ...
        Row1_Label Value1 Value2 ...
        Row2_Label Value1 Value2 ...
    """
    # Pattern: lines of data after Exhibit header, where values contain % or $ or numbers
    # We'll use a targeted approach for the most common patterns
    
    lines = text.split('\n')
    result_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect exhibit header pattern
        exhibit_match = re.match(r'\*?\*?Exhibit\s+(\d+)\*?\*?\s*:?\s*$', line, re.IGNORECASE)
        if not exhibit_match:
            # Also try: "**Exhibit N:**"
            exhibit_match = re.match(r'\*\*Exhibit\s+(\d+):\*\*\s*$', line, re.IGNORECASE)
        
        if exhibit_match:
            # Found exhibit header — collect subsequent lines to see if they form a plain text table
            result_lines.append(lines[i])
            i += 1
            
            # Skip blank lines and title line
            title_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('|'):
                stripped = lines[i].strip()
                # Check if this line contains tabular data (multiple % values or $ amounts)
                pct_count = len(re.findall(r'\d+\.?\d*%', stripped))
                dollar_count = len(re.findall(r'[\$€£][\d,]+', stripped))
                num_count = len(re.findall(r'\b\d+\.\d+\b', stripped))
                
                if pct_count >= 2 or dollar_count >= 2 or (pct_count >= 1 and num_count >= 1):
                    # This looks like a data row — try to parse the table
                    # First, collect all potential header lines above
                    table_data_lines = [stripped]
                    i += 1
                    while i < len(lines):
                        next_stripped = lines[i].strip()
                        if not next_stripped:
                            break
                        next_pct = len(re.findall(r'\d+\.?\d*%', next_stripped))
                        next_dollar = len(re.findall(r'[\$€£C][\$€£A-Z]*[\d,]+', next_stripped))
                        next_num = len(re.findall(r'\b\d+[\.,]\d+\b', next_stripped))
                        if next_pct >= 1 or next_dollar >= 1 or next_num >= 1:
                            table_data_lines.append(next_stripped)
                            i += 1
                        else:
                            break
                    
                    # Try to format as markdown table
                    md_table = try_format_as_table(title_lines, table_data_lines)
                    if md_table:
                        result_lines.append(md_table)
                    else:
                        # Couldn't format — keep original
                        result_lines.extend(title_lines)
                        result_lines.extend(table_data_lines)
                    break
                else:
                    title_lines.append(lines[i])
                    i += 1
            else:
                # No table data found after exhibit header
                result_lines.extend(title_lines)
        else:
            result_lines.append(lines[i])
            i += 1
    
    return '\n'.join(result_lines)


def try_format_as_table(header_lines: list, data_lines: list) -> str:
    """
    Attempt to parse plain text header + data lines into a markdown table.
    Returns markdown table string or None if can't parse reliably.
    """
    if not data_lines:
        return None
    
    # Simple approach: split data rows by detecting where numbers/percentages start
    # This handles patterns like: "India government securities 50% 0.015% 0.206%"
    parsed_rows = []
    for dl in data_lines:
        # Split into label + values
        # Find where numeric data starts
        match = re.match(r'^(.+?)\s+([\d\$€£C].*)', dl)
        if match:
            label = match.group(1).strip()
            values_str = match.group(2).strip()
            # Split values by whitespace
            values = re.split(r'\s{2,}|\s+(?=[\d\$€£C])', values_str)
            # Clean up
            values = [v.strip() for v in values if v.strip()]
            parsed_rows.append([label] + values)
    
    if not parsed_rows:
        return None
    
    # Determine max columns
    max_cols = max(len(r) for r in parsed_rows)
    if max_cols < 2:
        return None
    
    # Build header from header_lines
    # Combine header lines that look like column names
    header_text = ' '.join(l.strip() for l in header_lines if l.strip())
    
    # Create simple header
    headers = [''] * max_cols
    headers[0] = header_text if header_text else 'Item'
    
    # Pad rows
    for row in parsed_rows:
        while len(row) < max_cols:
            row.append('')
    
    # Build markdown
    header_row = '| ' + ' | '.join(headers) + ' |'
    sep_row = '| ' + ' | '.join([':---'] * max_cols) + ' |'
    data_rows_md = []
    for row in parsed_rows:
        data_rows_md.append('| ' + ' | '.join(row) + ' |')
    
    return '\n'.join([header_row, sep_row] + data_rows_md)


def main():
    print(f"Loading {INPUT_PATH}...")
    with open(INPUT_PATH, 'r') as f:
        data = json.load(f)
    
    # Create backup
    print(f"Creating backup at {BACKUP_PATH}...")
    with open(BACKUP_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    fixed_narrative = 0
    fixed_exhibit = 0
    total = len(data['vignettes'])
    
    for i, v in enumerate(data['vignettes']):
        original_text = v.get('case_study_text', '')
        
        # Fix #1: Broken narrative in pipe tables
        fixed_text = fix_broken_pipe_narrative(original_text)
        if fixed_text != original_text:
            fixed_narrative += 1
        
        # Fix #2: Plain text exhibits → markdown tables  
        fixed_text2 = fix_plain_text_exhibits(fixed_text)
        if fixed_text2 != fixed_text:
            fixed_exhibit += 1
        
        data['vignettes'][i]['case_study_text'] = fixed_text2
    
    # Save
    print(f"Saving fixed data to {INPUT_PATH}...")
    with open(INPUT_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults:")
    print(f"  Total vignettes: {total}")
    print(f"  Fixed broken narrative tables: {fixed_narrative}")
    print(f"  Fixed plain text exhibits: {fixed_exhibit}")
    print(f"  Backup saved to: {BACKUP_PATH}")


if __name__ == '__main__':
    main()
