const { spawn } = require('child_process');
const { Dealer } = require('zeromq');
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');

// 配置常量
const ZMQ_PORT = 5555;
const WEB_PORT = 3000; // Web服务器端口
const PROJECT_OPEN_PATH = 'D:\\software\\weChat\\file\\xwechat_files\\wxid_bf2mrq3875u022_88a5\\msg\\file\\2025-09\\plcemulator\\Blink';
const PYTHON_SCRIPT_PATH = 'editor/Laucher.py';

// 创建Express应用和HTTP服务器
const app = express();
app.use(express.json()); // 解析JSON请求体
app.use(express.static(path.join(__dirname, 'public'))); // 提供静态文件
const server = http.createServer(app);

// 创建WebSocket服务器
const wss = new WebSocket.Server({ server });

// 创建ZeroMQ dealer socket
const dealerSocket = new Dealer();
const clientId = `js_client_${Math.random().toString(36).substring(2)}`;
dealerSocket.identity = clientId;

// 启动Python进程
const pythonProcess = spawn('python', [PYTHON_SCRIPT_PATH, PROJECT_OPEN_PATH]);

// 清理函数
function cleanup() {
    try {
        dealerSocket.close();
    } catch (err) {
        console.error('关闭ZeroMQ socket错误:', err);
    }
    try {
        if (!pythonProcess.killed) {
            pythonProcess.kill();
        }
    } catch (err) {
        console.error('终止Python进程错误:', err);
    }
    try {
        server.close();
        console.log('Web服务器已关闭');
    } catch (err) {
        console.error('关闭Web服务器错误:', err);
    }
}

// 处理进程终止信号
process.on('SIGINT', () => {
    console.log('\n收到终止信号，正在清理...');
    cleanup();
    process.exit(0);
});

// 连接ZeroMQ socket
function connectSocket() {
    try {
        dealerSocket.connect(`tcp://localhost:${ZMQ_PORT}`);
        console.log(`已连接到ZeroMQ服务器，端口: ${ZMQ_PORT}`);
    } catch (err) {
        console.error('ZeroMQ连接失败:', err);
        cleanup();
        process.exit(1);
    }
}

// 处理Python进程输出
pythonProcess.stdout.on('data', (data) => {
    const output = `${data}`;
    console.log(output);
    // 向所有WebSocket客户端广播Python输出
    broadcastToWebClients({
        type: 'python_output',
        data: output
    });
});

pythonProcess.stderr.on('data', (data) => {
    const error = `${data}`;
    console.error(error);
    // 向所有WebSocket客户端广播Python错误
    broadcastToWebClients({
        type: 'python_error',
        data: error
    });
});

pythonProcess.on('close', (code) => {
    console.log(`Python进程已退出，代码: ${code}`);
    // 通知所有WebSocket客户端Python进程已退出
    broadcastToWebClients({
        type: 'python_exit',
        code: code
    });
    cleanup();
    process.exit(code);
});

// 发送命令到Python
async function sendCommand(type, payload = {}) {
    try {
        await dealerSocket.send(["", JSON.stringify({ type, ...payload })]);
        console.log(`已发送命令: ${type}`);
        return { success: true, message: `命令已发送: ${type}` };
    } catch (err) {
        console.error('发送命令失败:', err);
        return { success: false, error: err.message };
    }
}

// 处理来自Python的消息并广播到WebSocket客户端
(async function() {
    try {
        for await (const [msg] of dealerSocket) {
            const message = JSON.parse(msg.toString());
            console.log('从Python接收:', message);
            
            // 向所有WebSocket客户端发送从Python收到的消息
            broadcastToWebClients({
                type: 'python_message',
                data: message
            });
        }
    } catch (err) {
        console.error('消息解析错误:', err);
    } finally {
        dealerSocket.close();
    }
})();

// 广播消息到所有WebSocket客户端
function broadcastToWebClients(message) {
    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify(message));
        }
    });
}

// WebSocket连接处理
wss.on('connection', (ws) => {
    console.log('新的WebSocket连接');
    
    ws.on('message', (message) => {
        try {
            const command = JSON.parse(message);
            console.log('通过WebSocket接收命令:', command);
            
            // 处理WebSocket命令
            handleCommand(command.type, command.payload)
                .then(response => {
                    ws.send(JSON.stringify({
                        type: 'command_response',
                        command: command.type,
                        response: response
                    }));
                })
                .catch(error => {
                    ws.send(JSON.stringify({
                        type: 'command_error',
                        command: command.type,
                        error: error.message
                    }));
                });
        } catch (err) {
            console.error('处理WebSocket消息错误:', err);
            ws.send(JSON.stringify({
                type: 'error',
                message: '无效的命令格式'
            }));
        }
    });
    
    ws.on('close', () => {
        console.log('WebSocket连接已关闭');
    });
});

