import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Any
import os

def extract_text_from_pdf(pdf_path: str) -> str:
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
    dim_list = []
    for line in lines:
        if line and len(line) > 1:
            dim_name = line[0].split('#')[1]
            try:
                unit = re.split(r'[\d\.\d]+', line[1])[1]
                if unit == '':
                    unit = line[2]
            except Exception:
                unit = 'None'
            if not any(entry['tag'] == dim_name for entry in dim_list):
                dim_list.append({'tag': dim_name, 'values': [], 'unit': unit})
    for line in lines:
        if len(line) > 1:
            dim_name = line[0].split('#')[1]
            match = re.match(r'[\d.]+', line[1])
            if match:
                value = match.group(0)
                for entry in dim_list:
                    if entry['tag'] == dim_name:
                        entry['values'].append(value)
    return dim_list

def normalize_tag(tag: str) -> str:
    match = re.match(r"(\d+)", tag)
    return match.group(1) if match else None

def get_priority(tag: str) -> int:
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
            if priority < existing_priority:
                prioritized[base] = (priority, entry)
    result = []
    for base, (_, entry) in sorted(prioritized.items(), key=lambda x: int(x[0])):
        result.append({
            "tag": base,
            "values": entry["values"],
            "unit": entry["unit"]
        })
    return result

# ✅ This replaces the old extract_calypso_data()
def extract_calypso_data(pdf_path: str) -> List[Dict[str, Any]]:
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        return []
    lines = extract_dim_lines(text)
    dim_list = create_dim_list(lines)
    filtered = prioritize_tags(dim_list)

    measurements = []
    for entry in filtered:
        for value in entry['values']:
            try:
                measurements.append({
                    'Name': f'DIM#{entry["tag"]}',
                    'Measured_Value': float(value),
                    'Unit': entry['unit'], 
                    'Nominal_Value': None,
                    'Plus_Tolerance': None,
                    'Minus_Tolerance': None,
                    'Deviation': None
                })
            except ValueError:
                continue
    return measurements

# Sorting & DataFrame building logic unchanged
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
