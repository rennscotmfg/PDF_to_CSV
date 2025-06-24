from flask import Flask, request, send_file, jsonify, render_template_string
import pdfplumber
import pandas as pd
import os
import re
from io import BytesIO
import tempfile

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

REVISION = "1.0.2"

# Required packages - install with:
# pip install flask pdfplumber pandas

def extract_calypso_data(pdf_path):
    """Extract measurement data from Calypso CMM PDF reports"""
    measurements = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"\n=== Processing PDF: {pdf_path} ===")
            print(f"Total pages: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages):
                print(f"\n--- Page {page_num + 1} ---")
                
                # Always try text extraction (simpler approach)
                text = page.extract_text()
                if text:
                    page_measurements = process_text_data(text)
                    measurements.extend(page_measurements)
                    print(f"Page {page_num + 1}: Found {len(page_measurements)} measurements")
                else:
                    print(f"Page {page_num + 1}: No text found")
    
    except Exception as e:
        print(f"Error processing PDF: {str(e)}")
        return []
    
    print(f"\n=== PDF Processing Complete ===")
    print(f"Total measurements from all pages: {len(measurements)}")
    return measurements

def process_table_data(table):
    """Process tabular measurement data"""
    measurements = []
    
    for row in table:
        if not row or len(row) < 6:
            continue
            
        # Look for rows that contain dimension names (starting with DIM)
        name_cell = row[0] if row[0] else ""
        if not name_cell or "DIM" not in name_cell:
            continue
            
        try:
            # Extract measurement data from table row
            measurement = {
                'Name': clean_name(name_cell),
                'Measured_Value': extract_numeric_value(row[1]) if len(row) > 1 else None,
                'Unit': extract_unit(row[1]) if len(row) > 1 else 'mm',
                'Nominal_Value': extract_numeric_value(row[2]) if len(row) > 2 else None,
                'Plus_Tolerance': extract_numeric_value(row[3]) if len(row) > 3 else None,
                'Minus_Tolerance': extract_numeric_value(row[4]) if len(row) > 4 else None,
                'Deviation': extract_numeric_value(row[5]) if len(row) > 5 else None
            }
            
            if measurement['Measured_Value'] is not None:
                measurements.append(measurement)
                
        except Exception as e:
            print(f"Error processing row {row}: {str(e)}")
            continue
    
    return measurements

def process_text_data(text):
    """Process text data using simple string operations - NO REGEX!"""
    measurements = []
    lines = text.split('\n')
    
    # Filter lines that contain DIM measurements and units
    dim_lines = [line.strip() for line in lines if line.strip() and 'DIM' in line and ('mm' in line or 'inches' in line)]
    
    print(f"Found {len(dim_lines)} lines with DIM and units")
    
    for line in dim_lines:
        print(f"\n--- Processing line ---")
        print(f"Original: {line}")
        
        # Step 2: Remove _X, _Y, _Z if present
        cleaned_line = line
        for suffix in ['_X', '_Y', '_Z']:
            if suffix in cleaned_line:
                cleaned_line = cleaned_line.replace(suffix, '')
                print(f"Removed {suffix}: {cleaned_line}")
        
        # Step 1: Find the unit and delete everything after it
        unit = None
        if 'mm' in cleaned_line:
            unit = 'mm'
            unit_pos = cleaned_line.find('mm')
            # Delete everything after 'mm'
            cleaned_line = cleaned_line[:unit_pos + 2]
        elif 'inches' in cleaned_line:
            unit = 'inches'
            unit_pos = cleaned_line.find('inches')
            # Delete everything after 'inches'
            cleaned_line = cleaned_line[:unit_pos + 6]
        
        if not unit:
            print("No unit found, skipping")
            continue
            
        print(f"After cutting at unit: {cleaned_line}")
        
        # Remove all spaces
        cleaned_line = cleaned_line.replace(' ', '')
        print(f"After removing spaces: {cleaned_line}")
        
        # Now extract the data
        try:
            # Find the unit position again (after space removal)
            if unit == 'mm':
                unit_pos = cleaned_line.find('mm')
            else:
                unit_pos = cleaned_line.find('inches')
            
            # Get everything before the unit
            before_unit = cleaned_line[:unit_pos]
            print(f"Before unit: {before_unit}")
            
            # Find the last dash to split DIM name and measured value
            last_dash = before_unit.rfind('-')
            if last_dash == -1:
                print("No dash found, skipping")
                continue
            
            # Extract DIM name (everything before last dash)
            dim_name = before_unit[:last_dash + 1]  # Include the dash
            print(f"DIM name: {dim_name}")
            
            # Extract measured value (everything after last dash)
            measured_value_str = before_unit[last_dash + 1:]
            print(f"Measured value string: {measured_value_str}")
            
            # Convert measured value to float
            measured_value = float(measured_value_str)
            print(f"Measured value: {measured_value}")
            
            # Create measurement record
            measurement = {
                'Name': dim_name,
                'Measured_Value': measured_value,
                'Unit': unit,
                'Nominal_Value': None,
                'Plus_Tolerance': None,
                'Minus_Tolerance': None,
                'Deviation': None
            }
            
            measurements.append(measurement)
            print(f"✓ Successfully extracted: {dim_name} = {measured_value} {unit}")
            
        except (ValueError, IndexError) as e:
            print(f"Error processing line: {e}")
            continue
    
    print(f"\n=== SUMMARY ===")
    print(f"Total measurements extracted: {len(measurements)}")
    for i, m in enumerate(measurements[:5]):  # Show first 5
        print(f"{i+1}. {m['Name']} = {m['Measured_Value']} {m['Unit']}")
    
    return measurements

def clean_name(name):
    """Clean and standardize dimension names"""
    if not name:
        return ""
    
    # Remove extra whitespace and special characters
    cleaned = re.sub(r'\s+', ' ', name.strip())
    
    # Remove symbols that might interfere with CSV
    cleaned = re.sub(r'[^\w\s\-\.\#]', '', cleaned)
    
    return cleaned

def extract_numeric_value(cell_value):
    """Extract numeric value from cell, handling various formats"""
    if not cell_value:
        return None
    
    # Convert to string if not already
    str_value = str(cell_value).strip()
    
    # Extract first number found (handles cases like "3.25983 mm")
    number_match = re.search(r'([\-\+]?\d+\.?\d*)', str_value)
    if number_match:
        try:
            return float(number_match.group(1))
        except ValueError:
            return None
    
    return None

def extract_unit(cell_value):
    """Extract unit from cell value"""
    if not cell_value:
        return 'mm'
    
    str_value = str(cell_value).strip()
    if 'mm' in str_value:
        return 'mm'
    elif 'in' in str_value:
        return 'in'
    else:
        return 'mm'  # Default to mm

def sort_dim_columns(dim_names):
    """Sort DIM columns intelligently (numerically, not alphabetically)"""
    
    def extract_dim_number(dim_name):
        """Extract the main DIM number for sorting"""
        try:
            # Remove DIM prefix and clean up
            clean_name = dim_name.replace('DIM', '').replace('#', '')
            
            # Extract the first number (main DIM number)
            # Examples: "6.1-" -> 6, "21.2-Boss" -> 21, "7-" -> 7
            parts = clean_name.split('.')
            if parts:
                # Get the first part and extract number
                first_part = parts[0].replace('-', '').replace('_', '')
                # Find the first sequence of digits
                num_str = ''
                for char in first_part:
                    if char.isdigit():
                        num_str += char
                    elif num_str:  # Stop when we hit non-digit after finding digits
                        break
                
                if num_str:
                    return int(num_str)
            
            return 999999  # Put unrecognized patterns at the end
            
        except (ValueError, IndexError):
            return 999999  # Put problematic names at the end
    
    def extract_sub_number(dim_name):
        """Extract sub-number for secondary sorting (like .1, .2, etc.)"""
        try:
            if '.' in dim_name:
                # Extract everything after the dot
                after_dot = dim_name.split('.')[1]
                # Extract first number after dot
                num_str = ''
                for char in after_dot:
                    if char.isdigit():
                        num_str += char
                    else:
                        break
                return int(num_str) if num_str else 0
            return 0
        except (ValueError, IndexError):
            return 0
    
    # Create list of (original_name, main_num, sub_num) for sorting
    dim_data = []
    for dim_name in dim_names:
        main_num = extract_dim_number(dim_name)
        sub_num = extract_sub_number(dim_name)
        dim_data.append((dim_name, main_num, sub_num))
    
    # Sort by main number first, then sub number, then alphabetically
    sorted_dims = sorted(dim_data, key=lambda x: (x[1], x[2], x[0]))
    
    # Return just the original names in sorted order
    return [item[0] for item in sorted_dims]

def create_wide_format_table(all_measurements):
    """Convert measurements to wide format: Part# | DIM#1 | DIM#2 | ... | Unit"""
    
    print(f"\n=== Creating Wide Format Table ===")
    print(f"Total measurements to process: {len(all_measurements)}")
    
    if not all_measurements:
        return pd.DataFrame()
    
    # Group measurements by source file (each file = one part)
    parts_data = {}
    all_dims = set()
    
    for measurement in all_measurements:
        source_file = measurement['Source_File']
        dim_name = measurement['Name']
        measured_value = measurement['Measured_Value']
        unit = measurement['Unit']
        
        # Initialize part data if not exists
        if source_file not in parts_data:
            parts_data[source_file] = {
                'measurements': {},
                'unit': unit  # Assume all measurements in a file have same unit
            }
        
        # Store the measurement
        parts_data[source_file]['measurements'][dim_name] = measured_value
        all_dims.add(dim_name)
    
    print(f"Found {len(parts_data)} parts")
    print(f"Found {len(all_dims)} unique dimensions")
    
    # Sort dimensions intelligently (numerically)
    sorted_dims = sort_dim_columns(list(all_dims))
    print(f"Sorted dimensions: {sorted_dims[:10]}{'...' if len(sorted_dims) > 10 else ''}")
    
    # Create the wide format table
    table_data = []
    
    for part_index, (source_file, part_data) in enumerate(parts_data.items(), 1):
        row = {
            'Part_Number': f"Part_{part_index:03d}",  # Part_001, Part_002, etc.
            'Source_File': source_file
        }
        
        # Add each dimension as a column (in sorted order)
        for dim_name in sorted_dims:
            # Clean up column name (remove special characters)
            clean_dim_name = dim_name.replace('#', '').replace('-', '_').replace('.', '_')
            if clean_dim_name.endswith('_'):
                clean_dim_name = clean_dim_name[:-1]
            
            # Get the measured value for this dimension, or None if not measured
            measured_value = part_data['measurements'].get(dim_name, None)
            row[clean_dim_name] = measured_value
        
        # Add unit as last column
        row['Unit'] = part_data['unit']
        
        table_data.append(row)
        print(f"Part_{part_index:03d} ({source_file}): {len(part_data['measurements'])} measurements")
    
    # Create DataFrame
    df = pd.DataFrame(table_data)
    
    print(f"\n=== Wide Format Table Created ===")
    print(f"Table shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"Columns: Part_Number, Source_File, {len(sorted_dims)} dimension columns, Unit")
    
    return df

@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Fallback for systems with encoding issues
        with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except FileNotFoundError:
        # Return a simple HTML if file doesn't exist
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>Calypso PDF Converter</title></head>
        <body>
        <h1>Calypso PDF to CSV Converter</h1>
        <p>Please ensure index.html is in the same directory as app.py</p>
        </body>
        </html>
        '''

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'success': False, 'error': 'No files provided'})
        
        all_measurements = []
        processed_files = []
        errors = []
        
        for file in files:
            if file.filename == '':
                continue
                
            if not file.filename.lower().endswith('.pdf'):
                errors.append(f"{file.filename}: Not a PDF file")
                continue
            
            try:
                # Save uploaded file temporarily
                temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(temp_path)
                
                # Extract measurements
                measurements = extract_calypso_data(temp_path)
                
                if measurements:
                    # Add source file and part info to each measurement
                    for measurement in measurements:
                        measurement['Source_File'] = file.filename
                        # You can add part number extraction here later
                        measurement['Part_Number'] = 'Unknown'  # Placeholder
                    
                    all_measurements.extend(measurements)
                    processed_files.append(file.filename)
                    print(f"✓ {file.filename}: {len(measurements)} measurements")
                else:
                    errors.append(f"{file.filename}: No measurement data found")
                
                # Clean up temp file
                os.remove(temp_path)
                
            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
                # Clean up temp file if it exists
                temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        if not all_measurements:
            return jsonify({
                'success': False, 
                'error': 'No measurement data extracted from any files',
                'details': errors
            })
        
        # Convert to wide format table
        df = create_wide_format_table(all_measurements)
        
        # Store in session/memory (you might want to use a proper session store)
        app.config['CURRENT_DATA'] = df
        
        # Prepare response with preview data
        preview_data = df.head(10).to_dict('records') if not df.empty else []
        
        response_data = {
            'success': True,
            'total_measurements': len(all_measurements),
            'total_parts': len(df) if not df.empty else 0,
            'processed_files': processed_files,
            'errors': errors if errors else None,
            'columns': df.columns.tolist() if not df.empty else [],
            'preview': preview_data
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

@app.route('/download_csv', methods=['POST'])
def download_csv():
    try:
        data = request.get_json()
        include_stats = data.get('include_stats', False)
        
        # Get the current data
        df = app.config.get('CURRENT_DATA')
        if df is None or df.empty:
            return jsonify({'error': 'No data available'}), 400
        
        # Create CSV content
        output = BytesIO()
        
        # Create transposed version: Dimensions as rows, Parts as columns
        dimension_cols = [col for col in df.columns if col not in ['Part_Number', 'Source_File', 'Unit']]
        
        # Create transposed data
        transposed_data = {
            'Dimension': dimension_cols
        }
        
        # Add each part as a column
        for _, row in df.iterrows():
            part_number = row['Part_Number']
            source_file = row['Source_File']
            column_name = f"{part_number} ({source_file})"
            
            # Get values for each dimension for this part
            part_values = []
            for dim_col in dimension_cols:
                value = row[dim_col]
                if pd.notna(value):
                    part_values.append(round(value, 6))
                else:
                    part_values.append('')  # Empty for missing measurements
            
            transposed_data[column_name] = part_values
        
        # Create transposed DataFrame
        transposed_df = pd.DataFrame(transposed_data)
        
        print(f"\n=== Creating Transposed CSV ===")
        print(f"Original shape: {df.shape[0]} parts × {len(dimension_cols)} dimensions")
        print(f"Transposed shape: {len(dimension_cols)} dimensions × {df.shape[0]} parts")
        
        if include_stats:
            # Add statistics as additional columns
            stats_data = {
                'Count_Parts_Measured': [],
                'Mean_Value': [],
                'Min_Value': [],
                'Max_Value': [],
                'Std_Dev': []
            }
            
            for dim_col in dimension_cols:
                values = df[dim_col].dropna()
                
                stats_data['Count_Parts_Measured'].append(len(values))
                stats_data['Mean_Value'].append(round(values.mean(), 6) if len(values) > 0 else '')
                stats_data['Min_Value'].append(round(values.min(), 6) if len(values) > 0 else '')
                stats_data['Max_Value'].append(round(values.max(), 6) if len(values) > 0 else '')
                stats_data['Std_Dev'].append(round(values.std(), 6) if len(values) > 1 else '')
            
            # Add stats columns to transposed data
            for stat_name, stat_values in stats_data.items():
                transposed_df[stat_name] = stat_values
            
            print(f"Added statistics columns: {list(stats_data.keys())}")
        
        # Add unit information as the last column
        unit_values = []
        for dim_col in dimension_cols:
            # Get the unit from any part that has this measurement
            unit = df['Unit'].iloc[0] if not df.empty else 'mm'  # Default to mm
            unit_values.append(unit)
        
        transposed_df['Unit'] = unit_values
        
        # Write header comment
        output.write(b"# Calypso CMM Measurement Data - Transposed Format\n")
        output.write(b"# Rows = Dimensions, Columns = Parts\n")
        output.write(f"# Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n".encode())
        output.write(b"\n")
        print(transposed_df)
        # Write transposed data
        transposed_df.to_csv(output, index=False, lineterminator='\n')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'calypso_measurements_transposed.csv'
        )
        
    except Exception as e:
        return jsonify({'error': f'Error generating CSV: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)