const API_BASE = window.location.origin + "/api";

const INDUSTRY_CATEGORY_MAP = {
    'tech': ['半導體', '電腦及週邊設備', '通信網路', '光電', '電子零組件', '電子通路', '資訊服務', '其他電子', '科技', 'Technology', 'Semiconductors', 'Electronic', 'Software', 'Computing', 'Electronic Components', 'Consumer Electronics', 'Communication Equipment', 'Computer Hardware'],
    'finance': ['金融保險', '金融服務', 'Financial', 'Insurance', 'Banking', 'Banks', 'Credit Services'],
    'material': ['塑膠', '橡膠', '化學', '油電燃氣', '水泥', '玻璃陶瓷', '鋼鐵', '各類材料', '基本材料', 'Basic Materials', 'Chemicals', 'Steel', 'Specialty Chemicals', 'Oil & Gas', 'Lumber'],
    'consumer': ['食品', '紡織纖維', '觀光', '觀光事業', '消費循環', '消費防禦', 'Consumer Cyclical', 'Consumer Defensive', 'Food', 'Textiles', 'Beverages', 'Apparel', 'Auto Manufacturers'],
    'medical': ['生技醫療', '醫療保健', 'Healthcare', 'Biotechnology', 'Medical', 'Drug Manufacturers', 'Medical Devices'],
    'construction': ['建材營造', '房地產', 'Real Estate', 'Construction', 'Building Products', 'Residential Construction'],
    'industrial': ['電機機械', '電器電纜', '造紙', '汽車', '工業', 'Industrials', 'Machinery', 'Electrical', 'Conglomerates', 'Aerospace'],
    'shipping': ['航運', '能源', '公用事業', 'Energy', 'Utilities', 'Transportation', 'Shipping', 'Air Freight'],
    'commerce': ['貿易百貨', '文化創意', '電商', '通訊服務', 'Communication Services', 'Retailing', 'Media', 'Entertainment'],
    'others': ['其他', '未分類', 'Other', 'Miscellaneous']
};

const DEFAULT_INDUSTRIES = [
    '半導體', '光電', '通信網路', '金融保險', '建材營造', '航運', '其他'
];

document.addEventListener('DOMContentLoaded', function() {
    // 初始化界面元素
    initializeUI();
    // 載入可用日期
    loadAvailableDates();
    // 初始化產業過濾選項
    updateIndustryFilterOptions(DEFAULT_INDUSTRIES);
    // 加載保存的設置
    loadSavedSettings();
    // 顯示已保存的結果(如果有)
    displaySavedResults();
});

