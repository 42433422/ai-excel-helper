let uiEventsBound = false;
function bindUiEvents() {
    if (uiEventsBound) return;
    uiEventsBound = true;

    document.querySelectorAll('.menu-item').forEach(item => {
        if (item.classList.contains('menu-item-link')) return;
        item.addEventListener('click', function() {
            const view = this.getAttribute('data-view');
            switchView(view);
        });
    });

    const callIfExists = (fnName, ...args) => {
        if (typeof window[fnName] === 'function') {
            window[fnName](...args);
        }
    };

    const bind = (id, eventName, handler) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener(eventName, handler);
    };

    bind('fileUploadEntry', 'click', () => callIfExists('openImportWindow'));
    bind('chooseFileBtn', 'click', () => {
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.click();
    });
    bind('openCameraBtn', 'click', () => callIfExists('openCamera'));
    bind('capturePhotoBtn', 'click', () => callIfExists('capturePhoto'));
    bind('proExitBtn', 'click', () => callIfExists('toggleProMode'));
    bind('modeSwitch', 'click', () => callIfExists('toggleProMode'));
    bind('logoutWechatBtn', 'click', () => callIfExists('logoutWechat'));
    bind('clearWechatMessagesBtn', 'click', () => callIfExists('clearWechatMessages'));

    bind('batchDeleteProductsBtn', 'click', () => callIfExists('batchDeleteProducts'));
    bind('exportProductPriceListBtn', 'click', () => callIfExists('exportProductPriceList'));
    bind('showProductModalBtn', 'click', () => callIfExists('showProductModal'));
    bind('toggleAllProductsCheckbox', 'change', e => callIfExists('toggleAllProducts', e.target));
    bind('productSearch', 'input', () => callIfExists('searchProducts'));
    bind('productUnitSelect', 'change', () => callIfExists('loadProducts'));

    bind('batchDeleteMaterialsBtn', 'click', () => callIfExists('batchDeleteMaterials'));
    bind('showMaterialModalBtn', 'click', () => callIfExists('showMaterialModal'));
    bind('toggleAllMaterialsCheckbox', 'change', e => callIfExists('toggleAllMaterials', e.target));
    bind('materialSearch', 'input', () => callIfExists('searchMaterials'));
    bind('materialCategoryFilter', 'change', () => callIfExists('searchMaterials'));

    bind('clearAllOrdersBtn', 'click', () => callIfExists('clearAllOrders'));
    bind('orderSearch', 'input', () => callIfExists('searchOrders'));
    bind('orderDate', 'change', () => callIfExists('searchOrders'));

    bind('loadShipmentRecordsBtn', 'click', () => callIfExists('loadShipmentRecords'));
    bind('exportShipmentRecordsBtn', 'click', () => callIfExists('exportShipmentRecords'));
    bind('shipmentRecordUnitSelect', 'change', () => callIfExists('onShipmentRecordUnitChange'));

    bind('batchDeleteCustomersBtn', 'click', () => callIfExists('batchDeleteCustomers'));
    bind('importCustomersExcelBtn', 'click', () => {
        const input = document.getElementById('importCustomersExcelInput');
        if (input) input.click();
    });
    bind('importCustomersExcelInput', 'change', function() {
        const input = this;
        const file = input.files && input.files[0];
        if (!file) return;
        const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
        const form = new FormData();
        form.append('file', file);
        fetch(apiBase + '/api/customers/import', { method: 'POST', body: form })
            .then(function (r) {
                return r.text().then(function (text) {
                    try {
                        return { ok: r.ok, status: r.status, data: JSON.parse(text) };
                    } catch (_) {
                        return { ok: false, status: r.status, data: { success: false, message: text || '服务器返回异常（' + r.status + '）' } };
                    }
                });
            })
            .then(function (_r) {
                var data = _r.data;
                if (data.success) {
                    var msg = data.message;
                    if (data.not_found && data.not_found.length) {
                        msg += '\n未匹配到单位：' + data.not_found.slice(0, 5).join('、') + (data.not_found.length > 5 ? '...' : '');
                    }
                    if (data.inserted_unit_names && data.inserted_unit_names.length) {
                        msg += '\n新增：' + data.inserted_unit_names.join('、');
                    }
                    if (data.skipped_row_numbers && data.skipped_row_numbers.length) {
                        msg += '\n第 ' + data.skipped_row_numbers.join('、') + ' 行单位名称为空已跳过，请补全后重新导入';
                    }
                    alert(msg);
                    if (typeof loadCustomers === 'function') loadCustomers();
                } else {
                    alert('导入失败：' + (data.message || '未知错误') + (_r.status === 500 ? '（服务器 500，请查看控制台或后端日志）' : ''));
                }
            })
            .catch(function (err) { return alert('导入失败：' + (err.message || '网络错误')); })
            .finally(() => { input.value = ''; });
    });
    bind('exportCustomersExcelBtn', 'click', () => {
        const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
        const link = document.createElement('a');
        // 后端客户导出接口是 `/api/customers/export`
        link.href = `${apiBase}/api/customers/export`;
        link.download = '购买单位列表.xlsx';
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        setTimeout(() => link.remove(), 0);
    });
    bind('toggleAllCustomersCheckbox', 'change', e => callIfExists('toggleAllCustomers', e.target));

    bind('printProductSelect', 'change', () => callIfExists('previewLabel'));
    bind('printLabelBtn', 'click', () => callIfExists('printLabel'));
    bind('saveSettingsBtn', 'click', () => callIfExists('saveSettings'));
    bind('wechatContactSaveBtn', 'click', () => callIfExists('saveWechatContactFromForm'));
    bind('wechatContactClearBtn', 'click', () => callIfExists('clearWechatContactForm'));
    bind('wechatContactRefreshCacheBtn', 'click', () => callIfExists('refreshWechatContactCache'));
    bind('wechatContactRefreshMessagesCacheBtn', 'click', () => callIfExists('refreshWechatMessagesCache'));
    bind('wechatContactSearchBtn', 'click', () => callIfExists('searchWechatContactsForStar'));
    bind('wechatContactUnstarAllBtn', 'click', () => callIfExists('unstarAllWechatContacts'));
    bind('wechatContactEditSaveBtn', 'click', () => callIfExists('saveWechatContactEdit'));
    bind('wechatContactSearch', 'input', () => callIfExists('filterWechatContacts'));
    bind('wechatContactTypeFilter', 'change', () => callIfExists('loadWechatContacts'));
    bind('toolSearch', 'input', () => callIfExists('filterTools'));
    bind('toolCategoryFilter', 'change', () => callIfExists('filterTools'));

    document.addEventListener('click', function(e) {
        const actionBtn = e.target.closest('.template-preview-action[data-template-action]');
        if (!actionBtn) return;
        const action = actionBtn.getAttribute('data-template-action');
        const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
        if (action === 'view-print' || action === 'open-print') {
            if (typeof switchView === 'function') switchView('print');
            if (typeof window.handleAutoAction === 'function') window.handleAutoAction({ type: 'show_print' });
        } else if (action === 'view-labels-export' || action === 'show-labels-export') {
            if (typeof window.handleAutoAction === 'function') window.handleAutoAction({ type: 'show_labels_export' });
        } else if (action === 'open-excel-preview') {
            var templateId = actionBtn.getAttribute('data-template-id');
            if (templateId) {
                window.open(apiBase + '/api/templates/' + encodeURIComponent(templateId) + '/file', '_blank');
            }
        } else if (action === 'view-template-overview') {
            showTemplateOverviewModal(apiBase);
        } else if (action === 'show-template-overview') {
            window.open(apiBase + '/api/shipment-template/overview?filename=' + encodeURIComponent('发货单模板.xlsx'), '_blank');
        } else if (action === 'view-shipment-records' || action === 'open-shipment-records') {
            if (typeof switchView === 'function') switchView('shipment-records');
        }
    });
}

