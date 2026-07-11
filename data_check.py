# data_check.py
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
import re

# 頁面設定
st.set_page_config(
    page_title="成品庫存資料開賬檢測工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自訂 CSS 樣式
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: #f8f9ff;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #333;
    }
    .stat-label {
        color: #666;
        font-size: 0.9rem;
    }
    .error-stat {
        border-left-color: #f44336;
    }
    .success-stat {
        border-left-color: #4caf50;
    }
    .warning-stat {
        border-left-color: #ff9800;
    }
    .error-table {
        font-size: 0.9rem;
    }
    .download-btn {
        background: #4caf50;
        color: white;
        padding: 0.5rem 2rem;
        border-radius: 25px;
        text-decoration: none;
        font-weight: 600;
        border: none;
        cursor: pointer;
    }
    .download-btn:hover {
        background: #388e3c;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
    }
    .error-box {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 10px;
        padding: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ============ 核心檢測函數 ============

# 定義表頭規則
HEADER_RULES = {
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

# 預期表頭列表（用於顯示）
EXPECTED_HEADERS = [rule['name'] for rule in HEADER_RULES.values()]

def validate_year_month(yymm):
    """驗證YYMM格式（6位字符型年月）"""
    if not yymm:
        return False
    yymm_str = str(yymm).strip()
    # 檢查是否為6位數字
    if len(yymm_str) != 6:
        return False
    if not yymm_str.isdigit():
        return False
    # 前4位為年，後2位為月
    year = int(yymm_str[:4])
    month = int(yymm_str[4:])
    # 年份範圍：2000-2099
    if year < 2000 or year > 2099:
        return False
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
    
    # 獲取BARCODE欄位數據
    barcodes = df.iloc[:, barcode_col].dropna()
    if len(barcodes) == 0:
        return
    
    # 檢查重複值
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
    
    # 檢查欄位數量
    if len(headers) < len(EXPECTED_HEADERS):
        errors.append({
            'sheet': sheet_name,
            'row': 1,
            'column': '-',
            'field': '表頭結構',
            'error_type': '表頭結構異常',
            'message': f'欄位數量不足，預期 {len(EXPECTED_HEADERS)} 欄，實際 {len(headers)} 欄',
            'suggestion': f'請確認表頭包含以下欄位：{", ".join(EXPECTED_HEADERS)}',
            'value': f'實際有 {len(headers)} 欄'
        })
        return False
    
    # 檢查每個欄位
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
        
        # 檢查欄位名稱是否匹配
        if actual_header != expected:
            # 如果是"可以為空"欄位，只要不是空值就報錯
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
            
            # 驗證必要欄位不能為空
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
            
            # 特定欄位驗證
            if field_name == '品牌':
                if not pd.isna(value) and str(value).strip() != '13':
                    errors.append({
                        'sheet': sheet_name,
                        'row': excel_row,
                        'column': col_letter,
                        'field': field_name,
                        'error_type': '資料錯誤',
                        'message': f'品牌值應為 "13"，實際為 "{value}"',
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
                            'suggestion': 'YYMM必須為6位數字，前4位為年，後2位為月（如：202407）',
                            'value': str(value)
                        })

def analyze_file(uploaded_file):
    """分析上傳的檔案"""
    errors = []
    total_records = 0
    sheet_count = 0
    
    try:
        # 根據檔案類型讀取
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'csv':
            # 讀取CSV檔案
            df = pd.read_csv(uploaded_file, header=0)
            sheet_name = 'Sheet1'
            sheet_count = 1
            
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
            else:
                total_records += len(df)
                validate_header(df, sheet_name, errors)
                validate_barcode_unique(df, sheet_name, errors)
                validate_rfid_unique(df, sheet_name, errors)
                validate_data(df, sheet_name, errors)
        
        else:
            # 讀取Excel檔案的所有工作表
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            sheet_count = len(sheet_names)
            
            for sheet_name in sheet_names:
                df = pd.read_excel(uploaded_file, sheet_name=sheet_name, header=0)
                
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
    
    # 計算異常筆數（排除表頭錯誤和系統錯誤）
    error_records_count = len(set(
        f"{e['sheet']}-{e['row']}" 
        for e in errors 
        if e.get('row') not in [1, '-'] and e.get('error_type') != '表頭結構異常'
    ))
    
    return {
        'total_records': total_records,
        'sheet_count': sheet_count,
        'error_count': len(errors),
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
        'row': 'EXCEL列數',
        'column': 'EXCEL欄數',
        'field': '異常欄位',
        'error_type': '錯誤類型',
        'message': '錯誤描述',
        'suggestion': '系統建議',
        'value': '實際抓取內容'
    })
    
    columns_order = ['頁簽名稱', 'EXCEL列數', 'EXCEL欄數', '異常欄位', '錯誤類型', '錯誤描述', '系統建議', '實際抓取內容']
    df_errors = df_errors[columns_order]
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_errors.to_excel(writer, sheet_name='錯誤清單', index=False)
        
        # 調整欄位寬度
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

# ============ Streamlit UI ============

def main():
    # 標題區域
    st.markdown("""
    <div class="main-header">
        <h1>📊 成品庫存開賬資料檢測工具</h1>
        <p style="font-size: 1.1rem; opacity: 0.9;">支援跨頁簽掃描、Barcode 唯一值鎖定及多項合規驗證</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 側邊欄 - 檢測規則說明
    with st.sidebar:
        st.markdown("### 📋 檢測規則說明")
        
        with st.expander("📌 表頭結構要求", expanded=True):
            st.markdown("""
            | 欄位 | 名稱 | 必填 |
            |:---:|:---|:---:|
            | A | 可以為空 | ❌ |
            | B | **BARCODE** | ✅ |
            | C | RFID | ❌ |
            | D | **倉庫代號** | ✅ |
            | E | **儲位代號** | ✅ |
            | F | **品牌** | ✅ |
            | G | **MODEL_NAME** | ✅ |
            | H | **ARTICLE** | ✅ |
            | I | **COLOR_CODE** | ✅ |
            | J | 底模 | ❌ |
            | K | **size** | ✅ |
            | L | **SHOE_KIND** | ✅ |
            | M | **STOCK_QTY** | ✅ |
            | N | **YYMM** | ✅ |
            """)
        
        with st.expander("🔍 資料驗證規則", expanded=True):
            st.markdown("""
            **BARCODE**
            - 不能為空值
            - 同一檔案內不得重複
            
            **RFID**
            - 可以為空值
            - 有值時不得重複
            
            **品牌**
            - 固定值為 **13**
            
            **SHOE_KIND**
            - 只能為：FL, FR, UL, UR, BL, BR
            
            **STOCK_QTY**
            - 正數且為 0.5 的倍數
            
            **YYMM**
            - 6位數字（如：202407）
            - 前4位年，後2位月
            """)
        
        st.markdown("---")
        st.caption("💡 支援 .xlsx, .xls, .csv 格式")
    
    # 主要內容區域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "📁 請選擇或拖拽上傳您的 Excel / CSV 檔案",
            type=['xlsx', 'xls', 'csv'],
            help="支援 .xlsx, .xls, .csv 格式，自動掃描所有頁簽"
        )
    
    with col2:
        st.markdown("""
        <div style="background: #e3f2fd; padding: 1.2rem; border-radius: 10px; margin-top: 1.8rem;">
            <p style="margin:0; font-size:0.9rem; color:#1976d2;">
                <strong>📌 使用說明</strong><br>
                1. 點擊上傳按鈕選擇檔案<br>
                2. 系統自動進行全面檢測<br>
                3. 查看檢測報告與異常清單<br>
                4. 下載錯誤清單進行修正
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # 處理上傳的檔案
    if uploaded_file is not None:
        st.markdown("---")
        
        # 顯示檔案資訊
        file_size = uploaded_file.size / 1024
        file_size_str = f"{file_size:.1f} KB" if file_size < 1024 else f"{file_size/1024:.2f} MB"
        
        st.info(f"📄 **已上傳：** {uploaded_file.name} ({file_size_str})")
        
        # 執行檢測
        with st.spinner("🔄 正在檢測中，請稍候..."):
            result = analyze_file(uploaded_file)
        
        # 顯示檢測報告
        st.markdown("### 📊 檢測報告與數據統計")
        
        # 統計卡片
        col1, col2, col3, col4 = st.columns(4)
        
        correct_count = result['total_records'] - result['error_records_count']
        
        with col1:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{result['total_records']}</div>
                <div class="stat-label">📊 總檢測筆數</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="stat-card success-stat">
                <div class="stat-number">{correct_count}</div>
                <div class="stat-label">✅ 正確通過筆數</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="stat-card error-stat">
                <div class="stat-number">{result['error_records_count']}</div>
                <div class="stat-label">❌ 發生異常筆數</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="stat-card warning-stat">
                <div class="stat-number">{result['error_count']}</div>
                <div class="stat-label">⚠️ 錯誤項目總數</div>
            </div>
            """, unsafe_allow_html=True)
        
        # 頁簽數量資訊
        if result['sheet_count'] > 1:
            st.caption(f"📑 共檢測 {result['sheet_count']} 個頁簽")
        
        # 顯示錯誤明細
        st.markdown("---")
        st.markdown("### ❌ 異常明細清單")
        
        if result['error_count'] == 0:
            st.markdown("""
            <div class="success-box">
                <h2 style="color: #155724;">🎉 恭喜！未發現異常</h2>
                <p style="color: #155724; font-size: 1.1rem;">所有資料皆通過檢測</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"⚠️ 發現 {result['error_count']} 個異常項目")
            
            # 顯示錯誤表格
            if result['errors']:
                df_errors = pd.DataFrame(result['errors'])
                
                # 重新命名欄位
                df_errors_display = df_errors.rename(columns={
                    'sheet': '頁簽名稱',
                    'row': 'EXCEL列數',
                    'column': 'EXCEL欄數',
                    'field': '異常欄位',
                    'error_type': '錯誤類型',
                    'message': '錯誤描述',
                    'suggestion': '系統建議',
                    'value': '實際抓取內容'
                })
                
                # 使用 st.dataframe 顯示
                st.dataframe(
                    df_errors_display,
                    use_container_width=True,
                    height=400,
                    column_config={
                        "頁簽名稱": st.column_config.TextColumn("頁簽名稱", width="small"),
                        "EXCEL列數": st.column_config.TextColumn("EXCEL列數", width="small"),
                        "EXCEL欄數": st.column_config.TextColumn("EXCEL欄數", width="small"),
                        "異常欄位": st.column_config.TextColumn("異常欄位", width="small"),
                        "錯誤類型": st.column_config.TextColumn("錯誤類型", width="small"),
                        "錯誤描述": st.column_config.TextColumn("錯誤描述", width="medium"),
                        "系統建議": st.column_config.TextColumn("系統建議", width="medium"),
                        "實際抓取內容": st.column_config.TextColumn("實際抓取內容", width="small"),
                    }
                )
                
                # 產生並下載錯誤清單
                st.markdown("---")
                st.markdown("### 📥 檔案匯出")
                
                error_excel = generate_error_excel(result['errors'])
                if error_excel:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        st.download_button(
                            label="📥 匯出錯誤清單 (Excel)",
                            data=error_excel,
                            file_name=f"error_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            type="primary"
                        )
    
    else:
        # 未上傳檔案時的歡迎訊息
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 2rem 0;">
                <p style="font-size: 3rem;">📁</p>
                <h3>歡迎使用【成品資料智慧檢測系統】</h3>
                <p style="color: #666;">系統已就緒，支援跨頁簽掃描、Barcode 唯一值鎖定及合規驗證</p>
                <p style="color: #999; font-size: 0.9rem;">請點擊上傳按鈕選擇您的 Excel / CSV 檔案</p>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