// 初始化界面元素和事件監聽
function initializeUI() {
    // 主要控制按鈕
    const screenBtn = document.getElementById('screen-btn');
    const updateBtn = document.getElementById('update-btn');
    
    // 驗證相關元素
    const verifyPriceCheckbox = document.getElementById('verify-price');
    const verifyWeeksSlider = document.getElementById('verify-weeks');
    const verifyWeeksValue = document.getElementById('verify-weeks-value');
    const verifyPercentSlider = document.getElementById('verify-percent');
    const verifyPercentValue = document.getElementById('verify-percent-value');
    const filterVerifiedCheckbox = document.getElementById('filter-verified');
    const verifyFilterContainer = document.getElementById('verify-filter-container');
    
    // 驗證價格功能切換
    verifyPriceCheckbox.addEventListener('change', function() {
        const isChecked = this.checked;
        verifyWeeksSlider.disabled = !isChecked;
        verifyPercentSlider.disabled = !isChecked;
        
        // 更新驗證組的樣式
        const verifyGroups = document.querySelectorAll('.verify-group');
        verifyGroups.forEach(group => {
            if (isChecked) {
                group.classList.add('active');
            } else {
                group.classList.remove('active');
            }
        });
        
        // 儲存設置到 localStorage
        localStorage.setItem('verify_price', isChecked);
    });

    // 產業類別連動觸發
    const industryCategorySelect = document.getElementById('industry-category-filter');
    const industrySelect = document.getElementById('industry-filter');
    
    industryCategorySelect.addEventListener('change', function() {
        const category = this.value;
        updateSubIndustryOptions(category);
    });

    // 驗證週數滑桿變化
    verifyWeeksSlider.addEventListener('input', function() {
        verifyWeeksValue.textContent = `${this.value}週`;
        localStorage.setItem('verify_weeks', this.value);
    });

    // 驗證百分比滑桿變化
    verifyPercentSlider.addEventListener('input', function() {
        verifyPercentValue.textContent = `${this.value}%`;
        localStorage.setItem('verify_percent', this.value);
    });

    // 其他控制滑桿
    const retailLevelSlider = document.getElementById('retail-level');
    const retailLevelValue = document.getElementById('retail-level-value');
    
    const getRetailDesc = (val) => {
        const levels = {
            '5': '≤5張', '6': '≤10張', '7': '≤15張', '8': '≤20張', 
            '9': '≤50張', '10': '≤80張', '11': '≤100張'
        };
        return levels[val] || '';
    };

    retailLevelSlider.addEventListener('input', function() {
        retailLevelValue.textContent = `減少 (${this.value}級: ${getRetailDesc(this.value)})`;
    });

    const largeLevelSlider = document.getElementById('large-level');
    const largeLevelValue = document.getElementById('large-level-value');
    
    const getLargeDesc = (val) => {
        const levels = {
            '13': '≥200張', '14': '≥400張', '15': '≥600張'
        };
        return levels[val] || '';
    };

    largeLevelSlider.addEventListener('input', function() {
        largeLevelValue.textContent = `增加 (${this.value}級: ${getLargeDesc(this.value)})`;
    });

    // 初始化顯示
    retailLevelValue.textContent = `減少 (${retailLevelSlider.value}級: ${getRetailDesc(retailLevelSlider.value)})`;
    largeLevelValue.textContent = `增加 (${largeLevelSlider.value}級: ${getLargeDesc(largeLevelSlider.value)})`;

    const weeksSlider = document.getElementById('weeks');
    const weeksValue = document.getElementById('weeks-value');
    weeksSlider.addEventListener('input', function() {
        weeksValue.textContent = `${this.value}週`;
    });

    const maDiffSlider = document.getElementById('ma-diff');
    const maDiffValue = document.getElementById('ma-diff-value');
    maDiffSlider.addEventListener('input', function() {
        maDiffValue.textContent = `≤${this.value}%`;
    });

    const volRatioSlider = document.getElementById('vol-ratio');
    const volRatioValue = document.getElementById('vol-ratio-value');
    volRatioSlider.addEventListener('input', function() {
        volRatioValue.textContent = `≥${this.value}倍`;
    });

    // 篩選驗證達標股票
    filterVerifiedCheckbox.addEventListener('change', function() {
        const stocks = JSON.parse(localStorage.getItem('lastScreenResults') || '[]');
        displayResults(stocks, this.checked);
        localStorage.setItem('filter_verified', this.checked);
    });

    // 篩選按鈕點擊事件
    screenBtn.addEventListener('click', startScreening);
    
    // 更新資料按鈕點擊事件
    updateBtn.addEventListener('click', updateData);

    // 重置按鈕點擊事件
    const resetBtn = document.getElementById('reset-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetSystemState);
    }
    
    // 股價圖表模態框相關事件
    initChartModalEvents();
}

// 初始化股價圖表模態框事件
function initChartModalEvents() {
    const chartModal = document.getElementById('chart-modal');
    const closeModal = document.getElementById('close-modal');
    
    // 關閉模態框按鈕
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            chartModal.classList.add('hidden');
        });
    }
    
    // 點擊模態框背景關閉
    if (chartModal) {
        chartModal.addEventListener('click', (e) => {
            if (e.target === chartModal) {
                chartModal.classList.add('hidden');
            }
        });
    }
}

