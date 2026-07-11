# app.py
import os
import re
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import openpyxl
from io import BytesIO
import tempfile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.secret_key = 'your-secret-key-here'

# 確保上傳目錄存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 定義表頭規則
HEADER_RULES = {
    'A': {'name': '可以為空', 'required': False},
    'B': {'name': 'BARCODE', 'required': True},
    'C': {'name': 'RFID', 'required': False},
    'D': {'name': '倉庫代號', 'required': True},
    'E': {'name': '儲位代號', 'required': True},
    'F': {'name': '品牌', 'required': True},
    'G': {'name': 'MODEL_NAME', 'required': True},
    'H': {'name': 'ARTICLE', 'required': True},
    'I': {'name': 'COLOR_CODE', 'required': True},
    'J': {'name': '底模', 'required': False},
    'K': {'name': 'size', 'required': True},
    'L': {'name': 'SHOE_KIND', 'required': True},
    'M': {'name': 'STOCK_QTY', 'required': True},
    'N': {'name': 'YYMM', 'required': True}
}

# 欄位列號映射
COLUMN_MAPPING = {
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4,
    'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
    'K': 10, 'L': 11, 'M': 12, 'N': 13
}

# 定義有效鞋型
VALID_SHOE_KIND = {'FL', 'FR', 'UL', 'UR', 'BL', 'BR'}

def validate_year_month(yymm):
    """驗證YYMM格式"""
    if not yymm:
        return False
    yymm_str = str(yymm).strip()
    if len(yymm_str) != 4:
        return False
    if not yymm_str.isdigit():
        return False
    year = int(yymm_str[:2])
    month = int(yymm_str[2:])
    if month < 1 or month > 12:
        return False
    return True

def validate_shoe_kind(value):
    """驗證鞋型格式"""
    if not value:
        return False
    return str(value).strip().upper() in VALID_SHOE_KIND

def validate_stock_qty(value):
    """驗證庫存數量"""
    try:
        val = float(value)
        if val < 0:
            return False
        # 檢查是否為0.5的倍數
        return abs(val * 2 - round(val * 2)) < 0.0001
    except (ValueError, TypeError):
        return False

def validate_barcode_unique(df, sheet_name, errors):
    """驗證BARCODE唯一性"""
    barcode_col = COLUMN_MAPPING['B']
    if barcode_col >= len(df.columns):
        return
    
    barcodes = df.iloc[:, barcode_col].dropna()
    if len(barcodes) == 0:
        return
    
    unique, counts = np.unique(barcodes, return_counts=True)
    duplicates = unique[counts > 1]
    
    for dup in duplicates:
        duplicate_rows = df[df.iloc[:, barcode_col] == dup].index.tolist()
        for row in duplicate_rows:
            errors.append({
                'sheet': sheet_name,
                'row': row + 2,
                'column': 'B',
                'field': 'BARCODE',
                'error_type': '資料錯誤',
                'message': f'BARCODE "{dup}" 有重複值',
                'suggestion': '請確保BARCODE在檔案內為唯一值',
                'value': dup
            })

def validate_rfid_unique(df, sheet_name, errors):
    """驗證RFID唯一性（如果有值）"""
    rfid_col = COLUMN_MAPPING['C']
    if rfid_col >= len(df.columns):
        return
    
    rfids = df.iloc[:, rfid_col].dropna()
    if len(rfids) == 0:
        return
    
    unique, counts = np.unique(rfids, return_counts=True)
    duplicates = unique[counts > 1]
    
    for dup in duplicates:
        duplicate_rows = df[df.iloc[:, rfid_col] == dup].index.tolist()
        for row in duplicate_rows:
            errors.append({
                'sheet': sheet_name,
                'row': row + 2,
                'column': 'C',
                'field': 'RFID',
                'error_type': '資料錯誤',
                'message': f'RFID "{dup}" 有重複值',
                'suggestion': '如果RFID有值，請確保為檔案內唯一值',
                'value': dup
            })

