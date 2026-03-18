let customersTableBound = false;

function bindCustomersTableEvents() {
    if (customersTableBound) return;
    customersTableBound = true;
}

function loadCustomers() {
    fetch(API_BASE + '/api/customers')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const customers = data.customers || data.data || [];
                renderCustomers(customers);
                document.getElementById('customerCount').textContent = customers.length;
            }
        });
}

function renderCustomers(customers) {
    bindCustomersTableEvents();
    const tbody = document.getElementById('customersTableBody');
    tbody.textContent = '';
    if (!customers || customers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty-state">暂无客户</td></tr>';
        return;
    }
    customers.forEach(c => {
        const tr = document.createElement('tr');

        const checkboxTd = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'customer-checkbox';
        checkbox.value = String(c.id);
        checkboxTd.appendChild(checkbox);
        tr.appendChild(checkboxTd);

        const unitTd = document.createElement('td');
        unitTd.textContent = c.unit_name || c.name || '';
        tr.appendChild(unitTd);

        const contactTd = document.createElement('td');
        contactTd.textContent = c.contact_person || '';
        tr.appendChild(contactTd);

        const phoneTd = document.createElement('td');
        phoneTd.textContent = c.contact_phone || '';
        tr.appendChild(phoneTd);

        const addressTd = document.createElement('td');
        addressTd.textContent = c.address || '';
        tr.appendChild(addressTd);

        tbody.appendChild(tr);
    });
}

function toggleAllCustomers(checkbox) {
    document.querySelectorAll('.customer-checkbox').forEach(cb => {
        cb.checked = checkbox.checked;
    });
}

function batchDeleteCustomers() {
    const checked = document.querySelectorAll('.customer-checkbox:checked');
    if (checked.length === 0) {
        alert('请选择要删除的客户');
        return;
    }
    const key = prompt('请输入密钥确认删除:');
    if (key !== '61408693') {
        alert('密钥错误');
        return;
    }
    
    const ids = Array.from(checked).map(cb => parseInt(cb.value));
    
    fetch(API_BASE + '/api/customers/batch-delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({customer_ids: ids})
    }).then(r => r.json()).then(data => {
        if (data.success) {
            alert(data.message);
            loadCustomers();
        } else {
            alert('删除失败: ' + data.message);
        }
    }).catch(e => {
        alert('删除失败: ' + e.message);
    });
}