// 加載保存的設置
function loadSavedSettings() {
    // 從本地存儲加載設置
    const verifyPrice = localStorage.getItem('verify_price') === 'true';
    const verifyWeeks = localStorage.getItem('verify_weeks');
    const verifyPercent = localStorage.getItem('verify_percent');
    const filterVerified = localStorage.getItem('filter_verified') === 'true';
    
    const verifyPriceCheckbox = document.getElementById('verify-price');
    const verifyWeeksSlider = document.getElementById('verify-weeks');
    const verifyWeeksValue = document.getElementById('verify-weeks-value');
    const verifyPercentSlider = document.getElementById('verify-percent');
    const verifyPercentValue = document.getElementById('verify-percent-value');
    const filterVerifiedCheckbox = document.getElementById('filter-verified');
    
    // 設置驗證選項
    if (verifyPrice) {
        verifyPriceCheckbox.checked = true;
        verifyWeeksSlider.disabled = false;
        verifyPercentSlider.disabled = false;
        
        // 更新驗證組的樣式
        const verifyGroups = document.querySelectorAll('.verify-group');
        verifyGroups.forEach(group => group.classList.add('active'));
    }
    
    if (verifyWeeks) {
        verifyWeeksSlider.value = verifyWeeks;
        verifyWeeksValue.textContent = `${verifyWeeks}週`;
    }
    
    if (verifyPercent) {
        verifyPercentSlider.value = verifyPercent;
        verifyPercentValue.textContent = `${verifyPercent}%`;
    }
    
    filterVerifiedCheckbox.checked = filterVerified !== null ? filterVerified : true;
}

// 顯示已保存的篩選結果
function displaySavedResults() {
    const savedResults = localStorage.getItem('lastScreenResults');
    if (savedResults) {
        const results = JSON.parse(savedResults);
        const verifyFilterContainer = document.getElementById('verify-filter-container');
        const verifyColumns = document.querySelectorAll('.verify-col');
        const filterVerifiedCheckbox = document.getElementById('filter-verified');
        
        // 檢查是否包含驗證結果
        const hasVerifyResults = results.some(stock => 'verify_price_change_pct' in stock);
        
        // 顯示或隱藏驗證相關欄位
        if (hasVerifyResults) {
            verifyFilterContainer.classList.remove('hidden');
            verifyColumns.forEach(col => col.classList.remove('hidden'));
        } else {
            verifyFilterContainer.classList.add('hidden');
            verifyColumns.forEach(col => col.classList.add('hidden'));
        }
        
        // 顯示結果
        const filterVerified = localStorage.getItem('filter_verified') === 'true';
        displayResults(results, filterVerified && hasVerifyResults);
    }
}

// 顯示狀態訊息
function showMessage(msg, type) {
    const statusMsg = document.getElementById('status-msg');
    const isUpdating = document.getElementById('progress-container').classList.contains('hidden') === false;
    
    // 如果正在進行耗時任務，不要清除狀態顯示，除非是錯誤
    statusMsg.textContent = msg;
    statusMsg.className = `status-msg msg-${type}`;
    
    if (type !== 'info' || !isUpdating) {
        setTimeout(() => {
            // 只有在當前訊息與之前沒變時才清除
            if (statusMsg.textContent === msg) {
                statusMsg.textContent = '';
                statusMsg.className = 'status-msg';
            }
        }, 8000);
    }
}

// 更新產業過濾選項
function updateIndustryFilterOptions(availableIndustries) {
    const industryFilter = document.getElementById('industry-filter');
    const currentValue = industryFilter.value;
    
    // 清空現有選項
    industryFilter.innerHTML = '';
    
    // 新增「全部產業」選項
    const allOption = document.createElement('option');
    allOption.value = 'all';
    allOption.textContent = '全部產業';
    industryFilter.appendChild(allOption);
    
    // 新增可用的產業選項
    availableIndustries.forEach(industry => {
        const option = document.createElement('option');
        option.value = industry;
        option.textContent = industry;
        industryFilter.appendChild(option);
    });
    
    // 恢復之前選擇的值，如果還存在的話
    if (currentValue && (currentValue === 'all' || availableIndustries.includes(currentValue))) {
        industryFilter.value = currentValue;
    }
}

