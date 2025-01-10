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
    """웹사이트에서 지원하는 SSL/TLS 버전을 확인합니다."""
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

def check_tls_versions(domain):
    """웹사이트 또는 IP:포트에서 지원하는 SSL/TLS 버전을 확인합니다."""
    tls_versions = {
        "TLS 1.3": ssl.TLSVersion.TLSv1_3,
        "TLS 1.2": ssl.TLSVersion.TLSv1_2,
        "TLS 1.1": ssl.TLSVersion.TLSv1_1,
        "TLS 1.0": ssl.TLSVersion.TLSv1
    }

    results = {}
    host, _, port = domain.partition(':')
    port = int(port) if port else 443

    for version_name, version in tls_versions.items():
        try:
            context = ssl.create_default_context()
            context.minimum_version = version
            context.maximum_version = version
            with socket.create_connection((host, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=host):
                    results[version_name] = "Supported"
        except (ssl.SSLError, socket.error):
            # 오류가 발생하면 "지원 안 함"으로 처리
            results[version_name] = "Not Supported"

    return results



def get_ssl_info_with_tls_versions(domain):
    """SSL 인증서 정보와 TLS 버전 지원 여부를 함께 조회합니다."""
    cert_info = get_ssl_certificate_info(domain)
    tls_versions = check_tls_versions(domain)

    if 'error' in cert_info:
        return cert_info

    cert_info['tls_versions'] = tls_versions
    return cert_info

# 테스트용 코드
if __name__ == "__main__":
    domain = input("도메인을 입력하세요: ").strip()
    info = get_ssl_info_with_tls_versions(domain)
    print(info)
