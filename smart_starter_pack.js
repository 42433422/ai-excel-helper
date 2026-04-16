// 智能新手对话包管理系统
class SmartStarterPack {
    constructor() {
        this.functions = this.getDefaultFunctions();
        this.userPreferences = this.loadUserPreferences();
        this.init();
    }
    
    // 默认功能配置
    getDefaultFunctions() {
        return [
            // 查询类功能
            { id: 'query-price', label: '查产品价格', category: 'query', icon: '🔍', 
              description: '快速查询产品价格信息，支持多种查询方式', 
              example: '查询产品「七彩乐园9803」', usage: 156, favorite: true },
            
            { id: 'query-stock', label: '库存查询', category: 'query', icon: '📦', 
              description: '实时查询产品库存状态和可用数量', 
              example: '查询9806A库存情况', usage: 89, favorite: false },
            
            { id: 'query-customer', label: '客户信息查询', category: 'query', icon: '👤', 
              description: '查看客户资料、联系方式和交易记录', 
              example: '查询客户张三的信息', usage: 67, favorite: true },
            
            { id: 'query-invoice-status', label: '发货单状态查询', category: 'query', icon: '📋', 
              description: '跟踪发货单处理进度和当前状态', 
              example: '查询发货单FH2024001状态', usage: 45, favorite: false },
            
            { id: 'query-specs', label: '产品规格查询', category: 'query', icon: '📏', 
              description: '查看产品详细规格参数和技术指标', 
              example: '查询9806A产品规格', usage: 34, favorite: false },
            
            { id: 'query-history', label: '历史订单查询', category: 'query', icon: '📊', 
              description: '查看过往订单记录和交易明细', 
              example: '查询上月订单记录', usage: 28, favorite: false },
            
            { id: 'query-supplier', label: '供应商信息查询', category: 'query', icon: '🏢', 
              description: '查看供应商联系方式和合作记录', 
              example: '查询供应商A的联系方式', usage: 23, favorite: false },
            
            // 操作类功能
            { id: 'add-invoice', label: '增加发货单', category: 'operation', icon: '➕', 
              description: '批量增加发货单数量和规格信息', 
              example: '增加2桶9806规格23', usage: 134, favorite: true },
            
            { id: 'edit-invoice', label: '修改发货单', category: 'operation', icon: '✏️', 
              description: '编辑已创建的发货单内容和信息', 
              example: '修改发货单FH2024001数量', usage: 78, favorite: false },
            
            { id: 'delete-invoice', label: '删除发货单', category: 'operation', icon: '🗑️', 
              description: '删除不需要或错误的发货单记录', 
              example: '删除发货单FH2024002', usage: 56, favorite: false },
            
            { id: 'approve-invoice', label: '发货单审核', category: 'operation', icon: '✅', 
              description: '审核待处理的发货单并确认通过', 
              example: '审核待处理发货单', usage: 42, favorite: true },
            
            { id: 'batch-operate', label: '批量操作', category: 'operation', icon: '🔧', 
              description: '批量处理多个发货单或产品信息', 
              example: '批量更新发货单状态', usage: 38, favorite: false },
            
            { id: 'update-status', label: '状态更新', category: 'operation', icon: '🔄', 
              description: '更新发货单处理状态和进度信息', 
              example: '更新发货单为已发货', usage: 31, favorite: false },
            
            { id: 'export-data', label: '数据导出', category: 'operation', icon: '📤', 
              description: '导出发货单数据为Excel或PDF格式', 
              example: '导出本月发货单数据', usage: 27, favorite: true },
            
            // 生成类功能
            { id: 'generate-invoice', label: '生成发货单', category: 'generate', icon: '📄', 
              description: '自动生成发货单及相关产品信息', 
              example: '发货单蕊芯1一桶9806A规格23', usage: 189, favorite: true },
            
            { id: 'generate-label', label: '生成产品标签', category: 'generate', icon: '🏷️', 
              description: '创建产品标签、条码和识别信息', 
              example: '生成9806A产品标签', usage: 95, favorite: false },
            
            { id: 'generate-report', label: '生成报表', category: 'generate', icon: '📈', 
              description: '生成销售、库存和业务分析报表', 
              example: '生成本月销售报表', usage: 63, favorite: true },
            
            { id: 'generate-statement', label: '生成对账单', category: 'generate', icon: '💳', 
              description: '创建客户对账单和结算信息', 
              example: '生成客户A对账单', usage: 47, favorite: false },
            
            { id: 'generate-purchase', label: '生成采购单', category: 'generate', icon: '🛒', 
              description: '基于库存情况生成采购需求单', 
              example: '生成库存不足产品采购单', usage: 39, favorite: false },
            
            { id: 'generate-notice', label: '生成通知', category: 'generate', icon: '📢', 
              description: '自动生成业务通知和提醒信息', 
              example: '生成发货完成通知', usage: 52, favorite: true }
        ];
    }
    
