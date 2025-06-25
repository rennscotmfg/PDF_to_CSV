import pdfplumber
import pandas as pd
import re

def extract_calypso_data(pdf_path):
    measurements = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    measurements.extend(process_text_data(text))
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
    return measurements

def process_text_data(text):
    measurements = []
    lines = text.split('\n')
    dim_lines = [line.strip() for line in lines if line.strip() and 'DIM' in line and ('mm' in line or 'inches' in line)]

    for line in dim_lines:
        cleaned_line = line
        for suffix in ['_X', '_Y', '_Z']:
            cleaned_line = cleaned_line.replace(suffix, '')
        unit = 'mm' if 'mm' in cleaned_line else 'inches' if 'inches' in cleaned_line else None
        if not unit:
            continue
        cleaned_line = cleaned_line[:cleaned_line.find(unit) + len(unit)].replace(' ', '')
        try:
            unit_pos = cleaned_line.find(unit)
            before_unit = cleaned_line[:unit_pos]
            last_dash = before_unit.rfind('-')
            if last_dash == -1:
                continue
            dim_name = before_unit[:last_dash + 1]
            measured_value = float(before_unit[last_dash + 1:])
            measurements.append({
                'Name': dim_name,
                'Measured_Value': measured_value,
                'Unit': unit,
                'Nominal_Value': None,
                'Plus_Tolerance': None,
                'Minus_Tolerance': None,
                'Deviation': None
            })
        except:
            continue
    return measurements

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
