# import asyncio
# import json
# import logging
# import time
# import socket
# from queue import Queue
# from threading import Thread, Lock
# import websockets
# from websockets.exceptions import ConnectionClosed

# class WebSocketServer:
#     def __init__(self, host='localhost', port=8765, max_connections=100):
#         self.host = host
#         self.port = port
#         self.max_connections = max_connections
#         self.connections = set()
#         self.connections_lock = Lock()
#         self.message_queue = Queue()
#         self.server_thread = None
#         self.loop = None
#         self.server = None
#         self._running = False
#         self._shutdown_event = None
#         self._socket = None 
        
#         logging.basicConfig(
#             level=logging.INFO,
#             format='%(asctime)s - %(levelname)s - %(message)s'
#         )
#         self.logger = logging.getLogger(__name__)

#     async def handler(self, websocket):
#         remote_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
#         self.logger.info(f"Client connected: {remote_addr}")
        
#         with self.connections_lock:
#             if len(self.connections) >= self.max_connections:
#                 await websocket.close(code=1008, reason="Too many connections")
#                 return
#             self.connections.add(websocket)

#         try:
#             # Send connection confirmation message
#             await websocket.send(json.dumps({
#                 "type": "system",
#                 "message": "Connection established",
#                 "timestamp": time.time(),
#                 "connection_count": len(self.connections)
#             }))
            
#             # Continuous message receiving loop
#             while self._running:
#                 try:
#                     message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
#                     self.logger.info(f"Received message from {remote_addr}: {message}")
                    
#                     # Process message and reply (example: echo back)
#                     response = {
#                         "type": "echo",
#                         "content": message,
#                         "timestamp": time.time()
#                     }
#                     await websocket.send(json.dumps(response))
                    
#                 except asyncio.TimeoutError:
#                     continue  # Normal timeout, continue loop
#                 except ConnectionClosed:
#                     self.logger.info(f"Client {remote_addr} disconnected")
#                     break
#                 except Exception as e:
#                     self.logger.error(f"Error processing message: {e}")
#                     break
                    
#         except Exception as e:
#             self.logger.error(f"Connection handling exception: {e}")
#         finally:
#             with self.connections_lock:
#                 if websocket in self.connections:
#                     self.connections.remove(websocket)
#             self.logger.info(f"Client {remote_addr} disconnected")

#     async def broadcast_messages(self):
#         """Broadcast messages to all clients"""
#         try:
#             while self._running:
#                 if not self.message_queue.empty():
#                     message = self.message_queue.get()
#                     disconnected = set()
                    
#                     with self.connections_lock:
#                         connections_copy = self.connections.copy()
                    
#                     for ws in connections_copy:
#                         try:
#                             await ws.send(message)
#                         except (ConnectionClosed, ConnectionError):
#                             disconnected.add(ws)
#                         except Exception as e:
#                             self.logger.warning(f"Failed to broadcast message: {e}")
#                             disconnected.add(ws)
                    
#                     if disconnected:
#                         with self.connections_lock:
#                             for ws in disconnected:
#                                 if ws in self.connections:
#                                     self.connections.remove(ws)
                
#                 await asyncio.sleep(0.1)
#         except asyncio.CancelledError:
#             self.logger.info("Broadcast task cancelled")
#         except Exception as e:
#             self.logger.error(f"Broadcast task exception: {e}")

#     def send_message(self, data):
#         """Thread-safe message sending method"""
#         if isinstance(data, dict):
#             try:
#                 data = json.dumps(data, ensure_ascii=False, default=str)
#             except Exception as e:
#                 self.logger.error(f"JSON serialization failed: {e}")
#                 return
#         self.message_queue.put(data)

#     async def _create_socket(self):
#         """Create and configure socket"""
#         sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         sock.bind((self.host, self.port))
#         sock.setblocking(False)
#         return sock

#     async def start_server(self):
#         """Start WebSocket server"""
#         self._running = True
#         # Create Event object in server thread's event loop
#         self._shutdown_event = asyncio.Event()
        
#         try:
#             # Create and configure socket
#             self._socket = await self._create_socket()
            
#             self.server = await websockets.serve(
#                 self.handler,
#                 sock=self._socket,
#                 ping_interval=20,
#                 ping_timeout=20,
#                 max_size=2**20,
#                 close_timeout=5
#             )
#             self.logger.info(f"WebSocket server started at ws://{self.host}:{self.port}")
            
