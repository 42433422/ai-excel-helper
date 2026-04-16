/**
 * 出货记录管理：按购买单位查看、导出出货记录 Excel
 */
(function() {
    const apiBase = typeof API_BASE !== 'undefined' ? API_BASE : '';
    let currentUnits = [];
    let currentRecords = null;
    let currentSheetNames = [];
    let currentSheetIndex = 0;

    function getSelect() {
        return document.getElementById('shipmentRecordUnitSelect');
    }

    function getTableHead() {
        return document.getElementById('shipmentRecordsTableHead');
    }

    function getTableBody() {
        return document.getElementById('shipmentRecordsTableBody');
    }

    function getCardTitle() {
        return document.getElementById('shipmentRecordsCardTitle');
    }

    function getSheetsTabs() {
        return document.getElementById('shipmentRecordsSheetsTabs');
    }

    /** 加载购买单位列表到下拉框 */
    function loadShipmentRecordsUnits() {
        const sel = getSelect();
        if (!sel) return;
        sel.innerHTML = '<option value="">加载中...</option>';
        fetch(apiBase + '/api/shipment-records/units')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                currentUnits = (data.data || []);
                sel.innerHTML = '<option value="">请选择购买单位</option>';
                currentUnits.forEach(function(u) {
                    const opt = document.createElement('option');
                    opt.value = u;
                    opt.textContent = u;
                    sel.appendChild(opt);
                });
            })
            .catch(function(e) {
                sel.innerHTML = '<option value="">加载失败</option>';
                console.error('出货记录单位列表加载失败', e);
            });
    }

    /** 切换工作表标签 */
    function renderSheetTabs() {
        const container = getSheetsTabs();
        if (!container) return;
        if (!currentRecords || !currentSheetNames.length) {
            container.style.display = 'none';
            return;
        }
        container.style.display = 'block';
        container.innerHTML = '';
        currentSheetNames.forEach(function(name, idx) {
            const btn = document.createElement('button');
            btn.className = 'btn btn-sm ' + (idx === currentSheetIndex ? 'btn-primary' : 'btn-secondary');
            btn.textContent = name;
            btn.style.marginRight = '8px';
            btn.onclick = function() {
                currentSheetIndex = idx;
                renderCurrentSheet();
                renderSheetTabs();
            };
            container.appendChild(btn);
        });
    }

    /** 渲染当前工作表的表格（带操作列与编辑） */
    function renderCurrentSheet() {
        const thead = getTableHead();
        const tbody = getTableBody();
        const cardTitle = getCardTitle();
        if (!currentRecords || !currentSheetNames.length) {
            if (thead) thead.innerHTML = '<th>暂无数据</th>';
            if (tbody) tbody.innerHTML = '<tr><td colspan="1" class="empty-state">请先选择购买单位并加载</td></tr>';
            return;
        }
        const sheetName = currentSheetNames[currentSheetIndex];
        const rows = currentRecords[sheetName] || [];
        if (rows.length === 0) {
            if (thead) thead.innerHTML = '<th>暂无数据</th>';
            if (tbody) tbody.innerHTML = '<tr><td colspan="1" class="empty-state">该工作表无数据</td></tr>';
            return;
        }
        const cols = Object.keys(rows[0]);
        if (thead) {
            thead.innerHTML = cols.map(function(c) { return '<th>' + escapeHtml(c) + '</th>'; }).join('') + '<th class="th-actions">操作</th>';
        }
        if (tbody) {
            tbody.innerHTML = '';
            rows.forEach(function(row, rowIndex) {
                const tr = document.createElement('tr');
                tr.className = 'shipment-record-row';
                cols.forEach(function(c) {
                    const td = document.createElement('td');
                    td.className = 'shipment-record-cell';
                    td.title = String(row[c] || '');
                    td.textContent = String(row[c] || '');
                    tr.appendChild(td);
                });
                const tdAction = document.createElement('td');
                tdAction.className = 'shipment-record-actions';
                const btnEdit = document.createElement('button');
                btnEdit.type = 'button';
                btnEdit.className = 'btn btn-sm btn-secondary shipment-record-edit-btn';
                btnEdit.textContent = '编辑';
                btnEdit.dataset.rowIndex = String(rowIndex);
                btnEdit.onclick = function() { openEditModal(sheetName, rowIndex, cols, row); };
                const btnDelete = document.createElement('button');
                btnDelete.type = 'button';
                btnDelete.className = 'btn btn-sm btn-danger shipment-record-delete-btn';
                btnDelete.textContent = '删除';
                btnDelete.dataset.rowIndex = String(rowIndex);
                btnDelete.onclick = function() { confirmDeleteRecord(sheetName, rowIndex, row); };
                btnDelete.style.marginLeft = '4px';
                tdAction.appendChild(btnEdit);
                tdAction.appendChild(btnDelete);
                tr.appendChild(tdAction);
                tbody.appendChild(tr);
            });
        }
        var unit = getSelect() ? getSelect().value : '';
        if (cardTitle) cardTitle.textContent = (unit ? unit + ' - ' : '') + '工作表：' + sheetName + '（共 ' + rows.length + ' 条）';
    }

    var editModalRowIndex = null;
    var editModalSheetName = null;
    var editModalCols = null;

    function openEditModal(sheetName, rowIndex, cols, row) {
        editModalSheetName = sheetName;
        editModalRowIndex = rowIndex;
        editModalCols = cols;
        var form = document.getElementById('shipmentRecordEditForm');
        var modal = document.getElementById('shipmentRecordEditModal');
        if (!form || !modal) return;
        form.innerHTML = '';
        cols.forEach(function(col) {
            var label = document.createElement('label');
            label.className = 'form-label';
            label.textContent = col;
            label.style.display = 'block';
            label.style.marginTop = '10px';
            form.appendChild(label);
            var input = document.createElement('input');
            input.type = 'text';
            input.className = 'form-control';
            input.name = col;
            input.value = String(row[col] != null ? row[col] : '');
            input.style.width = '100%';
            input.style.marginBottom = '4px';
            form.appendChild(input);
        });
        modal.classList.add('show');
    }

    function closeEditModal() {
        var modal = document.getElementById('shipmentRecordEditModal');
        if (modal) modal.classList.remove('show');
        editModalRowIndex = null;
        editModalSheetName = null;
        editModalCols = null;
    }

    function saveEditModal() {
        var form = document.getElementById('shipmentRecordEditForm');
        var unit = getSelect() ? getSelect().value : '';
        if (!form || !unit || editModalSheetName == null || editModalRowIndex == null || !editModalCols) {
            closeEditModal();
            return;
        }
        var updates = {};
        editModalCols.forEach(function(col) {
            var input = form.querySelector('input[name="' + col + '"]');
            if (input) updates[col] = input.value;
        });
        fetch(apiBase + '/api/shipment-records/record', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                purchase_unit: unit,
                sheet_name: editModalSheetName,
                row_index: editModalRowIndex,
                updates: updates
            })
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    closeEditModal();
                    loadShipmentRecords();
                } else {
                    alert(data.message || '保存失败');
                }
            })
            .catch(function(e) {
                alert('保存失败：' + (e.message || '网络错误'));
            });
    }

    function confirmDeleteRecord(sheetName, rowIndex, row) {
        var displayText = '';
        for (var key in row) {
            if (row[key]) {
                displayText += (row[key] + ' ');
                if (displayText.length > 50) {
                    displayText += '...';
                    break;
                }
            }
        }
        if (confirm('确定要删除这条记录吗？\n\n' + displayText)) {
            deleteRecord(sheetName, rowIndex);
        }
    }

    function deleteRecord(sheetName, rowIndex) {
        var unit = getSelect() ? getSelect().value : '';
        if (!unit) {
            alert('请先选择购买单位');
            return;
        }
        fetch(apiBase + '/api/shipment-records/record', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                purchase_unit: unit,
                sheet_name: sheetName,
                row_index: rowIndex
            })
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.success) {
                    loadShipmentRecords();
                } else {
                    alert(data.message || '删除失败');
                }
            })
            .catch(function(e) {
                alert('删除失败：' + (e.message || '网络错误'));
            });
    }

    function bindShipmentRecordEditModal() {
        var cancel = document.getElementById('shipmentRecordEditCancel');
        var save = document.getElementById('shipmentRecordEditSave');
        var modal = document.getElementById('shipmentRecordEditModal');
        if (cancel) cancel.onclick = closeEditModal;
        if (save) save.onclick = saveEditModal;
        if (modal) {
            modal.onclick = function(e) {
                if (e.target === modal) closeEditModal();
            };
        }
    }

    function escapeHtml(s) {
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    /** 查看记录：按当前选中的购买单位加载并渲染 */
    function loadShipmentRecords() {
        const sel = getSelect();
        if (!sel || !sel.value) {
            alert('请先选择购买单位');
            return;
        }
        const unit = sel.value;
        const tbody = getTableBody();
        if (tbody) tbody.innerHTML = '<tr><td colspan="1" class="empty-state">加载中...</td></tr>';
        fetch(apiBase + '/api/shipment-records/records?purchase_unit=' + encodeURIComponent(unit))
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!data.success) {
                    if (getTableBody()) getTableBody().innerHTML = '<tr><td colspan="1" class="empty-state">' + (data.message || '加载失败') + '</td></tr>';
                    currentRecords = null;
                    currentSheetNames = [];
                    return;
                }
                currentRecords = data.shipment_records || {};
                currentSheetNames = data.sheets || [];
                currentSheetIndex = 0;
                renderSheetTabs();
                renderCurrentSheet();
            })
            .catch(function(e) {
                if (getTableBody()) getTableBody().innerHTML = '<tr><td colspan="1" class="empty-state">请求失败：' + (e.message || '网络错误') + '</td></tr>';
                console.error('出货记录加载失败', e);
            });
    }

    /** 导出当前选中单位的出货记录 Excel（下载） */
    function exportShipmentRecords() {
        const sel = getSelect();
        if (!sel || !sel.value) {
            alert('请先选择购买单位');
            return;
        }
        var unit = sel.value;
        var url = apiBase + '/api/shipment-records/export?purchase_unit=' + encodeURIComponent(unit);
        fetch(url)
            .then(function(res) {
                if (!res.ok) return res.json().then(function(j) { throw new Error(j.message || '导出失败'); });
                return res.blob();
            })
            .then(function(blob) {
                var a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = (unit.replace(/[<>:"/\\|?*]/g, '') || '出货记录') + '_出货记录.xlsx';
                a.style.display = 'none';
                document.body.appendChild(a);
                a.click();
                URL.revokeObjectURL(a.href);
                setTimeout(function() { a.remove(); }, 100);
            })
            .catch(function(e) {
                alert('导出失败：' + (e.message || '未知错误'));
            });
    }

    function onShipmentRecordUnitChange() {
        currentRecords = null;
        currentSheetNames = [];
        var tbody = getTableBody();
        var thead = getTableHead();
        if (tbody) tbody.innerHTML = '<tr><td colspan="1" class="empty-state">请点击「查看记录」加载数据</td></tr>';
        if (thead) thead.innerHTML = '<th>暂无数据</th>';
        if (getSheetsTabs()) getSheetsTabs().style.display = 'none';
        if (getCardTitle()) getCardTitle().textContent = '选择购买单位后点击「查看记录」加载数据';
    }

    window.loadShipmentRecordsUnits = loadShipmentRecordsUnits;
    window.loadShipmentRecords = loadShipmentRecords;
    window.exportShipmentRecords = exportShipmentRecords;
    window.onShipmentRecordUnitChange = onShipmentRecordUnitChange;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindShipmentRecordEditModal);
    } else {
        bindShipmentRecordEditModal();
    }
})();
