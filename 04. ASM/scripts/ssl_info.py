import ssl
import socket
from datetime import datetime

def get_ssl_certificate_info(domain):
    """도메인의 SSL 인증서 정보를 조회합니다."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()

        start_date = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
        end_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')

        # 발급자 정보 처리
        issuer = ''
        if 'issuer' in cert:
            issuer_parts = cert['issuer']
            issuer = ', '.join(
                f"{key}={value}" for part in issuer_parts for key, value in part
            )

        return {
            'domain': domain,
            'start_date': start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'end_date': end_date.strftime('%Y-%m-%d %H:%M:%S'),
            'issuer': issuer
        }
    except Exception as e:
        return {'error': str(e)}
