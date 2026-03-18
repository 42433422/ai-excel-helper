let allTools = [];
let toolContainerDelegationBound = false;

function bindToolsEvents() {
    if (toolContainerDelegationBound) return;
    toolContainerDelegationBound = true;

    const container = document.getElementById('toolsContainer');
    if (!container) return;

    container.addEventListener('click', function(e) {
        const queryBtn = e.target.closest('[data-action="open-tool"][data-tool-id]');
        if (queryBtn) {
            e.stopPropagation();
            showToolDetail(queryBtn.getAttribute('data-tool-id'));
            return;
        }

        const card = e.target.closest('.tool-card[data-tool-id]');
        if (card) {
            showToolDetail(card.getAttribute('data-tool-id'));
        }
    });

    document.addEventListener('click', function(e) {
        const closeBtn = e.target.closest('[data-action="close-tool-modal"]');
        if (closeBtn) {
            closeToolModal();
            return;
        }

        const modal = e.target.closest('#toolDetailModal');
        if (modal && e.target === modal) {
            closeToolModal();
        }
    });
}

function loadTools() {
    bindToolsEvents();
    fetch(API_BASE + '/api/db-tools')
        .then(r => r.json())
        .then(data => {
            if (data.success && data.tools && data.tools.length > 0) {
                allTools = data.tools;
                renderTools(allTools);
            } else {
                return fetch(API_BASE + '/api/tools')
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            allTools = data.tools || data || [];
                            renderTools(allTools);
                        }
                    });
            }
        })
        .catch(err => {
            console.error('加载工具失败:', err);
            const container = document.getElementById('toolsContainer');
            if (!container) return;
            container.textContent = '';
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error';
            errorDiv.textContent = '加载失败: ' + String(err);
            container.appendChild(errorDiv);
        });
}

function renderTools(tools) {
    const container = document.getElementById('toolsContainer');
    if (!container) return;
    container.textContent = '';
    if (!tools || tools.length === 0) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'empty';
        emptyDiv.textContent = '没有找到工具';
        container.appendChild(emptyDiv);
        return;
    }

    const categoryNames = {
        products: '产品管理',
        customers: '客户/购买单位',
        orders: '出货单',
        excel: 'Excel 处理',
        ocr: '图片 OCR',
        materials: '原材料仓库',
        print: '标签打印',
        database: '数据库管理',
        system: '系统设置'
    };

    tools.forEach(tool => {
        const categoryKey = (tool && tool.category && tool.category.category_key) ? tool.category.category_key : (tool && tool.category ? tool.category : 'other');
        const categoryName = categoryNames[categoryKey] || categoryKey;
        const toolId = (tool && tool.id != null) ? String(tool.id) : tool.tool_key;

        const card = document.createElement('div');
        card.className = 'tool-card';
        card.setAttribute('data-tool-id', toolId);

        const categorySpan = document.createElement('span');
        categorySpan.className = `tool-category ${categoryKey}`;
        categorySpan.textContent = categoryName;
        card.appendChild(categorySpan);

        const nameDiv = document.createElement('div');
        nameDiv.className = 'tool-name';
        nameDiv.textContent = tool.name || '';
        card.appendChild(nameDiv);

        const descDiv = document.createElement('div');
        descDiv.className = 'tool-description';
        descDiv.textContent = tool.description || '';
        card.appendChild(descDiv);

        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'tool-actions';
        const viewBtn = document.createElement('button');
        viewBtn.className = 'tool-action-btn query';
        viewBtn.textContent = '查看';
        viewBtn.setAttribute('data-action', 'open-tool');
        viewBtn.setAttribute('data-tool-id', toolId);
        actionsDiv.appendChild(viewBtn);
        card.appendChild(actionsDiv);

        container.appendChild(card);
    });
}

function getActionClass(actionName) {
    const actionMap = {
        'query': 'query',
        'search': 'query',
        'list': 'query',
        'add': 'add',
        'create': 'add',
        'new': 'add',
        'edit': 'edit',
        'update': 'edit',
        'modify': 'edit',
        'delete': 'delete',
        'remove': 'delete'
    };
    return actionMap[actionName.toLowerCase()] || 'query';
}

function filterTools() {
    const search = document.getElementById('toolSearch').value.toLowerCase();
    const category = document.getElementById('toolCategoryFilter').value;

    let filtered = allTools.filter(tool => {
        const categoryKey = (tool && tool.category && tool.category.category_key)
            ? tool.category.category_key
            : (tool && tool.category ? tool.category : '');
        const matchSearch = !search || 
            (tool.name || '').toLowerCase().includes(search) || 
            (tool.description || '').toLowerCase().includes(search);
        const matchCategory = !category || categoryKey === category;
        return matchSearch && matchCategory;
    });

    renderTools(filtered);
}

