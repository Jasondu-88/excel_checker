<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>成品庫存資料檢測系統</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .upload-area {
            border: 2px dashed #667eea;
            border-radius: 15px;
            padding: 60px 20px;
            text-align: center;
            background: #f8f9ff;
            transition: all 0.3s ease;
            cursor: pointer;
        }
        .upload-area:hover {
            border-color: #764ba2;
            background: #f0f0ff;
        }
        .upload-area.dragover {
            border-color: #764ba2;
            background: #e8e0ff;
        }
        .upload-icon {
            font-size: 60px;
            margin-bottom: 20px;
        }
        .upload-text {
            font-size: 18px;
            color: #555;
            margin-bottom: 10px;
        }
        .upload-hint {
            font-size: 14px;
            color: #999;
        }
        #fileInput {
            display: none;
        }
        #uploadBtn {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 40px;
            border-radius: 30px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
            margin-top: 20px;
        }
        #uploadBtn:hover {
            background: #764ba2;
        }
        #uploadBtn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .results {
            display: none;
            margin-top: 40px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #f8f9ff;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        .stat-number {
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }
        .stat-card.error {
            border-left-color: #f44336;
        }
        .stat-card.success {
            border-left-color: #4caf50;
        }
        .stat-card.warning {
            border-left-color: #ff9800;
        }
        .error-section {
            background: #fff5f5;
            border: 1px solid #fcc;
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
        }
        .error-section.success {
            background: #f0f8f0;
            border-color: #b8d4b8;
        }
        .error-table-wrapper {
            overflow-x: auto;
            margin-top: 20px;
        }
        .error-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        .error-table th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        .error-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        .error-table tr:hover {
            background: #f5f5ff;
        }
        .error-table .error-row {
            background: #fff0f0;
        }
        .error-table .error-row:hover {
            background: #ffe8e8;
        }
        .download-btn {
            display: inline-block;
            background: #4caf50;
            color: white;
            padding: 12px 30px;
            border-radius: 30px;
            text-decoration: none;
            font-weight: 600;
            margin-top: 20px;
            transition: background 0.3s;
            border: none;
            cursor: pointer;
            font-size: 16px;
        }
        .download-btn:hover {
            background: #388e3c;
        }
        .no-errors {
            text-align: center;
            padding: 30px;
            font-size: 18px;
            color: #4caf50;
        }
        .no-errors .icon {
            font-size: 60px;
            display: block;
            margin-bottom: 10px;
        }
        .file-info {
            margin: 15px 0;
            padding: 15px;
            background: #e3f2fd;
            border-radius: 8px;
            display: none;
        }
        .file-info .filename {
            font-weight: 600;
            color: #1976d2;
        }
        @media (max-width: 768px) {
            .container {
                padding: 20px;
            }
            .stats {
                grid-template-columns: 1fr 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 成品庫存開賬資料檢測系統</h1>
        <p class="subtitle">支援跨頁簽掃描、Barcode 唯一值鎖定及多項合規驗證</p>
        
        <div class="upload-area" id="uploadArea">
            <div class="upload-icon">📁</div>
            <div class="upload-text">請選擇或拖拽上傳您的 Excel / CSV 檔案</div>
            <div class="upload-hint">支援 .xlsx, .xls, .csv 格式，最大 50MB</div>
            <input type="file" id="fileInput" accept=".xlsx,.xls,.csv">
            <button id="uploadBtn">選擇檔案</button>
            <div id="fileInfo" class="file-info">
                <span>📄 已選擇：<span id="fileName" class="filename"></span></span>
                <button id="analyzeBtn" style="margin-left:15px;background:#4caf50;color:white;border:none;padding:8px 20px;border-radius:20px;cursor:pointer;">開始檢測</button>
            </div>
        </div>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>正在檢測中，請稍候...</p>
        </div>
        
        <div class="results" id="results">
            <h2>📋 檢測報告</h2>
            
            <div class="stats" id="stats"></div>
            
            <div id="errorSection">
                <h3>❌ 異常明細清單</h3>
                <div id="errorContent"></div>
            </div>
            
            <div id="downloadSection" style="text-align:center;margin-top:20px;"></div>
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const uploadBtn = document.getElementById('uploadBtn');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const stats = document.getElementById('stats');
        const errorContent = document.getElementById('errorContent');
        const downloadSection = document.getElementById('downloadSection');
        let selectedFile = null;

        // 點擊按鈕觸發檔案選擇
        uploadBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });

        // 點擊上傳區域觸發檔案選擇
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        // 檔案選擇
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                selectedFile = e.target.files[0];
                fileName.textContent = selectedFile.name;
                fileInfo.style.display = 'block';
                uploadBtn.textContent = '重新選擇';
            }
        });

        // 拖拽功能
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                selectedFile = e.dataTransfer.files[0];
                fileName.textContent = selectedFile.name;
                fileInfo.style.display = 'block';
                uploadBtn.textContent = '重新選擇';
                // 自動上傳
                uploadFile(selectedFile);
            }
        });

        // 分析按鈕
        analyzeBtn.addEventListener('click', () => {
            if (selectedFile) {
                uploadFile(selectedFile);
            }
        });

        function uploadFile(file) {
            const formData = new FormData();
            formData.append('file', file);

            loading.style.display = 'block';
            results.style.display = 'none';
            uploadArea.style.opacity = '0.5';

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';
                uploadArea.style.opacity = '1';
                results.style.display = 'block';
                
                if (data.error) {
                    alert('錯誤：' + data.error);
                    return;
                }
                
                displayResults(data);
            })
            .catch(error => {
                loading.style.display = 'none';
                uploadArea.style.opacity = '1';
                alert('上傳失敗：' + error.message);
            });
        }

        function displayResults(data) {
            // 顯示統計
            const errorRate = data.total_records > 0 ? ((data.error_records_count / data.total_records) * 100).toFixed(1) : 0;
            
            stats.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${data.total_records}</div>
                    <div class="stat-label">📊 總檢測筆數</div>
                </div>
                <div class="stat-card success">
                    <div class="stat-number">${data.total_records - data.error_records_count}</div>
                    <div class="stat-label">✅ 正確通過筆數</div>
                </div>
                <div class="stat-card error">
                    <div class="stat-number">${data.error_records_count}</div>
                    <div class="stat-label">❌ 發生異常筆數</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-number">${data.error_count}</div>
                    <div class="stat-label">⚠️ 錯誤項目總數</div>
                </div>
            `;

            // 顯示錯誤內容
            const errorSection = document.getElementById('errorSection');
            
            if (!data.has_errors || data.errors.length === 0) {
                errorContent.innerHTML = `
                    <div class="no-errors">
                        <span class="icon">🎉</span>
                        <p><strong>恭喜！未發現異常</strong></p>
                        <p style="color:#666;font-size:14px;margin-top:10px;">所有資料皆通過檢測</p>
                    </div>
                `;
                errorSection.querySelector('h3').textContent = '✅ 檢測通過';
                errorSection.className = 'error-section success';
            } else {
                errorSection.className = 'error-section';
                let tableHtml = `
                    <div class="error-table-wrapper">
                        <table class="error-table">
                            <thead>
                                <tr>
                                    <th>頁簽名稱</th>
                                    <th>EXCEL 列數</th>
                                    <th>EXCEL 欄數</th>
                                    <th>異常欄位</th>
                                    <th>錯誤類型</th>
                                    <th>錯誤描述</th>
                                    <th>系統建議</th>
                                    <th>實際抓取內容</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                
                data.errors.forEach(err => {
                    tableHtml += `
                        <tr class="error-row">
                            <td>${err.sheet || '-'}</td>
                            <td>${err.row || '-'}</td>
                            <td>${err.column || '-'}</td>
                            <td>${err.field || '-'}</td>
                            <td><strong>${err.error_type || '-'}</strong></td>
                            <td>${err.message || '-'}</td>
                            <td style="color:#1976d2;">${err.suggestion || '-'}</td>
                            <td>${err.value || '-'}</td>
                        </tr>
                    `;
                });
                
                tableHtml += `</tbody></table></div>`;
                errorContent.innerHTML = tableHtml;
                
                if (data.errors.length > 1000) {
                    errorContent.innerHTML += `<p style="color:#ff9800;margin-top:10px;">⚠️ 顯示前 1000 筆錯誤，完整清單請下載錯誤報表</p>`;
                }
                
                // 顯示下載按鈕
                if (data.error_file) {
                    downloadSection.innerHTML = `
                        <a href="${data.error_file}" class="download-btn" download>
                            📥 匯出錯誤清單 (Excel)
                        </a>
                    `;
                }
            }
        }
    </script>
</body>
</html>
