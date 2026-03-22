function openPreviewWindow(mediaUrl, mediaType, sourceElement) {
    const previewWindow = document.getElementById('previewFloatWindow');
    const mediaContainer = document.getElementById('previewMedia');
    
    if (mediaType === 'image') {
        mediaContainer.innerHTML = '<img src="' + mediaUrl + '" alt="预览图片">';
    } else if (mediaType === 'video') {
        mediaContainer.innerHTML = '<video src="' + mediaUrl + '" controls></video>';
    } else {
        mediaContainer.innerHTML = '<div class="preview-placeholder">不支持的媒体类型</div>';
    }

    if (sourceElement) {
        animatePreviewWindow(sourceElement, previewWindow);
    } else {
        previewWindow.classList.add('show');
    }

    setTimeout(() => {
        initHoverHighlight(mediaContainer);
    }, 400);
}

function animatePreviewWindow(sourceElement, targetWindow) {
    const firstRect = sourceElement.getBoundingClientRect();
    const targetRect = targetWindow.getBoundingClientRect();
    
    const deltaX = firstRect.left - targetRect.left;
    const deltaY = firstRect.top - targetRect.top;
    const deltaWidth = firstRect.width - targetRect.width;
    const deltaHeight = firstRect.height - targetRect.height;
    
    targetWindow.classList.add('animating');
    targetWindow.style.display = 'block';
    targetWindow.style.opacity = '0';
    targetWindow.style.transform = `translate(${deltaX}px, ${deltaY}px) scale(${firstRect.width / targetRect.width})`;
    targetWindow.style.transformOrigin = 'top left';
    
    requestAnimationFrame(() => {
        targetWindow.style.transition = 'opacity 0.35s ease-out, transform 0.35s ease-out';
        targetWindow.style.opacity = '1';
        targetWindow.style.transform = 'translate(0, 0) scale(1)';
    });
    
    setTimeout(() => {
        targetWindow.classList.remove('animating');
        targetWindow.classList.add('show');
        targetWindow.style.transition = '';
        targetWindow.style.transform = '';
        targetWindow.style.transformOrigin = '';
    }, 350);
}

function closePreviewWindow() {
    const previewWindow = document.getElementById('previewFloatWindow');
    
    if (previewWindow.classList.contains('show')) {
        previewWindow.style.opacity = '0';
        previewWindow.style.transform = 'scale(0.8)';
        previewWindow.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
        
        setTimeout(() => {
            previewWindow.classList.remove('show');
            previewWindow.style.display = 'none';
            previewWindow.style.opacity = '';
            previewWindow.style.transform = '';
            previewWindow.style.transition = '';
            removeHoverHighlight();
        }, 300);
    }
}

(function() {
    const highlightBox = document.createElement('div');
    highlightBox.className = 'hover-highlight-box';
    document.body.appendChild(highlightBox);

    let activeContainer = null;
    let boxWidth = 0;
    let boxHeight = 0;
    let animationFrameId = null;
    let lastX = 0;
    let lastY = 0;

    const updateHighlightPosition = () => {
        if (activeContainer) {
            const x = lastX - boxWidth / 2;
            const y = lastY - boxHeight / 2;
            highlightBox.style.left = x + 'px';
            highlightBox.style.top = y + 'px';
        }
        animationFrameId = null;
    };

    document.addEventListener('mousemove', function(e) {
        if (activeContainer) {
            lastX = e.clientX;
            lastY = e.clientY;
            if (!animationFrameId) {
                animationFrameId = requestAnimationFrame(updateHighlightPosition);
            }
        }
    });

    window.initHoverHighlight = function(mediaContainer) {
        if (!mediaContainer) return;
        
        activeContainer = mediaContainer;
        const rect = mediaContainer.getBoundingClientRect();
        boxWidth = Math.min(rect.width, 300);
        boxHeight = Math.min(rect.height, 200);
        highlightBox.style.width = boxWidth + 'px';
        highlightBox.style.height = boxHeight + 'px';
        highlightBox.classList.add('active');

        mediaContainer.addEventListener('mouseleave', function() {
            highlightBox.classList.remove('active');
            activeContainer = null;
        });

        mediaContainer.addEventListener('mouseenter', function() {
            activeContainer = mediaContainer;
            highlightBox.classList.add('active');
        });
    };

    window.removeHoverHighlight = function() {
        highlightBox.classList.remove('active');
        activeContainer = null;
    };
})();

