import subprocess
import csv
import logging
import re

# 로깅 설정
logging.basicConfig(
    filename='forensic.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def read_logfile_info():
    try:
        # logfile_info.txt 파일로 출력 저장
        with open('logfile_info.txt', 'w') as logfile:
            subprocess.run(['fsutil', 'usn', 'readjournal', 'C:'], stdout=logfile, stderr=subprocess.PIPE, check=True)
            logging.info('Logfile info read successfully.')
    except Exception as e:
        logging.error(f'Error reading logfile_info.txt: {e}')

def read_unjournal_info():
    try:
        # unjrnl_info.txt 파일로 출력 저장
        with open('unjrnl_info.txt', 'w') as unjrnlfile:
            subprocess.run(['fsutil', 'usn', 'readjournal', 'C:'], stdout=unjrnlfile, stderr=subprocess.PIPE, check=True)
            logging.info('Unjournal info read successfully.')
    except Exception as e:
        logging.error(f'Error reading unjrnl_info.txt: {e}')

def extract_important_data(filename):
    important_data = []
    
    try:
        with open(filename, 'r') as file:
            for line in file:
                # 필요한 데이터 정제 (예시: 파일 이름, 날짜, 시간 등)
                match = re.search(r'(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.*)', line)
                if match:
                    date, time, operation, file_name, *rest = match.groups()
                    important_data.append([file_name, date, time, operation])
    except Exception as e:
        logging.error(f'Error extracting data from {filename}: {e}')
    
    return important_data

def save_to_csv(data, output_path):
    try:
        with open(output_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['File Name', 'Date', 'Time', 'Operation'])  # 헤더 추가
            writer.writerows(data)
        logging.info(f'Data has been saved to {output_path}')
    except Exception as e:
        logging.error(f'Error saving data to CSV: {e}')

def main():
    read_logfile_info()
    read_unjournal_info()

    # 데이터 추출 및 CSV 저장
    logfile_data = extract_important_data('logfile_info.txt')
    unjrnl_data = extract_important_data('unjrnl_info.txt')

    # 각각의 CSV 파일로 저장
    save_to_csv(logfile_data, 'logfile_data.csv')
    save_to_csv(unjrnl_data, 'unjrnl_data.csv')

if __name__ == "__main__":
    main()