function showTemplateOverviewModal(apiBase) {
    apiBase = apiBase || (typeof API_BASE !== 'undefined' ? API_BASE : '');
    var modal = document.getElementById('templateOverviewModal');
    var content = document.getElementById('templateOverviewContent');
    if (!modal || !content) return;
    content.innerHTML = '<p class="muted">加载中...</p>';
    modal.classList.add('active');
    fetch(apiBase + '/api/shipment-template/overview?filename=' + encodeURIComponent('发货单模板.xlsx'))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.success) {
                content.innerHTML = '<p class="muted">' + (data.message || '加载失败') + '</p>';
                return;
            }
            var t = data.template || {};
            var entries = data.editable_entries || [];
            var price = data.price_calculation || {};
            var intro = data.template_display_intro || [];
            var html = '<p><strong>模板：</strong>' + (t.name || '-') + '（工作表：' + (t.sheet || '-') + '）</p>';
            if (intro.length) {
                html += '<p><strong>说明：</strong></p><ul style="margin:0 0 12px 20px;">';
                intro.forEach(function(s) { html += '<li>' + s + '</li>'; });
                html += '</ul>';
            }
            if (entries.length) {
                html += '<p><strong>可编辑词条：</strong></p><p style="margin:0 0 8px;font-size:13px;color:#666;">' + entries.map(function(e) { return e.name + '(' + (e.column || '') + ')'; }).join('、') + '</p>';
            }
            if (price.detail_formula || price.total_formula) {
                html += '<p><strong>金额计算：</strong></p><ul style="margin:0 0 12px 20px;font-size:13px;">';
                if (price.detail_formula) html += '<li>' + price.detail_formula + '</li>';
                if (price.total_formula) html += '<li>' + price.total_formula + '</li>';
                if (price.uppercase_amount) html += '<li>' + price.uppercase_amount + '</li>';
                if (price.lowercase_amount) html += '<li>' + price.lowercase_amount + '</li>';
                html += '</ul>';
            }
            content.innerHTML = html;
        })
        .catch(function(err) {
            content.innerHTML = '<p class="muted">加载失败：' + (err.message || '网络错误') + '</p>';
        });
    bind('saveProductBtn', 'click', () => callIfExists('saveProduct'));
    bind('saveMaterialBtn', 'click', () => callIfExists('saveMaterial'));

    // 统一关闭事件委托：支持 data-close-action / data-close-target / 点击 modal 蒙层关闭
    document.addEventListener('click', function(e) {
        const actionCloser = e.target.closest('[data-close-action]');
        if (actionCloser) {
            const action = actionCloser.getAttribute('data-close-action');
            callIfExists(action);
            return;
        }

        const targetCloser = e.target.closest('[data-close-target]');
        if (targetCloser) {
            const targetId = targetCloser.getAttribute('data-close-target');
            const targetEl = targetId ? document.getElementById(targetId) : null;
            if (targetEl) {
                if (targetEl.classList.contains('modal')) {
                    targetEl.classList.remove('active');
                } else {
                    targetEl.style.display = 'none';
                }
            }
            return;
        }

        // 点击模态框遮罩层时关闭（仅对统一 modal 生效）
        if (e.target.classList && e.target.classList.contains('modal') && e.target.id) {
            e.target.classList.remove('active');
            if (e.target.id === 'toolDetailModal') {
                e.target.remove();
            }
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindUiEvents);
} else {
    bindUiEvents();
}

function switchView(view) {
    currentView = view;
    
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('data-view') === view) {
            item.classList.add('active');
        }
    });

    const titles = {
        'chat': '智能对话',
        'products': '产品管理',
        'materials': '原材料仓库',
        'orders': '出货单',
        'shipment-records': '出货记录管理',
        'customers': '客户管理',
        'wechat-contacts': '微信联系人列表',
        'print': '标签打印',
        'template-preview': '模板预览',
        'settings': '系统设置',
        'tools': '工具表'
    };
    const pageTitleEl = document.getElementById('pageTitle');
    if (pageTitleEl) {
        pageTitleEl.textContent = titles[view] || '';
    }

    document.querySelectorAll('.page-view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + view).classList.add('active');

    if (view === 'products') loadProducts();
    if (view === 'tools') loadTools();
    if (view === 'materials') { loadMaterials(); loadLowStock(); }
    if (view === 'orders') loadOrders();
    if (view === 'shipment-records') loadShipmentRecordsUnits();
    if (view === 'customers') loadCustomers();
    if (view === 'wechat-contacts' && typeof loadWechatContacts === 'function') loadWechatContacts();
    if (view === 'print') loadPrintProducts();
    if (view === 'settings') loadDistillationVersions();
}

