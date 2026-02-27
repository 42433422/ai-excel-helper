/**
 * 科密CM500高拍仪JavaScript接口
 * 用于前端调用本地扫描服务
 */

class CometScanner {
    constructor(serviceUrl = 'http://127.0.0.1:5001') {
        this.serviceUrl = serviceUrl;
        this.isConnected = false;
        this.deviceInfo = null;
    }

    /**
     * 检查扫描服务是否可用
     */
    async checkService() {
        try {
            const response = await fetch(`${this.serviceUrl}/api/status`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.isConnected = true;
                this.deviceInfo = data.device_info;
                return {
                    success: true,
                    connected: true,
                    deviceInfo: data.device_info
                };
            } else {
                this.isConnected = false;
                return {
                    success: false,
                    connected: false,
                    error: '服务未响应'
                };
            }
        } catch (error) {
            this.isConnected = false;
            return {
                success: false,
                connected: false,
                error: error.message
            };
        }
    }

    /**
     * 扫描图像
     * @param {string} resolution - 分辨率 (high/medium/low)
     * @returns {Promise<Object>} 扫描结果
     */
    async scan(resolution = 'high') {
        try {
            // 先检查服务状态
            const statusCheck = await this.checkService();
            if (!statusCheck.connected) {
                return {
                    success: false,
                    error: '扫描服务未启动，请先启动科密CM500服务'
                };
            }

            const response = await fetch(`${this.serviceUrl}/api/scan`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    resolution: resolution
                })
            });

            const result = await response.json();
            
            if (result.success) {
                return {
                    success: true,
                    imageBase64: result.image_base64,
                    imageId: result.image_id,
                    filepath: result.filepath,
                    resolution: result.resolution,
                    width: result.width,
                    height: result.height,
                    mode: result.mode
                };
            } else {
                return {
                    success: false,
                    error: result.error || '扫描失败'
                };
            }
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * 获取扫描的图像文件
     * @param {string} imageId - 图像ID
     * @returns {Promise<string>} 图像URL
     */
    async getImageUrl(imageId) {
        return `${this.serviceUrl}/api/image/${imageId}`;
    }

    /**
     * 显示扫描预览
     * @param {string} imageBase64 - base64编码的图像
     * @param {HTMLElement} container - 预览容器
     */
    showPreview(imageBase64, container) {
        if (!container) return;

        container.innerHTML = `
            <div class="scanner-preview-container" style="
                position: relative;
                display: inline-block;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            ">
                <img src="${imageBase64}" style="
                    max-width: 100%;
                    max-height: 400px;
                    display: block;
                " alt="扫描预览">
                <div style="
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    background: rgba(76, 175, 80, 0.9);
                    color: white;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 12px;
                ">
                    <i class="fa fa-check-circle"></i> 扫描完成
                </div>
            </div>
        `;
    }

    /**
     * 显示扫描中状态
     * @param {HTMLElement} container - 预览容器
     */
    showScanning(container) {
        if (!container) return;

        container.innerHTML = `
            <div class="scanner-scanning-container" style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px;
                background: #f5f5f5;
                border-radius: 8px;
                border: 2px dashed #ccc;
            ">
                <div style="
                    width: 50px;
                    height: 50px;
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #4CAF50;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                "></div>
                <p style="margin-top: 15px; color: #666;">正在扫描...</p>
            </div>
            <style>
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        `;
    }

    /**
     * 显示错误信息
     * @param {string} message - 错误信息
     * @param {HTMLElement} container - 预览容器
     */
    showError(message, container) {
        if (!container) return;

        container.innerHTML = `
            <div class="scanner-error-container" style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px;
                background: #ffebee;
                border-radius: 8px;
                border: 2px solid #ef5350;
            ">
                <i class="fa fa-exclamation-circle" style="
                    font-size: 48px;
                    color: #ef5350;
                    margin-bottom: 10px;
                "></i>
                <p style="color: #c62828; text-align: center;">${message}</p>
            </div>
        `;
    }
}

// 创建全局扫描仪实例
window.cometScanner = new CometScanner();

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CometScanner;
}