function testPreviewAnimation() {
    const testElement = document.createElement('div');
    testElement.className = 'message user';
    testElement.style.position = 'fixed';
    testElement.style.left = '30%';
    testElement.style.top = '40%';
    testElement.style.width = '200px';
    testElement.style.height = '150px';
    testElement.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    testElement.style.borderRadius = '12px';
    testElement.style.display = 'flex';
    testElement.style.alignItems = 'center';
    testElement.style.justifyContent = 'center';
    testElement.style.color = 'white';
    testElement.style.fontSize = '16px';
    testElement.style.boxShadow = '0 4px 15px rgba(0,0,0,0.2)';
    testElement.style.zIndex = '9999';
    testElement.innerHTML = '<span>📷 测试图片</span>';
    document.body.appendChild(testElement);
    
    setTimeout(() => {
        openPreviewWindow('https://picsum.photos/400/300', 'image', testElement);
        
        setTimeout(() => {
            testElement.remove();
        }, 400);
    }, 100);
}

let currentImportPurpose = 'general';
let dropZoneBound = false;
let activeUploadSessionId = null;
let isUploadProcessing = false;

function emitUploadState(state, extra = {}) {
    try {
        window.__aiUploadState = {
            state,
            ts: Date.now(),
            purpose: currentImportPurpose || 'general',
            ...extra
        };
        window.dispatchEvent(new CustomEvent('ai-upload-status', {
            detail: {
                state,
                purpose: currentImportPurpose || 'general',
                ...extra
            }
        }));
    } catch (e) {
        console.warn('emitUploadState failed:', e);
    }
}

function appendUploadMessage(text) {
    if (document.body && document.body.classList.contains('pro-mode-active') && typeof window.jarvisAddMessageExternal === 'function') {
        window.jarvisAddMessageExternal(text, 'ai');
        return;
    }
    if (typeof addMessage === 'function') {
        addMessage(text, 'system');
    }
}

function buildExcelNextStepPrompt(suggestedUseCustomersImport) {
    const options = suggestedUseCustomersImport
        ? ['导入购买单位', '加载产品', '加载公司名称', '加载入出货记录', '导入模板']
        : ['加载产品', '加载公司名称', '加载入出货记录', '导入模板'];
    return [
        '🧭 已识别到 Excel 文件。',
        '',
        '下一步你要我执行哪一项？可直接回复下面任一指令：',
        ...options,
        '',
        suggestedUseCustomersImport ? '💡 若为购买单位列表，回复「导入购买单位」或「上传客户管理」并重新选择该文件即可自动导入。' : '当前模板能力：发货单模板、出货记录模板（后续可继续扩展）。'
    ].join('\n');
}

function openImportWindow(purpose = 'general') {
    currentImportPurpose = purpose || 'general';
    // 打开新窗口时作废旧会话，防止旧任务继续回写
    activeUploadSessionId = null;
    isUploadProcessing = false;
    const window = document.getElementById('importFloatWindow');
    const titleEl = document.querySelector('#importFloatWindow .import-header h4');
    const hintEl = document.querySelector('#importFloatWindow .drop-zone-hint');
    if (titleEl) {
        if (currentImportPurpose === 'customers_import') {
            titleEl.textContent = '上传购买单位 Excel 更新客户';
        } else if (currentImportPurpose === 'product_import') {
            titleEl.textContent = 'PRODUCT IMPORT';
        } else if (currentImportPurpose === 'order_parse') {
            titleEl.textContent = 'ORDER PARSE';
        } else {
            titleEl.textContent = 'FILE ANALYZE';
        }
    }
    if (hintEl) {
        if (currentImportPurpose === 'customers_import') {
            hintEl.textContent = '请上传购买单位列表 .xlsx（需含「单位名称」列），将校验格式并更新联系人/电话/地址';
        } else if (currentImportPurpose === 'product_import') {
            hintEl.textContent = '产品导入模式：支持任意文件，自动识别并分析';
        } else if (currentImportPurpose === 'order_parse') {
            hintEl.textContent = '订单解析模式：上传后自动提取订单关键信息';
        } else {
            hintEl.textContent = '通用模式：支持任意文件类型，自动识别并分析';
        }
    }
    window.classList.add('show');
    hideFileUploadEntry();
    resetImportState();
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    initDropZone();
}

function closeImportWindow() {
    // 关闭时作废当前会话，避免异步结果继续更新UI
    activeUploadSessionId = null;
    isUploadProcessing = false;
    const window = document.getElementById('importFloatWindow');
    window.classList.remove('show');
    hideFileUploadEntry();
    resetImportState();
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
}

