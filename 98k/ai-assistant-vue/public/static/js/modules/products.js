let productListCache = [];
let productTableEventsBound = false;
/** 当前产品列表所属单位（从下拉选择），用于编辑/删除时传参 */
let currentProductUnitName = '';

function bindProductTableEvents() {
    if (productTableEventsBound) return;
    productTableEventsBound = true;

    const tbody = document.getElementById('productsTableBody');
    if (!tbody) return;

    tbody.addEventListener('click', function(e) {
        const target = e.target.closest('[data-action][data-product-id]');
        if (!target) return;

        const productId = Number(target.getAttribute('data-product-id'));
        if (!productId) return;

        if (target.getAttribute('data-action') === 'edit-product') {
            editProduct(productId);
            return;
        }

        if (target.getAttribute('data-action') === 'delete-product') {
            deleteProduct(productId);
        }
    });
}

function loadProductUnits() {
    const sel = document.getElementById('productUnitSelect');
    if (!sel || sel.options.length > 1) return;
    const base = (typeof API_BASE !== 'undefined' ? API_BASE : '') || '';
    fetch(base + '/api/customers')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (!sel) return;
            var list = (data && data.customers) ? data.customers : (data && data.data) ? data.data : [];
            list.forEach(function (item) {
                var opt = document.createElement('option');
                opt.value = item.unit_name || item.name || '';
                opt.textContent = item.unit_name || item.name || ('单位' + (item.id || ''));
                if (item.id) opt.setAttribute('data-id', String(item.id));
                sel.appendChild(opt);
            });
        })
        .catch(function () {});
    return;
}

function loadProducts() {
    var sel = document.getElementById('productUnitSelect');
    if (sel && sel.options.length <= 1) loadProductUnits();
    var unitName = (sel && sel.value) ? sel.value.trim() : '';
    currentProductUnitName = unitName;
    var tbody = document.getElementById('productsTableBody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="empty-state">加载中...</td></tr>';
    var base = (typeof API_BASE !== 'undefined' ? API_BASE : '') || '';
    var url = base + '/api/products';
    if (unitName) url += '?unit=' + encodeURIComponent(unitName);
    fetch(url)
        .then(function (r) { return r.json().catch(function () { return { success: false, message: '返回格式异常' }; }); })
        .then(function (data) {
            if (data && data.success && Array.isArray(data.data)) {
                renderProducts(data.data, unitName);
            } else {
                renderProducts([], unitName);
                if (tbody && data && !data.success && data.message) {
                    tbody.innerHTML = '<tr><td colspan="6" class="empty-state">加载失败：' + (data.message || '未知错误') + '</td></tr>';
                }
            }
        })
        .catch(function (err) {
            if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="empty-state">加载失败：' + (err.message || '网络错误') + '</td></tr>';
        });
}

function renderProducts(products, unitName) {
    bindProductTableEvents();
    productListCache = Array.isArray(products) ? products : [];
    var tbody = document.getElementById('productsTableBody');
    if (!tbody) return;
    tbody.textContent = '';
    if (!productListCache.length) {
        var hint = unitName
            ? '该单位暂无产品，可点击「添加产品」为该单位录入产品'
            : '请先选择购买单位，即可查看或添加该单位的产品';
        tbody.innerHTML = '<tr><td colspan="6" class="empty-state">' + hint + '</td></tr>';
        return;
    }
    productListCache.forEach(p => {
        const tr = document.createElement('tr');

        const checkboxTd = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'product-checkbox';
        checkbox.value = String(p.id);
        checkboxTd.appendChild(checkbox);
        tr.appendChild(checkboxTd);

        const modelTd = document.createElement('td');
        modelTd.textContent = p.model_number || '';
        tr.appendChild(modelTd);

        const nameTd = document.createElement('td');
        nameTd.textContent = p.name || '';
        tr.appendChild(nameTd);

        const specTd = document.createElement('td');
        specTd.textContent = p.specification || '';
        tr.appendChild(specTd);

        const priceTd = document.createElement('td');
        priceTd.textContent = `¥${Number(p.price || 0)}`;
        tr.appendChild(priceTd);

        const actionTd = document.createElement('td');
        const actionBtns = document.createElement('div');
        actionBtns.className = 'action-btns';
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-secondary';
        editBtn.textContent = '编辑';
        editBtn.setAttribute('data-action', 'edit-product');
        editBtn.setAttribute('data-product-id', String(p.id));
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-danger';
        deleteBtn.textContent = '删除';
        deleteBtn.setAttribute('data-action', 'delete-product');
        deleteBtn.setAttribute('data-product-id', String(p.id));
        actionBtns.appendChild(editBtn);
        actionBtns.appendChild(deleteBtn);
        actionTd.appendChild(actionBtns);
        tr.appendChild(actionTd);

        tbody.appendChild(tr);
    });
}

function toggleAllProducts(checkbox) {
    document.querySelectorAll('.product-checkbox').forEach(cb => {
        cb.checked = checkbox.checked;
    });
}

function batchDeleteProducts() {
    const checked = document.querySelectorAll('.product-checkbox:checked');
    if (checked.length === 0) {
        alert('请选择要删除的产品');
        return;
    }
    const key = prompt('请输入密钥确认删除:');
    if (key !== '61408693') {
        alert('密钥错误');
        return;
    }
    if (!confirm('确定要删除选中的 ' + checked.length + ' 个产品吗？')) return;
    
    const ids = Array.from(checked).map(cb => parseInt(cb.value));
    
    fetch(API_BASE + '/api/products/batch-delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({product_ids: ids})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            alert(data.message);
            loadProducts();
        } else {
            alert('删除失败: ' + data.message);
        }
    }).catch(e => {
        alert('删除失败: ' + e.message);
    });
}

