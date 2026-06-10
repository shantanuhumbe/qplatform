"""
Smart table renderer for case study text.

Processes raw case study text and auto-detects/fixes table formatting issues
at render time, without modifying the underlying JSON data.

Handles:
1. Properly formatted markdown pipe tables → converted to HTML
2. Plain text tabular data (lines with multiple values) → auto-converted to HTML tables  
3. Garbled pipe table headers (title split across cols) → reconstructed
4. Narrative text incorrectly placed in pipe tables → extracted as paragraphs
"""

import re
import markdown


def render_case_study(raw_text: str) -> str:
    """
    Main entry point: takes raw case study text and returns clean HTML.
    
    Pipeline:
    1. Fix broken pipe table blocks (narrative in tables, garbled headers)
    2. Detect and convert plain-text tabular data to markdown tables
    3. Ensure proper blank line spacing around tables (required by markdown lib)
    4. Remove duplicate content blocks
    5. Convert final markdown to HTML
    """
    text = raw_text
    
    # Pass 1: Fix broken pipe table blocks
    text = _fix_broken_pipe_blocks(text)
    
    # Pass 2: Convert plain-text exhibit data to markdown tables
    text = _convert_plain_text_tables(text)
    
    # Pass 3: Ensure blank lines around pipe tables (markdown lib requirement)
    text = _ensure_table_spacing(text)
    
    # Pass 4: Remove duplicate text blocks
    text = _remove_duplicates(text)
    
    # Pass 5: Convert markdown → HTML
    html = markdown.markdown(text, extensions=['tables', 'md_in_html'])
    
    return html


def _ensure_table_spacing(text: str) -> str:
    """
    Ensure blank lines before and after pipe table blocks.
    The Python markdown library requires this to recognise pipe tables.
    """
    lines = text.split('\n')
    result = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        is_pipe = stripped.startswith('|') and (stripped.endswith('|') or '|' in stripped[1:])
        
        if is_pipe:
            # Ensure blank line before table (if previous line isn't blank or another pipe row)
            if result and result[-1].strip() != '' and not (result[-1].strip().startswith('|')):
                result.append('')
            result.append(line)
            # Check if next line is NOT a pipe row → add blank line after
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if next_stripped and not next_stripped.startswith('|'):
                    pass  # Will be handled on next iteration
            elif i + 1 == len(lines):
                result.append('')
        else:
            # If previous line was a pipe row and this isn't blank, add blank
            if result and result[-1].strip().startswith('|') and stripped != '':
                result.append('')
            result.append(line)
    
    return '\n'.join(result)


def _remove_duplicates(text: str) -> str:
    """Remove duplicate long paragraphs that may arise from extraction."""
    lines = text.split('\n')
    result = []
    seen = set()
    
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 150:
            # Normalize for comparison
            normalized = re.sub(r'\s+', ' ', stripped.lower())
            if normalized in seen:
                continue  # Skip duplicate
            seen.add(normalized)
        result.append(line)
    
    return '\n'.join(result)


def _fix_broken_pipe_blocks(text: str) -> str:
    """Fix pipe table blocks with narrative text or garbled headers."""
    lines = text.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('|') and line.endswith('|'):
            # Collect full pipe block
            block = []
            block_start = i
            while i < len(lines) and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                block.append(lines[i].strip())
                i += 1
            
            # Process the block
            processed = _process_pipe_block(block)
            result.extend(processed)
        else:
            result.append(lines[i])
            i += 1
    
    return '\n'.join(result)


def _has_data_value(col_text: str) -> bool:
    """Check if a column value contains actual data (numbers, %, $, etc.)."""
    clean = col_text.replace('**', '').strip()
    if not clean:
        return False
    if re.search(r'\d+\.?\d*%', clean):
        return True
    if re.search(r'[\$€£]|CAD|USD|GBP|JPY|EUR|CHF', clean):
        return True
    if re.search(r'\b\d+[\.,]?\d*\b', clean):
        return True
    if clean.lower() in ('n/a', 'n/a*', 'na', 'n.a.', '—', '–', '-', '---', 'yes', 'no'):
        return True
    return False