// 載入可用日期
async function loadAvailableDates() {
    const loadingSpinner = document.getElementById('loading-spinner');
    loadingSpinner.classList.remove('hidden');
    
    try {
        const res = await fetch(`${API_BASE}/dates`);
        const data = await res.json();
        
        if (data.status === 'success' && data.dates.length > 0) {
            const startDateSelect = document.getElementById('start-date');
            const endDateSelect = document.getElementById('end-date');
            
            // 清空現有選項，保留第一個
            startDateSelect.innerHTML = '<option value="">從最早資料</option>';
            endDateSelect.innerHTML = '<option value="">到最新資料</option>';
            
            // 添加日期選項
            data.dates.forEach(dateObj => {
                const date = dateObj.date;
                const formattedDate = formatDate(date);
                const count = dateObj.count;
                
                const startOption = document.createElement('option');
                startOption.value = date;
                startOption.textContent = `${formattedDate} (${count}檔)`;
                startDateSelect.appendChild(startOption);
                
                const endOption = document.createElement('option');
                endOption.value = date;
                endOption.textContent = `${formattedDate} (${count}檔)`;
                endDateSelect.appendChild(endOption);
            });
            
            showMessage(`已載入 ${data.dates.length} 筆資料日期`, 'info');
            
            // 自動檢測是否需要更新當週數據
            checkAutoUpdate(data.dates);
        } else {
            showMessage('沒有可用的資料日期', 'warning');
            // 如果完全沒資料，也嘗試自動更新最初的12週
            updateData();
        }
    } catch (err) {
        console.error('Error loading dates:', err);
        showMessage('載入日期資料失敗', 'error');
    } finally {
        loadingSpinner.classList.add('hidden');
    }
}

// 自動檢測邏輯：檢查最新資料是否為本週五
function checkAutoUpdate(dates) {
    if (!dates || dates.length === 0) return;
    
    const latestDateStr = dates[0].date; // YYYYMMDD
    const latestDate = new Date(
        latestDateStr.substring(0, 4),
        latestDateStr.substring(4, 6) - 1,
        latestDateStr.substring(6, 8)
    );
    
    const now = new Date();
    const dayOfWeek = now.getDay(); // 0:Sunday, 5:Friday
    
    // 計算最近一個週五的日期
    let lastFriday = new Date(now);
    let diff = dayOfWeek >= 5 ? (dayOfWeek - 5) : (dayOfWeek + 2);
    lastFriday.setDate(now.getDate() - diff);
    lastFriday.setHours(21, 0, 0, 0); // 假設週五 21:00 後才有資料
    
    // 如果現在已經過週五晚上 9 點，且資料還停留在上週五以前
    if (now > lastFriday && latestDate < lastFriday) {
        console.log("偵測到新數據可能已發布，觸發自動更新...");
        showMessage('偵測到新數據發布，正在自動同步本週資料...', 'info');
        updateData();
    }
}

// 格式化日期
function formatDate(dateStr) {
    // 將 YYYYMMDD 格式轉為 YYYY-MM-DD
    return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`;
}

// 格式化漲跌數據
function formatChange(val, isPercent = false) {
    const symbol = val > 0 ? '+' : '';
    const colorClass = val > 0 ? 'text-positive' : (val < 0 ? 'text-negative' : '');
    const unit = isPercent ? '%' : ' 人';
    return `<span class="${colorClass}">${symbol}${val}${unit}</span>`;
}

// 更新資料
async function updateData() {
    const loadingSpinner = document.getElementById('loading-spinner');
    loadingSpinner.classList.remove('hidden');
    showMessage('正在更新資料...', 'info');
    
    try {
        const weeksInput = document.getElementById('update-weeks-input');
        const weeks = parseInt(weeksInput.value) || 12;
        
        // 啟動進度輪詢
        checkScreeningProgress();
        
        const res = await fetch(`${API_BASE}/update_data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ weeks }),
        });
        
        const data = await res.json();
        
        if (data.status === 'success') {
            showMessage(data.message, 'info');
        } else {
            showMessage(`資料更新失敗: ${data.message}`, 'error');
            loadingSpinner.classList.add('hidden');
        }
    } catch (err) {
        console.error('Error updating data:', err);
        showMessage('資料更新過程發生錯誤', 'error');
        loadingSpinner.classList.add('hidden');
    }
}

