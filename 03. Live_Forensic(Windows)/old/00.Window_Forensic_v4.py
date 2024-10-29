import os
import socket
import json
import subprocess
import sys
import ctypes
import ctypes.wintypes
import shutil
import psutil
import platform
from datetime import datetime
import urllib.request
import time
import pytsk3

class Logger:
    def __init__(self, folder_path, filename):
        self.terminal = sys.stdout
        self.log_file_path = os.path.join(folder_path, filename)
        self.log = open(self.log_file_path, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

class MemoryDumper:
    def __init__(self, base_dir):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = base_dir
        
    def download_winpmem(self):
        winpmem_url = "https://github.com/Velocidex/WinPmem/releases/download/v4.0.rc1/winpmem_mini_x64_rc2.exe"
        winpmem_path = os.path.join(self.base_dir, "winpmem.exe")
        
        if not os.path.exists(winpmem_path):
            print("[*] WinPmem 다운로드 중...")
            try:
                urllib.request.urlretrieve(winpmem_url, winpmem_path)
                print("[+] WinPmem 다운로드 완료")
            except Exception as e:
                print(f"[!] WinPmem 다운로드 실패: {str(e)}")
                return None
        
        return winpmem_path
    
    def dump_physical_memory(self, output_dir):
        try:
            dump_path = os.path.join(output_dir, f"physical_memory_{self.timestamp}.raw")
            
            winpmem_path = self.download_winpmem()
            if not winpmem_path:
                return False
            
            total_memory = psutil.virtual_memory().total
            print(f"[*] 총 물리 메모리 크기: {total_memory / (1024**3):.2f} GB")
            print(f"[*] 메모리 덤프 시작... ({dump_path})")
            
            process = subprocess.Popen(
                [winpmem_path, dump_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            
            process.wait()
            
            if os.path.exists(dump_path) and os.path.getsize(dump_path) > 0:
                dump_size = os.path.getsize(dump_path)
                print(f"[+] 메모리 덤프 완료")
                print(f"[*] 덤프 파일 크기: {dump_size / (1024**3):.2f} GB")
                return True
            else:
                print("[!] 메모리 덤프 파일이 생성되지 않았거나 비어있습니다.")
                return False
                
        except Exception as e:
            print(f"[!] 메모리 덤프 중 오류 발생: {str(e)}")
            return False
    
    def collect_system_info(self, output_dir):
        info_path = os.path.join(output_dir, "system_info.txt")
        
        with open(info_path, 'w', encoding='utf-8') as f:
            f.write("=== 시스템 정보 ===\n")
            f.write(f"덤프 시작 시간: {datetime.now()}\n")
            f.write(f"OS: {platform.system()} {platform.release()}\n")
            f.write(f"OS 버전: {platform.version()}\n")
            f.write(f"시스템 아키텍처: {platform.machine()}\n")
            f.write(f"프로세서: {platform.processor()}\n")
            
            mem = psutil.virtual_memory()
            f.write(f"\n=== 메모리 정보 ===\n")
            f.write(f"총 물리 메모리: {mem.total / (1024**3):.2f} GB\n")
            f.write(f"사용 중인 메모리: {mem.used / (1024**3):.2f} GB\n")
            f.write(f"메모리 사용률: {mem.percent}%\n")
            
            f.write(f"\n=== 실행 중인 프로세스 ===\n")
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    f.write(f"PID: {info['pid']}, Name: {info['name']}, "
                           f"CPU: {info['cpu_percent']}%, MEM: {info['memory_percent']:.1f}%\n")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue


def create_results_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

def get_registry_info(folder_name):
    ps_command = 'Get-ChildItem -Path "HKLM:\\SOFTWARE" | Select-Object -Property Name, Property | ConvertTo-Json'
    
    result = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True)
    
    if result.returncode == 0:
        registry_info = json.loads(result.stdout)
        
        for item in registry_info:
            key_name = item['Name'].replace('\\', '_').replace(':', '')  
            file_path = os.path.join(folder_name, f"{key_name}.json")

            with open(file_path, 'w') as f:
                json.dump(item, f, indent=4)
                
            print(f"{key_name} 수집 완료...")
    else:
        print("Error:", result.stderr)

def export_event_logs_to_evtx(folder_name):
    logs = ['Application', 'System', 'Security']
    for log in logs:
        evtx_file_path = os.path.join(folder_name, f"{log}_logs.evtx")
        ps_command = f"wevtutil epl {log} {evtx_file_path}"

        try:
            subprocess.run(["powershell", "-Command", ps_command], check=True)
            print(f"{log} 로그를 EVTX 형식으로 수집 완료...")
        except subprocess.CalledProcessError as e:
            print(f"{log} 로그 수집 실패: {e}")

def collect_prefetch_files(folder_name):
    prefetch_path = r"C:\Windows\Prefetch"
    destination_path = os.path.join(folder_name)

    create_results_folder(destination_path)

    try:
        for file_name in os.listdir(prefetch_path):
            full_file_name = os.path.join(prefetch_path, file_name)
            if os.path.isfile(full_file_name):
                shutil.copy(full_file_name, destination_path)
                print(f"{file_name} 프리패치 파일 수집 완료...")
    except Exception as e:
        print("프리패치 파일 수집 실패:", str(e))

def collect_recycle_bin_files(folder_name):
    recycle_bin_path = r"C:\$Recycle.Bin"
    destination_path = os.path.join(folder_name)

    create_results_folder(destination_path)

    try:
        for entry in os.listdir(recycle_bin_path):
            full_entry_path = os.path.join(recycle_bin_path, entry)
            if os.path.isdir(full_entry_path):
                for file_name in os.listdir(full_entry_path):
                    full_file_name = os.path.join(full_entry_path, file_name)
                    if os.path.isfile(full_file_name):
                        shutil.copy(full_file_name, destination_path)
                        print(f"{file_name} 휴지통 파일 수집 완료...")
    except Exception as e:
        print("휴지통 파일 수집 실패:", str(e))

def collect_shortcut_files(folder_name):
    shortcut_locations = [
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu"),
        os.path.join("C:\\ProgramData", "Microsoft", "Windows", "Start Menu"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Recent"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Internet Explorer", "Quick Launch"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Internet Explorer", "Quick Launch", "User Pinned", "TaskBar"),
    ]
    destination_path = os.path.join(folder_name)

    create_results_folder(destination_path)

    try:
        for location in shortcut_locations:
            if os.path.exists(location):
                for file_name in os.listdir(location):
                    if file_name.endswith('.lnk'):
                        full_file_name = os.path.join(location, file_name)
                        shutil.copy(full_file_name, destination_path)
                        print(f"{file_name} 바로가기 파일 수집 완료...")
    except Exception as e:
        print("바로가기 파일 수집 실패:", str(e))

def collect_jump_list_files(folder_name):
    jump_list_path = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Recent")
    destination_path = os.path.join(folder_name)

    create_results_folder(destination_path)

    try:
        for file_name in os.listdir(jump_list_path):
            if file_name.endswith('.lnk'):
                full_file_name = os.path.join(jump_list_path, file_name)
                shutil.copy(full_file_name, destination_path)
                print(f"{file_name} 점프 리스트 파일 수집 완료...")
    except Exception as e:
        print("점프 리스트 파일 수집 실패:", str(e))

def is_browser_running(browser_names):
    """ 특정 브라우저가 실행 중인지 확인 """
    for process in psutil.process_iter(['name']):
        if process.info['name'] in browser_names:
            return True
    return False

def collect_web_artifacts(folder_name):
    web_artifacts_folder = os.path.join(folder_name)
    create_results_folder(web_artifacts_folder)

    # Chrome 웹 아티팩트 수집
    chrome_folder = os.path.join(web_artifacts_folder, "Chrome")
    create_results_folder(chrome_folder)

    # Chrome 캐시 수집
    if is_browser_running(['chrome.exe']):
        print("Chrome이 실행 중이므로 캐시 수집을 생략합니다.")
    else:
        chrome_cache_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cache")
        if os.path.exists(chrome_cache_path):
            shutil.copytree(chrome_cache_path, os.path.join(chrome_folder, "Chrome_Cache"), dirs_exist_ok=True)
            print("Chrome 웹 캐시 수집 완료...")

    # Chrome 히스토리, 쿠키, 다운로드 목록 수집
    chrome_history_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data", "Default", "History")
    if os.path.exists(chrome_history_path):
        shutil.copy2(chrome_history_path, os.path.join(chrome_folder, "Chrome_History"))
        print("Chrome 웹 히스토리 수집 완료...")
    
    chrome_cookies_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Cookies")
    if os.path.exists(chrome_cookies_path):
        shutil.copy2(chrome_cookies_path, os.path.join(chrome_folder, "Chrome_Cookies"))
        print("Chrome 웹 쿠키 수집 완료...")
    
    chrome_downloads_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data", "Default", "Downloads")
    if os.path.exists(chrome_downloads_path):
        shutil.copy2(chrome_downloads_path, os.path.join(chrome_folder, "Chrome_Downloads"))
        print("Chrome 다운로드 목록 수집 완료...")

    # Edge 웹 아티팩트 수집
    edge_folder = os.path.join(web_artifacts_folder, "Edge")
    create_results_folder(edge_folder)

    # Edge 캐시 수집
    if is_browser_running(['msedge.exe']):
        print("Edge가 실행 중이므로 캐시 수집을 생략합니다.")
    else:
        edge_cache_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cache")
        if os.path.exists(edge_cache_path):
            shutil.copytree(edge_cache_path, os.path.join(edge_folder, "Edge_Cache"), dirs_exist_ok=True)
            print("Edge 웹 캐시 수집 완료...")

    # Edge 히스토리, 쿠키, 다운로드 목록 수집
    edge_history_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "History")
    if os.path.exists(edge_history_path):
        shutil.copy2(edge_history_path, os.path.join(edge_folder, "Edge_History"))
        print("Edge 웹 히스토리 수집 완료...")

    edge_cookies_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Cookies")
    if os.path.exists(edge_cookies_path):
        shutil.copy2(edge_cookies_path, os.path.join(edge_folder, "Edge_Cookies"))
        print("Edge 웹 쿠키 수집 완료...")

    edge_downloads_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Edge", "User Data", "Default", "Downloads")
    if os.path.exists(edge_downloads_path):
        shutil.copy2(edge_downloads_path, os.path.join(edge_folder, "Edge_Downloads"))
        print("Edge 다운로드 목록 수집 완료...")

    # IE 웹 아티팩트 수집
    ie_folder = os.path.join(web_artifacts_folder, "IE")
    create_results_folder(ie_folder)

    try:
        # IE 캐시 수집
        if is_browser_running(['iexplore.exe']):
            print("IE가 실행 중이므로 캐시 수집을 생략합니다.")
        else:
            ie_cache_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Windows", "INetCache")
            if os.path.exists(ie_cache_path):
                shutil.copytree(ie_cache_path, os.path.join(ie_folder, "IE_Cache"), dirs_exist_ok=True)
                print("IE 웹 캐시 수집 완료...")

        # IE 히스토리, 쿠키, 다운로드 목록 수집
        ie_history_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Windows", "History")
        if os.path.exists(ie_history_path):
            shutil.copytree(ie_history_path, os.path.join(ie_folder, "IE_History"), dirs_exist_ok=True)
            print("IE 웹 히스토리 수집 완료...")

        ie_cookies_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Windows", "INetCookies")
        if os.path.exists(ie_cookies_path):
            shutil.copytree(ie_cookies_path, os.path.join(ie_folder, "IE_Cookies"), dirs_exist_ok=True)
            print("IE 웹 쿠키 수집 완료...")

        ie_downloads_path = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Windows", "INetDownloads")
        if os.path.exists(ie_downloads_path):
            shutil.copy2(ie_downloads_path, os.path.join(ie_folder, "IE_Downloads"))
            print("IE 다운로드 목록 수집 완료...")
    except Exception as e:
        print(f"IE 수집 중 오류 발생: {e}")


def collect_email_files(folder_name):
    email_folder = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Outlook")
    destination_path = os.path.join(folder_name)

    create_results_folder(destination_path)

    collected_files = []
    
    try:
        for file_name in os.listdir(email_folder):
            if file_name.endswith(('.ost', '.pst', '.msg')):
                full_file_name = os.path.join(email_folder, file_name)
                shutil.copy(full_file_name, destination_path)
                collected_files.append(file_name)
                print(f"{file_name} 이메일 파일 수집 완료...")
    except Exception as e:
        print("이메일 파일 수집 실패:", str(e))
    
    if not collected_files:
        print("이메일 파일이 없습니다.")

def collect_vss(folder_name):
    destination_path = os.path.join(folder_name)
    create_results_folder(destination_path)

    try:
        # VSS 스냅샷 목록을 가져옵니다.
        vss_snapshots = subprocess.run(["vssadmin", "list", "shadow"], capture_output=True, text=True)

        if vss_snapshots.returncode == 0:
            # VSS 스냅샷 정보를 파일로 저장합니다.
            snapshot_file_path = os.path.join(destination_path, "vss_snapshots.txt")
            with open(snapshot_file_path, 'w') as f:
                f.write(vss_snapshots.stdout)
            print("VSS 스냅샷 정보를 수집 완료...")
        else:
            print("VSS 스냅샷 수집 실패:", vss_snapshots.stderr)
    except Exception as e:
        print("VSS 수집 중 오류 발생:", str(e))

def extract_file(file_object, output_dir, file_name):
    output_path = os.path.join(output_dir, file_name)
    try:
        with open(output_path, 'wb') as f:
            # 512 바이트씩 읽어오며 파일 저장
            offset = 0
            while True:
                data = file_object.read_random(offset, 512)
                if not data:
                    break
                f.write(data)
                offset += 512
        print(f"Extracted {file_name} to {output_path}")
    except Exception as e:
        print(f"Error writing {file_name}: {e}")
        
def extract_mft(output_dir):
    try:
        volume = pytsk3.Img_Info(r"\\.\C:")  # C 드라이브
        fs = pytsk3.FS_Info(volume)

        # $MFT 파일 찾기
        mft_file = fs.open("/$MFT")
        if mft_file:
            extract_file(mft_file, output_dir, "$MFT")
        else:
            print("$MFT를 찾을 수 없습니다.")
    except Exception as e:
        print(f"Error extracting $MFT: {e}")

def extract_logfile(output_dir):
    try:
        volume = pytsk3.Img_Info(r"\\.\C:")  # C 드라이브
        fs = pytsk3.FS_Info(volume)

        # $LogFile 파일 찾기
        log_file = fs.open("/$LogFile")
        if log_file:
            extract_file(log_file, output_dir, "$LogFile")
        else:
            print("$LogFile를 찾을 수 없습니다.")
    except Exception as e:
        print(f"Error extracting $LogFile: {e}")

def extract_usnjournal(output_dir):
    try:
        volume = pytsk3.Img_Info(r"\\.\C:")  # C 드라이브
        fs = pytsk3.FS_Info(volume)

        # $UsnJrnl 파일 찾기
        usn_journal = fs.open("/$Extend/$UsnJrnl:$J")
        if usn_journal:
            extract_file(usn_journal, output_dir, "$UsnJrnl")
        else:
            print("$UsnJrnl를 찾을 수 없습니다.")
    except Exception as e:
        print(f"Error extracting $UsnJrnl: {e}")

            
def get_local_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return local_ip

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    script = os.path.abspath(sys.argv[0])
    command = f"Start-Process python -ArgumentList '{script}' -Verb RunAs"
    subprocess.run(["powershell", "-Command", command], shell=True)

if __name__ == "__main__":
    if os.name != 'nt':
        print("이 스크립트는 Windows에서만 실행 가능합니다.")
        sys.exit(1)

    if not is_admin():
        run_as_admin()
        sys.exit()

    ip_address = get_local_ip()
    results_folder = f"Windows_Live_Forensic_{ip_address}"
    
    # 기존 폴더들
    registry_folder = os.path.join(results_folder, "01.Registry")
    eventlog_folder = os.path.join(results_folder, "02.evtlog")
    prefetch_folder = os.path.join(results_folder, "03.Prefetch")
    recycle_bin_folder = os.path.join(results_folder, "04.Recycle_Bin")
    shortcuts_folder = os.path.join(results_folder, "05.Shortcuts")
    jump_list_folder = os.path.join(results_folder, "06.Jump_Lists")
    web_artifacts_folder = os.path.join(results_folder, "07.Web_Artifacts")
    email_folder = os.path.join(results_folder, "08.Email")
    vss_folder = os.path.join(results_folder, "09.VSS")
    memory_dump_folder = os.path.join(results_folder, "10.Memory_Dump")
    ntfs_folder = os.path.join(results_folder, "11.NTFS_Tracker")

    # 모든 폴더 생성
    create_results_folder(registry_folder)
    create_results_folder(eventlog_folder)
    create_results_folder(prefetch_folder)
    create_results_folder(recycle_bin_folder)
    create_results_folder(shortcuts_folder)
    create_results_folder(jump_list_folder)
    create_results_folder(web_artifacts_folder)
    create_results_folder(email_folder)
    create_results_folder(vss_folder)
    create_results_folder(memory_dump_folder)
    create_results_folder(ntfs_folder)

    # Logger 설정
    sys.stdout = Logger(results_folder, "forensic_log.txt")

    print("레지스트리 수집 중...")
    get_registry_info(registry_folder)
    print("레지스트리 수집 완료.")
    
    print("이벤트 로그 수집 중...")
    export_event_logs_to_evtx(eventlog_folder)
    print("이벤트 로그 수집 완료.")

    print("프리패치 파일 수집 중...")
    collect_prefetch_files(prefetch_folder)
    print("프리패치 파일 수집 완료.")
    
    print("휴지통 파일 수집 중...")
    collect_recycle_bin_files(recycle_bin_folder)
    print("휴지통 파일 수집 완료.")
    
    print("바로가기 파일 수집 중...")
    collect_shortcut_files(shortcuts_folder)
    print("바로가기 파일 수집 완료.")
    
    print("점프 리스트 파일 수집 중...")
    collect_jump_list_files(jump_list_folder)
    print("점프 리스트 파일 수집 완료.")

    print("웹 아티팩트 수집 중...")
    collect_web_artifacts(web_artifacts_folder)
    print("웹 아티팩트 수집 완료.")
    
    print("이메일 내역 수집 중...")
    collect_email_files(email_folder)
    print("이메일 내역 수집 완료.")

    print("VSS(볼륨 섀도우 복사본) 수집 중...")
    collect_vss(vss_folder)
    print("VSS(볼륨 섀도우 복사본) 수집 완료.")

    print("메모리 덤프 수집 중...")
    memory_dumper = MemoryDumper(memory_dump_folder)
    memory_dumper.collect_system_info(memory_dump_folder)
    if memory_dumper.dump_physical_memory(memory_dump_folder):
        print("메모리 덤프 수집 완료.")
    else:
        print("메모리 덤프 수집 실패.")

    print("NTFS 파일 수집 중...")
    extract_mft(ntfs_folder)
    extract_logfile(ntfs_folder)
    extract_usnjournal(ntfs_folder)
    print("NTFS 파일 수집 완료.")
    
    print("\n모든 포렌식 작업이 완료되었습니다.")