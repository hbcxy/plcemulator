const { Dealer } = require('zeromq');
const readline = require('readline');

// Configuration constants
const PORT = 9001;

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

// Handle messages from Python (async loop)
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