function showFileUploadEntry() {
    const entry = document.getElementById('fileUploadEntry');
    if (entry && !entry.classList.contains('show')) {
        entry.classList.add('show');
        console.log('显示文件上传入口');
    }
}

function hideFileUploadEntry() {
    const entry = document.getElementById('fileUploadEntry');
    if (entry) {
        entry.classList.remove('show');
        console.log('隐藏文件上传入口');
    }
}

function initDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    if (!dropZone || !fileInput) return;
    if (dropZoneBound) return;
    dropZoneBound = true;
    
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });
    
    dropZone.addEventListener('dragenter', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!dropZone.contains(e.relatedTarget)) {
            dropZone.classList.remove('dragover');
        }
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files);
        }
    });
}

function resetImportState() {
    const progress = document.getElementById('importProgress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const status = document.getElementById('importStatus');
    if (progress) progress.classList.remove('show');
    if (progressBar) progressBar.style.width = '0%';
    if (progressText) progressText.textContent = '读取中...';
    if (progressPercent) progressPercent.textContent = '0%';
    if (status) status.classList.remove('show', 'success', 'error');
}

function handleFileSelect(files) {
    if (isUploadProcessing) {
        appendUploadMessage('⏳ 上一次文件仍在处理，请稍候或关闭后重新上传。');
        return;
    }
    const progress = document.getElementById('importProgress');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const status = document.getElementById('importStatus');
    
    progress.classList.add('show');
    status.classList.remove('show', 'success', 'error');
    if (progressBar) progressBar.style.width = '1%';
    if (progressPercent) progressPercent.textContent = '1%';
    if (progressText) progressText.textContent = '读取中: 准备上传...';
    
    const selectedFiles = [];
    for (let i = 0; i < files.length; i++) {
        selectedFiles.push(files[i]);
    }

    if (selectedFiles.length === 0) {
        progressText.textContent = '没有可处理的文件';
        if (progressPercent) progressPercent.textContent = '0%';
        status.textContent = '请选择文件后重试';
        status.classList.add('show', 'error');
        emitUploadState('error', { message: '没有可处理的文件' });
        return;
    }

    const uploadSessionId = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    activeUploadSessionId = uploadSessionId;
    isUploadProcessing = true;

    emitUploadState('pending', { fileCount: selectedFiles.length });
    appendUploadMessage(`⏳ 检测到 ${selectedFiles.length} 个文件，等待上传并读取中...`);
    processGenericFiles(selectedFiles, progressBar, progressText, progressPercent, status, uploadSessionId);
}

async function processGenericFiles(files, progressBar, progressText, progressPercent, status, uploadSessionId) {
    const allSummaries = [];
    let analyzedCount = 0;
    let uploadOnlyCount = 0;
    let hasExcelUpload = false;
    let hasCustomersList = false;
    let customersImportFileCount = 0;
    // Some multi-step flows (e.g. unit_products_db) need extra time for the user to read prompt.
    let delayCloseMs = 900;
    for (let i = 0; i < files.length; i++) {
        if (uploadSessionId !== activeUploadSessionId) {
            return;
        }
        const file = files[i];
        const startPercent = Math.max(1, Math.round((i / files.length) * 100));
        if (progressBar) progressBar.style.width = `${startPercent}%`;
        if (progressPercent) progressPercent.textContent = `${startPercent}%`;
        progressText.textContent = `读取中: ${file.name}`;
        emitUploadState('processing', { fileName: file.name, percent: startPercent });

        const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
        const customersImportUrl = (apiBase && String(apiBase).trim())
            ? (String(apiBase).replace(/\/$/, '') + '/api/customers/import')
            : (typeof window !== 'undefined' && window.location && window.location.origin && window.location.origin !== 'null'
                ? window.location.origin + '/api/customers/import'
                : '/api/customers/import');

        if (currentImportPurpose === 'customers_import') {
            if (!/\.xlsx$/i.test(file.name || '')) {
                appendUploadMessage(`❌ ${file.name}：购买单位导入仅支持 .xlsx，且表头需含「单位名称」列。`);
            } else {
                try {
                    const importForm = new FormData();
                    importForm.append('file', file);
                    const importResp = await fetch(customersImportUrl, { method: 'POST', body: importForm });
                    const rawText = await importResp.text();
                    if (uploadSessionId !== activeUploadSessionId) return;
                    let importData = null;
                    try {
                        if (rawText.trim().startsWith('<')) {
                            throw new Error('服务器返回了网页而非数据，请确认后端已启动且接口 /api/customers/import 可用（状态码 ' + importResp.status + '）');
                        }
                        importData = JSON.parse(rawText);
                    } catch (parseErr) {
                        const msg = parseErr.message || String(parseErr);
                        if (msg.indexOf('服务器返回') !== -1) throw parseErr;
                        appendUploadMessage(`❌ 导入请求失败 (${file.name})：服务器返回异常（${importResp.status}），请检查后端是否正常运行。`);
                        analyzedCount += 1;
                        continue;
                    }
                    if (importData.success) {
                        const inserted = (importData.inserted || 0);
                        const skipped = (importData.skipped || 0);
                        const insertedNames = importData.inserted_unit_names || [];
                        const skippedRows = importData.skipped_row_numbers || [];
                        let tip = `✅ 购买单位已更新：${importData.message}，列表已自动刷新`;
                        if (skipped > 0) {
                            const rowHint = skippedRows.length > 0 ? ` 第 ${skippedRows.join('、')} 行` : '';
                            tip += `（有 ${skipped} 行因「单位名称」为空被跳过${rowHint}，请补全后重新导入）`;
                        }
                        if (insertedNames.length > 0) {
                            tip += ` 新增单位：${insertedNames.join('、')}`;
                        }
                        appendUploadMessage(tip);
                        const refresh = typeof loadCustomers === 'function' ? loadCustomers : (typeof window !== 'undefined' && window.loadCustomers);
                        if (refresh) {
                            setTimeout(function () { refresh(); }, 150);
                        }
                        if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
                            window.dispatchEvent(new CustomEvent('customers-imported', { detail: importData }));
                        }
                        var sw = (typeof switchView === 'function') ? switchView : (typeof window !== 'undefined' && window.switchView);
                        if (inserted > 0 && sw) {
                            setTimeout(function () { sw('customers'); }, 300);
                            if (refresh) { setTimeout(function () { refresh(); }, 500); }
                        }
                    } else {
                        appendUploadMessage(`❌ 导入失败：${importData.message || '格式不符合或缺少「单位名称」列'}`);
                    }
                    analyzedCount += 1;
                } catch (err) {
                    appendUploadMessage(`❌ 导入请求失败 (${file.name})：${err.message || '网络错误'}`);
                }
            }
            customersImportFileCount += 1;
            const donePercent = Math.round(((i + 1) / files.length) * 100);
            if (progressBar) progressBar.style.width = `${donePercent}%`;
            if (progressPercent) progressPercent.textContent = `${donePercent}%`;
            continue;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('purpose', currentImportPurpose || 'general');

        try {
            const response = await fetch(apiBase + '/api/ai/file/analyze', {
                method: 'POST',
                body: formData
            });

            if (uploadSessionId !== activeUploadSessionId) {
                return;
            }

            const rawText = await response.text();
            let result = null;
            try {
                result = JSON.parse(rawText);
            } catch (parseErr) {
                result = {
                    success: false,
                    message: `服务返回非JSON响应(${response.status})`
                };
            }

            // 兼容旧后端：当通用分析接口不可用时，Excel回退到旧接口
            if ((!result || !result.success) && /\.(xlsx|xls|csv)$/i.test(file.name)) {
                const fallbackFormData = new FormData();
                fallbackFormData.append('excel_file', file);
                const fallbackResp = await fetch(apiBase + '/api/excel/upload', {
                    method: 'POST',
                    body: fallbackFormData
                });
                const fallbackText = await fallbackResp.text();
                try {
                    const fallbackJson = JSON.parse(fallbackText);
                    if (fallbackJson && fallbackJson.success) {
                        // 二段回退：尝试调用模板分解接口，拿真实分析结果
                        let deepSummary = '';
                        try {
                            const decomposeResp = await fetch(apiBase + '/api/excel/decompose', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    filename: file.name,
                                    file_path: fallbackJson.file_path || '',
                                    sample_rows: 5
                                })
                            });
                            const decomposeText = await decomposeResp.text();
                            const decomposeJson = JSON.parse(decomposeText);
                            if (decomposeJson && decomposeJson.success && decomposeJson.decomposition) {
                                const d = decomposeJson.decomposition;
                                const entryCount = Array.isArray(d.editable_entries) ? d.editable_entries.length : 0;
                                const amountCount = Array.isArray(d.amount_related_entries) ? d.amount_related_entries.length : 0;
                                deepSummary = `检测到表头行: ${d.header_row || '-'}；可编辑词条: ${entryCount} 个；金额相关字段: ${amountCount} 个。`;
                            }
                        } catch (deepErr) {
                            // 继续走普通回退提示
                        }

                        result = {
                            success: true,
                            parser_used: deepSummary ? 'excel_fallback+decompose' : 'excel_fallback',
                            extension: '.xlsx',
                            text_preview: '',
                            ai_summary: deepSummary || 'Excel 文件已上传成功（当前环境仅完成上传，未读取内容）。',
                            analyzed: !!deepSummary
                        };
                    } else if (fallbackJson && fallbackJson.message) {
                        result = {
                            success: false,
                            message: fallbackJson.message
                        };
                    }
                } catch (fallbackParseErr) {
                    result = result || {
                        success: false,
                        message: `回退接口返回非JSON(${fallbackResp.status})`
                    };
                }
            }
            const donePercent = Math.round(((i + 1) / files.length) * 100);
            if (progressBar) progressBar.style.width = `${donePercent}%`;
            if (progressPercent) progressPercent.textContent = `${donePercent}%`;
            emitUploadState('processing', { fileName: file.name, percent: donePercent });

            if (result && result.success) {
                const parser = result.parser_used || 'metadata';
                const resultExt = String(result.extension || '').toLowerCase();
                const nameIsExcel = /\.(xlsx|xls|csv)$/i.test(file.name || '');
                if (nameIsExcel || ['.xlsx', '.xls', '.csv'].includes(resultExt) || parser.includes('excel')) {
                    hasExcelUpload = true;
                }
                if (result.suggested_use === 'customers_import') hasCustomersList = true;
                const preview = (result.text_preview || '').trim();
                const summary = (result.ai_summary || '').trim();
                const resultText = summary || preview || '已完成读取，但该文件暂无可提取正文。';
                const hasAnalysis = result.analyzed !== false && (
                    parser.includes('decompose') ||
                    parser === 'excel' ||
                    parser === 'image_ocr' ||
                    parser === 'pdf' ||
                    parser === 'docx' ||
                    parser === 'text' ||
                    (summary && !summary.includes('仅完成上传'))
                );
                if (hasAnalysis) analyzedCount += 1;
                else uploadOnlyCount += 1;
                const messageParts = [
                    `📎 文件分析完成: ${file.name}`,
                    `解析器: ${parser}`,
                    `分析结果:\n${resultText.slice(0, 700)}`
                ];
                if (preview && summary && preview !== summary) {
                    messageParts.push(`内容预览:\n${preview.slice(0, 350)}`);
                }
                // Multi-step: unit_products_db requires user confirmation in chat.
                if (result.suggested_use === 'unit_products_db' && result.saved_name) {
                    delayCloseMs = Math.max(delayCloseMs, 2500);
                    try {
                        let sessionId = '';
                        try { sessionId = localStorage.getItem('ai_session_id') || ''; } catch (_) {}
                        window.__xcagiPendingUnitProductsImport = {
                            saved_name: result.saved_name,
                            unit_name_guess: (result.unit_name_guess || '').trim(),
                            unit_candidates: Array.isArray(result.unit_candidates) ? result.unit_candidates : [],
                            stage: 'confirm_filename',
                            session_id: sessionId
                        };
                        try { localStorage.setItem('xcagiPendingUnitProductsImport', JSON.stringify(window.__xcagiPendingUnitProductsImport)); } catch (_) {}
                    } catch (_) { /* best-effort */ }
                    const guess = (result.unit_name_guess || '').trim();
                    messageParts.push(
                        guess
                            ? `下一步：请到聊天里回复“是”以导入购买单位「${guess}」的产品；也可回复“否 / 改成 <名称>”。`
                            : `下一步：请到聊天里回复“是 / 否 / 改成 <名称>”以完成购买单位 + 产品导入。`
                    );
                }
                const msg = messageParts.join('\n\n');
                allSummaries.push(msg);
                appendUploadMessage(msg);
            } else {
                appendUploadMessage(`❌ 文件分析失败 (${file.name}): ${(result && (result.message || result.error)) || '未知错误'}`);
            }
        } catch (err) {
            if (uploadSessionId !== activeUploadSessionId) {
                return;
            }
            console.error('File analyze error:', err);
            const hint = (err && err.message === 'Failed to fetch') ? '（请检查网络连接或服务是否启动）' : '';
            appendUploadMessage(`❌ 文件请求失败 (${file.name}): ${err.message}${hint}`);
        }
    }

    if (uploadSessionId !== activeUploadSessionId) {
        return;
    }

    progressText.textContent = '文件分析完成';
    if (progressPercent) progressPercent.textContent = '100%';
    if (progressBar) progressBar.style.width = '100%';
    var wasCustomersImportOnly = (currentImportPurpose === 'customers_import' && customersImportFileCount === files.length);
    if (wasCustomersImportOnly) {
        status.textContent = `购买单位导入完成（${files.length} 个文件）`;
    } else if (uploadOnlyCount > 0 && analyzedCount === 0) {
        status.textContent = `已上传 ${files.length} 个文件（当前环境未完成内容分析）`;
    } else if (uploadOnlyCount > 0) {
        status.textContent = `已分析 ${analyzedCount} 个，另有 ${uploadOnlyCount} 个仅上传`;
    } else {
        status.textContent = `已完成 ${files.length} 个文件分析`;
    }
    status.classList.add('show', 'success');
    emitUploadState('completed', { fileCount: files.length });
    if (!wasCustomersImportOnly) {
        if (uploadOnlyCount > 0 && analyzedCount === 0) {
            appendUploadMessage(`✅ 文件上传完成：共 ${files.length} 个文件已接收，当前环境未完成内容分析。`);
        } else if (uploadOnlyCount > 0) {
            appendUploadMessage(`✅ 文件处理完成：已分析 ${analyzedCount} 个，另有 ${uploadOnlyCount} 个仅上传。`);
        } else {
            appendUploadMessage(`✅ 文件上传完成，已读取并分析 ${files.length} 个文件。`);
        }
        if (hasExcelUpload) {
            appendUploadMessage(buildExcelNextStepPrompt(hasCustomersList));
        }
    }
    isUploadProcessing = false;
    setTimeout(() => {
        try {
            closeImportWindow();
        } catch (e) {
            console.warn('自动关闭上传窗失败:', e);
        }
    }, delayCloseMs);
}

