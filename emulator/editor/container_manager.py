from flask import Flask, request, jsonify
import docker
import random
import subprocess

app = Flask(__name__)
client = docker.from_env()

def get_random_port(base=9000, offset=1000):
    """随机生成端口"""
    return base + random.randint(0, offset)

# -------------------- 创建容器 --------------------
@app.route('/containers/create', methods=['POST'])
def create_container():
    data = request.get_json()
    name = data.get("name", f"plc_{random.randint(1000,9999)}")
    cpus = data.get("cpus", "2")
    memory = data.get("memory", "2g")
    ports = data.get("ports", {})

    # 支持手动指定端口，没指定则自动分配
    flask_port = ports.get("flask", get_random_port(9100, 100))
    zmq_port = ports.get("zmq", get_random_port(9300, 100))
    ws_port = ports.get("ws", get_random_port(9500, 100))

    try:
        container = client.containers.run(
            "plcemulator",
            name=name,
            detach=True,
            tty=True,
            ports={
                "5000/tcp": flask_port,
                "5555/tcp": zmq_port,
                "8765/tcp": ws_port
            },
            cpuset_cpus="0-1",
            mem_limit=memory
        )
        return jsonify({
            "status": "success",
            "message": f"{name} created",
            "id": container.id,
            "ports": {"flask": flask_port, "zmq": zmq_port, "ws": ws_port}
        })
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# -------------------- 容器列表 --------------------
@app.route('/containers/list', methods=['GET'])
def list_containers():
    containers = [{
        "id": c.id,
        "name": c.name,
        "status": c.status,
        "ports": {k: v[0]["HostPort"] for k, v in c.attrs['NetworkSettings']['Ports'].items() if v}
    } for c in client.containers.list(all=True)]
    return jsonify(containers)

# -------------------- 停止容器 --------------------
@app.route('/containers/stop', methods=['POST'])
def stop_container():
    data = request.get_json()
    name = data.get('name')
    try:
        container = client.containers.get(name)
        container.stop()
        return jsonify({"status": "success", "message": f"{name} stopped"})
    except docker.errors.NotFound:
        return jsonify({"status": "error", "message": f"{name} not found"}), 404

# -------------------- 删除容器 --------------------
@app.route('/containers/delete', methods=['POST'])
def delete_container():
    data = request.get_json()
    name = data.get('name')
    try:
        container = client.containers.get(name)
        container.remove(force=True)
        return jsonify({"status": "success", "message": f"{name} deleted"})
    except docker.errors.NotFound:
        return jsonify({"status": "error", "message": f"{name} not found"}), 404

# -------------------- 获取端口映射 --------------------
@app.route('/containers/get_ports', methods=['POST'])
def get_ports():
    data = request.get_json()
    name = data.get('name')
    try:
        container = client.containers.get(name)
        ports = container.attrs['NetworkSettings']['Ports']
        mapped = {k: v[0]['HostPort'] for k, v in ports.items() if v}
        return jsonify({"ports": mapped})
    except docker.errors.NotFound:
        return jsonify({"status": "error", "message": f"{name} not found"}), 404

# -------------------- 获取日志 --------------------
@app.route('/containers/logs', methods=['POST'])
def container_logs():
    data = request.get_json()
    name = data.get('name')
    tail = int(data.get('tail', 100))  # 默认显示最近100行
    try:
        container = client.containers.get(name)
        logs = container.logs(tail=tail).decode('utf-8')
        return jsonify({"status": "success", "logs": logs})
    except docker.errors.NotFound:
        return jsonify({"status": "error", "message": f"{name} not found"}), 404

# -------------------- 启动 Flask --------------------
if __name__ == '__main__':
    import sys
    port = 8000  # 默认管理服务端口
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ 端口号必须是整数")
            sys.exit(1)
    print(f"🚀 Container manager running on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