function showToolDetail(toolId) {
    const tool = allTools.find(t => ((t && t.id != null) ? String(t.id) : null) === toolId || t.tool_key === toolId);
    if (!tool) return;

    const categoryNames = {
        products: '产品管理',
        customers: '客户/购买单位',
        orders: '出货单',
        excel: 'Excel 处理',
        ocr: '图片 OCR',
        materials: '原材料仓库',
        print: '标签打印',
        database: '数据库管理',
        system: '系统设置'
    };

    const categoryKey = (tool && tool.category && tool.category.category_key) ? tool.category.category_key : (tool && tool.category ? tool.category : 'other');
    const toolKey = tool.tool_key || tool.id;
    const params = tool.parameters || [];

    const existing = document.getElementById('toolDetailModal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'toolDetailModal';
    modal.style.display = 'flex';

    const content = document.createElement('div');
    content.className = 'modal-content';
    content.style.maxWidth = '500px';

    const header = document.createElement('div');
    header.className = 'modal-header';
    const title = document.createElement('span');
    title.textContent = tool.name || '';
    const close = document.createElement('span');
    close.className = 'close';
    close.textContent = '×';
    close.setAttribute('data-action', 'close-tool-modal');
    header.appendChild(title);
    header.appendChild(close);
    content.appendChild(header);

    const body = document.createElement('div');
    body.className = 'modal-body';

    const pCategory = document.createElement('p');
    pCategory.innerHTML = `<strong>分类：</strong>${escapeHtml(categoryNames[categoryKey] || categoryKey)}`;
    body.appendChild(pCategory);

    const pDesc = document.createElement('p');
    pDesc.innerHTML = `<strong>描述：</strong>${escapeHtml(tool.description || '无')}`;
    body.appendChild(pDesc);

    const pToolKey = document.createElement('p');
    pToolKey.innerHTML = `<strong>工具Key：</strong>${escapeHtml(toolKey)}`;
    body.appendChild(pToolKey);

    if (params.length > 0) {
        const paramsWrap = document.createElement('div');
        paramsWrap.className = 'tool-params';
        const paramsTitle = document.createElement('h4');
        paramsTitle.textContent = '参数';
        paramsWrap.appendChild(paramsTitle);

        params.forEach(param => {
            const paramDiv = document.createElement('div');
            paramDiv.className = 'tool-param';

            const label = document.createElement('label');
            label.textContent = `${param.name}${param.required ? ' *' : ''} (${param.type})`;
            paramDiv.appendChild(label);

            const input = document.createElement('input');
            input.type = param.type === 'number' ? 'number' : 'text';
            input.id = `param_${param.name}`;
            input.placeholder = param.description || '';
            paramDiv.appendChild(input);

            paramsWrap.appendChild(paramDiv);
        });

        body.appendChild(paramsWrap);
    }

    content.appendChild(body);
    modal.appendChild(content);
    document.body.appendChild(modal);
}

function closeToolModal() {
    const modal = document.getElementById('toolDetailModal');
    if (modal) modal.remove();
}

function executeToolAction(toolId, actionName) {
    const tool = allTools.find(t => t.id === toolId);
    if (!tool) return;

    if (tool.parameters && tool.parameters.some(p => p.required)) {
        showToolDetail(toolId);
        return;
    }

    executeToolActionFromModal(toolId, actionName);
}

function executeToolActionFromModal(toolId, actionName) {
    const tool = allTools.find(t => t.id === toolId);
    if (!tool) return;

    const params = {};
    if (tool.parameters) {
        tool.parameters.forEach(param => {
            const input = document.getElementById('param_' + param.name);
            if (input) {
                params[param.name] = input.value;
            }
        });
    }

    fetch(API_BASE + '/api/tools/execute', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            tool_id: toolId,
            action: actionName,
            params: params
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            // 检查是否是发货单生成
            if (toolId === 'shipment_generate' && data.doc_name) {
                // 显示下载按钮
                if (typeof window.showShipmentDownloadEntry === 'function') {
                    window.showShipmentDownloadEntry(data.doc_name);
                }
                alert('发货单生成成功：' + data.doc_name + '\n请点击下方的下载按钮下载文件');
            } else {
                alert('执行成功：' + (data.message || data.response || JSON.stringify(data.data)));
            }
            if (tool.category === 'tools') loadTools();
        } else {
            alert('执行失败：' + data.message);
        }
    })
    .catch(err => {
        alert('执行失败：' + err);
    });

    closeToolModal();
}
