import sqlite3
import ipaddress

class IPManager:
    def __init__(self, db_path='ip_list.db'):
        """
        IP 관리를 위한 데이터베이스 초기화
        
        테이블 구조:
        - id: 고유 식별자
        - ip_address: IP 주소
        - description: IP에 대한 설명
        - status: IP의 상태 (active, inactive 등)
        - last_seen: 마지막으로 확인된 시간
        """
        self.db_path = db_path
        self._create_table()

    def _get_connection(self):
        """데이터베이스 연결"""
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        """IP 목록 테이블 생성"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ip_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT UNIQUE NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'active',
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def validate_ip(self, ip):
        """IP 주소 유효성 검증"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def add_ip(self, ip_address, description=''):
        """
        새로운 IP 주소 추가
        
        :param ip_address: 추가할 IP 주소
        :param description: IP에 대한 설명 (선택사항)
        :return: 성공 여부와 메시지
        """
        if not self.validate_ip(ip_address):
            return False, "유효하지 않은 IP 주소입니다."
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO ip_list (ip_address, description) 
                    VALUES (?, ?)
                ''', (ip_address, description))
                conn.commit()
            return True, "IP 주소가 성공적으로 추가되었습니다."
        except sqlite3.IntegrityError:
            return False, "이미 존재하는 IP 주소입니다."

    def remove_ip(self, ip_address):
        """
        IP 주소 제거
        
        :param ip_address: 제거할 IP 주소
        :return: 성공 여부와 메시지
        """
        if not self.validate_ip(ip_address):
            return False, "유효하지 않은 IP 주소입니다."
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ip_list WHERE ip_address = ?', (ip_address,))
            if cursor.rowcount > 0:
                conn.commit()
                return True, "IP 주소가 성공적으로 삭제되었습니다."
            else:
                return False, "해당 IP 주소를 찾을 수 없습니다."

    def update_ip_description(self, ip_address, new_description):
        """
        IP 주소의 설명 업데이트
        
        :param ip_address: 업데이트할 IP 주소
        :param new_description: 새로운 설명
        :return: 성공 여부와 메시지
        """
        if not self.validate_ip(ip_address):
            return False, "유효하지 않은 IP 주소입니다."
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE ip_list 
                SET description = ?, last_seen = CURRENT_TIMESTAMP 
                WHERE ip_address = ?
            ''', (new_description, ip_address))
            
            if cursor.rowcount > 0:
                conn.commit()
                return True, "IP 주소 설명이 업데이트되었습니다."
            else:
                return False, "해당 IP 주소를 찾을 수 없습니다."

    def get_all_ips(self):
        """
        모든 IP 주소 목록 반환
        
        :return: IP 주소 목록
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT ip_address, description, status, last_seen FROM ip_list')
            return cursor.fetchall()

# 사용 예시
def main():
    ip_manager = IPManager()
    
    # IP 추가
    result, message = ip_manager.add_ip('192.168.1.100', '메인 서버')
    print(message)
    
    # IP 목록 조회
    ips = ip_manager.get_all_ips()
    for ip in ips:
        print(f"IP: {ip[0]}, 설명: {ip[1]}, 상태: {ip[2]}, 마지막 확인: {ip[3]}")
    
    # IP 제거
    result, message = ip_manager.remove_ip('192.168.1.100')
    print(message)

if __name__ == '__main__':
    main()