import json
import socket
import os
from termcolor import colored
import time
import hashlib
import re
import uuid

STATIC_FOLDER = './static'
UPLOAD_FOLDER = './upload'
TOKEN = hashlib.sha256('token'.encode('utf-8')).hexdigest()
CONTENT_TYPE = {
    'txt': 'text/plain',
    'bin': 'application/octet-stream',
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'pdf': 'application/pdf'
}

class Cookie:
    def __init__(self, sid=None, expires=None, path=None, cookie_str=None):
        self.cookie = {}
        if cookie_str:
            self.cookie = self.parse_cookie(cookie_str)
        else:
            if sid:
                self.cookie['sid'] = sid
            if expires:
                self.cookie['expires'] = expires
            if path:
                self.cookie['path'] = path
        self.cookie['HttpOnly'] = True
        
    def parse_cookie(self, cookie_str):
        cookie = {}
        for c in cookie_str.split('; '):
            key, value = c.split('=')
            cookie[key] = value
        return cookie
    
    def __getitem__(self, key):
        return self.cookie[key]
    
    def __setitem__(self, key, value):
        self.cookie[key] = value

    def __str__(self):
        cookie_str = ''
        for key, value in self.cookie.items():
            cookie_str += f'{key}={value}; '
        return cookie_str[:-2]
    
    def isValid(self, token):
        return self.cookie['sid'] == TOKEN

def create_response(status_code, headers, body=None):
    """建立回應訊息"""
    response = "HTTP/1.1 {}\r\n".format(status_code)
    for header in headers:
        response += "{}: {}\r\n".format(header[0], header[1])
    response += "\r\n"
    if body:
        if type(body) != str:
            return response.encode() + body
        else:
            response += body
    return response.encode()

def parse_request(request):
    """解析請求訊息"""
    request_lines = request.split("\r\n")
    method, path, _ = request_lines[0].split(" ")
    headers = {}

    for line in request_lines[1:]:
        if not line:
            break
        key, value = line.split(": ")
        headers[key] = value

    body = None
    if "\r\n\r\n" in request:
        request_lines = request.split("\r\n\r\n", 1)
        body = ''.join(request_lines[1:])

    return method, path, headers, body

def parse_body(body, content_type):
    """解析 body"""
    if body is None:
        raise ValueError
    data = {}
    if content_type.startswith('multipart/form-data'):
        boundary = content_type.split('; ')[1].split('=')[1]
        # parse form data
        raw_form_data = body.strip().split(f'--{boundary}')[1:-1]
        file_regex = rf'\r\nContent-Disposition: form-data; name="file"; filename="(?P<filename>.*)"\r\nContent-Type: (?P<content_type>.*)\r\n\r\n(?P<content>.*)\r\n'
        para_regex = rf'\r\nContent-Disposition: form-data; name="(?P<name>.*)"\r\n\r\n(?P<value>.*)\r\n'

        for raw_data in raw_form_data:
            if re.match(file_regex, raw_data):
                filename = re.match(file_regex, raw_data).group('filename')
                content_type = re.match(file_regex, raw_data).group('content_type')
                content = re.match(file_regex, raw_data).group('content')
                data['name'] = filename
                data['content'] = content
                data['content_type'] = content_type
            elif re.match(para_regex, raw_data):
                name = re.match(para_regex, raw_data).group('name')
                value = re.match(para_regex, raw_data).group('value')
                data[name] = value
    else:
        filename = str(uuid.uuid4())
        data['name'] = filename
        data['content'] = body
        data['content_type'] = content_type

    data['update_list'] = [] if 'update_list' not in data else data['update_list'].split(',')

    if 'name' not in data or 'content' not in data:
        raise ValueError
    if 'content_type' not in data:
        data['content_type'] = 'text/plain'
    
    return data