#             # Start broadcast task
#             broadcast_task = asyncio.create_task(self.broadcast_messages())
            
#             # Wait for shutdown signal
#             await self._shutdown_event.wait()
            
#             # Cancel broadcast task
#             broadcast_task.cancel()
#             try:
#                 await broadcast_task
#             except asyncio.CancelledError:
#                 pass
                
#         except Exception as e:
#             self.logger.critical(f"Server startup failed: {e}")
#             raise
#         finally:
#             await self._cleanup_resources()

#     async def _cleanup_resources(self):
#         """Safely clean up all resources"""
#         self.logger.info("Starting resource cleanup...")
        
#         # 1. Close all connections
#         if hasattr(self, 'connections'):
#             self.logger.info(f"Closing {len(self.connections)} connections...")
#             tasks = []
#             with self.connections_lock:
#                 for ws in list(self.connections):
#                     try:
#                         tasks.append(asyncio.create_task(ws.close(code=1000, reason="Server Shutdown")))
#                     except Exception as e:
#                         self.logger.warning(f"Failed to create close task: {e}")
            
#             if tasks:
#                 done, pending = await asyncio.wait(tasks, timeout=5.0)
#                 for task in pending:
#                     task.cancel()
                
#                 with self.connections_lock:
#                     self.connections.clear()
        
#         # 2. Close server
#         if self.server:
#             self.server.close()
#             try:
#                 await asyncio.wait_for(self.server.wait_closed(), timeout=5.0)
#             except asyncio.TimeoutError:
#                 self.logger.warning("Server shutdown timeout, forcing termination")

#         # 3. Close socket
#         if self._socket:
#             try:
#                 self._socket.close()
#             except Exception as e:
#                 self.logger.warning(f"Failed to close socket: {e}")
#             finally:
#                 self._socket = None
        
#         self.logger.info("Resource cleanup completed")

#     def run_in_thread(self):
#         """Run server in a new thread"""
#         def start():
#             try:
#                 self.loop = asyncio.new_event_loop()
#                 asyncio.set_event_loop(self.loop)
#                 self.loop.run_until_complete(self.start_server())
#             except Exception as e:
#                 self.logger.critical(f"Server thread exception: {e}")
#             finally:
#                 tasks = asyncio.all_tasks(self.loop)
#                 for task in tasks:
#                     task.cancel()
#                 self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
#                 self.loop.close()
#                 self.logger.info("Event loop closed")

#         self.server_thread = Thread(target=start, daemon=True)
#         self.server_thread.start()
#         self.logger.info("Server thread started")

#     def stop(self):
#         """Thread-safe stop method"""
#         if not self._running:
#             return
            
#         self.logger.info("Received stop request...")
#         self._running = False
        
#         if self.loop and self.loop.is_running():
#             try:
#                 # Submit shutdown task
#                 future = asyncio.run_coroutine_threadsafe(self._trigger_shutdown(), self.loop)
#                 future.result(timeout=10)  # Wait for 10 seconds
#             except asyncio.TimeoutError:
#                 self.logger.error("Shutdown timeout, forcing stop")
#             except Exception as e:
#                 self.logger.error(f"Error during shutdown: {e}")
#             finally:
#                 if self.server_thread and self.server_thread.is_alive():
#                     self.server_thread.join(timeout=2)
                
#         self.logger.info("WebSocket server fully stopped")

#     async def _trigger_shutdown(self):
#         """Trigger shutdown event"""
#         if self._shutdown_event and not self._shutdown_event.is_set():
#             self._shutdown_event.set()

#     async def stop_async(self):
#         """Async stop method"""
#         if not self._running:
#             return
            
#         self._running = False
#         self._shutdown_event.set()  # Trigger shutdown
#         await self._cleanup_resources()


import asyncio
import json
import logging
import time
import socket
from queue import Queue
from threading import Thread, Lock
import websockets
from websockets.exceptions import ConnectionClosed
from collections import deque

