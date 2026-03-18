let materialListCache = [];
let materialTableEventsBound = false;

function bindMaterialTableEvents() {
    if (materialTableEventsBound) return;
    materialTableEventsBound = true;

    const tbody = document.getElementById('materialsTableBody');
    if (!tbody) return;

    tbody.addEventListener('click', function(e) {
        const target = e.target.closest('[data-action][data-material-id]');
        if (!target) return;

        const materialId = Number(target.getAttribute('data-material-id'));
        if (!materialId) return;

        if (target.getAttribute('data-action') === 'edit-material') {
            editMaterial(materialId);
            return;
        }

        if (target.getAttribute('data-action') === 'delete-material') {
            deleteMaterial(materialId);
        }
    });
}

function loadMaterials() {
    fetch(API_BASE + '/api/materials')
        .then(r => r.json())
        .then(data => {
            if (data.success) renderMaterials(data.data);
        });
}

function renderMaterials(materials) {
    bindMaterialTableEvents();
    materialListCache = Array.isArray(materials) ? materials : [];
    const tbody = document.getElementById('materialsTableBody');
    tbody.textContent = '';
    if (!materialListCache.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state">暂无原材料</td></tr>';
        return;
    }
    materialListCache.forEach(m => {
        const isLow = Number(m.quantity || 0) <= Number(m.min_stock || 0);
        const tr = document.createElement('tr');
        if (isLow) tr.style.background = '#fff3cd';

        const checkboxTd = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'material-checkbox';
        checkbox.value = String(m.id);
        checkboxTd.appendChild(checkbox);
        tr.appendChild(checkboxTd);

        const codeTd = document.createElement('td');
        codeTd.textContent = m.material_code || '';
        tr.appendChild(codeTd);

        const nameTd = document.createElement('td');
        nameTd.textContent = m.name || '';
        tr.appendChild(nameTd);

        const categoryTd = document.createElement('td');
        categoryTd.textContent = m.category || '';
        tr.appendChild(categoryTd);

        const quantityTd = document.createElement('td');
        const quantityBadge = document.createElement('span');
        quantityBadge.className = `badge ${isLow ? 'badge-danger' : 'badge-success'}`;
        quantityBadge.textContent = String(Number(m.quantity || 0));
        quantityTd.appendChild(quantityBadge);
        tr.appendChild(quantityTd);

        const priceTd = document.createElement('td');
        priceTd.textContent = `¥${Number(m.unit_price || 0)}`;
        tr.appendChild(priceTd);

        const supplierTd = document.createElement('td');
        supplierTd.textContent = m.supplier || '';
        tr.appendChild(supplierTd);

        const actionTd = document.createElement('td');
        const actionBtns = document.createElement('div');
        actionBtns.className = 'action-btns';
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-secondary';
        editBtn.textContent = '编辑';
        editBtn.setAttribute('data-action', 'edit-material');
        editBtn.setAttribute('data-material-id', String(m.id));
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-danger';
        deleteBtn.textContent = '删除';
        deleteBtn.setAttribute('data-action', 'delete-material');
        deleteBtn.setAttribute('data-material-id', String(m.id));
        actionBtns.appendChild(editBtn);
        actionBtns.appendChild(deleteBtn);
        actionTd.appendChild(actionBtns);
        tr.appendChild(actionTd);

        tbody.appendChild(tr);
    });
}

function searchMaterials() {
    const query = document.getElementById('materialSearch').value;
    const categoryEl = document.getElementById('materialCategoryFilter');
    const category = categoryEl ? categoryEl.value.trim() : '';
    let url = API_BASE + '/api/materials';
    const params = [];
    if (query) params.push('search=' + encodeURIComponent(query));
    if (category) params.push('category=' + encodeURIComponent(category));
    if (params.length) url += '?' + params.join('&');
    fetch(url).then(r => r.json()).then(data => {
        if (data.success) renderMaterials(data.data);
    });
}