function loadDistillationVersions() {
    const el = document.getElementById('distillationVersionsContent');
    if (!el) return;
    const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
    el.innerHTML = '<p class="muted">加载中...</p>';
    fetch(apiBase + '/api/distillation/versions')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (!data.success) {
                el.innerHTML = '<p class="muted">无法加载：' + (data.message || '未知错误') + '</p>';
                return;
            }
            var versions = data.versions || [];
            var samples = data.distillation_samples != null ? data.distillation_samples : 0;
            if (versions.length === 0) {
                el.innerHTML = '<p class="muted">暂无训练产物。专业版对话会参与蒸馏，积累数据后运行「蒸馏/每周重训」即可生成 last.pt、best.pt。</p><p class="muted">已积累样本数：' + samples + '</p>';
                return;
            }
            var html = '<table class="table" style="width:100%; margin-bottom:12px;"><thead><tr><th>文件</th><th>说明</th><th>修改时间</th><th>大小</th></tr></thead><tbody>';
            versions.forEach(function(v) {
                html += '<tr><td>' + (v.name || '') + '</td><td>' + (v.label || '') + '</td><td>' + (v.modified || '-') + '</td><td>' + (v.size_kb != null ? v.size_kb + ' KB' : '-') + '</td></tr>';
            });
            html += '</tbody></table><p class="muted">已积累蒸馏样本数：' + samples + '（仅专业版对话参与）</p>';
            el.innerHTML = html;
        })
        .catch(function(err) {
            el.innerHTML = '<p class="muted">加载失败：' + (err.message || '网络错误') + '</p>';
        });
}

function openPreviewWindow(mediaUrl, mediaType, sourceElement) {
    const previewWindow = document.getElementById('previewFloatWindow');
    const mediaContainer = document.getElementById('previewMedia');
    mediaContainer.textContent = '';

    if (mediaType === 'image') {
        const img = document.createElement('img');
        img.src = mediaUrl;
        img.alt = '预览图片';
        mediaContainer.appendChild(img);
    } else if (mediaType === 'video') {
        const video = document.createElement('video');
        video.src = mediaUrl;
        video.controls = true;
        mediaContainer.appendChild(video);
    } else {
        const placeholder = document.createElement('div');
        placeholder.className = 'preview-placeholder';
        placeholder.textContent = '不支持的媒体类型';
        mediaContainer.appendChild(placeholder);
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
    const span = document.createElement('span');
    span.textContent = '📷 测试图片';
    testElement.appendChild(span);
    document.body.appendChild(testElement);
    
    setTimeout(() => {
        openPreviewWindow('https://picsum.photos/400/300', 'image', testElement);
        
        setTimeout(() => {
            testElement.remove();
        }, 400);
    }, 100);
}