// 開始篩選
async function startScreening() {
    const loadingSpinner = document.getElementById('loading-spinner');
    const verifyPriceCheckbox = document.getElementById('verify-price');
    const verifyWeeksSlider = document.getElementById('verify-weeks');
    const verifyPercentSlider = document.getElementById('verify-percent');
    const verifyFilterContainer = document.getElementById('verify-filter-container');
    const verifyColumns = document.querySelectorAll('.verify-col');
    
    loadingSpinner.classList.remove('hidden');
    showMessage('正在篩選股票...', 'info');
    
    const retailLevel = document.getElementById('retail-level').value;
    const largeLevel = document.getElementById('large-level').value;
    const weeks = document.getElementById('weeks').value;
    const maDiffPercent = document.getElementById('ma-diff').value;
    const volRatio = document.getElementById('vol-ratio').value;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const industryFilter = document.getElementById('industry-filter').value === 'all' ? null : document.getElementById('industry-filter').value;
    
    const verify = verifyPriceCheckbox.checked;
    const verifyWeeks = parseInt(verifyWeeksSlider.value);
    const verifyPercent = parseInt(verifyPercentSlider.value);
    
    if (verify) {
        verifyFilterContainer.classList.remove('hidden');
        verifyColumns.forEach(col => col.classList.remove('hidden'));
    } else {
        verifyFilterContainer.classList.add('hidden');
        verifyColumns.forEach(col => col.classList.add('hidden'));
    }

    try {
        checkScreeningProgress();
        
        const res = await fetch(`${API_BASE}/screener`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                retail_level: parseInt(retailLevel),
                large_level: parseInt(largeLevel),
                weeks: parseInt(weeks),
                ma_diff_percent: parseFloat(maDiffPercent),
                vol_ratio: parseFloat(volRatio),
                start_date: startDate || null,
                end_date: endDate || null,
                industry_filter: industryFilter,
                verify: verify,
                verify_weeks: verifyWeeks,
                verify_percent: verifyPercent
            }),
        });
        
        const data = await res.json();
        if (data.status === 'success') {
            showMessage(data.message, 'info');
        } else {
            showMessage(`篩選失敗: ${data.message}`, 'error');
            loadingSpinner.classList.add('hidden');
        }
    } catch (err) {
        console.error('Error starting screen:', err);
        showMessage('篩選請求失敗', 'error');
        loadingSpinner.classList.add('hidden');
    }
}

// 檢查進度 (遞迴輪詢)
async function checkScreeningProgress() {
    const progressBar = document.getElementById('progress-bar');
    const progressContainer = document.getElementById('progress-container');
    const progressPercent = document.getElementById('progress-percent');
    const progressState = document.getElementById('progress-state');
    
    progressContainer.classList.remove('hidden');
    
    // 將 isFinished 提升到全域或讓 reset 能存取
    window.currentPollingFinished = false;

    async function poll() {
        if (window.currentPollingFinished) return;
        try {
            const res = await fetch(`${API_BASE}/progress`);
            const progress = await res.json();
            
            if (progress.percent < 100 && progress.percent >= 0) {
                // 更新實體進度條
                progressBar.style.width = `${progress.percent}%`;
                
                // 格式化顯示: 75% (150/200 筆)
                let countText = '';
                if (progress.total > 0) {
                    countText = ` (${progress.current}/${progress.total} 筆)`;
                }
                progressPercent.textContent = `${progress.percent}%${countText}`;
                let etaLabel = document.getElementById('eta-label');
                
                // 如果找不到標籤（可能 HTML 修改失敗），則動態創建它
                if (!etaLabel) {
                    const statusContainer = progressContainer.querySelector('.progress-status-container') || progressContainer.querySelector('.progress-header');
                    etaLabel = document.createElement('span');
                    etaLabel.id = 'eta-label';
                    etaLabel.className = 'hidden';
                    statusContainer.appendChild(etaLabel);
                }

                if (progress.eta > 0) {
                    const etaMinutes = Math.floor(progress.eta / 60);
                    const etaSeconds = progress.eta % 60;
                    const etaText = `剩餘約 ${etaMinutes > 0 ? etaMinutes + '分' : ''}${etaSeconds}秒`;
                    etaLabel.textContent = etaText;
                    etaLabel.classList.remove('hidden');
                    // 同時更新顯示文字狀態
                    progressState.textContent = '計算下載中...';
                } else {
                    etaLabel.classList.add('hidden');
                    progressState.textContent = '正在獲取站內資料...';
                }
                setTimeout(poll, 1500);
            } else if (progress.percent >= 100) {
                window.currentPollingFinished = true;
                progressBar.style.width = '100%';
                progressPercent.textContent = '100%';
                progressState.textContent = '完成';
                
                try {
                    const resultRes = await fetch(`${API_BASE}/results`);
                    const resultData = await resultRes.json();
                    
                    if (resultData.status === 'processing') {
                        window.currentPollingFinished = false;
                        setTimeout(poll, 2000);
                        return;
                    }

                    if (resultData.status === 'success') {
                        const results = resultData.data;
                        if (results && !Array.isArray(results) && results.status) {
                            showMessage(`更新完成!`, 'success');
                            loadAvailableDates();
                        } else {
                            localStorage.setItem('lastScreenResults', JSON.stringify(results));
                            const verifyPriceCheckbox = document.getElementById('verify-price');
                            displayResults(results, document.getElementById('filter-verified').checked && verifyPriceCheckbox.checked);
                            showMessage(`篩選完成，找到 ${results ? results.length : 0} 檔股票`, 'success');
                        }
                    }
                } catch (e) {
                    console.error('Final result fetch error:', e);
                } finally {
                    setTimeout(() => {
                        progressContainer.classList.add('hidden');
                        document.getElementById('loading-spinner').classList.add('hidden');
                    }, 2000);
                }
            }
        } catch (e) {
            console.error('Progress poll error:', e);
            setTimeout(poll, 3000);
        }
    }
    poll();
}


