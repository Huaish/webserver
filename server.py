
import json
import socket
import os
from termcolor import colored
import time
import hashlib
import re
import uuid
from omegaconf import OmegaConf

CONTENT_TYPE = {
    'txt': 'text/plain',
    'bin': 'application/octet-stream',
    'html': 'text/html',
    'css': 'text/css',
    'js': 'application/javascript',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'pdf': 'application/pdf',
    'ico': 'image/x-icon'
}

class Cookie:
    def __init__(self, token=None, expires=None, path=None, cookie_str=None):
        self.cookie = {}
        if cookie_str:
            self.cookie = self.parse_cookie(cookie_str)
        else:
            if token:
                self.cookie['token'] = token
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

def create_response(status_code, headers=[], body=None):
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

def auth(headers, config):
    """驗證 token"""
    if 'Cookie' in headers:
        cookie = Cookie(cookie_str=headers['Cookie'])
        return cookie['token'] == config.token
    return False

def handle_request(request, config):
    try:
        method, path, headers, body = parse_request(request)
        if config.debug:
            print(colored(f"method: {method}", "green"))
            print(colored(f"path: {path}", "blue"))
            print(colored(f"headers: {headers}", "yellow"))
            print(colored(f"body: {body}", "white"))

        # Authorization
        if method not in ['GET', 'HEAD'] and not auth(headers, config):
                raise PermissionError
        
        if method == 'GET':
            if path == '/':
                # redirect to index.html status code 301
                return create_response(301, [('Location', '/index.html')]), 301
            if path == '/token':
                # redirect to index.html status code 301
                c = Cookie(token=config.token, expires=time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + 3600)), path='/')
                return create_response(301, [('Location', '/'), ('Set-Cookie', str(c)), ('Content-Type', 'text/html'), ('Cookie', str(c))]), 301
            
            elif path.startswith('/download'):
                if auth(headers, config):
                    path = path.replace('/download/', f'{config.upload_folder}/')
                    filename = path.split('/')[-1]
                    with open(path, 'rb') as download_file:
                        file_data = download_file.read()
                    headers = [(f"Content-Disposition", "attachment; filename={}".format(filename)), ('Content-Type', 'application/octet-stream'), ('Content-Length', os.path.getsize(os.path.join(config.upload_folder, filename)))]
                    return create_response(200, headers, file_data), 200
                else:
                    raise PermissionError
            
            elif path == '/file-list':
                data = {}
                if auth(headers, config):
                    # 回傳檔案列表
                    file_list = os.listdir(config.upload_folder)
                    for filename in file_list:
                        data[filename] = {}
                        data[filename]['url'] = f'http://{config.host}:{config.port}/download/{filename}'
                        data[filename]['size'] = os.path.getsize(os.path.join(config.upload_folder, filename))
                body = {
                    'total': len(data),
                    'ok': True,
                    'data': data,
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(body)), 200
            
            else:
                path = path[1:]
                type = path.split('.')[-1]
                if type in CONTENT_TYPE:
                    headers = [('Content-Type', CONTENT_TYPE[type])]

                if type in ['html', 'js', 'css']:
                    path = os.path.join(type, path)
                elif type in ['jpg', 'jpeg', 'png', 'gif', 'ico']:
                    path = os.path.join('images', path)
                elif not auth(headers, config):
                    raise PermissionError
                else:
                    path = os.path.join('upload', path)

                with open(os.path.join(config.static_folder, path), 'rb') as static_file:
                    file_data = static_file.read()

                return create_response(200, headers, file_data), 200
        
        elif method == 'HEAD':
            if path == '/auth':
                # check auth
                return (create_response(200, []), 200) if auth(headers, config) else (create_response(403, []), 403)

            else:
                # 回傳檔案資訊
                if not auth(headers, config):
                    return create_response(403, []), 403
                
                filename = path.split('/')[-1]
                if os.path.exists(os.path.join(config.upload_folder, filename)):
                    headers = [('Content-Length', os.path.getsize(os.path.join(config.upload_folder, filename))), ('Content-Type', CONTENT_TYPE[filename.split('.')[-1]])]
                    return create_response(200, headers, ''), 200
                else:
                    return create_response(404, []), 404
            
        elif method == 'POST':
            # 上傳檔案
            data = parse_body(body, headers['Content-Type'])
            # check file exist
            if os.path.exists(os.path.join(config.upload_folder, data['name'])):
                res = {
                    'ok': False,
                    'name': data['name'],
                    'size': len(data['content']),
                    'path': f'/file/{data["name"]}',
                    'error': 'File exists'
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200
            else:
                path = os.path.join(config.upload_folder, data['name'])
                with open(path, 'w') as upload_file:
                    upload_file.write(data['content'])
                
                res = {
                    'ok': True,
                    'name': data['name'],
                    'size': len(data['content']),
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200
        
        elif method == 'PUT':
            # 更新檔案
            data = parse_body(body, headers['Content-Type'])
            update_file, fail_file = [], []
            for filename in data['update_list']:
                # check file exist
                if not os.path.exists(os.path.join(config.upload_folder, filename)):
                    fail_file.append(filename)
                else:
                    path = os.path.join(config.upload_folder, filename)
                    with open(path, 'w') as upload_file:
                        upload_file.write(data['content'])
                    update_file.append(filename)
            res = {
                'ok': True if len(fail_file) == 0 else False,
                'update': update_file,
                'fail': fail_file,
                'error': 'File not exists' if len(fail_file) != 0 else None
            }
            return create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200
        
        elif method == 'DELETE':
            # 刪除檔案
            filename = path.split('/')[-1]
            if os.path.exists(os.path.join(config.upload_folder, filename)):
                os.remove(os.path.join(config.upload_folder, filename))
                res = {
                    'ok': True,
                    'name': filename,
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200
            else:
                res = {
                    'ok': False,
                    'name': filename,
                    'error': 'File not exists'
                }
                return create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200

        else:
            return create_response(505, []), 505
    except ValueError:
        return create_response(400, []), 400
    except KeyError:
        return create_response(400, []), 400
    except PermissionError as e:
        with open(os.path.join(config.static_folder, 'html/403.html'), 'rb') as static_file:
            file_data = static_file.read()
        return create_response(403, [('Content-Type', 'text/html')], file_data), 403
    except FileNotFoundError as e:
        with open(os.path.join(config.static_folder, 'html/404.html'), 'rb') as static_file:
            file_data = static_file.read()
        return create_response(404, [('Content-Type', 'text/html')], file_data), 404
    except Exception as e:
        print(colored(e, 'red'))
        return create_response(500, [('Content-Type', 'text/html')]), 500

def run_server(config):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((config.host, config.port))
    server.listen(10)
    print(f'Running on http://{config.host}:{config.port}')
    print('Press Ctrl + C to quit')

    try:
        while True:
            client, addr = server.accept()
            try:
                request = client.recv(1024).decode('utf-8')            
                method, path, headers, body = parse_request(request)
                if 'Content-Length' in headers:
                    content_length = int(headers['Content-Length'])
                    while len(body) < content_length:
                        request = request + client.recv(1024).decode()
                        _, _, headers, body = parse_request(request)
                response, status_code = handle_request(request, config)
                print(f'{addr[0]} - - [{time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time()))}]', end=' ')
                print(colored(f' "{method} {path} HTTP/1.1"', 'cyan'), end=' ')
                print(colored(f' {status_code} -', 'white'))
            except UnicodeDecodeError:
                pass
            client.send(response)
            client.close()

    except KeyboardInterrupt:
        server.close()
        print(colored('Server is successfully shut down', 'green'))
        

if __name__ == '__main__':
    args_cli = OmegaConf.from_cli()
    config = OmegaConf.load("./settings/config.yml")
    config = OmegaConf.merge(config, args_cli)
    config.token = hashlib.sha256(config.token.encode()).hexdigest()
    run_server(config)
