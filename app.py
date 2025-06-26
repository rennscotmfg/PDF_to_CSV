from flask import Flask, request, jsonify, send_file, render_template
import os
from parser import get_dataframe
from csv_exporter import generate_transposed_csv
from json_exporter import export_json
from io import BytesIO
import pandas as pd

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CURRENT_DATA'] = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'success': False, 'error': 'No files provided'})

        all_measurements = []
        file_paths = []
        file_names = []
        errors = []

        for file in files:
            if file.filename == '':
                continue
            if not file.filename.lower().endswith('.pdf'):
                errors.append(f"{file.filename}: Not a PDF file")
                continue

            try:
                temp_path = os.path.join(UPLOAD_FOLDER, file.filename)
                file_paths.append(temp_path)
                file_names.append(file.filename)
                file.save(temp_path)
            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
        
        try:
            df = get_dataframe(file_paths, file_names)
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error processing files: {str(e)}'})
        
        for file in file_paths:
            try:
                os.remove(file)
            except Exception as e:
                print(f"Warning: Could not delete temp file {file}: {str(e)}")

        app.config['CURRENT_DATA'] = df
        app.config['JSON_DATA'] = export_json(df)
        preview_data = df.head(10).to_dict('records') if not df.empty else []

        return jsonify({
            'success': True,
            'total_measurements': sum('DIM' in col for col in df.columns),
            'total_parts': len(df) if not df.empty else 0,
            'processed_files': file_names,
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

@app.route('/json_data', methods=['GET'])
def get_json_data():
    json_data = app.config.get('JSON_DATA')
    if json_data is None:
        return jsonify({'error': 'No JSON data available'}), 400
    return json_data

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
