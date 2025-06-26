import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Any
import os
import time

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a single PDF file."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
        return text
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return ""

def extract_dim_lines(text: str) -> List[List[str]]:
    """Extract lines containing DIM# tags from text."""
    unstructured_lines = text.split('\n')
    lines = []
    
    for line in unstructured_lines:
        word_list = line.split()
        if len(word_list) > 1:
            for i, word in enumerate(word_list):
                if word.startswith('DIM#'):
                    lines.append(word_list[i:])
    
    return lines

def create_dim_list(lines: List[List[str]]) -> List[Dict[str, Any]]:
    """Create initial dimension list from extracted lines."""
    dim_list = []
    
    # Create entries for each unique DIM tag
    for line in lines:
        if len(line) > 1:  # Check if line is not empty
            dim_name = line[0].split('#')[1]
            try:
                unit = re.split(r'[\d\.\d]+', line[1])[1]
                if unit == '':
                    unit = line[2]
            except Exception:
                unit = 'None'
            # Check if this tag already exists
            if not any(entry['tag'] == dim_name for entry in dim_list):
                entry = {'tag': dim_name, 'values': [], 'unit': unit}
                dim_list.append(entry)
    
    # Populate values for each tag
    for line in lines:
        if len(line) > 1:  # Ensure there's a value after the tag
            dim_name = line[0].split('#')[1]
            value = re.match(r'[\d\.\d]+', line[1]).group(0)
            for entry in dim_list:
                if entry['tag'] == dim_name:
                    entry['values'].append(value)
    
    return dim_list

def normalize_tag(tag: str) -> str:
    """Extract base number from tag."""
    match = re.match(r"(\d+)", tag)
    return match.group(1) if match else None

def get_priority(tag: str) -> int:
    """Determine priority of tag based on content."""
    tag_upper = tag.upper()
    if "(M)" in tag_upper:
        return 1
    elif re.fullmatch(r"\d+", tag):
        return 2
    elif "MIN" in tag_upper:
        return 3
    else:
        return 4