def _process_pipe_block(block: list) -> list:
    """Analyze and fix a pipe table block."""
    if not block:
        return block
    
    # Separate components
    separator_rows = []
    header = None
    data_rows = []
    narrative_rows = []
    
    for j, row in enumerate(block):
        if re.match(r'^\|\s*:?-+', row):
            separator_rows.append(row)
            continue
        
        cols = [c.strip() for c in row.split('|')]
        cols = [c for c in cols if c != '']
        
        if j == 0:
            header = row
            continue
        
        # Classify row: data vs narrative
        if len(cols) >= 2:
            val_cols = cols[1:]
            has_any_data = any(_has_data_value(c) for c in val_cols)
            
            if has_any_data:
                data_rows.append(row)
            else:
                # Check if first column also looks narrative
                col0 = cols[0].replace('**', '').strip()
                if len(col0) > 60 and not _has_data_value(col0):
                    narrative_rows.append(row)
                elif all(len(c.replace('**', '').split()) <= 2 for c in val_cols):
                    narrative_rows.append(row)
                else:
                    data_rows.append(row)
        else:
            data_rows.append(row)
    
    # Check header: is it garbled (title split across columns)?
    fixed_header = header
    if header:
        header_cols = [c.strip() for c in header.split('|') if c.strip()]
        
        # Too many empty/whitespace columns → broken
        if len(header_cols) > 10:
            # Oversized header — try to reconstruct
            fixed_header = _reconstruct_header(header, data_rows, separator_rows)
        elif len(header_cols) >= 3:
            # Check if columns look like a split sentence
            has_numeric = any(re.search(r'\d', c) for c in header_cols)
            has_header_keywords = any(kw in ' '.join(header_cols).lower() for kw in 
                                     ['characteristic', 'value', 'item', 'year', 'maturity',
                                      'rate', 'price', 'return', 'cost', 'ratio', 'stock',
                                      'bond', 'portfolio', 'factor', 'period', 'growth',
                                      'model', 'method', 'total', 'net', 'revenue', 'income'])
            if not has_numeric and not has_header_keywords:
                joined = ' '.join(header_cols)
                if len(joined) > 60:
                    fixed_header = _reconstruct_header(header, data_rows, separator_rows)
    
    # Build output
    output = []
    
    if data_rows:
        # Output clean table
        if fixed_header:
            output.append(fixed_header)
        for sr in separator_rows:
            # Ensure separator has right number of columns
            if fixed_header:
                # Count ALL columns including empty ones (e.g. | | col1 | col2 |)
                # Use pipe count - 1 on each side = number of columns
                ncols = fixed_header.count('|') - 1
                sr = '| ' + ' | '.join([':---'] * ncols) + ' |'
            output.append(sr)
        for dr in data_rows:
            output.append(dr)
        
        # Extract narrative rows as text
        if narrative_rows:
            output.append('')
            for nr in narrative_rows:
                cols = [c.strip().replace('**', '') for c in nr.split('|') if c.strip()]
                output.append(' '.join(cols))
    elif narrative_rows:
        # All narrative — convert to paragraph
        all_parts = []
        if header:
            cols = [c.strip().replace('**', '') for c in header.split('|') if c.strip()]
            all_parts.append(' '.join(cols))
        for nr in narrative_rows:
            cols = [c.strip().replace('**', '') for c in nr.split('|') if c.strip()]
            all_parts.append(' '.join(cols))
        output.append(' '.join(all_parts))
    else:
        # Only header/separator (edge case) — keep as-is
        for row in block:
            output.append(row)
    
    return output


def _reconstruct_header(header: str, data_rows: list, separator_rows: list) -> str:
    """Try to build a proper header based on the number of data columns."""
    if not data_rows:
        # If no data rows, just count columns from separator
        if separator_rows:
            ncols = len([c for c in separator_rows[0].split('|') if c.strip() or c == ':---'])
            ncols = separator_rows[0].count(':---') or separator_rows[0].count('---')
        else:
            return header
    else:
        # Count columns from first data row
        first_data_cols = [c.strip() for c in data_rows[0].split('|') if c.strip()]
        ncols = len(first_data_cols)
    
    if ncols < 2:
        return header
    
    # Generate generic headers
    headers = ['Item']
    for ci in range(1, ncols):
        headers.append(f'Value {ci}' if ncols > 2 else 'Value')
    
    return '| ' + ' | '.join(headers) + ' |'


