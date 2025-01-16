import os
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO  # Flask-SocketIO에서 SocketIO를 임포트
from scripts.port_scan import PortScanner  # PortScanner 클래스를 scripts 폴더에서 import
from scripts.ip_management import IPManager
import csv
from flask import send_file, Flask, render_template, request, jsonify
from flask_cors import CORS
from scripts.ssl_info import check_ssl_for_scanned_ports, get_ssl_certificate_info, get_ssl_info_with_tls_versions # ssl_info.py에서 함수 가져오기


app = Flask(__name__)
ip_manager = IPManager()
socketio = SocketIO(app)
CORS(app) 

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
    try:
        conn = port_scanner._get_scan_results_connection()
        cursor = conn.cursor()  # 커서를 명확히 정의
        cursor.execute('''
            SELECT ip, port, protocol, web_service, server_info, scan_time 
            FROM scan_results
        ''')
        results = cursor.fetchall()

        columns = ['ip', 'port', 'protocol', 'web_service', 'server_info', 'scan_time']
        scan_results = [dict(zip(columns, row)) for row in results]

        conn.close()
        return jsonify(scan_results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

      
@app.route('/export-scan-results', methods=['GET', 'POST'])  # GET, POST 메서드 모두 허용
def export_scan_results():
    """최근 스캔 결과를 CSV 파일로 내보내기"""
    try:
        conn = port_scanner._get_scan_results_connection()
        cursor = conn.cursor()
        
        # 가장 최근 스캔 시간 찾기
        cursor.execute('SELECT MAX(scan_time) FROM scan_results')
        latest_scan_time = cursor.fetchone()[0]
        
        if latest_scan_time:
            # 최근 스캔 시간의 결과만 가져오기
            cursor.execute('''
                SELECT ip, port, protocol, web_service, server_info, scan_time
                FROM scan_results
                WHERE scan_time = ?
                ORDER BY id
            ''', (latest_scan_time,))
            results = cursor.fetchall()
        else:
            # 결과가 없는 경우 빈 리스트 반환
            results = []
        
        # CSV 파일 생성 경로 설정
        export_dir = os.path.join(os.path.dirname(__file__), 'exports')
        os.makedirs(export_dir, exist_ok=True)
        csv_filename = os.path.join(export_dir, f'scan_results_{latest_scan_time.replace(":", "-")}.csv')
        
        # CSV 파일 작성
        with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            csv_writer = csv.writer(csvfile)
            # 헤더 작성
            csv_writer.writerow(['IP 주소', '포트', '프로토콜', '웹서비스', '서버 정보', '스캔 시간'])
            
            # 데이터 작성
            csv_writer.writerows(results)
        
        # CSV 파일 전송
        return send_file(csv_filename, 
                         mimetype='text/csv', 
                         as_attachment=True, 
                         download_name=os.path.basename(csv_filename))
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@app.route('/delete-scan-results', methods=['GET', 'POST'])
def delete_scan_results():
    """DB에서 모든 스캔 결과 삭제"""
    try:
        conn = port_scanner._get_scan_results_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM scan_results')
        conn.commit()
        conn.close()
        return jsonify({'message': '모든 스캔 결과가 삭제되었습니다.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/port-scan')
def port_scan_route():
    return render_template('port_scan.html')

@app.route('/ssl-info')
def ssl_info_page():
    return render_template('ssl_info.html')

@app.route('/get-ssl-info')
def get_ssl_info():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({'error': '도메인을 입력하세요.'}), 400

    result = get_ssl_certificate_info(domain)
    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result)



@app.route('/check-ssl-for-scanned-ips', methods=['POST', 'GET'])
def check_ssl_for_scanned_ips():
    """포트 스캔된 IP와 포트에 대해 SSL/TLS 버전 점검"""
    try:
        # 포트 스캔 결과 가져오기
        scan_results = port_scanner.get_scan_results()  # IP, 포트 포함
        print("Scan Results from Port Scanner:", scan_results)
        # 새 함수로 점검 수행
        ssl_results = check_ssl_for_scanned_ports(scan_results)
        print("SSL Results to Return:", ssl_results)

        return jsonify(ssl_results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/get-ssl-info-with-tls')
def get_ssl_info_with_tls():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({'error': '도메인을 입력하세요.'}), 400

    result = get_ssl_info_with_tls_versions(domain)
    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result)




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)