class WebSocketServer:
    def __init__(self, host='localhost', port=8765, max_connections=100, interval=5):
        """Initialize the WebSocket server with configuration parameters.
        
        Args:
            host (str): Host address to bind the server to
            port (int): Port number to listen on
            max_connections (int): Maximum number of concurrent connections
            interval (int): Interval in seconds between batch messages
        """
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.interval = interval  # Interval in seconds between batch messages
        self.connections = set()
        self.connections_lock = Lock()
        self.message_queue = Queue()  # For thread-safe message receiving
        self.batch_messages = deque()  # For accumulating messages between intervals
        self.batch_lock = Lock()  # Lock for batch_messages
        self.server_thread = None
        self.loop = None
        self.server = None
        self._running = False
        self._shutdown_event = None
        self._socket = None 
        self._batch_task = None
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    async def handler(self, websocket):
        """Handle incoming WebSocket connections and messages.
        
        Args:
            websocket: The WebSocket connection object
        """
        remote_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.logger.info(f"Client connected: {remote_addr}")
        
        with self.connections_lock:
            if len(self.connections) >= self.max_connections:
                await websocket.close(code=1008, reason="Too many connections")
                return
            self.connections.add(websocket)

        try:
            # Send connection confirmation message
            await websocket.send(json.dumps({
                "message": "Connection established",
                "timestamp": time.time(),
                "connection_count": len(self.connections)
            }))
            
            # Continuous message receiving loop
            while self._running:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    self.logger.info(f"Received message from {remote_addr}: {message}")
                    
                    # Process message and reply (example: echo back)
                    response = {
                        "content": message,
                        "timestamp": time.time()
                    }
                    await websocket.send(json.dumps(response))
                    
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue loop
                except ConnectionClosed:
                    self.logger.info(f"Client {remote_addr} disconnected")
                    break
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Connection handling exception: {e}")
        finally:
            with self.connections_lock:
                if websocket in self.connections:
                    self.connections.remove(websocket)
            self.logger.info(f"Client {remote_addr} disconnected")

    async def process_batch_messages(self):
        """Process the message queue and accumulate messages for batch sending.
        
        Continuously checks the message queue and accumulates valid messages
        into the batch_messages deque for later batch sending.
        """
        try:
            while self._running:
                # Get all available messages from the queue
                messages = []
                while not self.message_queue.empty():
                    try:
                        message = self.message_queue.get_nowait()
                        # Parse message if it's a string to ensure it's JSON
                        if isinstance(message, str):
                            try:
                                message = json.loads(message)
                            except json.JSONDecodeError:
                                self.logger.warning(f"Invalid JSON message: {message}")
                                continue
                        messages.append(message)
                    except:
                        break
                
                # Add to batch if we got messages
                if messages:
                    with self.batch_lock:
                        self.batch_messages.extend(messages)
                
                await asyncio.sleep(0.1)  # Small sleep to prevent busy waiting
        except asyncio.CancelledError:
            self.logger.info("Message processing task cancelled")
        except Exception as e:
            self.logger.error(f"Message processing exception: {e}")

    async def send_batch_messages(self):
        """Send accumulated messages to all clients at regular intervals.
        
        Periodically sends all accumulated messages to all connected clients
        in a single batch at the configured interval.
        """
        try:
            while self._running:
                await asyncio.sleep(self.interval)
                
                if not self._running:
                    break
                
                # Get all accumulated messages
                with self.batch_lock:
                    if not self.batch_messages:
                        continue
                    messages = list(self.batch_messages)
                    self.batch_messages.clear()
                
                # Prepare batch data as a simple array of messages
                batch_data = {
                    "timestamp": time.time(),
                    "messages": messages,
                    "count": len(messages)
                }
                
                # Send to all clients
                disconnected = set()
                with self.connections_lock:
                    connections_copy = self.connections.copy()
                
                for ws in connections_copy:
                    try:
                        await ws.send(json.dumps(batch_data))
                    except (ConnectionClosed, ConnectionError):
                        disconnected.add(ws)
                    except Exception as e:
                        self.logger.warning(f"Failed to send batch message: {e}")
                        disconnected.add(ws)
                
                if disconnected:
                    with self.connections_lock:
                        for ws in disconnected:
                            if ws in self.connections:
                                self.connections.remove(ws)
                
                # self.logger.info(f"Sent batch of {len(messages)} messages to {len(connections_copy)} clients")
                
        except asyncio.CancelledError:
            self.logger.info("Batch sending task cancelled")
        except Exception as e:
            self.logger.error(f"Batch sending exception: {e}")

    def send_message(self, data):
        """Thread-safe method to send a message to the server.
        
        Args:
            data: The message data to send (can be dict or JSON string)
        """
        if isinstance(data, str):
            try:
                # Validate if it's valid JSON string
                json.loads(data)
            except json.JSONDecodeError:
                self.logger.error("Invalid JSON string provided")
                return
        
        self.message_queue.put(data)

    async def _create_socket(self):
        """Create and configure the server socket.
        
        Returns:
            socket: Configured socket object
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.setblocking(False)
        return sock

    async def start_server(self):
        """Start the WebSocket server and related tasks."""
        self._running = True
        # Create Event object in server thread's event loop
        self._shutdown_event = asyncio.Event()
        
        try:
            # Create and configure socket
            self._socket = await self._create_socket()
            
            self.server = await websockets.serve(
                self.handler,
                sock=self._socket,
                ping_interval=20,
                ping_timeout=20,
                max_size=2**20,
                close_timeout=5
            )
            self.logger.info(f"WebSocket server started at ws://{self.host}:{self.port}")
            
            # Start tasks
            process_task = asyncio.create_task(self.process_batch_messages())
            self._batch_task = asyncio.create_task(self.send_batch_messages())
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
            # Cancel tasks
            process_task.cancel()
            self._batch_task.cancel()
            
            try:
                await process_task
                await self._batch_task
            except asyncio.CancelledError:
                pass
                
        except Exception as e:
            self.logger.critical(f"Server startup failed: {e}")
            raise
        finally:
            await self._cleanup_resources()

    async def _cleanup_resources(self):
        """Safely clean up all server resources and connections."""
        self.logger.info("Starting resource cleanup...")
        
        # 1. Close all connections
        if hasattr(self, 'connections'):
            self.logger.info(f"Closing {len(self.connections)} connections...")
            tasks = []
            with self.connections_lock:
                for ws in list(self.connections):
                    try:
                        tasks.append(asyncio.create_task(ws.close(code=1000, reason="Server Shutdown")))
                    except Exception as e:
                        self.logger.warning(f"Failed to create close task: {e}")
            
            if tasks:
                done, pending = await asyncio.wait(tasks, timeout=5.0)
                for task in pending:
                    task.cancel()
                
                with self.connections_lock:
                    self.connections.clear()
        
        # 2. Close server
        if self.server:
            self.server.close()
            try:
                await asyncio.wait_for(self.server.wait_closed(), timeout=5.0)
            except asyncio.TimeoutError:
                self.logger.warning("Server shutdown timeout, forcing termination")

        # 3. Close socket
        if self._socket:
            try:
                self._socket.close()
            except Exception as e:
                self.logger.warning(f"Failed to close socket: {e}")
            finally:
                self._socket = None
        
        self.logger.info("Resource cleanup completed")

    def run_in_thread(self):
        """Run the server in a separate thread."""
        def start():
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.loop.run_until_complete(self.start_server())
            except Exception as e:
                self.logger.critical(f"Server thread exception: {e}")
            finally:
                tasks = asyncio.all_tasks(self.loop)
                for task in tasks:
                    task.cancel()
                self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                self.loop.close()
                self.logger.info("Event loop closed")

        self.server_thread = Thread(target=start, daemon=True)
        self.server_thread.start()
        self.logger.info("Server thread started")

    def stop(self):
        """Stop the server safely from any thread."""
        if not self._running:
            return
            
        self.logger.info("Received stop request...")
        self._running = False
        
        if self.loop and self.loop.is_running():
            try:
                # Submit shutdown task
                future = asyncio.run_coroutine_threadsafe(self._trigger_shutdown(), self.loop)
                future.result(timeout=10)  # Wait for 10 seconds
            except asyncio.TimeoutError:
                self.logger.error("Shutdown timeout, forcing stop")
            except Exception as e:
                self.logger.error(f"Error during shutdown: {e}")
            finally:
                if self.server_thread and self.server_thread.is_alive():
                    self.server_thread.join(timeout=2)
                
        self.logger.info("WebSocket server fully stopped")

    async def _trigger_shutdown(self):
        """Trigger the shutdown event to initiate server shutdown."""
        if self._shutdown_event and not self._shutdown_event.is_set():
            self._shutdown_event.set()

    async def stop_async(self):
        """Asynchronously stop the server."""
        if not self._running:
            return
            
        self._running = False
        self._shutdown_event.set()  # Trigger shutdown
        await self._cleanup_resources()