function searchProducts() {
    var query = document.getElementById('productSearch').value;
    var sel = document.getElementById('productUnitSelect');
    var unitName = (sel && sel.value) ? sel.value.trim() : '';
    var base = (typeof API_BASE !== 'undefined' ? API_BASE : '') || '';
    var url = base + '/api/products?';
    if (unitName) url += 'unit=' + encodeURIComponent(unitName) + '&';
    if (query) url += 'search=' + encodeURIComponent(query);
    else if (!unitName) url = base + '/api/products';
    fetch(url).then(function (r) { return r.json(); }).then(function (data) {
        if (data.success) renderProducts(data.data, unitName);
    });
}

function showProductModal(id = null) {
    document.getElementById('productModal').classList.add('active');
    document.getElementById('productModalTitle').textContent = id ? '编辑产品' : '添加产品';
    if (!id) {
        document.getElementById('productId').value = '';
        document.getElementById('productModel').value = '';
        document.getElementById('productName').value = '';
        document.getElementById('productSpec').value = '';
        document.getElementById('productPrice').value = '';
    }
}

function closeProductModal() {
    document.getElementById('productModal').classList.remove('active');
}

function editProduct(id, model, name, spec, price) {
    if (typeof model === 'undefined') {
        const product = productListCache.find(p => Number(p.id) === Number(id));
        if (!product) return;
        model = product.model_number || '';
        name = product.name || '';
        spec = product.specification || '';
        price = product.price || 0;
    }
    document.getElementById('productModal').classList.add('active');
    document.getElementById('productModalTitle').textContent = '编辑产品';
    document.getElementById('productId').value = id;
    document.getElementById('productModel').value = model;
    document.getElementById('productName').value = name;
    document.getElementById('productSpec').value = spec;
    document.getElementById('productPrice').value = price;
}

function saveProduct() {
    var id = document.getElementById('productId').value;
    var sel = document.getElementById('productUnitSelect');
    var unitName = (sel && sel.value) ? sel.value.trim() : '';
    var unitId = (sel && sel.selectedOptions && sel.selectedOptions[0]) ? (sel.selectedOptions[0].getAttribute('data-id') || '') : '';
    var data = {
        model_number: document.getElementById('productModel').value,
        name: document.getElementById('productName').value,
        specification: document.getElementById('productSpec').value,
        price: parseFloat(document.getElementById('productPrice').value) || 0
    };
    if (!data.model_number || !data.name) {
        alert('请填写型号和名称');
        return;
    }
    if (!id && !unitName) {
        alert('请先选择购买单位，再添加产品');
        return;
    }
    if (unitName) {
        data.purchase_unit = unitName;
        if (unitId) data.purchase_unit_id = parseInt(unitId, 10);
    }
    if (id) {
        if (currentProductUnitName) data.unit_name = currentProductUnitName;
    }
    var base = (typeof API_BASE !== 'undefined' ? API_BASE : '') || '';
    var method = id ? 'PUT' : 'POST';
    var url = id ? base + '/api/products/' + id : base + '/api/products';
    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(function (r) { return r.json(); }).then(function (res) {
        if (res.success) {
            closeProductModal();
            loadProducts();
        } else {
            alert(res.message || '保存失败');
        }
    }).catch(function (e) { alert('保存失败：' + (e.message || '网络错误')); });
}

function deleteProduct(id) {
    if (!confirm('确定删除这个产品？')) return;
    var base = (typeof API_BASE !== 'undefined' ? API_BASE : '') || '';
    var opts = { method: 'DELETE', headers: { 'Content-Type': 'application/json' } };
    if (currentProductUnitName) opts.body = JSON.stringify({ purchase_unit: currentProductUnitName });
    fetch(base + '/api/products/' + id, opts)
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.success) loadProducts();
            else alert(data.message || '删除失败');
        })
        .catch(function (e) { alert('删除失败：' + (e.message || '网络错误')); });
}

/** 导出当前选中单位的产品价格表（Excel） */
function exportProductPriceList() {
    var sel = document.getElementById('productUnitSelect');
    if (!sel || !sel.value || !sel.value.trim()) {
        alert('请先选择购买单位');
        return;
    }
    var unitName = sel.value.trim();
    var unitId = (sel.selectedOptions && sel.selectedOptions[0]) ? (sel.selectedOptions[0].getAttribute('data-id') || '') : '';
    var base = (typeof API_BASE !== 'undefined' ? API_BASE : '') || '';
    var params = new URLSearchParams();
    if (unitId) params.set('unit_id', unitId);
    params.set('unit', unitName);
    var url = base + '/api/export_unit_products_xlsx?' + params.toString();
    fetch(url)
        .then(function (res) {
            if (res.ok) return res.blob();
            return res.text().then(function (text) {
                try {
                    var data = JSON.parse(text);
                    throw new Error(data.message || '导出失败');
                } catch (e) {
                    if (e instanceof SyntaxError || (text && text.trim().startsWith('<'))) {
                        throw new Error('服务器返回异常（' + res.status + '），请确认该单位有产品数据');
                    }
                    if (e instanceof Error) throw e;
                    throw new Error(text || res.statusText || '导出失败');
                }
            });
        })
        .then(function (blob) {
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = (unitName || '产品') + '_价格表.xlsx';
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            URL.revokeObjectURL(a.href);
            setTimeout(function () { a.remove(); }, 100);
        })
        .catch(function (err) {
            alert('导出失败：' + (err.message || '未返回文件'));
        });
}
