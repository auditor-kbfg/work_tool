from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import cgi
import urllib.parse

class FileUploadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # URL 디코딩
        parsed_path = urllib.parse.unquote(self.path)
        
        # 다운로드 요청 처리
        if parsed_path.startswith('/download/'):
            filename = parsed_path[10:]  # '/download/' 이후의 문자열
            self.handle_download(filename)
            return
            
        # 메인 페이지
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        # 업로드된 파일 목록 생성
        uploaded_files = ''
        for file in os.listdir('upload'):
            uploaded_files += f'<li><a href="/download/{urllib.parse.quote(file)}">{file}</a></li>\n'
        
        # HTML 페이지
        html = f'''
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                .progress-bar {{
                    width: 300px;
                    height: 20px;
                    background-color: #f0f0f0;
                    border-radius: 4px;
                    overflow: hidden;
                    margin: 10px 0;
                }}
                .progress {{
                    width: 0%;
                    height: 100%;
                    background-color: #4CAF50;
                    transition: width 0.3s ease;
                }}
                .file-item {{
                    margin: 10px 0;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }}
                #dropZone {{
                    width: 300px;
                    height: 200px;
                    border: 2px dashed #ccc;
                    text-align: center;
                    padding: 20px;
                    margin: 20px 0;
                }}
                #dropZone.dragover {{
                    background-color: #e1e1e1;
                    border-color: #999;
                }}
            </style>
        </head>
        <body>
            <h2>파일 업로드</h2>
            <div id="dropZone">
                파일을 여기에 드래그하거나<br><br>
                <input type="file" id="fileInput" multiple>
            </div>
            <div id="uploadList"></div>
            <button onclick="uploadFiles()">모든 파일 업로드</button>
            
            <h3>업로드된 파일 목록:</h3>
            <ul>
                {uploaded_files}
            </ul>

            <script>
                let filesToUpload = new Map();
                const dropZone = document.getElementById('dropZone');
                const fileInput = document.getElementById('fileInput');
                const uploadList = document.getElementById('uploadList');

                dropZone.addEventListener('dragover', (e) => {{
                    e.preventDefault();
                    dropZone.classList.add('dragover');
                }});

                dropZone.addEventListener('dragleave', (e) => {{
                    e.preventDefault();
                    dropZone.classList.remove('dragover');
                }});

                dropZone.addEventListener('drop', (e) => {{
                    e.preventDefault();
                    dropZone.classList.remove('dragover');
                    handleFiles(e.dataTransfer.files);
                }});

                fileInput.addEventListener('change', (e) => {{
                    handleFiles(e.target.files);
                }});

                function handleFiles(files) {{
                    for (let file of files) {{
                        if (!filesToUpload.has(file.name)) {{
                            filesToUpload.set(file.name, file);
                            addFileToList(file);
                        }}
                    }}
                }}

                function addFileToList(file) {{
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.innerHTML = `
                        <div>${{file.name}} (${{formatFileSize(file.size)}})</div>
                        <div class="progress-bar">
                            <div class="progress" id="progress-${{file.name}}"></div>
                        </div>
                        <div id="status-${{file.name}}">대기 중</div>
                    `;
                    uploadList.appendChild(fileItem);
                }}

                function formatFileSize(bytes) {{
                    if (bytes === 0) return '0 Bytes';
                    const k = 1024;
                    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
                    const i = Math.floor(Math.log(bytes) / Math.log(k));
                    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
                }}

                async function uploadFiles() {{
                    for (let [filename, file] of filesToUpload) {{
                        await uploadFile(file);
                    }}
                    // 업로드 완료 후 페이지 새로고침
                    location.reload();
                }}

                async function uploadFile(file) {{
                    const formData = new FormData();
                    formData.append('file', file);

                    const progressBar = document.getElementById(`progress-${{file.name}}`);
                    const statusDiv = document.getElementById(`status-${{file.name}}`);

                    try {{
                        const xhr = new XMLHttpRequest();
                        xhr.upload.onprogress = (e) => {{
                            if (e.lengthComputable) {{
                                const percentComplete = (e.loaded / e.total) * 100;
                                progressBar.style.width = percentComplete + '%';
                                statusDiv.textContent = `${{Math.round(percentComplete)}}% 완료`;
                            }}
                        }};

                        xhr.onload = () => {{
                            if (xhr.status === 200) {{
                                statusDiv.textContent = '업로드 완료';
                                progressBar.style.width = '100%';
                            }} else {{
                                statusDiv.textContent = '업로드 실패';
                            }}
                        }};

                        xhr.onerror = () => {{
                            statusDiv.textContent = '업로드 중 오류 발생';
                        }};

                        xhr.open('POST', '/upload');
                        xhr.send(formData);
                    }} catch (error) {{
                        statusDiv.textContent = '오류 발생: ' + error.message;
                    }}
                }}
            </script>
        </body>
        </html>
        '''
        self.wfile.write(html.encode())

    def do_POST(self):
        if self.path == '/upload':
            # Content-Type 확인
            content_type = self.headers.get('Content-Type')
            if not content_type:
                self.send_error(400, "Content-Type header missing")
                return
            
            # multipart/form-data 확인
            if not content_type.startswith('multipart/form-data'):
                self.send_error(400, "Wrong Content-Type")
                return

            # form 데이터 파싱
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': self.headers['Content-Type'],
                }
            )

            # 파일 필드 확인
            if 'file' not in form:
                self.send_error(400, "No file uploaded")
                return

            file_item = form['file']
            if not file_item.filename:
                self.send_error(400, "No file selected")
                return

            # 파일 저장
            filepath = os.path.join('upload', file_item.filename)
            with open(filepath, 'wb') as f:
                f.write(file_item.file.read())

            # 응답 전송
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f'파일 {file_item.filename}이(가) 성공적으로 업로드되었습니다.'.encode())

    def handle_download(self, filename):
        filepath = os.path.join('upload', filename)
        if not os.path.exists(filepath):
            self.send_error(404, "File not found")
            return
            
        # 파일 전송
        with open(filepath, 'rb') as f:
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(f.read())

def run_server(port=8000):
    # upload 폴더가 없으면 생성
    if not os.path.exists('upload'):
        os.makedirs('upload')
        
    # 서버 시작
    server_address = ('', port)
    httpd = HTTPServer(server_address, FileUploadHandler)
    print(f'서버가 포트 {port}에서 실행 중입니다...')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()