def _convert_plain_text_tables(text: str) -> str:
    """
    Detect plain-text tabular data after Exhibit headers and convert
    to markdown pipe tables.
    
    Looks for patterns like:
        **Exhibit N:**
        Title Text
        Column1 Column2 Column3
        Label1   Val1    Val2    Val3
        Label2   Val1    Val2    Val3
    """
    lines = text.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Detect exhibit header
        is_exhibit = re.match(r'\*?\*?Exhibit\s+\d+\*?\*?\s*:?\*?\*?\s*$', line, re.IGNORECASE)
        if not is_exhibit:
            is_exhibit = re.match(r'\*\*Exhibit\s+\d+:\*\*\s*$', line, re.IGNORECASE)
        
        if is_exhibit:
            result.append(lines[i])
            i += 1
            
            # Collect non-table, non-pipe lines after exhibit header
            pre_table = []
            while i < len(lines):
                s = lines[i].strip()
                if not s:
                    pre_table.append(lines[i])
                    i += 1
                    continue
                if s.startswith('|'):
                    break  # Already a pipe table
                if s.startswith('•') or s.startswith('**Statement') or s.startswith('Module'):
                    break  # Hit next section
                if len(s) > 120 and not re.search(r'\d+\.?\d*%', s):
                    break  # Long narrative paragraph
                
                # Check if this is a data line (has multiple numeric values)
                pct_count = len(re.findall(r'\d+\.?\d*%', s))
                money_count = len(re.findall(r'[\$€£][\d,]+|CAD[\d,]+', s))
                num_count = len(re.findall(r'\b\d+[\.,]\d+\b', s))
                
                if pct_count >= 2 or money_count >= 2 or (pct_count >= 1 and num_count >= 1):
                    # Found data — collect all data lines
                    data_lines = [s]
                    i += 1
                    while i < len(lines):
                        ns = lines[i].strip()
                        if not ns:
                            break
                        ns_pct = len(re.findall(r'\d+\.?\d*%', ns))
                        ns_money = len(re.findall(r'[\$€£][\d,]+|CAD[\d,]+', ns))
                        ns_num = len(re.findall(r'\b\d+[\.,]\d+\b', ns))
                        if ns_pct >= 1 or ns_money >= 1 or ns_num >= 1:
                            data_lines.append(ns)
                            i += 1
                        elif len(ns) < 40 and not ns.startswith('•') and not ns.startswith('**'):
                            # Could be a continuation of a multi-line label
                            data_lines.append(ns)
                            i += 1
                        else:
                            break
                    
                    # Output pre_table as title lines
                    for pl in pre_table:
                        if pl.strip():
                            result.append(pl)
                    result.append('')
                    
                    # Build markdown table from data lines
                    md_table = _build_table_from_lines(data_lines)
                    result.append(md_table)
                    result.append('')
                    pre_table = []
                    break
                else:
                    pre_table.append(lines[i])
                    i += 1
            else:
                # No data found — output pre_table as-is
                result.extend(pre_table)
        else:
            result.append(lines[i])
            i += 1
    
    return '\n'.join(result)


def _build_table_from_lines(data_lines: list) -> str:
    """Parse plain-text data lines into a markdown pipe table."""
    parsed = []
    
    # Try to handle multi-line labels
    i = 0
    while i < len(data_lines):
        dl = data_lines[i].strip()
        
        # Check if this line has numeric data
        has_values = bool(re.search(r'\d+\.?\d*%|[\$€£][\d,]+|CAD[\d,]+|\b\d+[\.,]\d+\b', dl))
        
        if has_values:
            # Split into label + values
            # Strategy: find where the first numeric-looking token starts
            match = re.match(r'^(.+?)\s{2,}([\d\$€£C(–\-].*)', dl)
            if not match:
                match = re.match(r'^(.+?)\s+([\d\$€£C][\d\.\,\$%\s\(\)–\-]+.*)$', dl)
            
            if match:
                label = match.group(1).strip()
                values_str = match.group(2).strip()
                
                # Check if previous line was a label fragment (no numbers)
                if i > 0 and not re.search(r'\d', data_lines[i-1]):
                    prev = data_lines[i-1].strip()
                    if prev and len(prev) < 60:
                        label = prev + ' ' + label
                        # Remove the previously added label-only line
                        if parsed and parsed[-1] == [prev]:
                            parsed.pop()
                
                # Split values by 2+ spaces or before numeric tokens
                values = re.split(r'\s{2,}', values_str)
                values = [v.strip() for v in values if v.strip()]
                parsed.append([label] + values)
            else:
                parsed.append([dl])
        else:
            # Label-only line — might be part of next data line
            if dl:
                parsed.append([dl])
        
        i += 1
    
    if not parsed:
        return '\n'.join(data_lines)
    
    # Determine column count from rows with most columns
    max_cols = max(len(r) for r in parsed)
    if max_cols < 2:
        return '\n'.join(data_lines)
    
    # Filter out label-only rows that were already merged
    final_rows = [r for r in parsed if len(r) >= 2 or (len(r) == 1 and len(r[0]) > 60)]
    if not final_rows:
        final_rows = parsed
    
    # Pad all rows to same column count
    for row in final_rows:
        while len(row) < max_cols:
            row.append('')
    
    # Build generic header
    headers = ['Item']
    for ci in range(1, max_cols):
        headers.append(f'Value {ci}' if max_cols > 2 else 'Value')
    
    # Build markdown
    lines_out = []
    lines_out.append('| ' + ' | '.join(headers) + ' |')
    lines_out.append('| ' + ' | '.join([':---'] * max_cols) + ' |')
    for row in final_rows:
        if len(row) >= 2:  # Only output rows with data
            lines_out.append('| **' + row[0] + '** | ' + ' | '.join(row[1:]) + ' |')
    
    return '\n'.join(lines_out)
