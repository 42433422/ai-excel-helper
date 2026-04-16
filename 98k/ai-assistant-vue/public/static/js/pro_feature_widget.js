/**
 * 专业版功能悬浮窗 - 科技感设计
 * 支持多种专业功能模块
 */

class ProFeatureWidget {
    constructor() {
        this.widgetId = 'pro-feature-widget';
        this.isShowing = false;
        this.checkInterval = null;
        this._loginPanelEl = null;
        this._loginStatusSource = null;
        this._pinnedCustomerRow = null;
        this._productCompanies = [];
        this._selectedProductCompany = null;
        this._productAllItems = [];
        this._selectedProductCompanyRow = null;
        this._customerManageBound = false;
        this._pinnedManageRow = null;
        this.init();
    }

    init() {
        this.createWidget();
        this.addStyles();
        this.bindEvents();
    }

    createWidget() {
        const widget = document.createElement('div');
        widget.id = this.widgetId;
        widget.className = 'pro-feature-widget-container hide';
        widget.innerHTML = `
            <div class="pro-feature-widget-panel">
                <div class="tech-border top"></div>
                <div class="tech-border right"></div>
                <div class="tech-border bottom"></div>
                <div class="tech-border left"></div>
                
                <div class="pro-feature-widget-header">
                    <div class="header-title">
                        <span class="icon" id="widget-icon">🔧</span>
                        <span id="widget-title">专业功能</span>
                    </div>
                    <button class="close-btn" title="关闭">×</button>
                </div>
                
                <div class="pro-feature-widget-content" id="widget-content"></div>
                
                <div class="pro-feature-widget-footer">
                    <div class="status-indicator">
                        <span class="status-dot"></span>
                        <span class="status-label" id="widget-status">就绪</span>
                    </div>
                    <div class="action-buttons" id="action-buttons"></div>
                </div>
            </div>
        `;
        document.body.appendChild(widget);
        this.addStyles();
    }