def prioritize_tags(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prioritize and filter tags based on rules."""
    prioritized = {}
    
    for entry in data:
        base = normalize_tag(entry["tag"])
        if not base:
            continue
            
        priority = get_priority(entry["tag"])
        
        if base not in prioritized:
            prioritized[base] = (priority, entry)
        else:
            existing_priority, _ = prioritized[base]
            # Replace only if new one has higher priority (lower number)
            if priority < existing_priority:
                prioritized[base] = (priority, entry)
    
    # Create result with base numbers as tags
    result = []
    for base, (_, entry) in sorted(prioritized.items(), key=lambda x: int(x[0])):
        result.append({
            "tag": base,
            "values": entry["values"],
            "unit": entry["unit"]
        })
    
    return result

def process_single_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """Process a single PDF and return filtered dimension data."""
    print(f"Processing: {pdf_path}")
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"Warning: File {pdf_path} not found")
        return []
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        print(f"Warning: No text extracted from {pdf_path}")
        return []
    
    # Extract DIM lines
    lines = extract_dim_lines(text)
    if not lines:
        print(f"Warning: No DIM# tags found in {pdf_path}")
        return []
    
    # Create dimension list
    dim_list = create_dim_list(lines)
    
    # Apply prioritization and filtering
    filtered = prioritize_tags(dim_list)
    
    return filtered

def process_multiple_pdfs(pdf_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Process multiple PDFs and return combined results.
    Uses the first PDF to establish the dimension structure,
    then adds values from subsequent PDFs to the same structure.
    
    Args:
        pdf_paths: List of paths to PDF files
        
    Returns:
        List of dimension entries with combined values from all PDFs
    """
    if not pdf_paths:
        return []
    
    print(f"Processing first PDF to establish dimension structure: {pdf_paths[0]}")
    
    # Process first PDF to establish the dimension structure
    first_pdf_path = pdf_paths[0]
    if not os.path.exists(first_pdf_path):
        print(f"Error: First PDF {first_pdf_path} not found")
        return []
    
    # Get the filtered structure from the first PDF
    combined_dim_list = process_single_pdf(first_pdf_path)
    
    if not combined_dim_list:
        print(f"Warning: No dimensions found in first PDF {first_pdf_path}")
        return []
    
    # Process remaining PDFs and add their values to existing structure
    for pdf_path in pdf_paths[1:]:
        print(f"Processing additional PDF: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            print(f"Warning: File {pdf_path} not found, skipping")
            continue
        
        # Extract text and lines from current PDF
        text = extract_text_from_pdf(pdf_path)
        if not text.strip():
            print(f"Warning: No text extracted from {pdf_path}, skipping")
            continue
        
        lines = extract_dim_lines(text)
        if not lines:
            print(f"Warning: No DIM# tags found in {pdf_path}, skipping")
            continue
        
        # Create temporary dim list for this PDF
        temp_dim_list = create_dim_list(lines)
        temp_filtered = prioritize_tags(temp_dim_list)
        
        # Add values from this PDF to the combined structure
        for temp_entry in temp_filtered:
            # Find matching tag in combined list
            for combined_entry in combined_dim_list:
                if combined_entry['tag'] == temp_entry['tag']:
                    # Add new values to existing entry
                    combined_entry['values'].extend(temp_entry['values'])
                    break
            else:
                # If tag not found in combined list, add it
                # (This shouldn't happen if first PDF defines all tags)
                print(f"Warning: Found new tag '{temp_entry['tag']}' in {pdf_path} not present in first PDF")
                combined_dim_list.append(temp_entry)
    
    return combined_dim_list

def sort_dim_columns(dim_names):
    def extract_dim_number(name):
        name = name.replace('DIM', '').replace('#', '')
        parts = name.split('.')
        try:
            return int(re.findall(r'\d+', parts[0])[0])
        except:
            return 999999
    def extract_sub_number(name):
        try:
            return int(re.findall(r'\.(\d+)', name)[0])
        except:
            return 0
    return sorted(dim_names, key=lambda x: (extract_dim_number(x), extract_sub_number(x), x))

def create_wide_format_table(all_measurements):
    if not all_measurements:
        return pd.DataFrame()
    parts_data = {}
    all_dims = set()
    for m in all_measurements:
        source = m['Source_File']
        dim = m['Name']
        val = m['Measured_Value']
        unit = m['Unit']
        parts_data.setdefault(source, {'measurements': {}, 'unit': unit})['measurements'][dim] = val
        all_dims.add(dim)

    sorted_dims = sort_dim_columns(list(all_dims))
    table_data = []
    for i, (source, data) in enumerate(parts_data.items(), 1):
        row = {
            'Part_Number': f"Part_{i:03d}",
            'Source_File': source
        }
        for dim in sorted_dims:
            col_name = dim.replace('#', '').replace('-', '_').replace('.', '_').rstrip('_')
            row[col_name] = data['measurements'].get(dim)
        row['Unit'] = data['unit']
        table_data.append(row)
    return pd.DataFrame(table_data)

def get_dataframe(pdf_paths: List[str], file_names) -> List[Dict[str, Any]]:
    """
    Main function to process PDFs and optionally save results.
    
    Args:
        pdf_paths: List of PDF file paths to process
        output_file: Optional path to save JSON output
        
    Returns:
        List containing combined dimension data from all PDFs
    """
    start = time.time()
    print("Starting processing...")
    print(f"Processing {len(pdf_paths)} PDF(s)...")
    
    # Process all PDFs with combined structure
    results = process_multiple_pdfs(pdf_paths)
    
    measurements = []
    for entry in results:
        for file_index, value in enumerate(entry['values']):
            try:
                measurements.append({
                    'Name': f'DIM#{entry["tag"]}',
                    'Measured_Value': float(value),
                    'Unit': entry['unit'], 
                    'Nominal_Value': None,
                    'Plus_Tolerance': None,
                    'Minus_Tolerance': None,
                    'Deviation': None,
                    'Source_File': file_names[file_index],
                    'Part_Number': ''
                })
            except ValueError:
                continue
    
    df = create_wide_format_table(measurements)
    
    print("Processing complete!")
    end = time.time()
    print(f"Total processing time: {end - start:.2f} seconds")
    return df