async function openCamera() {
    const cameraPanel = document.getElementById('cameraPanel');
    const cameraVideo = document.getElementById('cameraVideo');
    
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
        cameraVideo.srcObject = cameraStream;
        cameraPanel.style.display = 'block';
    } catch (err) {
        console.error('Camera error:', err);
        alert('无法访问摄像头: ' + err.message);
    }
}

function closeCamera() {
    const cameraPanel = document.getElementById('cameraPanel');
    const cameraVideo = document.getElementById('cameraVideo');
    
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    cameraPanel.style.display = 'none';
    cameraVideo.srcObject = null;
}

function capturePhoto() {
    const cameraVideo = document.getElementById('cameraVideo');
    const cameraCanvas = document.getElementById('cameraCanvas');
    const ctx = cameraCanvas.getContext('2d');
    
    cameraCanvas.width = cameraVideo.videoWidth;
    cameraCanvas.height = cameraVideo.videoHeight;
    
    ctx.drawImage(cameraVideo, 0, 0);
    
    cameraCanvas.toBlob(async (blob) => {
        const file = new File([blob], 'capture.jpg', { type: 'image/jpeg' });
        handleFileSelect([file]);
        closeCamera();
    }, 'image/jpeg');
}

// Vue `vue-dist` 页面在部分部署下可能不会加载 legacy `ui.js`，
// 导致 `[data-close-action="closeImportWindow"]` 的点击委托失效。
// 这里直接绑定 import 关闭按钮，确保 `importCloseBtn` 可点击。
(function ensureImportWindowCloseHandlers() {
    try {
        if (typeof window === 'undefined') return;
        if (window.__XCAGI_IMPORT_CLOSE_HANDLERS_BOUND__) return;
        window.__XCAGI_IMPORT_CLOSE_HANDLERS_BOUND__ = true;

        const bindCloseBtn = (id) => {
            const el = document.getElementById(id);
            if (!el) return;
            if (el.getAttribute('data-xcagi-bound-close-import') === '1') return;
            el.setAttribute('data-xcagi-bound-close-import', '1');
            el.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                try { closeImportWindow(); } catch (_) {}
            });
        };

        bindCloseBtn('importCloseBtn');
        bindCloseBtn('cancelImportBtn');

        document.addEventListener('click', (e) => {
            const target = e && e.target && e.target.closest ? e.target.closest('[data-close-action="closeImportWindow"]') : null;
            if (!target) return;
            e.preventDefault();
            e.stopPropagation();
            try { closeImportWindow(); } catch (_) {}
        });
    } catch (_) {
        // best-effort; do not break import module
    }
})();