def validate_header(df, sheet_name, errors):
    """驗證表頭結構"""
    headers = df.columns.tolist()
    expected_headers = [rule['name'] for rule in HEADER_RULES.values()]
    
    if len(headers) < len(expected_headers):
        errors.append({
            'sheet': sheet_name,
            'row': 1,
            'column': '-',
            'field': '表頭結構',
            'error_type': '表頭結構異常',
            'message': f'欄位數量不足，預期 {len(expected_headers)} 欄，實際 {len(headers)} 欄',
            'suggestion': f'請確認表頭包含以下欄位：{", ".join(expected_headers)}',
            'value': f'實際有 {len(headers)} 欄'
        })
        return False
    
    for col_letter, rule in HEADER_RULES.items():
        col_idx = COLUMN_MAPPING[col_letter]
        if col_idx >= len(headers):
            errors.append({
                'sheet': sheet_name,
                'row': 1,
                'column': col_letter,
                'field': rule['name'],
                'error_type': '表頭結構異常',
                'message': f'缺少欄位 "{rule["name"]}"',
                'suggestion': f'請在 {col_letter} 欄添加 "{rule["name"]}"',
                'value': '缺少此欄'
            })
            continue
        
        actual_header = str(headers[col_idx]).strip()
        expected = rule['name']
        if actual_header != expected:
            if rule['required'] or (actual_header != '' and actual_header != expected):
                errors.append({
                    'sheet': sheet_name,
                    'row': 1,
                    'column': col_letter,
                    'field': expected,
                    'error_type': '表頭結構異常',
                    'message': f'欄位名稱不符，預期 "{expected}"，實際 "{actual_header}"',
                    'suggestion': f'請將 {col_letter} 欄改為 "{expected}"',
                    'value': actual_header
                })
    
    return True

def validate_data(df, sheet_name, errors):
    """驗證資料內容"""
    if len(df) == 0:
        return
    
    for idx, row in df.iterrows():
        excel_row = idx + 2
        
        for col_letter, rule in HEADER_RULES.items():
            col_idx = COLUMN_MAPPING[col_letter]
            if col_idx >= len(df.columns):
                continue
            
            value = row.iloc[col_idx] if col_idx < len(row) else np.nan
            field_name = rule['name']
            
            if rule['required']:
                if pd.isna(value) or str(value).strip() == '':
                    errors.append({
                        'sheet': sheet_name,
                        'row': excel_row,
                        'column': col_letter,
                        'field': field_name,
                        'error_type': '資料錯誤',
                        'message': f'{field_name} 不能為空',
                        'suggestion': f'請在 {col_letter} 欄填入 {field_name} 資料',
                        'value': '空值'
                    })
                    continue
            
            if field_name == '品牌':
                if not pd.isna(value) and str(value).strip() != '13':
                    errors.append({
                        'sheet': sheet_name,
                        'row': excel_row,
                        'column': col_letter,
                        'field': field_name,
                        'error_type': '資料錯誤',
                        'message': f'品牌值應為 "13"',
                        'suggestion': '請將品牌欄位設為 "13"',
                        'value': str(value)
                    })
            
            elif field_name == 'SHOE_KIND':
                if not pd.isna(value) and not validate_shoe_kind(value):
                    errors.append({
                        'sheet': sheet_name,
                        'row': excel_row,
                        'column': col_letter,
                        'field': field_name,
                        'error_type': '資料錯誤',
                        'message': f'鞋型 "{value}" 不在允許清單中',
                        'suggestion': f'請使用以下任一值：{", ".join(VALID_SHOE_KIND)}',
                        'value': str(value)
                    })
            
            elif field_name == 'STOCK_QTY':
                if not pd.isna(value):
                    if not validate_stock_qty(value):
                        errors.append({
                            'sheet': sheet_name,
                            'row': excel_row,
                            'column': col_letter,
                            'field': field_name,
                            'error_type': '資料錯誤',
                            'message': f'庫存數量 "{value}" 格式錯誤',
                            'suggestion': '庫存數量必須為正數且為0.5的倍數（如：1, 1.5, 2）',
                            'value': str(value)
                        })
            
            elif field_name == 'YYMM':
                if not pd.isna(value):
                    if not validate_year_month(value):
                        errors.append({
                            'sheet': sheet_name,
                            'row': excel_row,
                            'column': col_letter,
                            'field': field_name,
                            'error_type': '資料錯誤',
                            'message': f'YYMM "{value}" 格式錯誤',
                            'suggestion': 'YYMM必須為4位數字，前2位為年，後2位為月（如：2407）',
                            'value': str(value)
                        })

