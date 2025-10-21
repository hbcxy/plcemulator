// const { spawn } = require('child_process');

// // 要传递给 Python 进程的参数
// const projectOpen = 'E:\\Projects\\Blink'
// const args = [projectOpen];

// const readline = require('readline');

// // 创建一个 readline 接口来处理命令行输入
// const rl = readline.createInterface({
//   input: process.stdin,
//   output: process.stdout,
// });

// // 启动 Python 进程
// const pythonProcess = spawn('python', ['editor/Laucher.py', ...args]);

// // 将 Node.js 的标准输入转发给 Python 子进程
// rl.on('line', (input) => {
//   pythonProcess.stdin.write(input + '\n');
// });

// // 监听 Python 进程的 stdout
// pythonProcess.stdout.on('data', (data) => {
// //   console.log(`Python 进程输出：${data}`);
//     process.stdout.write(`${data}`);
// });

// // 监听 Python 进程的 stderr
// pythonProcess.stderr.on('data', (data) => {
// //   console.error(`Python 进程错误：${data}`);
//     process.stderr.write(`${data}`);
// });

// // 向 Python 进程发送命令
// function sendCommand(command) {
//   pythonProcess.stdin.write(command + '\n');
// }

// // 示例：发送命令
// sendCommand('run');
// // setTimeout(() => {
// //   sendCommand('stop');
// //   setTimeout(() => {
// //     pythonProcess.kill();
// //   }, 0);
// // }, 10000); // 10秒后发送停止命令


// // sendCommand('build');


const { spawn } = require('child_process');
const { Dealer } = require('zeromq');
const readline = require('readline');

// Configuration constants
const PORT = 9001;
// 相对路径：从 test.js 所在目录（emulator/editor）向上两级到根目录，再进入 Blink
const PROJECT_OPEN_PATH = '../../Blink';
// 相对路径：Laucher.py 与 test.js 在同一目录（editor）下
const PYTHON_SCRIPT_PATH = './Laucher.py';  // 或直接写 'Laucher.py'

// Create ZeroMQ dealer socket
const dealerSocket = new Dealer();
const clientId = `js_client_${Math.random().toString(36).substring(2)}`;
dealerSocket.identity = clientId;

// Create readline interface
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

// Add Promise support to readline
rl.questionAsync = (question) => new Promise(resolve => rl.question(question, resolve));

// Start Python process
const pythonProcess = spawn('python', [PYTHON_SCRIPT_PATH, PROJECT_OPEN_PATH]);

// Cleanup function
function cleanup() {
    try {
        dealerSocket.close();
    } catch (err) {
        console.error('Error closing ZeroMQ socket:', err);
    }
    try {
        rl.close();
    } catch (err) {
        console.error('Error closing readline:', err);
    }
    try {
        if (!pythonProcess.killed) {
            pythonProcess.kill();
        }
    } catch (err) {
        console.error('Error killing Python process:', err);
    }
}

// Handle process termination signals
process.on('SIGINT', () => {
    console.log('\nReceived termination signal, cleaning up...');
    cleanup();
    process.exit(0);
});

// Connect ZeroMQ socket
function connectSocket() {
    try {
        dealerSocket.connect(`tcp://localhost:${PORT}`);
        console.log(`Connected to ZeroMQ server on port: ${PORT}`);
    } catch (err) {
        console.error('ZeroMQ connection failed:', err);
        cleanup();
        process.exit(1);
    }
}

// Handle Python process output
pythonProcess.stdout.on('data', (data) => {
    process.stdout.write(`${data}`);
});

pythonProcess.stderr.on('data', (data) => {
    process.stderr.write(`${data}`);
});

pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code: ${code}`);
    cleanup();
    process.exit(code);
});

// Send command to Python
async function sendCommand(type, payload = {}) {
    try {
        await dealerSocket.send(["", JSON.stringify({ type, ...payload })]);
        console.log(`Command sent: ${type}`);
    } catch (err) {
        console.error('Failed to send command:', err);
        throw err;
    }
}

// Handle messages from Python
(async function() {
    try {
        for await (const [msg] of dealerSocket) {
            const message = JSON.parse(msg.toString());
            console.log('Received from Python:', message);
        }
    } catch (err) {
        console.error('Message parse error:', err);
    } finally {
        dealerSocket.close();
    }
})();

// Main test function
async function runTest() {
    connectSocket();

    const menuText = '\nOperations:' + 
                    '\n1: run' +
                    '\n2: build' +
                    '\n3: stop' +
                    '\n4: subscribe' +
                    '\n5: unsubscribe' +
                    '\n6: force' +
                    '\n7: release' +
                    '\nEnter operation: ';

    // Show menu once at the beginning
    console.log(menuText);

    try {
        while (true) {
            const op = await rl.questionAsync('> ').then(ans => ans.trim().toLowerCase());

            try {
                if (['1', 'run'].includes(op)) {
                    await sendCommand('run');
                } else if (['2', 'build'].includes(op)) {
                    await sendCommand('build');
                } else if (['3', 'stop'].includes(op)) {
                    await sendCommand('stop');
                } else if (['4', 'subscribe'].includes(op)) {
                    const name = await rl.questionAsync('Enter variable name: ');
                    await sendCommand('subscribe', { name: name });
                } else if (['5', 'unsubscribe'].includes(op)) {
                    const name = await rl.questionAsync('Enter variable name: ');
                    await sendCommand('unsubscribe', { name: name });
                } else if (['6', 'force'].includes(op)) {
                    const name = await rl.questionAsync('Enter variable name: ');
                    const val = await rl.questionAsync('Enter value: ');
                    await sendCommand('force', { 
                        name: name,
                        value: isNaN(val) ? val : parseFloat(val) 
                    });
                } else if (['7', 'release'].includes(op)) {
                    const name = await rl.questionAsync('Enter variable name: ');
                    await sendCommand('release', { name: name });
                } else {
                    console.log('Invalid operation');
                }
            } catch (err) {
                console.error('Operation failed:', err);
            }
        }
    } finally {
        cleanup();
    }
}

// Start the test
runTest().catch(err => {
    console.error('Error running test:', err);
    cleanup();
    process.exit(1);
});