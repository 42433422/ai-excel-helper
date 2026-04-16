// 新手对话包增强功能
class StarterPackEnhancer {
    constructor() {
        this.functions = [
            {
                id: 'query-price',
                label: '查产品价格',
                hint: '快速查询产品价格信息，支持多种查询方式',
                category: 'query',
                usage: 15,
                favorite: true,
                example: '查询产品「七彩乐园9803」'
            },
            {
                id: 'generate-invoice',
                label: '生成发货单',
                hint: '自动生成发货单及相关产品信息',
                category: 'generate',
                usage: 8,
                favorite: false,
                example: '发货单蕊芯1一桶9806A规格23'
            },
            {
                id: 'add-invoice',
                label: '增加发货单',
                hint: '批量增加发货单数量和规格',
                category: 'operation',
                usage: 12,
                favorite: true,
                example: '增加2桶9806规格23'
            },
            {
                id: 'print-related',
                label: '打印相关',
                hint: '触发打印流程或标签生成',
                category: 'operation',
                usage: 6,
                favorite: false,
                example: '触发打印或标签流程'
            },
            {
                id: 'combo-task',
                label: '组合任务',
                hint: '一键完成开单、生成、打印全流程',
                category: 'generate',
                usage: 20,
                favorite: true,
                example: '一句话完成开单并打印'
            }
        ];
        
        this.init();
    }
    
    init() {
        this.setupSearch();
        this.setupCategories();
        this.setupFavorites();
        this.setupClickHandlers();
        this.loadUserPreferences();
    }
    