def analyze_file(file_path):
    """分析上傳的檔案"""
    errors = []
    total_records = 0
    error_records = set()
    
    try:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        for sheet_name in sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=0)
            
            if len(df) == 0:
                errors.append({
                    'sheet': sheet_name,
                    'row': 1,
                    'column': '-',
                    'field': '空白工作表',
                    'error_type': '資料錯誤',
                    'message': '工作表為空',
                    'suggestion': '請確認資料已正確填入',
                    'value': '空工作表'
                })
                continue
            
            total_records += len(df)
            
            validate_header(df, sheet_name, errors)
            validate_barcode_unique(df, sheet_name, errors)
            validate_rfid_unique(df, sheet_name, errors)
            validate_data(df, sheet_name, errors)
        
    except Exception as e:
        errors.append({
            'sheet': '系統錯誤',
            'row': '-',
            'column': '-',
            'field': '檔案讀取',
            'error_type': '系統錯誤',
            'message': f'讀取檔案時發生錯誤：{str(e)}',
            'suggestion': '請確認檔案格式正確且未損毀',
            'value': str(e)
        })
    
    error_count = len(errors)
    error_records_count = len(set(f"{e['sheet']}-{e['row']}" for e in errors if e['row'] != 1 and e['row'] != '-'))
    
    return {
        'total_records': total_records,
        'error_count': error_count,
        'error_records_count': error_records_count,
        'errors': errors
    }

def generate_error_excel(errors):
    """產生錯誤清單Excel檔案"""
    if not errors:
        return None
    
    df_errors = pd.DataFrame(errors)
    
    df_errors = df_errors.rename(columns={
        'sheet': '頁簽名稱',
        'row': 'EXCEL 列數',
        'column': 'EXCEL 欄數',
        'field': '異常欄位',
        'error_type': '錯誤類型',
        'message': '錯誤描述',
        'suggestion': '系統建議',
        'value': '實際抓取內容'
    })
    
    columns_order = ['頁簽名稱', 'EXCEL 列數', 'EXCEL 欄數', '異常欄位', '錯誤類型', '錯誤描述', '系統建議', '實際抓取內容']
    df_errors = df_errors[columns_order]
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_errors.to_excel(writer, sheet_name='錯誤清單', index=False)
        
        worksheet = writer.sheets['錯誤清單']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    return output

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '沒有選擇檔案'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '沒有選擇檔案'}), 400
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        return jsonify({'error': '檔案格式不支援，請上傳 Excel (.xlsx, .xls) 或 CSV 檔案'}), 400
    
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        result = analyze_file(filepath)
        
        error_excel = generate_error_excel(result['errors'])
        
        response = {
            'total_records': result['total_records'],
            'error_count': result['error_count'],
            'error_records_count': result['error_records_count'],
            'has_errors': result['error_count'] > 0,
            'errors': result['errors'][:1000]
        }
        
        if error_excel:
            error_filename = f"error_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            error_path = os.path.join(app.config['UPLOAD_FOLDER'], error_filename)
            with open(error_path, 'wb') as f:
                f.write(error_excel.getvalue())
            response['error_file'] = f'/download/{error_filename}'
        
        os.remove(filepath)
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'error': f'處理檔案時發生錯誤：{str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), 
                        as_attachment=True, 
                        download_name=filename)
    except Exception as e:
        return f'下載失敗：{str(e)}', 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