// 顯示篩選結果
function displayResults(results, filterVerified = false) {
    const tableBody = document.getElementById('table-body');
    const resultCount = document.getElementById('result-count');
    const industryCategory = document.getElementById('industry-category-filter').value;
    const industrySub = document.getElementById('industry-filter').value;
    
    tableBody.innerHTML = '';
    
    if (!results) return;

    // 層級 1: 驗證過濾與產業過濾
    let filteredResults = results.filter(stock => {
        // 1. 驗證過濾
        if (filterVerified && stock.verify_meets_criteria === false) return false;
        
        // 2. 產業細項過濾
        if (industrySub !== 'all' && stock.industry !== industrySub) return false;
        
        // 3. 產業大類過濾 (如果細項選了 all，則檢查大類)
        if (industrySub === 'all' && industryCategory !== 'all') {
            const allowedList = (INDUSTRY_CATEGORY_MAP[industryCategory] || []).map(i => i.toLowerCase());
            const currentIndustry = (stock.industry || '未分類').toLowerCase();
            
            // 強化匹配：如果 currentIndustry 包含了 allowedList 中的任何字詞，或者是 currentIndustry
            // 例如 'Electronic Components' 包含了 'Electronic'，或者包含了 'Technology'
            const isMatch = allowedList.some(item => {
                // 如果 Mapping 中有完整項目 (如 'Electronic Components')
                if (currentIndustry === item || currentIndustry.includes(item)) return true;
                // 或者 currentIndustry 的各個單詞 (拆分後) 有出現在 mapping 中
                const words = currentIndustry.split(/\s+/);
                return words.some(word => word.length > 3 && item.includes(word));
            });
            
            if (!isMatch) return false;
        }
        
        return true;
    });
    
    resultCount.textContent = `(${filteredResults.length}筆)`;
    
    // 層級 2: 自動按評分從高到低排序，其次按產業和代號
    filteredResults.sort((a, b) => {
        const scoreA = a.score || 0;
        const scoreB = b.score || 0;
        if (scoreA !== scoreB) {
            return scoreB - scoreA; // 評分高排在前面
        }
        const industryA = a.industry || '未分類';
        const industryB = b.industry || '未分類';
        if (industryA === industryB) {
            return a.stock_id.localeCompare(b.stock_id);
        }
        return industryA.localeCompare(industryB, 'zh-Hant');
    });

    // 計算每個產業的股票數量
    let currentIndustry = null;
    let industryCount = 0;
    const industryTotals = filteredResults.reduce((acc, stock) => {
        const key = stock.industry || '未分類';
        acc[key] = (acc[key] || 0) + 1;
        return acc;
    }, {});

    // 逐一添加股票到表格
    filteredResults.forEach((stock, index) => {
        const industry = stock.industry || '未分類';
        
        // 產業標題行
        if (industry !== currentIndustry) {
            currentIndustry = industry;
            const headerRow = document.createElement('tr');
            headerRow.className = 'industry-header';
            headerRow.innerHTML = `
                <td colspan="16" class="industry-header-cell">
                    <strong>${industry}</strong> - ${industryTotals[industry]} 檔
                </td>
            `;
            tableBody.appendChild(headerRow);
        }

        // 股票數據行
        const tr = document.createElement('tr');
        tr.style.animationDelay = `${index * 0.05}s`;
        const stockName = stock.stock_name || `股票${stock.stock_id}`;

        // 處理驗證結果欄位
        let verifyPriceChangeHtml = '';
        let verifyStatusHtml = '';
        
        if ('verify_price_change_pct' in stock) {
            const priceChangePct = stock.verify_price_change_pct;
            const colorClass = priceChangePct >= 0 ? 'text-positive' : 'text-negative';
            verifyPriceChangeHtml = `<span class="${colorClass}">${priceChangePct.toFixed(2)}%</span>`;
            
            if ('verify_meets_criteria' in stock) {
                verifyStatusHtml = stock.verify_meets_criteria ? 
                    '<span class="verify-icon success"><i class="fa-solid fa-check"></i></span>' : 
                    '<span class="verify-icon fail"><i class="fa-solid fa-xmark"></i></span>';
            }
        }

        // 處理分數顏色
        const score = stock.score || 0;
        let scoreClass = 'score-low';
        if (score >= 80) scoreClass = 'score-high';
        else if (score >= 60) scoreClass = 'score-mid';

        tr.innerHTML = `
            <td class="trigger-date">${stock.trigger_date}</td>
            <td class="stock-id">${stock.stock_id}</td>
            <td class="stock-name">${stockName}</td>
            <td>${industry}</td>
            <td>${stock.close}</td>
            <td>${stock.ma20}</td>
            <td>${formatChange(stock.ma_diff_pct, true)}</td>
            <td>${stock.retail_current.toLocaleString()}</td>
            <td>${formatChange(stock.retail_change)}</td>
            <td>${stock.large_current_pct.toFixed(2)}%</td>
            <td>${formatChange(stock.large_change_pct, true)}</td>
            <td><span class="${score >= 80 ? 'text-positive' : ''}">${stock.vol_ratio || 1.0}x</span></td>
            <td class="verify-col">${verifyPriceChangeHtml}</td>
            <td class="verify-col">${verifyStatusHtml}</td>
            <td><span class="score-badge ${scoreClass}">${score}</span></td>
            <td>
                <button class="btn-chart" data-id="${stock.stock_id}" data-name="${stockName}">
                    <i class="fa-solid fa-chart-line"></i> 走勢
                </button>
            </td>
        `;

        tableBody.appendChild(tr);
    });

    // 採用事件委派處理「走勢」點擊，這比在循環內綁定更高效且穩定
    if (!tableBody.dataset.hasDelegate) {
        tableBody.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-chart');
            if (btn) {
                const stockId = btn.dataset.id;
                const stockName = btn.dataset.name;
                showStockChart(stockId, stockName);
            }
        });
        tableBody.dataset.hasDelegate = "true";
    }
}

