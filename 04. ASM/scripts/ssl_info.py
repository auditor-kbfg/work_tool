import ssl
import socket
from datetime import datetime
import warnings
#import logging
import sqlite3

DB_PATH = "ssl_scan_results.db"

def initialize_ssl_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ssl_results (
            ip TEXT,
            port INTEGER,
            tls_v1_0 TEXT,
            tls_v1_1 TEXT,
            tls_v1_2 TEXT,
            tls_v1_3 TEXT,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_ssl_results(results):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for result in results:
        cursor.execute('''
            INSERT INTO ssl_results (ip, port, tls_v1_0, tls_v1_1, tls_v1_2, tls_v1_3)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            result['ip'],
            result['port'],
            result['tls_support'].get('TLSv1_0', 'Unknown'),
            result['tls_support'].get('TLSv1_1', 'Unknown'),
            result['tls_support'].get('TLSv1_2', 'Unknown'),
            result['tls_support'].get('TLSv1_3', 'Unknown')
        ))
    conn.commit()
    conn.close()

# DB 초기화 실행
initialize_ssl_db()

# 경고 메시지 숨기기
warnings.filterwarnings("ignore", category=DeprecationWarning)

#로그설정
#logging.basicConfig(filename="ssl_errors.log", level=logging.ERROR, format="%(asctime)s - %(message)s")


def check_ssl_for_scanned_ports(scan_results):
    tls_versions = {
        "TLSv1_0": ssl.PROTOCOL_TLSv1,
        "TLSv1_1": ssl.PROTOCOL_TLSv1_1,
        "TLSv1_2": ssl.PROTOCOL_TLSv1_2,
        "TLSv1_3": ssl.PROTOCOL_TLS_CLIENT  # TLS 1.3은 기본 컨텍스트 사용
    }

    results = []

    for result in scan_results:
        ip = result['ip']
        port = result['port']
        tls_support = {}

        for version, protocol in tls_versions.items():
            try:
                # TLS 1.3은 기본 컨텍스트 사용
                if version == "TLSv1_3":
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                else:
                    context = ssl.SSLContext(protocol)
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE

                # IP와 포트를 사용하여 연결
                with socket.create_connection((ip, port), timeout=5) as sock:
                    with context.wrap_socket(sock, server_hostname=ip):
                        tls_support[version] = "Supported"
            except ssl.SSLError:
                tls_support[version] = "Not Supported"
            except Exception as e:
                #logging.error(f"Error for {ip}:{port} - TLS Version {version}: {str(e)}")
                tls_support[version] = "Error"

        results.append({
            "ip": ip,
            "port": port,
            "tls_support": tls_support,
        })

    return results


def get_ssl_certificate_info(domain):
    """도메인의 SSL 인증서 정보를 조회합니다."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

        start_date = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
        end_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')

        issuer = ', '.join(
            f"{key}={value}" for part in cert['issuer'] for key, value in part
        )

        return {
            'domain': domain,
            'start_date': start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'end_date': end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'issuer': issuer
        }
    except Exception as e:
        return {'error': str(e)}

def check_tls_versions(domain):

    tls_versions = {
        "TLS 1.3": ssl.TLSVersion.TLSv1_3,
        "TLS 1.2": ssl.TLSVersion.TLSv1_2,
        "TLS 1.1": ssl.TLSVersion.TLSv1_1,
        "TLS 1.0": ssl.TLSVersion.TLSv1
    }

    results = {}

    for version_name, version in tls_versions.items():
        try:
            context = ssl.create_default_context()
            context.minimum_version = version
            context.maximum_version = version
            with socket.create_connection((domain, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=domain):
                    results[version_name] = "Supported"
        except ssl.SSLError:
            results[version_name] = "Not Supported"
        except Exception as e:
            results[version_name] = f"Error: {str(e)}"

    return results


def get_ssl_info_with_tls_versions(domain):
    """SSL 인증서 정보와 TLS 버전 지원 여부를 함께 조회합니다."""
        

    cert_info = get_ssl_certificate_info(domain)
    tls_versions = check_tls_versions(domain)

    if 'error' in cert_info:
        return cert_info

    cert_info['tls_versions'] = tls_versions
    return cert_info



if __name__ == "__main__":
    domain = input("도메인을 입력하세요: ").strip()
    info = get_ssl_info_with_tls_versions(domain)
    print(info)