    // 搜索功能
    setupSearch() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterFunctions(e.target.value);
            });
        }
    }
    
    // 分类功能
    setupCategories() {
        const tabs = document.querySelectorAll('.category-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const category = e.target.dataset.category;
                this.showCategory(category);
            });
        });
    }
    
    // 收藏功能
    setupFavorites() {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('favorite-star')) {
                e.stopPropagation();
                this.toggleFavorite(e.target);
            }
        });
    }
    
    // 点击处理
    setupClickHandlers() {
        document.addEventListener('click', (e) => {
            const item = e.target.closest('.starter-pack-item');
            if (item) {
                this.handleFunctionClick(item);
            }
        });
    }
    
    // 过滤功能
    filterFunctions(searchTerm) {
        const items = document.querySelectorAll('.starter-pack-item');
        items.forEach(item => {
            const label = item.querySelector('.starter-pack-label').textContent.toLowerCase();
            const hint = item.querySelector('.starter-pack-hint').textContent.toLowerCase();
            
            if (label.includes(searchTerm.toLowerCase()) || hint.includes(searchTerm.toLowerCase())) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    }
    
    // 显示分类
    showCategory(category) {
        const items = document.querySelectorAll('.starter-pack-item');
        
        items.forEach(item => {
            if (category === 'all') {
                item.style.display = 'block';
            } else if (category === 'favorite') {
                const isFavorite = item.querySelector('.favorite-star').textContent === '★';
                item.style.display = isFavorite ? 'block' : 'none';
            } else {
                const itemCategory = item.dataset.category;
                item.style.display = itemCategory === category ? 'block' : 'none';
            }
        });
        
        // 更新标签状态
        document.querySelectorAll('.category-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-category="${category}"]`).classList.add('active');
    }
    
    // 切换收藏
    toggleFavorite(star) {
        const item = star.closest('.starter-pack-item');
        const functionId = item.dataset.functionId;
        
        if (star.textContent === '☆') {
            star.textContent = '★';
            star.style.color = '#ffc107';
            this.saveFavorite(functionId, true);
        } else {
            star.textContent = '☆';
            star.style.color = '#ccc';
            this.saveFavorite(functionId, false);
        }
    }
    
    // 处理功能点击
    handleFunctionClick(item) {
        const functionId = item.dataset.functionId;
        const functionData = this.functions.find(f => f.id === functionId);
        
        if (functionData) {
            // 发送到聊天框
            this.sendToChat(functionData);
            
            // 增加使用计数
            this.incrementUsage(functionId);
            
            // 视觉反馈
            this.showClickFeedback(item);
        }
    }
    
    // 发送到聊天框
    sendToChat(functionData) {
        // 这里需要与您的聊天系统集成
        console.log('发送功能到聊天框:', functionData);
        
        // 示例：自动填充输入框并发送
        const message = this.generateMessage(functionData);
        
        // 假设有全局的聊天发送函数
        if (window.sendChatMessage) {
            window.sendChatMessage(message);
        } else {
            // 备用方案：填充输入框
            const inputElement = document.querySelector('#chat-input');
            if (inputElement) {
                inputElement.value = message;
                // 自动触发发送（根据您的系统调整）
                inputElement.dispatchEvent(new Event('input', { bubbles: true }));
            }
        }
    }
    
    // 生成消息内容
    generateMessage(functionData) {
        switch(functionData.id) {
            case 'query-price':
                return `请帮我查询产品价格：${functionData.example}`;
            case 'generate-invoice':
                return `请生成发货单：${functionData.example}`;
            case 'add-invoice':
                return `请增加发货单：${functionData.example}`;
            case 'print-related':
                return `请处理打印相关：${functionData.example}`;
            case 'combo-task':
                return `请执行组合任务：${functionData.example}`;
            default:
                return functionData.example;
        }
    }
    
    // 增加使用计数
    incrementUsage(functionId) {
        const functionData = this.functions.find(f => f.id === functionId);
        if (functionData) {
            functionData.usage++;
            
            // 更新UI
            const item = document.querySelector(`[data-function-id="${functionId}"]`);
            if (item) {
                const usageElement = item.querySelector('.usage-count');
                if (usageElement) {
                    usageElement.textContent = `${functionData.usage}次`;
                }
            }
            
            // 保存到本地存储
            this.saveUsage(functionId, functionData.usage);
        }
    }
    
    // 显示点击反馈
    showClickFeedback(item) {
        item.style.transform = 'scale(0.95)';
        item.style.boxShadow = '0 2px 8px rgba(0, 122, 255, 0.3)';
        
        setTimeout(() => {
            item.style.transform = '';
            item.style.boxShadow = '';
        }, 200);
    }
    
    // 保存用户偏好
    saveFavorite(functionId, isFavorite) {
        const favorites = this.getFavorites();
        if (isFavorite) {
            favorites[functionId] = true;
        } else {
            delete favorites[functionId];
        }
        localStorage.setItem('starterPackFavorites', JSON.stringify(favorites));
    }
    
    saveUsage(functionId, usage) {
        const usageData = this.getUsageData();
        usageData[functionId] = usage;
        localStorage.setItem('starterPackUsage', JSON.stringify(usageData));
    }
    
    // 加载用户偏好
    loadUserPreferences() {
        const favorites = this.getFavorites();
        const usageData = this.getUsageData();
        
        // 更新功能数据
        this.functions.forEach(func => {
            if (favorites[func.id]) {
                func.favorite = true;
            }
            if (usageData[func.id]) {
                func.usage = usageData[func.id];
            }
        });
        
        // 按使用频率排序
        this.functions.sort((a, b) => b.usage - a.usage);
        
        // 重新渲染UI（如果需要）
        this.renderFunctions();
    }
    
    getFavorites() {
        return JSON.parse(localStorage.getItem('starterPackFavorites') || '{}');
    }
    
    getUsageData() {
        return JSON.parse(localStorage.getItem('starterPackUsage') || '{}');
    }
    
    // 渲染功能列表
    renderFunctions() {
        const container = document.getElementById('functionGrid');
        if (!container) return;
        
        container.innerHTML = this.functions.map(func => `
            <div class="starter-pack-item" data-function-id="${func.id}" data-category="${func.category}">
                <span class="favorite-star" style="color: ${func.favorite ? '#ffc107' : '#ccc'}">
                    ${func.favorite ? '★' : '☆'}
                </span>
                <span class="usage-count">${func.usage}次</span>
                <div class="starter-pack-label">${func.label}</div>
                <div class="starter-pack-hint">${func.hint}</div>
                <div class="quick-action">示例：${func.example}</div>
            </div>
        `).join('');
    }
}

// 初始化增强功能
document.addEventListener('DOMContentLoaded', () => {
    new StarterPackEnhancer();
});

// 与现有系统集成的辅助函数
window.StarterPackUtils = {
    // 快速发送消息
    quickSend: function(message) {
        const input = document.querySelector('#chat-input, .message-input, input[type="text"]');
        if (input) {
            input.value = message;
            input.focus();
            
            // 尝试触发发送事件
            const sendButton = document.querySelector('.send-button, button[type="submit"]');
            if (sendButton) {
                sendButton.click();
            }
        }
    },
    
    // 获取当前用户信息
    getCurrentUser: function() {
        return {
            id: localStorage.getItem('userId') || 'anonymous',
            role: localStorage.getItem('userRole') || 'user'
        };
    },
    
    // 记录用户行为
    trackUsage: function(action, data) {
        console.log('用户行为追踪:', action, data);
        // 这里可以集成到您的分析系统
    }
};