// 顯示股票價格圖表
async function showStockChart(stockId, stockName) {
    const stockChartContainer = document.getElementById('stock-chart-container');
    const chartModal = document.getElementById('chart-modal');
    const chartTitle = document.getElementById('chart-title');
    const cacheIndicator = stockChartContainer.querySelector('.cache-indicator');
    
    // 清空之前的圖表
    stockChartContainer.innerHTML = '<div class="loading-chart"><i class="fa-solid fa-spinner fa-spin"></i> 載入中...</div>';
    if (cacheIndicator) {
        cacheIndicator.classList.add('hidden');
    }
    
    // 顯示模態框
    chartModal.classList.remove('hidden');
    chartTitle.textContent = `${stockName} (${stockId}) 近一個月走勢`;
    
    try {
        // 使用 API 端點，可能使用快取的數據
        const res = await fetch(`${API_BASE}/stock_price/${stockId}`);
        const data = await res.json();
        
        if (data.status === 'success') {
            // 清除載入指示器
            stockChartContainer.innerHTML = '<div class="cache-indicator hidden">使用快取數據</div>';
            
            // 解析返回的 Plotly 圖表 JSON
            const chartData = JSON.parse(data.chart);
            
            // 延遲渲染以確保容器寬高已正確初始化
            setTimeout(() => {
                // 清理容器並保留提示位
                stockChartContainer.innerHTML = '<div class="cache-indicator hidden">使用快取數據</div>';
                
                // 執行繪圖，使用後端傳來的精密 Layout
                Plotly.newPlot(stockChartContainer, chartData.data, chartData.layout, {
                    responsive: true,
                    displayModeBar: false
                });

                // 如果是使用快取的數據，顯示提示
                if (data.cached) {
                    const cacheIndicator = stockChartContainer.querySelector('.cache-indicator');
                    if (cacheIndicator) cacheIndicator.classList.remove('hidden');
                }
            }, 100);
            
        } else {
            stockChartContainer.innerHTML = `
                <div class="error-message">
                    <i class="fa-solid fa-exclamation-triangle"></i>
                    <p>無法載入股價數據: ${data.message || '未知錯誤'}</p>
                </div>
            `;
        }
    } catch (err) {
        console.error('Error loading chart data:', err);
        stockChartContainer.innerHTML = `
            <div class="error-message">
                <i class="fa-solid fa-exclamation-triangle"></i>
                <p>載入失敗: ${err.message}</p>
            </div>
        `;
    }
}