function loadLowStock() {
    fetch(API_BASE + '/api/materials/low-stock')
        .then(r => r.json())
        .then(data => {
            if (data.success && data.data.length > 0) {
                document.getElementById('lowStockWarning').style.display = 'block';
                document.getElementById('lowStockList').innerHTML = data.data.map(m => 
                    `<div>${escapeHtml(m.name)} (${Number(m.quantity || 0)}/${Number(m.min_stock || 0)}) - ${escapeHtml(m.supplier || '')}</div>`
                ).join('');
            } else {
                document.getElementById('lowStockWarning').style.display = 'none';
            }
        });
}

function showMaterialModal() {
    document.getElementById('materialModal').classList.add('active');
    document.getElementById('materialModalTitle').textContent = '添加原材料';
    document.getElementById('materialId').value = '';
}

function closeMaterialModal() {
    document.getElementById('materialModal').classList.remove('active');
}

function editMaterial(id) {
    const m = materialListCache.find(x => Number(x.id) === Number(id));
    if (!m) return;
    document.getElementById('materialModal').classList.add('active');
    document.getElementById('materialModalTitle').textContent = '编辑原材料';
    document.getElementById('materialId').value = m.id;
    document.getElementById('materialCode').value = m.material_code;
    document.getElementById('materialName').value = m.name;
    document.getElementById('materialCategory').value = m.category;
    document.getElementById('materialSpec').value = m.specification;
    document.getElementById('materialUnit').value = m.unit;
    document.getElementById('materialQuantity').value = m.quantity;
    document.getElementById('materialPrice').value = m.unit_price;
    document.getElementById('materialSupplier').value = m.supplier;
    document.getElementById('materialMinStock').value = m.min_stock;
}

function saveMaterial() {
    const id = document.getElementById('materialId').value;
    const data = {
        material_code: document.getElementById('materialCode').value,
        name: document.getElementById('materialName').value,
        category: document.getElementById('materialCategory').value,
        specification: document.getElementById('materialSpec').value,
        unit: document.getElementById('materialUnit').value,
        quantity: parseFloat(document.getElementById('materialQuantity').value) || 0,
        unit_price: parseFloat(document.getElementById('materialPrice').value) || 0,
        supplier: document.getElementById('materialSupplier').value,
        min_stock: parseFloat(document.getElementById('materialMinStock').value) || 0
    };

    if (!data.material_code || !data.name) {
        alert('请填写必填项');
        return;
    }

    const method = id ? 'PUT' : 'POST';
    const url = id ? API_BASE + '/api/materials/' + id : API_BASE + '/api/materials';

    fetch(url, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).then(r => r.json()).then(data => {
        if (data.success) {
            closeMaterialModal();
            loadMaterials();
        } else {
            alert(data.message || '保存失败');
        }
    });
}

function deleteMaterial(id) {
    if (!confirm('确定删除这个原材料？')) return;
    fetch(API_BASE + '/api/materials/' + id, {method: 'DELETE'})
        .then(r => r.json())
        .then(data => {
            if (data.success) loadMaterials();
            else alert(data.message);
        });
}

function toggleAllMaterials(checkbox) {
    document.querySelectorAll('.material-checkbox').forEach(cb => {
        cb.checked = checkbox.checked;
    });
}

function batchDeleteMaterials() {
    const checked = document.querySelectorAll('.material-checkbox:checked');
    if (checked.length === 0) {
        alert('请选择要删除的原材料');
        return;
    }
    const key = prompt('请输入密钥确认删除:');
    if (key !== '61408693') {
        alert('密钥错误');
        return;
    }
    
    const ids = Array.from(checked).map(cb => parseInt(cb.value));
    
    fetch(API_BASE + '/api/materials/batch-delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({material_ids: ids})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            alert(data.message);
            loadMaterials();
        } else {
            alert('删除失败: ' + data.message);
        }
    }).catch(e => {
        alert('删除失败: ' + e.message);
    });
}
