from flask import Flask, request, send_from_directory
import os

app = Flask(__name__)

# 업로드 폴더 설정
UPLOAD_FOLDER = 'upload'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 파일 크기 제한 없음
app.config['MAX_CONTENT_LENGTH'] = None

@app.route('/')
def index():
    return '''
    <html>
        <body>
            <h2>파일 업로드</h2>
            <form method="post" action="/upload" enctype="multipart/form-data">
                <input type="file" name="file">
                <input type="submit" value="업로드">
            </form>
            <h3>업로드된 파일 목록:</h3>
            <ul>
                ''' + '\n'.join([f'<li><a href="/download/{file}">{file}</a></li>' 
                               for file in os.listdir(UPLOAD_FOLDER)]) + '''
            </ul>
        </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return '파일이 없습니다', 400
    
    file = request.files['file']
    if file.filename == '':
        return '파일이 선택되지 않았습니다', 400
    
    filename = file.filename
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return f'파일 {filename}이(가) 성공적으로 업로드되었습니다. <a href="/">돌아가기</a>'

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