// 強制重置系統狀態
async function resetSystemState() {
    if (!confirm('確定要中斷並重置當前任務嗎？')) return;
    
    window.currentPollingFinished = true; // 停止前端輪詢
    
    try {
        const res = await fetch(`${API_BASE}/reset`, { method: 'POST' });
        const data = await res.json();
        
        if (data.status === 'success') {
            showMessage('系統狀態已重置', 'success');
            // 隱藏所有加載指示
            document.getElementById('progress-container').classList.add('hidden');
            document.getElementById('loading-spinner').classList.add('hidden');
            document.getElementById('progress-bar').style.width = '0%';
        }
    } catch (e) {
        console.error('Reset failed:', e);
        showMessage('重置失敗', 'error');
    }
}

// 根據大類更新細項選項
function updateSubIndustryOptions(category) {
    const industrySelect = document.getElementById('industry-filter');
    industrySelect.innerHTML = '<option value="all">所有細項</option>';
    
    let subIndustries = [];
    if (category === 'all') {
        Object.values(INDUSTRY_CATEGORY_MAP).forEach(list => {
            subIndustries = subIndustries.concat(list);
        });
    } else if (INDUSTRY_CATEGORY_MAP[category]) {
        subIndustries = INDUSTRY_CATEGORY_MAP[category];
    }
    
    subIndustries = [...new Set(subIndustries)].sort();
    subIndustries.forEach(industry => {
        const option = document.createElement('option');
        option.value = industry;
        option.textContent = industry;
        industrySelect.appendChild(option);
    });
    
    // 類別變更時即時刷新顯示結果
    refreshDisplay();
}

// 用於初始化產業過濾選項
function updateIndustryFilterOptions(industries) {
    updateSubIndustryOptions('all');
    
    // 為兩個選單都加入即時過濾
    const industryCategorySelect = document.getElementById('industry-category-filter');
    const industrySelect = document.getElementById('industry-filter');
    
    if (industryCategorySelect && !industryCategorySelect.dataset.hasListener) {
        industryCategorySelect.addEventListener('change', refreshDisplay);
        industrySelect.addEventListener('change', refreshDisplay);
        industryCategorySelect.dataset.hasListener = "true";
    }
}

// 快速刷新當前顯示
function refreshDisplay() {
    const lastResults = localStorage.getItem('lastScreenResults');
    if (lastResults) {
        const results = JSON.parse(lastResults);
        const filterVerified = document.getElementById('filter-verified').checked;
        const verifyPriceCheckbox = document.getElementById('verify-price');
        displayResults(results, filterVerified && verifyPriceCheckbox.checked);
    }
}