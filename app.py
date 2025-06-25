from flask import Flask, request, jsonify, send_file
import os
from parser import extract_calypso_data, create_wide_format_table
from csv_exporter import generate_transposed_csv
from io import BytesIO
import pandas as pd

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CURRENT_DATA'] = None
REVISION = "1.0.2"

@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open('index.html', 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except FileNotFoundError:
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
                temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(temp_path)

                measurements = extract_calypso_data(temp_path)
                if measurements:
                    for m in measurements:
                        m['Source_File'] = file.filename
                        m['Part_Number'] = 'Unknown'
                    all_measurements.extend(measurements)
                    processed_files.append(file.filename)
                else:
                    errors.append(f"{file.filename}: No measurement data found")

                os.remove(temp_path)
            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        if not all_measurements:
            return jsonify({'success': False, 'error': 'No measurement data extracted from any files', 'details': errors})

        df = create_wide_format_table(all_measurements)
        app.config['CURRENT_DATA'] = df
        print(df)
        preview_data = df.head(10).to_dict('records') if not df.empty else []

        return jsonify({
            'success': True,
            'total_measurements': len(all_measurements),
            'total_parts': len(df) if not df.empty else 0,
            'processed_files': processed_files,
            'errors': errors if errors else None,
            'columns': df.columns.tolist() if not df.empty else [],
            'preview': preview_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

@app.route('/download_csv', methods=['POST'])
def download_csv():
    try:
        data = request.get_json()
        include_stats = data.get('include_stats', False)

        df = app.config.get('CURRENT_DATA')
        if df is None or df.empty:
            return jsonify({'error': 'No data available'}), 400

        output = generate_transposed_csv(df, include_stats)
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='calypso_measurements_transposed.csv'
        )
    except Exception as e:
        return jsonify({'error': f'Error generating CSV: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