def handle_request(request):
    try:
        method, path, headers, body = parse_request(request)
        # Authorization
        if method not in ['GET', 'HEAD'] or path.startswith('/download'):
            if 'Cookie' not in headers or not Cookie(cookie_str=headers['Cookie']).isValid(TOKEN):
                raise PermissionError
        
        if method == 'GET':
            if path == '/' or path == '/index.html':
                path = "/html/index.html"
            
            if path == '/token':
                # redirect to index.html status code 301
                c = Cookie(sid=TOKEN, expires=time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + 3600)), path='/')
                return create_response(301, [('Location', '/'), ('Set-Cookie', str(c)), ('Content-Type', 'text/html'), ('Cookie', str(c))])
            
            elif path.startswith('/download'):
                filename = path.split('/')[-1]
                with open(os.path.join(UPLOAD_FOLDER, filename), 'rb') as download_file:
                    file_data = download_file.read()
                headers = [(f"Content-Disposition", "attachment; filename={}".format(filename)), ('Content-Type', 'application/octet-stream'), ('Content-Length', os.path.getsize(os.path.join(UPLOAD_FOLDER, filename)))]
                return create_response(200, headers, file_data)
            
            elif path == '/file-list':
                data = {}
                if 'Cookie' in headers and Cookie(cookie_str=headers['Cookie']).isValid(TOKEN):
                    # 回傳檔案列表
                    file_list = os.listdir(UPLOAD_FOLDER)
                    for filename in file_list:
                        data[filename] = {}
                        data[filename]['url'] = f'http://localhost:8080/download/{filename}'
                        data[filename]['size'] = os.path.getsize(os.path.join(UPLOAD_FOLDER, filename))
                body = {
                    'total': len(data),
                    'ok': True,
                    'data': data,
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(body))
            
            else:
                with open(os.path.join(STATIC_FOLDER, path[1:]), 'rb') as static_file:
                    file_data = static_file.read()
                headers = [('Content-Type', CONTENT_TYPE[path.split('.')[-1]])]
                return create_response(200, headers, file_data)
        
        elif method == 'HEAD':
            auth = 'Cookie' in headers and Cookie(cookie_str=headers['Cookie']).isValid(TOKEN)
            if path == '/auth':
                # check auth
                if auth:
                    return create_response(200, [])
                else:
                    return create_response(403, [])
            else:
                # 回傳檔案資訊
                if not auth:
                    return create_response(403, [])
                
                filename = path.split('/')[-1]
                if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
                    headers = [('Content-Length', os.path.getsize(os.path.join(UPLOAD_FOLDER, filename))), ('Content-Type', CONTENT_TYPE[filename.split('.')[-1]])]
                    return create_response(200, headers, '')
                else:
                    return create_response(404, [])
            
        elif method == 'POST':
            # 上傳檔案
            data = parse_body(body, headers['Content-Type'])
            # check file exist
            if os.path.exists(os.path.join(UPLOAD_FOLDER, data['name'])):
                res = {
                    'ok': False,
                    'name': data['name'],
                    'size': len(data['content']),
                    'path': f'/file/{data["name"]}',
                    'error': 'File exists'
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(res))
            else:
                path = os.path.join(UPLOAD_FOLDER, data['name'])
                with open(path, 'w') as upload_file:
                    upload_file.write(data['content'])
                
                res = {
                    'ok': True,
                    'name': data['name'],
                    'size': len(data['content']),
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(res))
        
        elif method == 'PUT':
            # 更新檔案
            data = parse_body(body, headers['Content-Type'])
            update_file, fail_file = [], []
            for filename in data['update_list']:
                # check file exist
                if not os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
                    fail_file.append(filename)
                else:
                    path = os.path.join(UPLOAD_FOLDER, filename)
                    with open(path, 'w') as upload_file:
                        upload_file.write(data['content'])
                    update_file.append(filename)
            res = {
                'ok': True if len(fail_file) == 0 else False,
                'update': update_file,
                'fail': fail_file,
                'error': 'File not exists' if len(fail_file) != 0 else None
            }
            return create_response(200, [('Content-Type', 'application/json')], json.dumps(res))
        
        elif method == 'DELETE':
            # 刪除檔案
            filename = path.split('/')[-1]
            if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
                os.remove(os.path.join(UPLOAD_FOLDER, filename))
                res = {
                    'ok': True,
                    'name': filename,
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(res))
            else:
                res = {
                    'ok': False,
                    'name': filename,
                    'error': 'File not exists'
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(res))

        else:
            return create_response(505, [('Content-Type', 'text/html')])
    except ValueError:
        return create_response(400, [('Content-Type', 'text/html')])
    except KeyError:
        return create_response(400, [('Content-Type', 'text/html')])
    except PermissionError as e:
        with open(os.path.join(STATIC_FOLDER, 'html/403.html'), 'rb') as static_file:
            file_data = static_file.read()
        return create_response(403, [('Content-Type', 'text/html')], file_data)
    except FileNotFoundError as e:
        with open(os.path.join(STATIC_FOLDER, 'html/404.html'), 'rb') as static_file:
            file_data = static_file.read()
        return create_response(404, [('Content-Type', 'text/html')], file_data)
    except Exception as e:
        print(colored(e, 'red'))
        return create_response(500, [('Content-Type', 'text/html')])    

def run_server():
    host = 'localhost'
    port = 8080
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(10)
    print(f'Running on http://{host}:{port}')
    print('Press Ctrl + C to quit')

    try:
        while True:
            client, addr = server.accept()
            try:
                request = client.recv(1024).decode('utf-8')            
                _, _, headers, body = parse_request(request)
                if 'Content-Length' in headers:
                    content_length = int(headers['Content-Length'])
                    while len(body) < content_length:
                        request = request + client.recv(1024).decode()
                        _, _, headers, body = parse_request(request)
                response = handle_request(request)
            except UnicodeDecodeError:
                pass
            client.send(response)
            client.close()

    except KeyboardInterrupt:
        server.close()
        print(colored('Server is successfully shut down', 'green'))
        

if __name__ == '__main__':
    run_server()
