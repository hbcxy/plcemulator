from flask import Flask, request, jsonify
import os

app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not file.filename.lower().endswith('.xml'):
        return jsonify({'error': 'Only XML files are allowed'}), 400

    # 修正路径：向上两级找到 Blink 目录
    blink_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'Blink'))
    os.makedirs(blink_dir, exist_ok=True)
    plcxml_path = os.path.join(blink_dir, 'plc.xml')
    
    file.save(plcxml_path)

    return jsonify({'message': 'File uploaded and saved successfully', 'filename': 'plc.xml'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)