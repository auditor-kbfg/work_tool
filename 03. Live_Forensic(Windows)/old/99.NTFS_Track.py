import os
import pytsk3
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        print(f"Admin check error: {e}")
        return False

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

def main():
    if not is_admin():
        print("이 프로그램은 관리자 권한으로 실행해야 합니다.")
        return

    output_directory = os.path.dirname(os.path.abspath(__file__))

    extract_usnjournal(output_directory)
    extract_mft(output_directory)
    extract_logfile(output_directory)


if __name__ == "__main__":
    main()