    // 初始化系统
    init() {
        this.loadUsageData();
        this.setupEventListeners();
        this.renderFunctions();
        this.updateStats();
    }
    
    // 加载用户偏好
    loadUserPreferences() {
        return {
            favorites: JSON.parse(localStorage.getItem('starterPackFavorites') || '{}'),
            usage: JSON.parse(localStorage.getItem('starterPackUsage') || '{}'),
            recent: JSON.parse(localStorage.getItem('starterPackRecent') || '[]'),
            settings: JSON.parse(localStorage.getItem('starterPackSettings') || '{"autoSend": true, "showExamples": true}')
        };
    }
    
    // 加载使用数据
    loadUsageData() {
        this.functions.forEach(func => {
            if (this.userPreferences.usage[func.id]) {
                func.usage = this.userPreferences.usage[func.id];
            }
            if (this.userPreferences.favorites[func.id]) {
                func.favorite = true;
            }
        });
        
        // 按使用频率排序
        this.functions.sort((a, b) => b.usage - a.usage);
    }
    
    // 设置事件监听
    setupEventListeners() {
        // 搜索功能
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this.handleSearch(e.target.value));
        }
        
        // 分类切换
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('category-tab')) {
                this.handleCategoryChange(e.target.dataset.category);
            }
        });
        
        // 收藏功能
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('favorite-star')) {
                e.stopPropagation();
                this.toggleFavorite(e.target.closest('.function-card').dataset.functionId);
            }
        });
        
        // 功能点击
        document.addEventListener('click', (e) => {
            const card = e.target.closest('.function-card');
            if (card) {
                this.handleFunctionClick(card.dataset.functionId);
            }
        });
    }
    
    // 处理搜索
    handleSearch(searchTerm) {
        const cards = document.querySelectorAll('.function-card');
        const term = searchTerm.toLowerCase();
        
        cards.forEach(card => {
            const title = card.querySelector('.function-title').textContent.toLowerCase();
            const desc = card.querySelector('.function-description').textContent.toLowerCase();
            
            card.style.display = (title.includes(term) || desc.includes(term)) ? 'block' : 'none';
        });
    }
    
    // 处理分类切换
    handleCategoryChange(category) {
        // 更新标签状态
        document.querySelectorAll('.category-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-category="${category}"]`).classList.add('active');
        
        // 过滤显示
        const cards = document.querySelectorAll('.function-card');
        cards.forEach(card => {
            if (category === 'all') {
                card.style.display = 'block';
            } else if (category === 'favorite') {
                const isFavorite = card.querySelector('.favorite-star').classList.contains('active');
                card.style.display = isFavorite ? 'block' : 'none';
            } else {
                const cardCategory = card.dataset.category;
                card.style.display = cardCategory === category ? 'block' : 'none';
            }
        });
    }
    
    // 切换收藏
    toggleFavorite(functionId) {
        const func = this.functions.find(f => f.id === functionId);
        if (func) {
            func.favorite = !func.favorite;
            this.userPreferences.favorites[functionId] = func.favorite;
            localStorage.setItem('starterPackFavorites', JSON.stringify(this.userPreferences.favorites));
            
            this.renderFunctions();
            this.updateStats();
        }
    }
    
    // 处理功能点击
    handleFunctionClick(functionId) {
        const func = this.functions.find(f => f.id === functionId);
        if (func) {
            // 增加使用计数
            func.usage++;
            this.userPreferences.usage[functionId] = func.usage;
            localStorage.setItem('starterPackUsage', JSON.stringify(this.userPreferences.usage));
            
            // 添加到最近使用
            this.addToRecent(functionId);
            
            // 发送到聊天系统
            this.sendToChat(func);
            
            // 更新UI
            this.updateUsageDisplay(functionId);
            this.updateStats();
            
            // 视觉反馈
            this.showClickFeedback(functionId);
        }
    }
    
    // 添加到最近使用
    addToRecent(functionId) {
        this.userPreferences.recent = this.userPreferences.recent.filter(id => id !== functionId);
        this.userPreferences.recent.unshift(functionId);
        this.userPreferences.recent = this.userPreferences.recent.slice(0, 10); // 保留最近10个
        localStorage.setItem('starterPackRecent', JSON.stringify(this.userPreferences.recent));
    }
    
    // 发送到聊天系统
    sendToChat(func) {
        const message = this.generateChatMessage(func);
        
        // 尝试多种发送方式
        if (window.sendChatMessage) {
            window.sendChatMessage(message);
        } else if (window.StarterPackUtils && window.StarterPackUtils.quickSend) {
            window.StarterPackUtils.quickSend(message);
        } else {
            // 备用方案：显示消息
            this.showMessage(`功能已准备：${func.label}\n消息：${message}`);
        }
        
        // 记录用户行为
        this.trackUsage('function_click', { functionId: func.id, functionName: func.label });
    }
    
    // 生成聊天消息
    generateChatMessage(func) {
        const baseMessages = {
            'query-price': '请帮我查询产品价格',
            'query-stock': '请查询库存情况',
            'query-customer': '请查询客户信息',
            'generate-invoice': '请生成发货单',
            'add-invoice': '请增加发货单',
            'generate-report': '请生成业务报表'
        };
        
        return baseMessages[func.id] || `请执行${func.label}功能：${func.example}`;
    }
    
    // 更新使用计数显示
    updateUsageDisplay(functionId) {
        const card = document.querySelector(`[data-function-id="${functionId}"]`);
        if (card) {
            const badge = card.querySelector('.usage-badge');
            const func = this.functions.find(f => f.id === functionId);
            if (badge && func) {
                badge.textContent = `${func.usage}次`;
            }
        }
    }
    
    // 显示点击反馈
    showClickFeedback(functionId) {
        const card = document.querySelector(`[data-function-id="${functionId}"]`);
        if (card) {
            card.style.transform = 'scale(0.95)';
            card.style.boxShadow = '0 4px 12px rgba(0, 122, 255, 0.3)';
            
            setTimeout(() => {
                card.style.transform = '';
                card.style.boxShadow = '';
            }, 200);
        }
    }
    
    // 显示消息
    showMessage(text) {
        // 创建临时提示
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #34C759;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            animation: slideInRight 0.3s ease-out;
        `;
        toast.textContent = text;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    // 记录用户行为
    trackUsage(action, data) {
        console.log('用户行为追踪:', action, data);
        // 这里可以集成到分析系统
    }
    
    // 渲染功能列表
    renderFunctions() {
        const container = document.getElementById('functionsGrid');
        if (!container) return;
        
        container.innerHTML = this.functions.map(func => `
            <div class="function-card" data-function-id="${func.id}" data-category="${func.category}">
                <span class="favorite-star ${func.favorite ? 'active' : ''}">${func.favorite ? '★' : '☆'}</span>
                <span class="usage-badge">${func.usage}次</span>
                <div class="function-icon ${func.category}">${func.icon}</div>
                <div class="function-title">${func.label}</div>
                <div class="function-description">${func.description}</div>
                <div class="function-example">示例：${func.example}</div>
            </div>
        `).join('');
    }
    
    // 更新统计信息
    updateStats() {
        const totalFunctions = this.functions.length;
        const favoriteCount = this.functions.filter(f => f.favorite).length;
        const todayUsage = this.calculateTodayUsage();
        
        const statsBar = document.querySelector('.stats-bar');
        if (statsBar) {
            statsBar.innerHTML = `
                <div>总计：${totalFunctions}个功能</div>
                <div>今日使用：${todayUsage}个功能</div>
                <div>收藏功能：${favoriteCount}个</div>
            `;
        }
    }
    
    // 计算今日使用
    calculateTodayUsage() {
        // 简化实现，实际应该基于时间戳
        return this.functions.filter(f => f.usage > 0).length;
    }
    
    // 获取推荐功能（基于使用习惯）
    getRecommendedFunctions(limit = 5) {
        return this.functions
            .sort((a, b) => b.usage - a.usage)
            .slice(0, limit);
    }
    
    // 获取最近使用功能
    getRecentFunctions(limit = 5) {
        return this.userPreferences.recent
            .map(id => this.functions.find(f => f.id === id))
            .filter(f => f)
            .slice(0, limit);
    }
}

// 初始化系统
document.addEventListener('DOMContentLoaded', () => {
    window.starterPack = new SmartStarterPack();
});

// 工具函数
window.StarterPackUtils = {
    // 快速发送消息
    quickSend: function(message) {
        // 尝试多种输入框选择器
        const selectors = ['#chat-input', '.message-input', 'input[type="text"]', 'textarea'];
        let input = null;
        
        for (const selector of selectors) {
            input = document.querySelector(selector);
            if (input) break;
        }
        
        if (input) {
            input.value = message;
            input.focus();
            
            // 触发输入事件
            input.dispatchEvent(new Event('input', { bubbles: true }));
            
            // 尝试自动发送
            const sendButton = document.querySelector('.send-button, button[type="submit"]');
            if (sendButton) {
                setTimeout(() => sendButton.click(), 100);
            }
        }
    },
    
    // 导出功能配置
    exportConfig: function() {
        const config = {
            functions: window.starterPack.functions,
            preferences: window.starterPack.userPreferences,
            exportTime: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'starter-pack-config.json';
        a.click();
        URL.revokeObjectURL(url);
    },
    
    // 导入功能配置
    importConfig: function(file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const config = JSON.parse(e.target.result);
                // 实现配置导入逻辑
                console.log('导入配置:', config);
            } catch (error) {
                console.error('配置导入失败:', error);
            }
        };
        reader.readAsText(file);
    }
};