    addStyles() {
        const styleId = 'pro-widget-styles';
        if (document.getElementById(styleId)) return;

        const styles = `
            <style id="${styleId}">
                .pro-feature-widget-container {
                    position: fixed;
                    top: 50%;
                    right: -450px;
                    transform: translateY(-50%);
                    z-index: 10000;
                    transition: right 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                    pointer-events: none;
                }
                .pro-feature-widget-container.show { right: 20px; }
                .pro-feature-widget-container.hide { display: none; }
                
                .pro-feature-widget-panel {
                    width: 400px;
                    background: linear-gradient(135deg, rgba(26,26,46,0.98) 0%, rgba(22,33,62,0.95) 100%);
                    border-radius: 16px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.4), 0 0 0 1px rgba(74,144,217,0.2);
                    backdrop-filter: blur(20px);
                    overflow: hidden;
                    position: relative;
                    pointer-events: auto;
                }
                
                .tech-border {
                    position: absolute;
                    background: linear-gradient(90deg, #4a90d9, #6ab0ff);
                    opacity: 0.6;
                }
                .tech-border.top { top: 0; left: 20px; right: 20px; height: 2px; }
                .tech-border.right { top: 20px; right: 0; bottom: 20px; width: 2px; }
                .tech-border.bottom { bottom: 0; left: 20px; right: 20px; height: 2px; }
                .tech-border.left { top: 20px; left: 0; bottom: 20px; width: 2px; }
                
                .pro-feature-widget-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 16px 20px;
                    border-bottom: 1px solid rgba(74,144,217,0.2);
                    background: rgba(0,0,0,0.2);
                }
                .header-title {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    color: #fff;
                    font-size: 16px;
                    font-weight: 600;
                }
                .header-title .icon { font-size: 20px; }
                .close-btn {
                    background: rgba(255,255,255,0.1);
                    border: none;
                    color: rgba(255,255,255,0.6);
                    width: 28px;
                    height: 28px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 18px;
                    transition: all 0.2s;
                }
                .close-btn:hover { background: rgba(255,255,255,0.2); color: #fff; }
                
                .pro-feature-widget-content {
                    padding: 24px 20px;
                    min-height: 300px;
                }
                
                .pro-feature-widget-footer {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 20px;
                    border-top: 1px solid rgba(74,144,217,0.2);
                    background: rgba(0,0,0,0.2);
                }
                .status-indicator {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    color: rgba(255,255,255,0.6);
                    font-size: 13px;
                }
                .status-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #ffc107;
                    animation: blink 1.5s ease-in-out infinite;
                }
                @keyframes blink { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
                .status-dot.success {
                    background: #28a745;
                    animation: none;
                    box-shadow: 0 0 8px rgba(40,167,69,0.6);
                }
                
                .action-buttons { display: flex; gap: 8px; }
                .action-btn {
                    background: rgba(74,144,217,0.2);
                    border: 1px solid rgba(74,144,217,0.4);
                    color: rgba(255,255,255,0.8);
                    padding: 6px 12px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 13px;
                    transition: all 0.2s;
                }
                .action-btn:hover { background: rgba(74,144,217,0.3); }
                .action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
                
                /* 微信登录样式 */
                .wechat-qrcode-wrapper {
                    text-align: center;
                }
                .wechat-qrcode-img {
                    width: 200px;
                    height: 200px;
                    margin: 0 auto 16px;
                    border-radius: 12px;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
                }
                .scan-line {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(90deg, transparent, #4a90d9, transparent);
                    animation: scan 2s linear infinite;
                }
                @keyframes scan { 0% { top: 0; } 100% { top: 100%; } }
                .wechat-tips {
                    background: rgba(74,144,217,0.1);
                    border-radius: 8px;
                    padding: 16px;
                    margin-top: 16px;
                }
                .tip-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    color: rgba(255,255,255,0.7);
                    font-size: 13px;
                    margin-bottom: 8px;
                }
                .tip-item:last-child { margin-bottom: 0; }
                .tip-icon { color: #4a90d9; font-weight: bold; }

                .pro-feature-widget-container.open-layout .pro-feature-widget-panel {
                    width: min(640px, calc(100vw - 24px));
                    border-radius: 18px;
                    background: linear-gradient(180deg, rgba(9, 17, 30, 0.96), rgba(12, 22, 38, 0.92));
                    box-shadow: 0 26px 80px rgba(0,0,0,0.52), 0 0 0 1px rgba(122, 187, 255, 0.25);
                    clip-path: none;
                }
                .pro-feature-widget-container.open-layout .pro-feature-widget-content {
                    min-height: 420px;
                    padding: 16px;
                }
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-footer {
                    display: none;
                }
                .pro-feature-widget-container.clean-user-list {
                    right: -760px;
                    left: auto;
                    transition: right 0.35s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                }
                .pro-feature-widget-container.clean-user-list.show {
                    right: 6px;
                    left: auto;
                }
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-header {
                    display: none;
                }
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content {
                    padding: 0;
                    min-height: auto;
                }
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-panel {
                    background: transparent;
                    box-shadow: none;
                    border-radius: 0;
                    overflow: visible;
                    backdrop-filter: none;
                    -webkit-backdrop-filter: none;
                    pointer-events: none;
                }
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content {
                    pointer-events: none;
                }
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content button,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content input,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content textarea,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content select,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .floating-unit-token,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .product-item,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .company-token,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .inline-detail,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .product-query-search,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .customer-input,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .customer-save-btn {
                    pointer-events: auto;
                }
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .product-company-cloud .customer-row {
                    pointer-events: none;
                }
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .product-company-cloud .floating-unit-token,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .product-company-cloud .inline-detail,
                .pro-feature-widget-container.clean-user-list .pro-feature-widget-content .product-company-cloud .inline-detail * {
                    pointer-events: auto;
                }
                .pro-feature-widget-container.clean-user-list .tech-border {
                    display: none;
                }

                .customer-panel {
                    display: grid;
                    grid-template-columns: 1fr;
                    gap: 12px;
                    position: relative;
                    min-height: 420px;
                    align-items: start;
                }
                .pro-feature-widget-container.clean-user-list .customer-panel {
                    min-height: auto;
                    border-radius: 0;
                    background: transparent;
                    border: none;
                    padding: 0;
                }
                .customer-manage-panel {
                    display: grid;
                    gap: 10px;
                    align-content: start;
                }
                .customer-manage-card {
                    border: 1px solid rgba(132, 198, 255, 0.2);
                    border-radius: 10px;
                    background: rgba(7, 20, 35, 0.35);
                    padding: 10px;
                    display: grid;
                    gap: 8px;
                }
                .customer-manage-title {
                    font-size: 12px;
                    color: rgba(169, 229, 255, 0.95);
                    letter-spacing: 0.45px;
                }
                .customer-manage-input,
                .customer-manage-select {
                    width: 100%;
                    border: 1px solid rgba(141, 201, 255, 0.28);
                    border-radius: 8px;
                    background: rgba(8, 18, 32, 0.78);
                    color: #eff7ff;
                    padding: 6px 8px;
                    font-size: 12px;
                    outline: none;
                }
                .customer-manage-input:focus,
                .customer-manage-select:focus {
                    border-color: rgba(156, 215, 255, 0.78);
                    box-shadow: 0 0 0 2px rgba(156, 215, 255, 0.12);
                }
                .customer-manage-btn {
                    border-radius: 8px;
                    border: 1px solid rgba(128, 201, 255, 0.42);
                    color: #eaf5ff;
                    background: linear-gradient(90deg, rgba(82, 168, 255, 0.22), rgba(98, 186, 255, 0.14));
                    padding: 6px 8px;
                    font-size: 12px;
                    cursor: pointer;
                }
                .customer-manage-btn.danger {
                    border-color: rgba(248, 113, 113, 0.6);
                    background: rgba(248, 113, 113, 0.12);
                    color: #ffd6d6;
                }
                .pro-feature-widget-container.clean-user-list .customer-manage-card {
                    background: transparent;
                    border-color: rgba(132, 198, 255, 0.12);
                }
                .customer-manage-dock {
                    position: fixed;
                    left: 16px;
                    top: 50%;
                    transform: translateY(-50%);
                    width: min(300px, 34vw);
                    z-index: 10020;
                    pointer-events: none;
                }
                .customer-manage-dock .customer-cloud {
                    align-items: flex-start;
                    min-height: auto;
                    gap: 10px;
                }
                .customer-manage-dock .customer-row {
                    width: 100%;
                    margin-left: 0;
                    pointer-events: auto;
                }
                .customer-manage-dock .floating-unit-token {
                    text-align: left;
                    width: fit-content;
                    min-width: 140px;
                    max-width: 100%;
                    background: rgba(15, 38, 64, 0.36);
                }
                .customer-manage-dock .customer-row .inline-detail {
                    left: 0;
                    right: auto;
                    width: min(300px, 34vw);
                    background: rgba(8, 18, 32, 0.66);
                    border-color: rgba(132, 198, 255, 0.28);
                }
                .pro-feature-widget-container.clean-user-list .customer-list {
                    background: transparent;
                    border: none;
                    border-radius: 0;
                    padding: 0;
                    max-height: none;
                    overflow: visible;
                }
                .pro-feature-widget-container.clean-user-list .customer-panel::before {
                    display: none;
                }
                .customer-panel::before {
                    content: '';
                    position: absolute;
                    inset: 0;
                    border-radius: 14px;
                    pointer-events: none;
                    background:
                        radial-gradient(600px 120px at -10% 0%, rgba(116, 196, 255, 0.14), transparent 70%),
                        radial-gradient(420px 120px at 110% 100%, rgba(66, 153, 225, 0.12), transparent 70%);
                }
                .pro-feature-widget-container.clean-user-list .customer-panel::before {
                    display: none;
                }
                .customer-list {
                    min-height: 180px;
                    max-height: 320px;
                    overflow-y: auto;
                    display: block;
                    position: relative;
                    z-index: 1;
                    border: 1px dashed rgba(141, 201, 255, 0.26);
                    border-radius: 12px;
                    background: rgba(10, 20, 35, 0.55);
                    padding: 14px;
                }
                .customer-cloud {
                    position: relative;
                    width: 100%;
                    min-height: 150px;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    align-items: flex-end;
                }
                .customer-row {
                    width: min(360px, 88%);
                    margin-left: auto;
                    position: relative;
                    transition: opacity 0.06s linear;
                }
                .floating-unit-token {
                    position: relative;
                    width: 100%;
                    margin-left: 0;
                    text-align: right;
                    border: 1px solid rgba(126, 190, 255, 0.22);
                    border-radius: 8px;
                    background: rgba(20, 42, 66, 0.22);
                    color: #7ef7ff;
                    font-family: "Consolas", "JetBrains Mono", "SFMono-Regular", monospace;
                    font-size: 13px;
                    letter-spacing: 0.4px;
                    cursor: pointer;
                    padding: 8px 10px;
                    transition: transform 0.18s ease, opacity 0.2s ease, color 0.2s ease, border-color 0.2s ease, background 0.2s ease;
                    text-shadow: none;
                }
                .pro-feature-widget-container.clean-user-list .floating-unit-token {
                    color: #86f9ff;
                    text-shadow: 0 0 8px rgba(87, 246, 255, 0.48);
                    border-color: rgba(95, 240, 255, 0.36);
                }
                .floating-unit-token:hover {
                    color: #e9ffff;
                    border-color: rgba(108, 248, 255, 0.78);
                    background: rgba(23, 120, 140, 0.3);
                    transform: none;
                }
                .floating-unit-token.active {
                    color: #ffffff;
                    transform: none;
                    border-color: rgba(124, 255, 255, 0.98);
                    background: rgba(16, 158, 178, 0.36);
                    box-shadow: 0 0 16px rgba(102, 247, 255, 0.3);
                    font-weight: 700;
                }
                .floating-unit-token.pinned {
                    border-color: rgba(255, 220, 120, 0.92);
                    background: rgba(182, 138, 26, 0.22);
                    box-shadow: 0 0 16px rgba(255, 219, 120, 0.28);
                }
                .floating-unit-token.hidden {
                    opacity: 0;
                    height: 0;
                    padding-top: 0;
                    padding-bottom: 0;
                    margin: 0;
                    border: none;
                    pointer-events: none;
                }
                .customer-row .inline-detail {
                    display: none;
                    position: absolute;
                    right: 0;
                    top: calc(100% + 6px);
                    width: 100%;
                    border-radius: 10px;
                    padding: 10px;
                    border: 1px solid rgba(132, 198, 255, 0.22);
                    background: rgba(8, 18, 32, 0.45);
                    animation: customerDetailExpand 0.18s ease;
                    z-index: 6;
                }
                .customer-row.expanded .inline-detail {
                    display: block;
                }
                .customer-row.expanded {
                    z-index: 8;
                }
                .customer-row.collapsed {
                    opacity: 0.1;
                    pointer-events: none;
                    transform: none;
                }
                .pro-feature-widget-container.clean-user-list .customer-row .inline-detail {
                    background: transparent;
                    border: 1px solid rgba(132, 198, 255, 0.12);
                }
                .pro-feature-widget-container.clean-user-list .customer-card {
                    background: transparent;
                    border: 1px solid rgba(132, 198, 255, 0.12);
                }
                .pro-feature-widget-container.clean-user-list .customer-input {
                    background: transparent;
                    border: 1px solid rgba(141, 201, 255, 0.24);
                }
                .pro-feature-widget-container.clean-user-list .customer-save-btn {
                    background: transparent;
                    border: 1px solid rgba(128, 201, 255, 0.32);
                }
                @keyframes customerDetailExpand {
                    from { opacity: 0; transform: translateY(8px) scale(0.985); }
                    to { opacity: 1; transform: translateY(0) scale(1); }
                }
                .customer-detail.show {
                    display: block;
                }
                .customer-card {
                    border-radius: 10px;
                    padding: 10px;
                    background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
                    border: 1px solid rgba(132, 198, 255, 0.2);
                }
                .customer-detail-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 10px;
                }
                .customer-back-btn {
                    border: 1px solid rgba(141, 201, 255, 0.35);
                    background: rgba(141, 201, 255, 0.1);
                    color: #d8ecff;
                    border-radius: 8px;
                    padding: 4px 8px;
                    cursor: pointer;
                    font-size: 12px;
                }
                .customer-title {
                    color: #d8ebff;
                    font-size: 14px;
                    font-weight: 600;
                    margin-bottom: 8px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .customer-label {
                    display: block;
                    color: rgba(199, 224, 255, 0.72);
                    font-size: 11px;
                    margin: 4px 0;
                    letter-spacing: 0.3px;
                }
                .customer-input {
                    width: 100%;
                    border-radius: 8px;
                    border: 1px solid rgba(141, 201, 255, 0.28);
                    background: rgba(8, 18, 32, 0.86);
                    color: #eff7ff;
                    padding: 8px 9px;
                    font-size: 12px;
                    outline: none;
                }
                .customer-input:focus {
                    border-color: rgba(156, 215, 255, 0.78);
                    box-shadow: 0 0 0 2px rgba(156, 215, 255, 0.12);
                }
                .customer-save-btn {
                    margin-top: 10px;
                    width: 100%;
                    border-radius: 8px;
                    background: linear-gradient(90deg, rgba(82, 168, 255, 0.3), rgba(98, 186, 255, 0.2));
                    border: 1px solid rgba(128, 201, 255, 0.42);
                    color: #eaf5ff;
                }
                .customer-save-btn.saving {
                    border-color: rgba(120, 200, 255, 0.9);
                    box-shadow: 0 0 0 2px rgba(120, 200, 255, 0.16);
                }
                .customer-save-btn.saved {
                    border-color: rgba(52, 211, 153, 0.9);
                    background: rgba(52, 211, 153, 0.2);
                    box-shadow: 0 0 12px rgba(52, 211, 153, 0.35);
                }
                .customer-save-btn.failed {
                    border-color: rgba(248, 113, 113, 0.85);
                    background: rgba(248, 113, 113, 0.16);
                }
                .customer-card.saved-flash {
                    animation: customerCardSavedPulse 0.7s ease;
                }
                @keyframes customerCardSavedPulse {
                    0% { box-shadow: 0 0 0 rgba(52, 211, 153, 0); }
                    40% { box-shadow: 0 0 0 2px rgba(52, 211, 153, 0.45), 0 0 20px rgba(52, 211, 153, 0.28); }
                    100% { box-shadow: inset 0 0 12px rgba(74, 144, 217, 0.1); }
                }
                .customer-loading, .customer-empty {
                    padding: 30px 12px;
                    text-align: center;
                    color: rgba(255,255,255,0.65);
                    position: relative;
                    z-index: 1;
                }
                .product-query-panel {
                    display: grid;
                    grid-template-columns: 1fr;
                    grid-template-rows: auto auto;
                    gap: 10px;
                    min-height: 340px;
                    align-items: start;
                    transform: scale(0.9);
                    transform-origin: top right;
                }
                .product-query-main {
                    border: 1px solid rgba(113, 196, 255, 0.26);
                    border-radius: 12px;
                    background: rgba(6, 16, 31, 0.48);
                    padding: 9px 10px;
                    width: min(68%, 360px);
                    min-width: 260px;
                    margin-left: auto;
                }
                .product-query-panel .product-query-main {
                    order: 2;
                }
                .product-query-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 7px;
                }
                .product-query-company-name {
                    font-size: 12px;
                    color: #9ae8ff;
                    letter-spacing: 0.55px;
                    min-height: 16px;
                    flex: 1;
                }
                .product-query-export-btn {
                    flex-shrink: 0;
                    padding: 4px 10px;
                    font-size: 12px;
                    border: 1px solid rgba(128, 209, 255, 0.5);
                    border-radius: 6px;
                    background: rgba(8, 22, 42, 0.8);
                    color: #9ae8ff;
                    cursor: pointer;
                }
                .product-query-export-btn:hover {
                    background: rgba(20, 50, 90, 0.9);
                    border-color: rgba(151, 231, 255, 0.7);
                }
                .product-query-export-btn-icon {
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                }
                .product-query-export-btn-icon .excel-icon-svg {
                    flex-shrink: 0;
                }
                .product-query-search {
                    width: min(72%, 320px);
                    min-width: 220px;
                    border: 1px solid rgba(128, 209, 255, 0.35);
                    border-radius: 8px;
                    background: rgba(5, 13, 25, 0.65);
                    color: #e8f8ff;
                    padding: 7px 10px;
                    font-size: 13px;
                    outline: none;
                    margin-bottom: 8px;
                    margin-left: auto;
                    display: block;
                }
                .product-query-search:focus {
                    border-color: rgba(151, 231, 255, 0.72);
                    box-shadow: 0 0 0 2px rgba(123, 205, 255, 0.14);
                }
                .product-query-list {
                    display: grid;
                    gap: 6px;
                    max-height: 190px;
                    overflow: auto;
                    padding-right: 4px;
                }
                .product-item {
                    border: 1px solid rgba(109, 193, 255, 0.3);
                    background: rgba(8, 22, 42, 0.55);
                    color: #dff2ff;
                    border-radius: 10px;
                    padding: 9px 10px;
                    cursor: pointer;
                    transition: all 0.18s ease;
                }
                .product-item:hover {
                    border-color: rgba(157, 225, 255, 0.8);
                    box-shadow: 0 0 14px rgba(79, 173, 255, 0.22);
                }
                .product-item.active {
                    border-color: rgba(96, 255, 233, 0.85);
                    box-shadow: 0 0 16px rgba(96, 255, 233, 0.24);
                    transform: translateX(-2px);
                }
                .product-item-title {
                    font-size: 13px;
                    color: #f0fbff;
                    margin-bottom: 4px;
                }
                .product-item-meta {
                    font-size: 12px;
                    color: rgba(200, 228, 255, 0.7);
                    display: flex;
                    justify-content: space-between;
                    gap: 10px;
                }
                .product-query-company-cloud {
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    gap: 6px;
                    border: none;
                    border-radius: 0;
                    background: transparent;
                    padding: 0;
                }
                .product-query-panel .product-query-company-cloud {
                    order: 1;
                }
                .company-token {
                    border: 1px solid rgba(126, 210, 255, 0.42);
                    background: rgba(9, 24, 44, 0.52);
                    color: #b9ebff;
                    border-radius: 10px;
                    font-family: Consolas, "Courier New", monospace;
                    font-size: 12px;
                    letter-spacing: 0.7px;
                    padding: 8px 10px;
                    cursor: pointer;
                    transition: all 0.16s ease;
                    max-width: 100%;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .company-token:hover {
                    border-color: rgba(162, 231, 255, 0.86);
                    color: #e7fbff;
                }
                .company-token.active {
                    border-color: rgba(102, 251, 225, 0.95);
                    box-shadow: 0 0 18px rgba(96, 245, 255, 0.2);
                    color: #e9fffe;
                }
                .product-query-empty {
                    color: rgba(206, 227, 255, 0.76);
                    text-align: center;
                    padding: 18px 10px;
                }
                .product-company-cloud {
                    min-height: 240px;
                }
                .product-company-cloud .customer-row {
                    width: fit-content;
                    max-width: min(360px, 88%);
                }
                .product-company-cloud .floating-unit-token {
                    width: auto;
                    display: inline-block;
                    max-width: min(360px, 88vw);
                }
                .product-company-hint {
                    font-size: 11px;
                    color: rgba(191, 226, 255, 0.78);
                    letter-spacing: 0.4px;
                    text-align: right;
                }
                @media (max-width: 900px) {
                    .customer-panel {
                        grid-template-columns: 1fr;
                    }
                    .product-query-company-cloud {
                        align-items: stretch;
                    }
                    .customer-list {
                        min-height: 140px;
                    }
                }
            </style>
        `;
        document.head.insertAdjacentHTML('beforeend', styles);
    }

