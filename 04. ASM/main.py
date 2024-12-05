import os
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO  # Flask-SocketIO에서 SocketIO를 임포트
from scripts.port_scan import PortScanner  # PortScanner 클래스를 scripts 폴더에서 import
from scripts.ip_management import IPManager

app = Flask(__name__)
ip_manager = IPManager()
socketio = SocketIO(app)

# PortScanner 인스턴스를 생성할 때 socketio 객체를 전달
port_scanner = PortScanner(socketio)
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/ip-list')
def ip_list():
    ip_list = ip_manager.get_all_ips()
    return render_template('ip_list.html', ip_list=ip_list)

@app.route('/ip-list/add', methods=['POST'])
def add_ip():
    ip_address = request.form.get('ip_address')
    description = request.form.get('description', '')
    
    success, message = ip_manager.add_ip(ip_address, description)
    
    return redirect(url_for('ip_list'))

@app.route('/ip-list/delete', methods=['POST'])
def delete_ip():
    ip_address = request.form.get('ip_address')
    
    success, message = ip_manager.remove_ip(ip_address)
    
    return redirect(url_for('ip_list'))

@app.route('/get-ip-list')
def get_ip_list():
    """API endpoint to get list of IPs for frontend"""
    try:
        ips = port_scanner.get_all_ips()
        return jsonify(ips)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/start-port-scan', methods=['POST'])
def start_port_scan():
    """Start a manual port scan"""
    try:
        # 디버깅을 위해 요청 데이터 출력
        print("Received scan request:", request.json)
        
        data = request.json or {}
        scan_type = data.get('scan_type', 'all')
        start_port = int(data.get('start_port', 1))
        end_port = int(data.get('end_port', 1024))
        
        results = []
        if scan_type == 'specific':
            ip = data.get('ip')
            if not ip:
                return jsonify({'error': 'IP 주소를 지정해야 합니다.'}), 400
            results = port_scanner.scan_ports(ip, (start_port, end_port))
        else:
            results = port_scanner.scan_all_ips((start_port, end_port))
        
        # 결과 저장
        port_scanner.save_scan_results(results)
        
        # 디버깅을 위해 결과 출력
        print(f"Scan results: {results}")
        
        return jsonify(results), 200
    except Exception as e:
        # 오류 상세 출력
        import traceback
        print("Error during port scan:")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/start-background-scan', methods=['POST'])
def start_background_scan():
    """Start a background port scan"""
    try:
        data = request.json or {}
        start_port = int(data.get('start_port', 1))
        end_port = int(data.get('end_port', 1024))
        
        port_scanner.start_background_scan((start_port, end_port))
        return jsonify({'message': '백그라운드 스캔 시작'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-scan-results')
def get_scan_results():
    """Retrieve the most recent port scanning results"""
    try:
        conn = port_scanner._get_scan_results_connection()
        cursor = conn.cursor()
        
        # 가장 최근 스캔 시간 찾기
        cursor.execute('SELECT MAX(scan_time) FROM scan_results')
        latest_scan_time = cursor.fetchone()[0]
        
        if latest_scan_time:
            # 최근 스캔 시간의 결과만 가져오기
            cursor.execute('''
                SELECT * FROM scan_results 
                WHERE scan_time = ? 
                ORDER BY id
            ''', (latest_scan_time,))
            results = cursor.fetchall()
        else:
            # 결과가 없는 경우 빈 리스트 반환
            results = []
        
        # Convert results to list of dictionaries
        columns = ['id', 'ip', 'port', 'protocol', 'service', 'server', 'scan_time']
        scan_results = [dict(zip(columns, result)) for result in results]
        
        return jsonify(scan_results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/port-scan')
def port_scan_route():
    return render_template('port_scan.html')

@app.route('/server-info')
def server_info_route():
    return render_template('server_info.html')

@app.route('/options')
def options_route():
    return render_template('options.html')

@app.route('/put')
def put_route():
    return render_template('put.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)