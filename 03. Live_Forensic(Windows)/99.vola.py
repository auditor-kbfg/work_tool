import subprocess

# 메모리 덤프 파일 경로
dump_path = r"C:\Users\superuser\Downloads\Live_Forensic_Windows\memory_dump.dmp"

# Volatility 3 pslist 플러그인 실행
subprocess.run(["python", "-m", "volatility3", "-f", dump_path, "windows.pslist"])