    bindEvents() {
        const widget = document.getElementById(this.widgetId);
        const closeBtn = widget.querySelector('.close-btn');
        closeBtn.addEventListener('click', () => this.hide());
    }

    // 显示功能模块
    showFeature(featureType, config = {}) {
        this.currentFeature = featureType;
        this.featureConfig = config;
        
        const widget = document.getElementById(this.widgetId);
        const title = document.getElementById('widget-title');
        const icon = document.getElementById('widget-icon');
        const content = document.getElementById('widget-content');
        const actionButtons = document.getElementById('action-buttons');
        widget.classList.remove('open-layout', 'clean-user-list');
        if (featureType !== 'product_query' && typeof window.setProProductQueryStage === 'function') {
            window.setProProductQueryStage('idle', {});
        }
        if (featureType !== 'product_query') {
            this._selectedProductCompanyRow = null;
        }
        if (featureType !== 'user_list') {
            this.hideCustomerManageDock();
        }
        const iconRing = document.getElementById('iconRingContainer');
        if (iconRing) iconRing.classList.remove('visible');

        // 根据功能类型渲染不同内容
        switch(featureType) {
            case 'wechat_login':
                // 微信扫码登录不再使用 pro-feature-widget 的“老壳”（header/content/footer），
                // 只展示十二面体扫码面板（.dodeca-scan-panel）
                this.hide();
                this.showWechatLoginPanel();
                fetch('/api/wechat/status')
                    .then(r => r.json())
                    .then(d => {
                        if (d && d.logined) {
                            this.hideWechatLoginPanel();
                            this._refreshWechatContacts();
                        }
                    });
                return;
            case 'wechat_contacts':
                title.textContent = '微信联系人';
                icon.textContent = '👥';
                content.textContent = '';
                content.appendChild(this.renderWechatContacts());
                actionButtons.textContent = '';
                const refreshBtn = document.createElement('button');
                refreshBtn.className = 'action-btn';
                refreshBtn.textContent = '刷新列表';
                refreshBtn.addEventListener('click', () => this.loadContacts());
                actionButtons.appendChild(refreshBtn);
                this.loadContacts();
                break;
            case 'user_list':
                widget.classList.add('open-layout');
                widget.classList.add('clean-user-list');
                title.textContent = '用户列表';
                icon.textContent = '🧾';
                content.textContent = '';
                content.appendChild(this.renderUserListPanel(config));
                this.showCustomerManageDock();
                actionButtons.textContent = '';
                const refreshUsersBtn = document.createElement('button');
                refreshUsersBtn.className = 'action-btn';
                refreshUsersBtn.textContent = '刷新用户';
                refreshUsersBtn.addEventListener('click', () => this.loadUserList(config));
                actionButtons.appendChild(refreshUsersBtn);
                const exportUsersBtn = document.createElement('button');
                exportUsersBtn.className = 'action-btn';
                exportUsersBtn.textContent = '导出XLSX';
                exportUsersBtn.addEventListener('click', () => {
                    const apiBase = (typeof API_BASE !== 'undefined' ? API_BASE : '');
                    const link = document.createElement('a');
                    link.href = `${apiBase}/api/customers/export.xlsx`;
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    link.click();
                    setTimeout(() => {
                        link.remove();
                    }, 0);
                });
                actionButtons.appendChild(exportUsersBtn);
                this.loadUserList(config);
                if (iconRing) {
                    iconRing.classList.add('visible');
                    if (typeof window.createIconRing === 'function') window.createIconRing();
                }
                break;
            case 'product_query':
                widget.classList.add('open-layout');
                widget.classList.add('clean-user-list');
                title.textContent = '产品查询';
                icon.textContent = '🧪';
                content.textContent = '';
                content.appendChild(this.renderProductQueryPanel());
                actionButtons.textContent = '';
                if (typeof window.setProProductQueryStage === 'function') {
                    window.setProProductQueryStage('companies', {});
                }
                this.loadProductQueryCompanies(config);
                break;
            default:
                title.textContent = '专业功能';
                icon.textContent = '🔧';
                content.innerHTML = '<p>功能开发中...</p>';
                actionButtons.textContent = '';
        }
        
        widget.classList.remove('hide');
        widget.classList.add('show');
        this.isShowing = true;
        
        // wechat_login 的状态检测由面板内部 SSE/轮询负责
    }

