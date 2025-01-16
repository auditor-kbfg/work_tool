import socket
import sqlite3
import threading
import time
import datetime
import requests
from urllib.parse import urlparse
from flask_socketio import SocketIO, emit
from concurrent.futures import ThreadPoolExecutor
import traceback
import pytz


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
        """
        # 가장 최근 스캔 결과 가져오기
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
        columns = ['id', 'ip', 'port', 'protocol', 'web_service', 'server_info', 'scan_time']
        return [dict(zip(columns, result)) for result in results]
         """
        
        #모든 스캔 결과 가져오기
        conn = self._get_scan_results_connection()
        cursor = conn.cursor()

        # 모든 스캔 결과 가져오기
        cursor.execute('SELECT * FROM scan_results ORDER BY id')
        results = cursor.fetchall()

        columns = ['id', 'ip', 'port', 'protocol', 'web_service', 'server_info', 'scan_time']
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
                    web_service TEXT,  
                    server_info TEXT,  
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
        if not ip:
            raise ValueError("IP 주소는 필수입니다.")

        web_service, server_info = self.check_web_service(ip, port)
        return {
            'ip': ip,
            'port': port,
            'protocol': 'tcp',
            'web_service': web_service,
            'server_info': server_info
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
        
    def check_web_service(self, ip, port):
        """웹 서비스 확인 및 서버 정보 추출"""
        web_services = ['http', 'https']
        server_info = 'Unknown'
        web_service = 'No'

        for protocol in web_services:
            try:
                url = f"{protocol}://{ip}:{port}"
                response = requests.get(url, timeout=3, allow_redirects=True)
                
                web_service = protocol.upper()
                server_info = response.headers.get('Server', 'Unknown')
                
                # 서버 정보가 없으면 다른 헤더로 대체
                if server_info == 'Unknown':
                    server_info = response.headers.get('X-Powered-By', 'Unknown')
                
                break  # 첫 번째 성공한 프로토콜로 결정
            except Exception:
                continue

        return web_service, server_info
            

    def save_scan_results(self, results):
        try:
            from datetime import datetime
            import pytz

            # 서울 시간 설정
            seoul_tz = pytz.timezone('Asia/Seoul')
            current_time = datetime.now(seoul_tz)

            with self._get_scan_results_connection() as conn:
                cursor = conn.cursor()
                for result in results:
                    ip = result.get('ip')
                    if not ip:
                        raise ValueError("IP 주소는 필수입니다.")

                    cursor.execute('''
                        INSERT OR IGNORE INTO scan_results 
                        (ip, port, protocol, web_service, server_info, scan_time) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        ip,
                        result.get('port', 0),
                        result.get('protocol', ''),
                        result.get('web_service', 'No'),
                        result.get('server_info', 'Unknown'),
                        current_time.strftime('%Y-%m-%d %H:%M:%S')
                    ))
                conn.commit()
        except sqlite3.OperationalError as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error saving scan results: {e}")

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
