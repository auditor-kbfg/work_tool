import socket
import sqlite3
import threading
import time
from flask_socketio import SocketIO, emit
from concurrent.futures import ThreadPoolExecutor
import socket

class PortScanner:
    def __init__(self, socketio, ip_db_path='ip_list.db', scan_results_db_path='scan_results.db', max_threads=50):
        self.socketio = socketio
        self.ip_db_path = ip_db_path
        self.scan_results_db_path = scan_results_db_path
        self.max_threads = max_threads
        self._create_scan_results_table()
        self.scanning = False

    def _get_ip_connection(self):
        """IP 목록 데이터베이스 연결"""
        return sqlite3.connect(self.ip_db_path)
        
    def get_scan_results(self):
        """가장 최근 스캔 결과 가져오기"""
        conn = self._get_scan_results_connection()
        cursor = conn.cursor()
        
        # 최근 스캔 시간의 결과만 가져오기
        cursor.execute('''
            SELECT * FROM scan_results 
            WHERE scan_time = (
                SELECT MAX(scan_time) FROM scan_results
            )
            ORDER BY id
        ''')
        
        results = cursor.fetchall()
        columns = ['id', 'ip', 'port', 'protocol', 'service', 'server', 'scan_time']
        return [dict(zip(columns, result)) for result in results]

    def _get_scan_results_connection(self):
        """스캔 결과 데이터베이스 연결"""
        return sqlite3.connect(self.scan_results_db_path)

    def _create_scan_results_table(self):
        """스캔 결과 테이블 생성"""
        with self._get_scan_results_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    protocol TEXT,
                    service TEXT,
                    server TEXT,
                    scan_time DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def get_all_ips(self):
        """모든 IP 주소 가져오기"""
        try:
            with self._get_ip_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT ip_address FROM ip_list')
                return [ip[0] for ip in cursor.fetchall()]
        except sqlite3.OperationalError:
            # IP 리스트 테이블이 없는 경우 빈 리스트 반환
            return []

    def is_port_open(self, ip, port):
        """특정 포트가 열려있는지 확인"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def get_port_details(self, ip, port):
        """포트의 상세 정보 가져오기 (기본값 사용)"""
        return {
            'ip': ip,
            'port': port,
            'protocol': 'tcp',
            'service': 'Unknown',
            'server': 'Unknown'
        }

    def scan_ports(self, ip, port_range=(1, 1024)):
        """특정 IP의 포트 스캔"""
        results = []
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_port = {executor.submit(self.is_port_open, ip, port): port for port in range(port_range[0], port_range[1] + 1)}
            
            for future in future_to_port:
                port = future_to_port[future]
                try:
                    if future.result():
                        port_details = self.get_port_details(ip, port)
                        results.append(port_details)
                        self.socketio.emit('scan_progress', {'ip': ip, 'port': port, 'progress': 100 * (port - port_range[0] + 1) / (port_range[1] - port_range[0] + 1)})
                except Exception as e:
                    print(f"Error scanning port {port} on {ip}: {e}")
        
        return results

    def save_scan_results(self, results):
        """스캔 결과 저장"""
        with self._get_scan_results_connection() as conn:
            cursor = conn.cursor()
            for result in results:
                cursor.execute('''
                    INSERT INTO scan_results 
                    (ip, port, protocol, service, server, scan_time) 
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    result['ip'], 
                    result['port'], 
                    result.get('protocol', ''),
                    result.get('service', ''),
                    result.get('server', '')
                ))
            conn.commit()

    def scan_all_ips(self, port_range=(1, 1024)):
        """모든 IP 대상으로 포트 스캔"""
        all_results = []
        ips = self.get_all_ips()
        
        if not ips:
            print("경고: IP 목록이 비어있습니다.")
            return all_results
        
        for ip in ips:
            print(f"Scanning IP: {ip}")
            self.socketio.emit('scan_status', {'status': f'Scanning {ip}...'})
            ip_results = self.scan_ports(ip, port_range)
            all_results.extend(ip_results)
            self.save_scan_results(ip_results)
            self.socketio.emit('scan_status', {'status': f'Completed scanning {ip}'})
        
        self.socketio.emit('scan_status', {'status': 'All scans completed.'})
        return all_results

    def start_background_scan(self, port_range=(1, 65535)):
        """백그라운드 스레드로 스캔 시작"""
        if not self.scanning:
            self.scanning = True
            scan_thread = threading.Thread(target=self.scan_all_ips, args=(port_range,))
            scan_thread.start()
        else:
            print("Scan already in progress.")

# Flask 웹 서버 및 SocketIO 설정
from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

scanner = PortScanner(socketio)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start-port-scan', methods=['POST'])
def start_scan():
    start_port = 1
    end_port = 1024
    socketio.emit('scan_status', {'status': 'Scan started...'})
    scanner.start_background_scan((start_port, end_port))
    return "Scan started"

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")

if __name__ == '__main__':
    socketio.run(app, debug=True)