    showWechatLoginPanel() {
        // 触发后端启动 itchat 登录流程（生成二维码文件 wechat_qr.png）
        fetch('/api/wechat/login', { method: 'POST' }).catch(() => {});

        // Debug evidence: prove show_login -> panel creation path ran
        try {
            fetch('/api/debug/client-log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    runId: 'p5',
                    hypothesisId: 'H-ui',
                    location: 'pro_feature_widget.js:showWechatLoginPanel',
                    message: 'called',
                    data: { readyState: document.readyState }
                })
            }).catch(() => {});
        } catch (e) {}

        let panel = document.getElementById('wechatDodecaScanPanel');
        if (!panel) {
            panel = document.createElement('div');
            panel.id = 'wechatDodecaScanPanel';
            panel.className = 'dodeca-scan-panel';
            const closeBtn = document.createElement('button');
            closeBtn.className = 'close-scan';
            closeBtn.title = '关闭';
            closeBtn.textContent = '×';
            panel.appendChild(closeBtn);

            const refreshBtn = document.createElement('button');
            refreshBtn.className = 'refresh-scan';
            refreshBtn.title = '刷新二维码';
            refreshBtn.textContent = '↻';
            panel.appendChild(refreshBtn);

            const dodecaContainer = document.createElement('div');
            dodecaContainer.className = 'dodeca-container static';
            const polyhedron = document.createElement('div');
            polyhedron.className = 'polyhedron poly-dodeca';
            for (let i = 1; i <= 12; i++) {
                const face = document.createElement('div');
                face.className = `poly-face f${i}`;
                polyhedron.appendChild(face);
            }
            dodecaContainer.appendChild(polyhedron);
            panel.appendChild(dodecaContainer);

            const scanContent = document.createElement('div');
            scanContent.className = 'dodeca-scan-content';
            const scanTitle = document.createElement('div');
            scanTitle.className = 'dodeca-scan-title';
            scanTitle.textContent = '微信扫码登录';
            scanContent.appendChild(scanTitle);

            const scanFrame = document.createElement('div');
            scanFrame.className = 'dodeca-scan-frame';
            const scanLine = document.createElement('div');
            scanLine.className = 'dodeca-scan-line';
            scanLine.id = 'dodecaScanLineWidget';
            scanFrame.appendChild(scanLine);
            const qrImg = document.createElement('img');
            qrImg.id = 'wechatQrCodeWidget';
            qrImg.alt = '微信登录二维码';
            scanFrame.appendChild(qrImg);
            const scanLoading = document.createElement('div');
            scanLoading.className = 'dodeca-scan-loading';
            scanLoading.id = 'scanLoadingWidget';
            scanLoading.textContent = '正在获取二维码...';
            scanFrame.appendChild(scanLoading);
            scanContent.appendChild(scanFrame);

            const scanStatus = document.createElement('div');
            scanStatus.className = 'dodeca-scan-status';
            scanStatus.id = 'scanStatusWidget';
            scanStatus.textContent = '请使用手机微信扫描上方二维码';
            scanContent.appendChild(scanStatus);
            panel.appendChild(scanContent);
            document.body.appendChild(panel);
            // Entrance animation: extract from center to the right
            panel.classList.add('entering');
            setTimeout(() => {
                try { panel.classList.remove('entering'); } catch (e) {}
            }, 950);
            try {
                fetch('/api/debug/client-log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        runId: 'p5',
                        hypothesisId: 'H-ui',
                        location: 'pro_feature_widget.js:showWechatLoginPanel',
                        message: 'panel_appended',
                        data: { zIndex: (window.getComputedStyle(panel).zIndex || '') }
                    })
                }).catch(() => {});
            } catch (e) {}

            closeBtn.addEventListener('click', () => this.hideWechatLoginPanel());
            refreshBtn.addEventListener('click', () => this.refreshQRCode());
        }

        this._loginPanelEl = panel;
        this.refreshQRCode();
        // 延迟启动扫描线，保证 img src 已更新
        setTimeout(() => this.startScanAnimation(), 200);
        this.startWechatStatusMonitoring();

        // 如果本来就已登录，直接进入成功态（但不自动关闭面板）
        fetch('/api/wechat/status')
            .then((r) => r.json())
            .then((d) => {
                if (d && d.success && d.logined) {
                    this.hideWechatLoginPanel();
                    this._refreshWechatContacts();
                }
                this.onWechatLoginSuccess();
            })
            .catch(() => {});
    }

    hideWechatLoginPanel() {
        this.stopWechatStatusMonitoring();
        if (this._loginPanelEl) {
            this._loginPanelEl.remove();
            this._loginPanelEl = null;
        }
    }
    
    startScanAnimation() {
        const scanLine = document.getElementById('dodecaScanLineWidget');
        const qrImg = document.getElementById('wechatQrCodeWidget');
        if (qrImg) {
            qrImg.src = '/api/wechat/qrcode?ts=' + Date.now();
        }
        const loading = document.getElementById('scanLoadingWidget');
        
        if (scanLine && qrImg) {
            // 显示扫描线
            scanLine.classList.add('scanning');
            scanLine.style.animation = 'dodecaScanLine 2.5s ease-in-out forwards';
            
            // 扫描完成后显示二维码
            setTimeout(() => {
                if (loading) {
                    loading.style.display = 'none';
                }
                qrImg.classList.add('show');
                qrImg.style.opacity = '1';
            }, 2500);
        }
    }

    renderWechatLogin() {
        return document.createElement('div');
    }

    refreshQRCode() {
        const img = document.getElementById('wechatQrCodeWidget');
        const scanLine = document.getElementById('dodecaScanLineWidget');
        const loading = document.getElementById('scanLoadingWidget');
        const status = document.getElementById('scanStatusWidget');
        
        if (img) {
            const url = '/api/wechat/qrcode?ts=' + Date.now();
            img.src = url;
            // 二维码文件生成可能有延迟：遇到 404/加载失败时自动重试
            img.onerror = function() {
                if (status) status.textContent = '二维码生成中，正在重试...';
                setTimeout(() => {
                    this.src = '/api/wechat/qrcode?ts=' + Date.now();
                }, 1200);
            };
            img.style.opacity = '0';
            img.classList.remove('show');
            
            if (loading) {
                loading.style.display = 'block';
            }
            if (status) {
                status.textContent = '请使用手机微信扫描上方二维码';
            }
            
            // 重新启动扫描线动画
            if (scanLine) {
                scanLine.style.animation = 'none';
                scanLine.offsetHeight; // 触发重排
                scanLine.style.animation = 'dodecaScanLine 2.5s ease-in-out forwards';
                scanLine.classList.add('scanning');
                
                setTimeout(() => {
                    if (loading) {
                        loading.style.display = 'none';
                    }
                    img.classList.add('show');
                    img.style.opacity = '1';
                    if (status) status.textContent = '等待扫码确认...';
                }, 2500);
            }
        }
    }

    startWechatStatusMonitoring() {
        this.stopWechatStatusMonitoring();
        try {
            this._loginStatusSource = new EventSource('/api/wechat/status/stream');
            this._loginStatusSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'status' && data.logined) {
                        this.hideWechatLoginPanel();
                        this._refreshWechatContacts();
                    }
                    this.onWechatLoginSuccess();
                } catch (e) {}
            };
            this._loginStatusSource.onerror = () => {
                this.stopWechatStatusMonitoring();
                this.startWechatStatusPollingFallback();
            };
        } catch (e) {
            this.startWechatStatusPollingFallback();
        }
    }

    stopWechatStatusMonitoring() {
        if (this._loginStatusSource) {
            try { this._loginStatusSource.close(); } catch (e) {}
            this._loginStatusSource = null;
        }
        this.stopStatusCheck();
    }

    startWechatStatusPollingFallback() {
        this.stopStatusCheck();
        this.checkInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/wechat/status');
                const data = await response.json();
                if (data.success && data.logined) {
                    this.hideWechatLoginPanel();
                    this._refreshWechatContacts();
                }
                this.onWechatLoginSuccess();
            } catch (e) {}
        }, 2000);
    }

    stopStatusCheck() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    onWechatLoginSuccess() {
        this.stopWechatStatusMonitoring();
        
        const statusDot = document.querySelector('.status-dot');
        const statusLabel = document.getElementById('widget-status');
        
        statusDot.classList.add('success');
        statusLabel.textContent = '已登录';
        
        // 获取十二面体容器
        const dodecaPanel = document.getElementById('wechatDodecaScanPanel');
        const dodecaContainer = dodecaPanel ? dodecaPanel.querySelector('.dodeca-container') : null;
        const dodecaContent = dodecaPanel ? dodecaPanel.querySelector('.dodeca-scan-content') : null;
        
        if (dodecaPanel && dodecaContainer) {
            // 触发 ui-components.css: 右侧移动到中心 + 开始旋转 + 内容淡出
            dodecaPanel.classList.add('login-success');
            dodecaContainer.classList.remove('static');
            dodecaContainer.classList.add('rotating');
            
            // 隐藏内容
            if (dodecaContent) {
                dodecaContent.style.opacity = '0';
                dodecaContent.style.transition = 'opacity 0.5s ease';
            }
        }
        
        // 成功动画
        const widget = document.getElementById(this.widgetId);
        widget.style.animation = 'successPulse 0.6s ease-in-out';
        
        // 不再自动关闭二维码/面板：避免“已登录”或状态误判时窗口自己消失
        // 现在的行为：进入 login-success 旋转态，保留面板，用户手动关闭
        setTimeout(() => {
            try { widget.style.animation = ''; } catch (e) {}
        }, 600);
    }

    hide() {
        const widget = document.getElementById(this.widgetId);
        if (!widget) return;
        widget.classList.remove('show');
        widget.classList.remove('open-layout', 'clean-user-list');
        widget.classList.add('hide');
        const content = document.getElementById('widget-content');
        const actionButtons = document.getElementById('action-buttons');
        if (content) content.textContent = '';
        if (actionButtons) actionButtons.textContent = '';
        this._pinnedCustomerRow = null;
        this._productCompanies = [];
        this._selectedProductCompany = null;
        this._productAllItems = [];
        this._selectedProductCompanyRow = null;
        if (typeof window.setProProductQueryStage === 'function') {
            window.setProProductQueryStage('idle', {});
        }
        this.hideCustomerManageDock();
        this._pinnedManageRow = null;
        this.isShowing = false;
        this.stopStatusCheck();
        this.stopWechatStatusMonitoring();
        this.hideContactsCounter();
        this.hideWechatLoginPanel();
        const iconRing = document.getElementById('iconRingContainer');
        if (iconRing) iconRing.classList.remove('visible');
    }

    renderWechatContacts() {
        const container = document.createElement('div');
        container.className = 'contacts-container';

        const loading = document.createElement('div');
        loading.className = 'contacts-loading';
        loading.id = 'contactsLoading';
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        loading.appendChild(spinner);
        const loadingText = document.createElement('p');
        loadingText.textContent = '正在加载联系人...';
        loading.appendChild(loadingText);

        const list = document.createElement('div');
        list.className = 'contacts-list';
        list.id = 'contactsList';
        list.style.display = 'none';

        const empty = document.createElement('div');
        empty.className = 'contacts-empty';
        empty.id = 'contactsEmpty';
        empty.style.display = 'none';
        const emptyText = document.createElement('p');
        emptyText.textContent = '暂无联系人数据';
        empty.appendChild(emptyText);

        container.appendChild(loading);
        container.appendChild(list);
        container.appendChild(empty);
        return container;
    }

    /**
     * AI 调用图片/视频展示入口：
     * - 后端返回 autoAction: {type:'show_images'|'show_videos'}
     * - 前端 chat.js 会调用 window.proFeatureWidget.showMediaPanel(...)
     * 这里复用 ui-components.css 现成的 .dodeca-media-panel 十二面体面板样式
     */
    showMediaPanel(mediaType, source) {
        const panel = document.createElement('div');
        panel.className = 'dodeca-media-panel';
        const closeBtn = document.createElement('button');
        closeBtn.className = 'close-media';
        closeBtn.textContent = '×';
        closeBtn.addEventListener('click', () => panel.remove());
        panel.appendChild(closeBtn);

        const dodecaContainer = document.createElement('div');
        dodecaContainer.className = 'dodeca-container static';
        const polyhedron = document.createElement('div');
        polyhedron.className = 'polyhedron poly-dodeca';
        for (let i = 1; i <= 12; i++) {
            const face = document.createElement('div');
            face.className = `poly-face f${i}`;
            polyhedron.appendChild(face);
        }
        dodecaContainer.appendChild(polyhedron);
        panel.appendChild(dodecaContainer);

        const content = document.createElement('div');
        content.className = 'dodeca-media-content';

        const header = document.createElement('div');
        header.className = 'dodeca-media-header';
        const title = document.createElement('span');
        title.className = 'dodeca-media-title';
        title.textContent = mediaType === 'image' ? '🖼️ 图片' : '🎬 视频';
        const count = document.createElement('span');
        count.className = 'dodeca-media-count';
        count.textContent = '加载中...';
        header.appendChild(title);
        header.appendChild(count);

        const frame = document.createElement('div');
        frame.className = 'dodeca-media-frame';
        const loading = document.createElement('div');
        loading.className = 'dodeca-media-loading';
        loading.textContent = '正在加载媒体文件...';
        frame.appendChild(loading);

        const nav = document.createElement('div');
        nav.className = 'dodeca-media-nav';
        const prevBtn = document.createElement('button');
        prevBtn.className = 'dodeca-media-nav-btn prev';
        prevBtn.textContent = '◀';
        prevBtn.disabled = true;
        const indicator = document.createElement('span');
        indicator.className = 'dodeca-media-indicator';
        indicator.textContent = '0 / 0';
        const nextBtn = document.createElement('button');
        nextBtn.className = 'dodeca-media-nav-btn next';
        nextBtn.textContent = '▶';
        nextBtn.disabled = true;
        nav.appendChild(prevBtn);
        nav.appendChild(indicator);
        nav.appendChild(nextBtn);

        content.appendChild(header);
        content.appendChild(frame);
        content.appendChild(nav);
        panel.appendChild(content);
        document.body.appendChild(panel);

        this.loadMediaList(panel, mediaType, source);
    }

    async loadMediaList(panel, mediaType, source) {
        const mediaFrame = panel.querySelector('.dodeca-media-frame');
        const mediaCount = panel.querySelector('.dodeca-media-count');
        const mediaIndicator = panel.querySelector('.dodeca-media-indicator');
        const prevBtn = panel.querySelector('.prev');
        const nextBtn = panel.querySelector('.next');

        try {
            const apiPath = mediaType === 'image' ? '/api/media/images' : '/api/media/videos';
            const response = await fetch(apiPath);
            const data = await response.json();

            if (data.success && data.files) {
                const files = data.files;
                mediaCount.textContent = `${files.length} 个${mediaType === 'image' ? '文件' : '视频'}`;

                if (files.length === 0) {
                    mediaFrame.textContent = '';
                    const empty = document.createElement('div');
                    empty.className = 'dodeca-media-empty';
                    empty.textContent = `暂无${mediaType === 'image' ? '图片' : '视频'}`;
                    mediaFrame.appendChild(empty);
                    return;
                }

                let currentIndex = 0;

                const renderMedia = (index) => {
                    const file = files[index];
                    mediaFrame.textContent = '';
                    if (mediaType === 'image') {
                        const img = document.createElement('img');
                        img.src = file.url;
                        img.alt = file.name || '';
                        img.className = 'show';
                        mediaFrame.appendChild(img);
                    } else {
                        const video = document.createElement('video');
                        video.src = file.url;
                        video.controls = true;
                        video.className = 'show';
                        mediaFrame.appendChild(video);
                    }
                    mediaIndicator.textContent = `${index + 1} / ${files.length}`;
                    prevBtn.disabled = index === 0;
                    nextBtn.disabled = index === files.length - 1;
                };

                renderMedia(0);

                prevBtn.onclick = () => {
                    if (currentIndex > 0) {
                        currentIndex--;
                        renderMedia(currentIndex);
                    }
                };

                nextBtn.onclick = () => {
                    if (currentIndex < files.length - 1) {
                        currentIndex++;
                        renderMedia(currentIndex);
                    }
                };
            } else {
                mediaFrame.textContent = '';
                const error = document.createElement('div');
                error.className = 'dodeca-media-error';
                error.textContent = `加载失败: ${data.message || '未知错误'}`;
                mediaFrame.appendChild(error);
            }
        } catch (e) {
            mediaFrame.textContent = '';
            const error = document.createElement('div');
            error.className = 'dodeca-media-error';
            error.textContent = `加载失败: ${e.message}`;
            mediaFrame.appendChild(error);
        }
    }

    async loadContacts() {
        const loadingEl = document.getElementById('contactsLoading');
        const listEl = document.getElementById('contactsList');
        const emptyEl = document.getElementById('contactsEmpty');
        
        if (loadingEl) loadingEl.style.display = 'flex';
        if (listEl) listEl.style.display = 'none';
        if (emptyEl) emptyEl.style.display = 'none';
        
        this.showContactsCounter(0, true);
        
        try {
            const response = await fetch('/api/wechat/contacts');
            const data = await response.json();
            
            if (data.success && data.contacts) {
                this.renderContactsList(data.contacts, data.count);
            } else {
                if (emptyEl) emptyEl.style.display = 'block';
                if (loadingEl) loadingEl.style.display = 'none';
                this.updateContactsCounter(0);
            }
        } catch (error) {
            console.error('加载联系人失败:', error);
            if (emptyEl) {
                emptyEl.querySelector('p').textContent = '加载失败: ' + error.message;
                emptyEl.style.display = 'block';
            }
            if (loadingEl) loadingEl.style.display = 'none';
        }
    }

    renderContactsList(contacts, totalCount) {
        const loadingEl = document.getElementById('contactsLoading');
        const listEl = document.getElementById('contactsList');
        
        if (loadingEl) loadingEl.style.display = 'none';
        
        if (!contacts || contacts.length === 0) {
            const emptyEl = document.getElementById('contactsEmpty');
            if (emptyEl) {
                emptyEl.style.display = 'block';
            }
            this.updateContactsCounter(0);
            return;
        }
        
        if (listEl) {
            listEl.textContent = '';
            const grid = document.createElement('div');
            grid.className = 'contacts-grid';

            contacts.forEach((contact, index) => {
                const avatar = contact.HeadImgUrl || contact.avatar || '';
                const name = contact.NickName || contact.name || '未知';
                const remark = contact.RemarkName || contact.remark || '';

                const item = document.createElement('div');
                item.className = 'contact-item';
                item.style.animation = 'fadeInUp 0.3s ease forwards';
                item.style.animationDelay = `${index * 0.02}s`;
                item.style.opacity = '0';

                const avatarWrap = document.createElement('div');
                avatarWrap.className = 'contact-avatar';
                if (avatar) {
                    const img = document.createElement('img');
                    img.src = avatar;
                    img.alt = name;
                    img.addEventListener('error', () => { img.style.display = 'none'; });
                    avatarWrap.appendChild(img);
                } else {
                    const placeholder = document.createElement('div');
                    placeholder.className = 'avatar-placeholder';
                    placeholder.textContent = name.charAt(0) || '?';
                    avatarWrap.appendChild(placeholder);
                }
                item.appendChild(avatarWrap);

                const info = document.createElement('div');
                info.className = 'contact-info';
                const nameEl = document.createElement('div');
                nameEl.className = 'contact-name';
                nameEl.textContent = name;
                info.appendChild(nameEl);
                if (remark) {
                    const remarkEl = document.createElement('div');
                    remarkEl.className = 'contact-remark';
                    remarkEl.textContent = remark;
                    info.appendChild(remarkEl);
                }
                item.appendChild(info);
                grid.appendChild(item);
            });

            listEl.appendChild(grid);
            listEl.style.display = 'block';
        }
        
        this.updateContactsCounter(totalCount);
        
        this.animateContactsToTop();
    }

    showContactsCounter(count, isLoading = false) {
        let counterEl = document.getElementById('wechatContactsCounter');
        
        if (!counterEl) {
            counterEl = document.createElement('div');
            counterEl.id = 'wechatContactsCounter';
            counterEl.className = 'wechat-contacts-counter';
            document.body.appendChild(counterEl);
            
            const style = document.createElement('style');
            style.textContent = `
                .wechat-contacts-counter {
                    position: fixed;
                    top: 20px;
                    left: 20px;
                    background: linear-gradient(135deg, rgba(26,26,46,0.95) 0%, rgba(22,33,62,0.95) 100%);
                    border: 1px solid rgba(74,144,217,0.4);
                    border-radius: 12px;
                    padding: 12px 20px;
                    color: #fff;
                    font-size: 14px;
                    z-index: 9999;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3), 0 0 20px rgba(74,144,217,0.2);
                    backdrop-filter: blur(10px);
                    animation: slideInLeft 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                    opacity: 0;
                    transform: translateX(-100px);
                }
                .wechat-contacts-counter.show {
                    opacity: 1;
                    transform: translateX(0);
                }
                .wechat-contacts-counter .counter-icon {
                    font-size: 20px;
                }
                .wechat-contacts-counter .counter-text {
                    color: rgba(255,255,255,0.8);
                }
                .wechat-contacts-counter .counter-count {
                    color: #4a90d9;
                    font-weight: bold;
                    font-size: 18px;
                }
                .wechat-contacts-counter .counter-loading {
                    width: 16px;
                    height: 16px;
                    border: 2px solid rgba(74,144,217,0.3);
                    border-top-color: #4a90d9;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                @keyframes slideInLeft {
                    from { opacity: 0; transform: translateX(-100px); }
                    to { opacity: 1; transform: translateX(0); }
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .contacts-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 12px;
                    max-height: 400px;
                    overflow-y: auto;
                }
                .contact-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 10px;
                    background: rgba(74,144,217,0.1);
                    border-radius: 8px;
                    border: 1px solid rgba(74,144,217,0.2);
                }
                .contact-avatar {
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    overflow: hidden;
                    flex-shrink: 0;
                }
                .contact-avatar img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                }
                .avatar-placeholder {
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(135deg, #4a90d9, #6ab0ff);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    color: #fff;
                    font-size: 16px;
                }
                .contact-info {
                    flex: 1;
                    min-width: 0;
                }
                .contact-name {
                    color: #fff;
                    font-size: 13px;
                    font-weight: 500;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .contact-remark {
                    color: rgba(255,255,255,0.5);
                    font-size: 11px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .contacts-container {
                    min-height: 300px;
                }
                .contacts-loading {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 60px 20px;
                    color: rgba(255,255,255,0.6);
                }
                .loading-spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid rgba(74,144,217,0.3);
                    border-top-color: #4a90d9;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin-bottom: 16px;
                }
                .contacts-empty {
                    text-align: center;
                    padding: 60px 20px;
                    color: rgba(255,255,255,0.5);
                }
            `;
            document.head.appendChild(style);
        }
        
        if (isLoading) {
            this._renderContactsCounter(counterEl, count, true);
        } else {
            this._renderContactsCounter(counterEl, count, false);
        }
        
        counterEl.classList.add('show');
    }

    updateContactsCounter(count) {
        const counterEl = document.getElementById('wechatContactsCounter');
        if (counterEl) {
            this._renderContactsCounter(counterEl, count, false);
        }
    }

    _renderContactsCounter(counterEl, count, isLoading) {
        counterEl.textContent = '';

        const icon = document.createElement('span');
        icon.className = 'counter-icon';
        icon.textContent = '👥';
        counterEl.appendChild(icon);

        const status = document.createElement('span');
        status.className = 'counter-text';
        status.textContent = isLoading ? '加载中' : '已加载';
        counterEl.appendChild(status);

        if (isLoading) {
            const loading = document.createElement('div');
            loading.className = 'counter-loading';
            counterEl.appendChild(loading);
            return;
        }

        const countEl = document.createElement('span');
        countEl.className = 'counter-count';
        countEl.textContent = String(count);
        counterEl.appendChild(countEl);

        const suffix = document.createElement('span');
        suffix.className = 'counter-text';
        suffix.textContent = '位联系人';
        counterEl.appendChild(suffix);
    }

    hideContactsCounter() {
        const counterEl = document.getElementById('wechatContactsCounter');
        if (counterEl) {
            counterEl.classList.remove('show');
            setTimeout(() => {
                counterEl.remove();
            }, 300);
        }
    }

    animateContactsToTop() {
        const counterEl = document.getElementById('wechatContactsCounter');
        if (counterEl) {
            counterEl.style.transition = 'all 0.5s ease';
            counterEl.style.top = '80px';
            setTimeout(() => {
                counterEl.style.top = '20px';
            }, 100);
        }
    }

    renderUserListPanel(config = {}) {
        const wrapper = document.createElement('div');
        wrapper.className = 'customer-panel';

        const list = document.createElement('div');
        list.className = 'customer-list';
        list.id = 'proCustomerList';
        wrapper.appendChild(list);

        const loading = document.createElement('div');
        loading.className = 'customer-loading';
        loading.id = 'proCustomerLoading';
        loading.textContent = '正在加载用户列表...';
        list.appendChild(loading);

        const empty = document.createElement('div');
        empty.className = 'customer-empty';
        empty.id = 'proCustomerEmpty';
        empty.style.display = 'none';
        empty.textContent = '暂无用户数据';
        list.appendChild(empty);
        return wrapper;
    }

    _safeText(value) {
        if (window.escapeHtml && typeof window.escapeHtml === 'function') {
            return window.escapeHtml(value);
        }
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    async loadUserList(config = {}) {
        const loadingEl = document.getElementById('proCustomerLoading');
        const listEl = document.getElementById('proCustomerList');
        const emptyEl = document.getElementById('proCustomerEmpty');

        if (loadingEl) loadingEl.style.display = 'block';
        if (listEl) {
            const cloud = listEl.querySelector('.customer-cloud');
            if (cloud) cloud.remove();
        }
        if (emptyEl) emptyEl.style.display = 'none';

        try {
            const response = await fetch('/api/customers');
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.message || '加载失败');
            }

            const customers = data.customers || data.data || [];
            this.syncCustomerManageOptions(customers);
            if (!Array.isArray(customers) || customers.length === 0) {
                if (loadingEl) loadingEl.style.display = 'none';
                if (emptyEl) emptyEl.style.display = 'block';
                return;
            }

            if (listEl) {
                const cloud = document.createElement('div');
                cloud.className = 'customer-cloud';
                cloud.id = 'proCustomerCloud';

                customers.forEach((c, index) => {
                    const id = Number(c.id || 0);
                    const name = this._safeText(c.unit_name || c.name || `单位${index + 1}`);
                    const contact = this._safeText(c.contact_person || '');
                    const phone = this._safeText(c.contact_phone || '');
                    const address = this._safeText(c.address || '');

                    const row = document.createElement('div');
                    row.className = 'customer-row';
                    row.setAttribute('data-id', String(id));

                    const token = document.createElement('button');
                    token.type = 'button';
                    token.className = 'floating-unit-token';
                    token.setAttribute('data-id', String(id));
                    token.innerHTML = name;

                    const detail = document.createElement('div');
                    detail.className = 'inline-detail';
                    detail.innerHTML = `
                        <div class="customer-card" data-customer-id="${id}">
                            <label class="customer-label">联系人</label>
                            <input class="customer-input" data-field="contact_person" value="${contact}">
                            <label class="customer-label">电话</label>
                            <input class="customer-input" data-field="contact_phone" value="${phone}">
                            <label class="customer-label">地址</label>
                            <input class="customer-input" data-field="address" value="${address}">
                            <button class="action-btn customer-save-btn" data-action="save-customer" data-id="${id}">
                                保存
                            </button>
                        </div>
                    `;

                    row.appendChild(token);
                    row.appendChild(detail);
                    row.addEventListener('mouseenter', () => this.toggleCustomerRowFocus(cloud, row));
                    row.addEventListener('mouseleave', (evt) => this.handleCustomerRowMouseLeave(cloud, row, evt));
                    token.addEventListener('click', () => this.pinCustomerRow(cloud, row));
                    cloud.appendChild(row);
                });

                listEl.appendChild(cloud);
                this.bindCustomerSaveEvents(cloud);
            }

            if (loadingEl) loadingEl.style.display = 'none';
        } catch (error) {
            if (loadingEl) loadingEl.style.display = 'none';
            if (emptyEl) {
                emptyEl.style.display = 'block';
                emptyEl.textContent = `加载失败: ${error.message}`;
            }
        }
    }

    showCustomerManageDock() {
        let dock = document.getElementById('proCustomerManageDock');
        if (!dock) {
            dock = document.createElement('div');
            dock.id = 'proCustomerManageDock';
            dock.className = 'customer-manage-dock';
            dock.innerHTML = `
                <div class="customer-cloud" id="proCustomerManageCloud">
                    <div class="customer-row" data-action-row="add">
                        <button type="button" class="floating-unit-token">添加单位</button>
                        <div class="inline-detail">
                            <div class="customer-card">
                                <input id="proAddUnitName" class="customer-manage-input" placeholder="单位名称（必填）">
                                <input id="proAddUnitContact" class="customer-manage-input" placeholder="联系人（选填）">
                                <input id="proAddUnitPhone" class="customer-manage-input" placeholder="联系电话（选填）">
                                <input id="proAddUnitAddress" class="customer-manage-input" placeholder="地址（选填）">
                                <button id="proAddUnitBtn" class="customer-manage-btn">确认添加</button>
                            </div>
                        </div>
                    </div>
                    <div class="customer-row" data-action-row="delete">
                        <button type="button" class="floating-unit-token">删除单位</button>
                        <div class="inline-detail">
                            <div class="customer-card">
                                <select id="proDeleteUnitSelect" class="customer-manage-select">
                                    <option value="">请选择要删除的单位</option>
                                </select>
                                <button id="proDeleteUnitBtn" class="customer-manage-btn danger">确认删除</button>
                            </div>
                        </div>
                    </div>
                    <div class="customer-row" data-action-row="wechat">
                        <a href="/wechat-contacts" target="_blank" class="floating-unit-token" style="text-decoration: none; color: inherit;">微信联系人</a>
                        <div class="inline-detail">
                            <div class="customer-card" style="padding: 8px 12px;">
                                <span style="color: #7f8c8d; font-size: 12px;">管理微信联系人列表（与购买单位类似）</span>
                            </div>
                        </div>
                    </div>
                    <div class="customer-row" data-action-row="wechat-db">
                        <a href="/wechat-db" target="_blank" class="floating-unit-token" style="text-decoration: none; color: inherit;">微信本地库</a>
                        <div class="inline-detail">
                            <div class="customer-card" style="padding: 8px 12px;">
                                <span style="color: #7f8c8d; font-size: 12px;">从界面获取 SQL 数据（需已解密的 .db 文件）</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(dock);
        }
        dock.style.display = 'block';
        this.bindCustomerManageEvents();
    }

    hideCustomerManageDock() {
        const dock = document.getElementById('proCustomerManageDock');
        if (dock) dock.style.display = 'none';
        this._pinnedManageRow = null;
    }

    bindCustomerManageEvents() {
        if (this._customerManageBound) return;
        this._customerManageBound = true;

        const cloud = document.getElementById('proCustomerManageCloud');
        if (cloud) {
            const rows = cloud.querySelectorAll('.customer-row');
            rows.forEach((row) => {
                const token = row.querySelector('.floating-unit-token');
                if (!token) return;
                row.addEventListener('mouseenter', () => this.toggleManageRowFocus(cloud, row));
                row.addEventListener('mouseleave', () => this.handleManageRowMouseLeave(cloud, row));
                token.addEventListener('click', () => this.pinManageRow(cloud, row));
            });
        }

        const addBtn = document.getElementById('proAddUnitBtn');
        if (addBtn) {
            addBtn.addEventListener('click', async () => {
                const unitName = (document.getElementById('proAddUnitName')?.value || '').trim();
                const contact = (document.getElementById('proAddUnitContact')?.value || '').trim();
                const phone = (document.getElementById('proAddUnitPhone')?.value || '').trim();
                const address = (document.getElementById('proAddUnitAddress')?.value || '').trim();
                if (!unitName) {
                    addBtn.textContent = '单位名称必填';
                    setTimeout(() => { addBtn.textContent = '确认添加'; }, 1000);
                    return;
                }
                const oldText = addBtn.textContent;
                addBtn.disabled = true;
                addBtn.textContent = '添加中...';
                try {
                    const response = await fetch('/api/purchase_units', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            unit_name: unitName,
                            contact_person: contact,
                            contact_phone: phone,
                            address: address
                        })
                    });
                    const data = await response.json();
                    if (!data.success) throw new Error(data.message || '添加失败');
                    addBtn.textContent = '已添加';
                    ['proAddUnitName', 'proAddUnitContact', 'proAddUnitPhone', 'proAddUnitAddress'].forEach((id) => {
                        const el = document.getElementById(id);
                        if (el) el.value = '';
                    });
                    await this.loadUserList(this.featureConfig || {});
                } catch (error) {
                    addBtn.textContent = `失败: ${error.message}`;
                } finally {
                    setTimeout(() => {
                        addBtn.textContent = oldText || '确认添加';
                        addBtn.disabled = false;
                    }, 1200);
                }
            });
        }

        const deleteBtn = document.getElementById('proDeleteUnitBtn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', async () => {
                const selectEl = document.getElementById('proDeleteUnitSelect');
                const unitId = Number(selectEl?.value || 0);
                if (!unitId) {
                    deleteBtn.textContent = '先选择单位';
                    setTimeout(() => { deleteBtn.textContent = '确认删除'; }, 1000);
                    return;
                }
                if (!window.confirm('确定删除该单位吗？')) return;
                const oldText = deleteBtn.textContent;
                deleteBtn.disabled = true;
                deleteBtn.textContent = '删除中...';
                try {
                    const response = await fetch(`/api/purchase_units/${unitId}`, { method: 'DELETE' });
                    const data = await response.json();
                    if (!data.success) throw new Error(data.message || '删除失败');
                    deleteBtn.textContent = '已删除';
                    await this.loadUserList(this.featureConfig || {});
                } catch (error) {
                    deleteBtn.textContent = `失败: ${error.message}`;
                } finally {
                    setTimeout(() => {
                        deleteBtn.textContent = oldText || '确认删除';
                        deleteBtn.disabled = false;
                    }, 1200);
                }
            });
        }
    }

    toggleManageRowFocus(cloud, activeRow) {
        if (!cloud || !activeRow) return;
        if (this._pinnedManageRow && this._pinnedManageRow !== activeRow) return;
        const rows = cloud.querySelectorAll('.customer-row');
        rows.forEach((row) => {
            const token = row.querySelector('.floating-unit-token');
            const isActive = row === activeRow;
            row.classList.toggle('expanded', isActive);
            row.classList.toggle('collapsed', !isActive);
            if (token) token.classList.toggle('active', isActive);
        });
    }

    pinManageRow(cloud, row) {
        if (!cloud || !row) return;
        if (this._pinnedManageRow === row) {
            this._pinnedManageRow = null;
            this.clearManageRowFocus(cloud);
            return;
        }
        this._pinnedManageRow = row;
        this.toggleManageRowFocus(cloud, row);
    }

    handleManageRowMouseLeave(cloud, row) {
        if (!cloud || !row) return;
        if (this._pinnedManageRow === row) return;
        this.clearManageRowFocus(cloud);
    }

    clearManageRowFocus(cloud) {
        if (!cloud) return;
        const rows = cloud.querySelectorAll('.customer-row');
        rows.forEach((row) => {
            const token = row.querySelector('.floating-unit-token');
            row.classList.remove('expanded', 'collapsed');
            if (token) token.classList.remove('active');
        });
    }

    syncCustomerManageOptions(customers) {
        const selectEl = document.getElementById('proDeleteUnitSelect');
        if (!selectEl) return;
        const list = Array.isArray(customers) ? customers : [];
        const options = ['<option value="">请选择要删除的单位</option>'];
        list.forEach((item, idx) => {
            const id = Number(item.id || 0);
            const name = this._safeText(item.unit_name || item.name || `单位${idx + 1}`);
            if (id > 0) options.push(`<option value="${id}">${name}</option>`);
        });
        selectEl.innerHTML = options.join('');
    }

    renderProductQueryPanel() {
        const wrapper = document.createElement('div');
        wrapper.className = 'product-query-panel';

        const main = document.createElement('div');
        main.className = 'product-query-main';
        const excelIconSvg = '<svg class="excel-icon-svg" viewBox="0 0 24 24" width="20" height="20"><rect width="24" height="24" rx="3" fill="#217346"/><path stroke="#fff" stroke-width="2.2" stroke-linecap="round" fill="none" d="M7 7l10 10M17 7L7 17"/></svg>';
        main.innerHTML = `
            <div class="product-query-header">
                <div class="product-query-company-name" id="proProductCompanyName">请选择购买单位</div>
                <button type="button" class="product-query-export-btn product-query-export-btn-icon" id="proProductExportExcelBtn" style="display:none" title="导出该单位产品列表">${excelIconSvg}<span>导出</span></button>
            </div>
            <input class="product-query-search" id="proProductSearch" placeholder="搜索产品（名称/型号）" />
            <div class="product-query-list" id="proProductList">
                <div class="product-query-empty">先选择右侧购买单位</div>
            </div>
        `;

        const exportBtn = main.querySelector('#proProductExportExcelBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportProductListExcel());
        }

        const cloud = document.createElement('div');
        cloud.className = 'product-query-company-cloud';
        cloud.id = 'proProductCompanyCloud';
        cloud.innerHTML = '<div class="product-query-empty">正在加载单位...</div>';

        wrapper.appendChild(cloud);
        wrapper.appendChild(main);

        const searchInput = main.querySelector('#proProductSearch');
        if (searchInput) {
            searchInput.addEventListener('input', () => this.filterProductQueryList());
        }

        return wrapper;
    }

    async loadProductQueryCompanies(config = {}) {
        const cloud = document.getElementById('proProductCompanyCloud');
        const companyNameEl = document.getElementById('proProductCompanyName');
        const productListEl = document.getElementById('proProductList');
        this._selectedProductCompany = null;
        this._selectedProductCompanyRow = null;
        const exportBtn = document.getElementById('proProductExportExcelBtn');
        if (exportBtn) exportBtn.style.display = 'none';
        const iconRing = document.getElementById('iconRingContainer');
        if (iconRing) iconRing.classList.remove('visible');
        if (cloud) cloud.innerHTML = '<div class="product-query-empty">正在加载单位...</div>';
        if (companyNameEl) companyNameEl.textContent = '请选择购买单位';
        if (productListEl) productListEl.innerHTML = '<div class="product-query-empty">先选择右侧购买单位</div>';

        try {
            const response = await fetch('/api/customers');
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.message || '加载单位失败');
            }
            const customers = Array.isArray(data.customers) ? data.customers : (Array.isArray(data.data) ? data.data : []);
            this._productCompanies = customers.map((item, index) => ({
                id: Number(item.id || 0),
                name: String(item.unit_name || item.name || `单位${index + 1}`)
            })).filter(item => item.id > 0 || item.name);

            if (!this._productCompanies.length) {
                if (cloud) cloud.innerHTML = '<div class="product-query-empty">暂无可用购买单位</div>';
                return;
            }

            if (cloud) {
                cloud.innerHTML = '';
                const companyCloud = document.createElement('div');
                companyCloud.className = 'customer-cloud product-company-cloud';

                this._productCompanies.forEach((company, index) => {
                    const row = document.createElement('div');
                    row.className = 'customer-row';
                    row.setAttribute('data-id', String(company.id));

                    const token = document.createElement('button');
                    token.type = 'button';
                    token.className = 'floating-unit-token';
                    token.setAttribute('data-id', String(company.id));
                    token.textContent = company.name || `单位${index + 1}`;

                    const detail = document.createElement('div');
                    detail.className = 'inline-detail';
                    detail.innerHTML = `
                        <div class="customer-card">
                            <div class="product-company-hint">点击选择该单位并加载产品列表</div>
                        </div>
                    `;

                    row.appendChild(token);
                    row.appendChild(detail);
                    token.addEventListener('mouseenter', () => this.toggleProductCompanyFocus(companyCloud, row));
                    token.addEventListener('mouseleave', () => this.clearProductCompanyFocus(companyCloud));
                    detail.addEventListener('mouseenter', () => this.toggleProductCompanyFocus(companyCloud, row));
                    detail.addEventListener('mouseleave', () => this.clearProductCompanyFocus(companyCloud));
                    token.addEventListener('click', () => this.selectProductCompany(company, row, token));
                    companyCloud.appendChild(row);
                });

                cloud.appendChild(companyCloud);
            }

            if (typeof window.setProProductQueryStage === 'function') {
                window.setProProductQueryStage('companies', {
                    companies: this._productCompanies.map(item => item.name)
                });
            }

            const query = (config && config.query ? String(config.query) : '').trim();
            if (query) {
                const matched = this._productCompanies.find(item => item.name.includes(query));
                if (matched) {
                    const row = cloud ? cloud.querySelector(`.customer-row[data-id="${matched.id}"]`) : null;
                    const token = row ? row.querySelector('.floating-unit-token') : null;
                    this.selectProductCompany(matched, row || null, token || null);
                }
            }
        } catch (error) {
            if (cloud) cloud.innerHTML = `<div class="product-query-empty">加载单位失败: ${this._safeText(error.message)}</div>`;
        }
    }

    toggleProductCompanyFocus(cloud, activeRow) {
        if (!cloud || !activeRow) return;
        if (this._selectedProductCompanyRow && this._selectedProductCompanyRow !== activeRow) return;
        const rows = cloud.querySelectorAll('.customer-row');
        rows.forEach((row) => {
            const token = row.querySelector('.floating-unit-token');
            const isActive = row === activeRow;
            row.classList.toggle('expanded', isActive);
            row.classList.toggle('collapsed', !isActive);
            if (token) token.classList.toggle('active', isActive);
        });
    }

    clearProductCompanyFocus(cloud) {
        if (!cloud) return;
        if (this._selectedProductCompanyRow) return;
        const rows = cloud.querySelectorAll('.customer-row');
        rows.forEach((row) => {
            const token = row.querySelector('.floating-unit-token');
            row.classList.remove('expanded', 'collapsed');
            if (token) token.classList.remove('active');
        });
    }

    async selectProductCompany(company, rowEl, tokenEl) {
        if (!company) return;
        this._selectedProductCompany = company;
        this._productAllItems = [];
        this._selectedProductCompanyRow = rowEl || null;

        const cloudWrap = document.getElementById('proProductCompanyCloud');
        const cloud = cloudWrap ? cloudWrap.querySelector('.customer-cloud') : null;
        if (cloud) {
            const rows = cloud.querySelectorAll('.customer-row');
            rows.forEach((row) => {
                const token = row.querySelector('.floating-unit-token');
                const active = String(company.id) === row.getAttribute('data-id');
                row.classList.toggle('expanded', active);
                row.classList.toggle('collapsed', !active);
                if (token) {
                    token.classList.toggle('active', active);
                    token.classList.toggle('pinned', active);
                }
            });
        }
        if (tokenEl && tokenEl.classList) tokenEl.classList.add('active', 'pinned');

        const companyNameEl = document.getElementById('proProductCompanyName');
        if (companyNameEl) companyNameEl.textContent = company.name || '已选择单位';
        const exportBtn = document.getElementById('proProductExportExcelBtn');
        if (exportBtn) exportBtn.style.display = '';

        const productListEl = document.getElementById('proProductList');
        if (productListEl) {
            productListEl.innerHTML = '<div class="product-query-empty">正在加载该单位产品...</div>';
        }

        const products = await this.loadProductsForCompany(company);
        this._productAllItems = products;
        this.renderProductQueryList(products);

        if (typeof window.setProProductQueryStage === 'function') {
            window.setProProductQueryStage('company_selected', {
                company: company.name,
                products: products.map((p) => p.name || p.model_number || '产品')
            });
        }
        // 选择单位且产品列表已出后，再显示图标环，用于导出该公司价格表
        const iconRing = document.getElementById('iconRingContainer');
        if (iconRing) iconRing.classList.add('visible');
        this.updateProductQueryIconRing();
    }

    async loadProductsForCompany(company) {
        const requests = [];
        if (company && company.name) {
            requests.push(`/api/products?unit=${encodeURIComponent(company.name)}`);
        }
        if (company && company.id > 0) {
            requests.push(`/api/products/${company.id}`);
            requests.push(`/api/products?customer_id=${encodeURIComponent(company.id)}`);
            requests.push(`/api/products?purchase_unit_id=${encodeURIComponent(company.id)}`);
        }
        requests.push('/api/products');

        for (const url of requests) {
            try {
                const response = await fetch(url);
                if (!response.ok) continue;
                const data = await response.json();
                if (!data || data.success === false) continue;
                const products = this._normalizeProductList(data);
                if (products.length > 0 || url === '/api/products') {
                    return products;
                }
            } catch (e) {
                // 继续尝试后续兼容接口
            }
        }
        return [];
    }

    _normalizeProductList(data) {
        const source = Array.isArray(data.products)
            ? data.products
            : (Array.isArray(data.data) ? data.data : []);
        return source.map((item) => ({
            id: Number(item.id || 0),
            name: this._safeText(item.name || ''),
            model_number: this._safeText(item.model_number || item.model || ''),
            specification: this._safeText(item.specification || ''),
            price: Number(item.price || 0)
        }));
    }

    renderProductQueryList(products) {
        const productListEl = document.getElementById('proProductList');
        if (!productListEl) return;

        if (!Array.isArray(products) || products.length === 0) {
            productListEl.innerHTML = '<div class="product-query-empty">该单位暂无产品</div>';
            return;
        }

        productListEl.innerHTML = '';
        products.forEach((product, index) => {
            const row = document.createElement('button');
            row.type = 'button';
            row.className = 'product-item';
            row.setAttribute('data-index', String(index));
            row.innerHTML = `
                <div class="product-item-title">${product.name || `产品${index + 1}`}</div>
                <div class="product-item-meta">
                    <span>${product.model_number || '无型号'}</span>
                    <span>¥${Number(product.price || 0).toFixed(2)}</span>
                </div>
            `;
            row.addEventListener('click', () => this.selectProductItem(product, row));
            productListEl.appendChild(row);
        });
    }

    filterProductQueryList() {
        const keyword = (document.getElementById('proProductSearch')?.value || '').trim().toLowerCase();
        const list = Array.isArray(this._productAllItems) ? this._productAllItems : [];
        if (!keyword) {
            this.renderProductQueryList(list);
            return;
        }
        const filtered = list.filter((item) => {
            const hay = `${item.name || ''} ${item.model_number || ''}`.toLowerCase();
            return hay.includes(keyword);
        });
        this.renderProductQueryList(filtered);
    }

    exportProductListExcel() {
        const company = this._selectedProductCompany;
        if (!company || (!company.id && !company.name)) {
            alert('请先选择购买单位');
            return;
        }
        const apiBase = (typeof window.API_BASE !== 'undefined' ? window.API_BASE : '') || '';
        const params = new URLSearchParams();
        if (company.id) params.set('unit_id', String(company.id));
        if (company.name) params.set('unit', company.name);
        // 使用单段路径避免 404
        const url = `${apiBase}/api/export_unit_products_xlsx?${params.toString()}`;
        fetch(url)
            .then(function (res) {
                if (res.ok) return res.blob();
                return res.text().then(function (text) {
                    try {
                        const data = JSON.parse(text);
                        throw new Error(data.message || '导出失败');
                    } catch (e) {
                        if (e instanceof SyntaxError || (text && text.trim().startsWith('<'))) {
                            throw new Error('服务器返回了错误页（' + res.status + '），请确认该单位有产品数据');
                        }
                        if (e instanceof Error) throw e;
                        throw new Error(text || res.statusText || '导出失败，未返回文件');
                    }
                });
            })
            .then(function (blob) {
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = (company.name || '产品') + '_产品列表.xlsx';
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

    /** 产品查询时右上角图标环：显示「导出该单位产品列表」Excel 图标 */
    updateProductQueryIconRing() {
        const container = document.getElementById('iconRingContainer');
        if (!container) return;
        container.innerHTML = '';
        const excelIconSvg = '<svg class="excel-icon-svg" viewBox="0 0 24 24" width="28" height="28"><rect width="24" height="24" rx="3" fill="#217346"/><path stroke="#fff" stroke-width="2.2" stroke-linecap="round" fill="none" d="M7 7l10 10M17 7L7 17"/></svg>';
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'icon-ring-btn';
        btn.title = '导出该单位产品列表';
        btn.innerHTML = excelIconSvg;
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            if (typeof this.exportProductListExcel === 'function') this.exportProductListExcel();
        }.bind(this));
        container.appendChild(btn);
    }

    selectProductItem(product, rowEl) {
        if (!product) return;
        const container = document.getElementById('proProductList');
        if (container) {
            container.querySelectorAll('.product-item').forEach((el) => el.classList.remove('active'));
        }
        if (rowEl) rowEl.classList.add('active');

        if (typeof window.setProProductQueryStage === 'function') {
            window.setProProductQueryStage('product_selected', {
                product_id: Number(product.id || 0),
                name: product.name,
                model: product.model_number || product.specification || '',
                price: Number(product.price || 0),
                unit_name: this._selectedProductCompany ? String(this._selectedProductCompany.name || '') : '',
                customer_id: this._selectedProductCompany ? Number(this._selectedProductCompany.id || 0) : 0
            });
        }
    }

    async selectProductCompanyByName(companyName) {
        const name = String(companyName || '').trim();
        if (!name || !Array.isArray(this._productCompanies) || this._productCompanies.length === 0) return;
        const company = this._productCompanies.find((item) => String(item.name || '') === name)
            || this._productCompanies.find((item) => String(item.name || '').includes(name));
        if (!company) return;

        const cloud = document.getElementById('proProductCompanyCloud');
        const row = cloud ? cloud.querySelector(`.customer-row[data-id="${company.id}"]`) : null;
        const token = row ? row.querySelector('.floating-unit-token') : null;
        await this.selectProductCompany(company, row || null, token || null);
    }

    selectProductItemByName(productName) {
        const name = String(productName || '').trim();
        if (!name || !Array.isArray(this._productAllItems) || this._productAllItems.length === 0) return;

        const product = this._productAllItems.find((item) => String(item.name || '') === name || String(item.model_number || '') === name)
            || this._productAllItems.find((item) => (`${item.name || ''} ${item.model_number || ''}`).includes(name));
        if (!product) return;

        const list = document.getElementById('proProductList');
        const rows = list ? Array.from(list.querySelectorAll('.product-item')) : [];
        const row = rows.find((el) => (el.querySelector('.product-item-title')?.textContent || '').trim() === String(product.name || '').trim())
            || null;
        this.selectProductItem(product, row);
    }

    bindCustomerSaveEvents(containerEl) {
        if (!containerEl) return;
        containerEl.querySelectorAll('[data-action="save-customer"]').forEach((btn) => {
            btn.addEventListener('click', () => this.saveCustomerFromCard(btn));
        });
    }

    toggleCustomerRowFocus(cloud, activeRow) {
        if (!cloud || !activeRow) return;
        if (this._pinnedCustomerRow && this._pinnedCustomerRow !== activeRow) return;
        const rows = cloud.querySelectorAll('.customer-row');
        rows.forEach((row) => {
            const token = row.querySelector('.floating-unit-token');
            const isActive = row === activeRow;
            row.classList.toggle('expanded', isActive);
            row.classList.toggle('collapsed', !isActive);
            if (token) token.classList.toggle('active', isActive);
        });
    }

    pinCustomerRow(cloud, row) {
        if (!cloud || !row) return;

        // 再点一次可取消固定，恢复全部
        if (this._pinnedCustomerRow === row) {
            this._pinnedCustomerRow = null;
            this.clearCustomerRowFocus(cloud);
            return;
        }

        this._pinnedCustomerRow = row;
        this.toggleCustomerRowFocus(cloud, row);
        const rows = cloud.querySelectorAll('.customer-row');
        rows.forEach((item) => {
            const token = item.querySelector('.floating-unit-token');
            if (token) token.classList.toggle('pinned', item === row);
        });
    }

    handleCustomerRowMouseLeave(cloud, row, evt) {
        if (!cloud || !row) return;

        // 固定状态：只有从左侧离开才解除固定
        if (this._pinnedCustomerRow === row) {
            const rect = row.getBoundingClientRect();
            const x = evt && typeof evt.clientX === 'number' ? evt.clientX : rect.left;
            const leftExit = x <= rect.left + 2;
            if (leftExit) {
                this._pinnedCustomerRow = null;
                this.clearCustomerRowFocus(cloud);
            }
            return;
        }

        this.clearCustomerRowFocus(cloud);
    }

    clearCustomerRowFocus(cloud) {
        if (!cloud) return;
        const rows = cloud.querySelectorAll('.customer-row');
        rows.forEach((row) => {
            const token = row.querySelector('.floating-unit-token');
            row.classList.remove('expanded', 'collapsed');
            if (token) token.classList.remove('active', 'pinned');
        });
    }

    async saveCustomerFromCard(button) {
        const customerId = Number(button.getAttribute('data-id') || 0);
        if (!customerId) return;

        const card = button.closest('.customer-card');
        if (!card) return;

        const payload = {
            contact_person: (card.querySelector('[data-field="contact_person"]')?.value || '').trim(),
            contact_phone: (card.querySelector('[data-field="contact_phone"]')?.value || '').trim(),
            address: (card.querySelector('[data-field="address"]')?.value || '').trim(),
            discount_rate: 1,
            is_active: 1
        };

        const oldText = button.textContent;
        button.disabled = true;
        button.classList.remove('saved', 'failed');
        button.classList.add('saving');
        button.textContent = '保存中...';

        try {
            const response = await fetch(`/api/customers/${customerId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.message || '保存失败');
            }
            button.classList.remove('saving');
            button.classList.add('saved');
            button.textContent = '已保存';
            if (card) {
                card.classList.remove('saved-flash');
                void card.offsetWidth;
                card.classList.add('saved-flash');
            }
            setTimeout(() => {
                button.textContent = oldText;
                button.disabled = false;
                button.classList.remove('saved');
            }, 800);
        } catch (error) {
            button.classList.remove('saving');
            button.classList.add('failed');
            button.textContent = `失败: ${error.message}`;
            setTimeout(() => {
                button.textContent = oldText;
                button.disabled = false;
                button.classList.remove('failed');
            }, 1200);
        }
    }
}

// 全局实例
window.proFeatureWidget = null;

// 初始化函数
function initProFeatureWidget() {
    if (!window.proFeatureWidget) {
        console.log('初始化专业版功能悬浮窗组件...');
        window.proFeatureWidget = new ProFeatureWidget();
        console.log('专业版功能悬浮窗组件初始化完成');
    }
}

// 立即初始化（如果 DOM 已加载）
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProFeatureWidget);
} else {
    // DOM 已经加载完成，立即初始化
    initProFeatureWidget();
}

// 暴露 API
window.showProFeature = (feature, config) => {
    if (window.proFeatureWidget) {
        window.proFeatureWidget.showFeature(feature, config);
    } else {
        console.error('悬浮窗组件未初始化');
    }
};

window.hideProFeature = () => {
    if (window.proFeatureWidget) {
        window.proFeatureWidget.hide();
    }
};
