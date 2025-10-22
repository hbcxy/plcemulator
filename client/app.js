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

        this.socket.onopen = () => {
            this.reconnectAttempts = 0;
            console.log('成功连接到 WebSocket 服务器');
            document.getElementById('connectBtn').disabled = true;
            document.getElementById('disconnectBtn').disabled = false;
            this.addMessage('系统', '连接已建立', 'info');
        };

        this.socket.onmessage = (event) => {
            try {
                console.log('Raw message:', event.data);
                const data = JSON.parse(event.data);
                // console.log('收到数据:', data);
                if (data) {
                    this.addMessage('PLC', this.formatJson(data), 'data');
                }
            } catch (e) {
                console.error('消息解析错误:', e);
                this.addMessage('系统', `无效消息: ${event.data}`, 'error');
            }
        };

        this.socket.onclose = (event) => {
            console.log('连接已关闭', event);
            document.getElementById('connectBtn').disabled = false;
            document.getElementById('disconnectBtn').disabled = true;

            if (this.isManualDisconnect) {
                this.addMessage('系统', '已手动断开连接', 'info');
                return; // 手动断开不重连
            }

            if (event.wasClean) {
                this.addMessage('系统', '服务器已主动关闭连接', 'info');
                return; // 服务器主动关闭不重连
            }

            // 只有意外断开时才尝试重连
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = this.reconnectDelay;
                console.log(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
                this.addMessage('系统', `连接意外断开，${delay/1000}秒后尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})`, 'warning');
                setTimeout(() => this.connect(), delay);
            } else {
                this.addMessage('系统', '已达到最大重连次数，请手动重新连接', 'error');
            }
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket错误:', error);
            this.addMessage('系统', `连接错误: ${error.message || '未知错误'}`, 'error');
        };
    }

    disconnect() {
        if (this.socket) {
            this.isManualDisconnect = true;
            this.socket.close();
        }
    }

    formatJson(data) {
        return `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    }

    addMessage(source, text, type) {
        const messagesDiv = document.getElementById('messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.innerHTML = `<strong>${source}:</strong> ${text}`;
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

// 初始化客户端
const plcClient = new PLCWebSocketClient();

// 绑定按钮事件
document.getElementById('connectBtn').addEventListener('click', () => {
    plcClient.connect();
});

document.getElementById('disconnectBtn').addEventListener('click', () => {
    plcClient.disconnect();
});