// API端点
app.post('/api/command/:type', async (req, res) => {
    const commandType = req.params.type;
    const payload = req.body || {};
    
    try {
        const result = await handleCommand(commandType, payload);
        res.json(result);
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// 提供一个简单的测试页面
app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>PLC Emulator Controller</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                .commands { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 20px 0; }
                button { padding: 10px; cursor: pointer; }
                .output { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 10px; margin: 20px 0; }
                .variable-form { margin: 10px 0; padding: 10px; border: 1px solid #eee; }
            </style>
        </head>
        <body>
            <h1>PLC Emulator Controller</h1>
            
            <div class="commands">
                <button onclick="sendCommand('run')">Run</button>
                <button onclick="sendCommand('build')">Build</button>
                <button onclick="sendCommand('stop')">Stop</button>
            </div>
            
            <div class="variable-form">
                <h3>Subscribe to Variable</h3>
                <input type="text" id="subscribeName" placeholder="Variable name">
                <button onclick="sendCommand('subscribe', { name: document.getElementById('subscribeName').value })">Subscribe</button>
            </div>
            
            <div class="variable-form">
                <h3>Unsubscribe from Variable</h3>
                <input type="text" id="unsubscribeName" placeholder="Variable name">
                <button onclick="sendCommand('unsubscribe', { name: document.getElementById('unsubscribeName').value })">Unsubscribe</button>
            </div>
            
            <div class="variable-form">
                <h3>Force Variable Value</h3>
                <input type="text" id="forceName" placeholder="Variable name">
                <input type="text" id="forceValue" placeholder="Value">
                <button onclick="sendCommand('force', { 
                    name: document.getElementById('forceName').value, 
                    value: document.getElementById('forceValue').value 
                })">Force</button>
            </div>
            
            <div class="variable-form">
                <h3>Release Variable</h3>
                <input type="text" id="releaseName" placeholder="Variable name">
                <button onclick="sendCommand('release', { name: document.getElementById('releaseName').value })">Release</button>
            </div>
            
            <h3>Output</h3>
            <div class="output" id="output"></div>
            
            <script>
                // 连接WebSocket
                const ws = new WebSocket('ws://' + window.location.host);
                
                // 处理WebSocket消息
                ws.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    const outputDiv = document.getElementById('output');
                    const time = new Date().toLocaleTimeString();
                    outputDiv.innerHTML += \`[\${time}] \${JSON.stringify(message)}\\n\`;
                    outputDiv.scrollTop = outputDiv.scrollHeight;
                };
                
                // 发送命令函数
                function sendCommand(type, payload = {}) {
                    ws.send(JSON.stringify({ type, payload }));
                }
                
                // 页面关闭时关闭WebSocket连接
                window.onbeforeunload = function() {
                    ws.close();
                };
            </script>
        </body>
        </html>
    `);
});

// 命令处理函数
async function handleCommand(type, payload = {}) {
    switch (type) {
        case 'run':
            return await sendCommand('run');
        case 'build':
            return await sendCommand('build');
        case 'stop':
            return await sendCommand('stop');
        case 'subscribe':
            if (!payload.name) {
                return { success: false, error: '需要变量名称' };
            }
            return await sendCommand('subscribe', { name: payload.name });
        case 'unsubscribe':
            if (!payload.name) {
                return { success: false, error: '需要变量名称' };
            }
            return await sendCommand('unsubscribe', { name: payload.name });
        case 'force':
            if (!payload.name || payload.value === undefined) {
                return { success: false, error: '需要变量名称和值' };
            }
            return await sendCommand('force', { 
                name: payload.name,
                value: isNaN(payload.value) ? payload.value : parseFloat(payload.value) 
            });
        case 'release':
            if (!payload.name) {
                return { success: false, error: '需要变量名称' };
            }
            return await sendCommand('release', { name: payload.name });
        default:
            return { success: false, error: '无效的命令类型' };
    }
}

// 启动服务器
function startServer() {
    connectSocket();
    
    server.listen(WEB_PORT, () => {
        console.log(`Web服务器运行在端口 ${WEB_PORT}`);
        console.log(`访问 http://localhost:${WEB_PORT} 查看控制界面`);
        console.log(`WebSocket地址: ws://localhost:${WEB_PORT}`);
    });
}

// 启动应用程序
startServer().catch(err => {
    console.error('启动服务器错误:', err);
    cleanup();
    process.exit(1);
});
