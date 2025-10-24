// Node.js 环境版本
const WebSocket = require('ws');

class PLCWebSocketClient {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // 3秒
        this.isManualDisconnect = false;
    }

    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            console.log('已经连接到服务器');
            return;
        }

        this.isManualDisconnect = false;
        this.socket = new WebSocket('ws://localhost:9002');

        this.socket.on('open', () => {
            this.reconnectAttempts = 0;
            console.log('✅ 成功连接到 WebSocket 服务器');
        });

        this.socket.on('message', (message) => {
            try {
                console.log('📨 原始消息:', message.toString());
                const data = JSON.parse(message);
                console.log('🔹 来自 PLC 的数据:\n', JSON.stringify(data, null, 2));
            } catch (e) {
                console.error('❌ 消息解析错误:', e.message);
                console.log('无效消息:', message.toString());
            }
        });

        this.socket.on('close', (code, reason) => {
            console.log(`⚠️ 连接已关闭 (code=${code}, reason=${reason.toString() || '无'})`);

            if (this.isManualDisconnect) {
                console.log('ℹ️ 已手动断开连接');
                return;
            }

            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                console.log(`⏳ 尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})，${this.reconnectDelay/1000}秒后重试...`);
                setTimeout(() => this.connect(), this.reconnectDelay);
            } else {
                console.error('🚫 已达到最大重连次数，请手动重新连接');
            }
        });

        this.socket.on('error', (error) => {
            console.error('❗ WebSocket 错误:', error.message);
        });
    }

    disconnect() {
        if (this.socket) {
            this.isManualDisconnect = true;
            console.log('🔌 正在断开连接...');
            this.socket.close();
        }
    }
}

// 使用示例
const plcClient = new PLCWebSocketClient();

// 连接到服务器
plcClient.connect();

// 监听 Ctrl+C 事件，手动断开
process.on('SIGINT', () => {
    console.log('\n🛑 收到退出信号 (Ctrl+C)，正在断开...');
    plcClient.disconnect();
    setTimeout(() => process.exit(0), 1000);
});
