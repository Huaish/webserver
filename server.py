
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

# ======================== 
# Exceptions Start
# ========================
class BadRequestError(Exception):
    '''400 請求訊息格式錯誤'''
    pass

class HTTPVersionNotSupportedError(Exception):
    '''505 HTTP 版本不支援'''
    pass

class NotImplementError(Exception):
    '''501 請求方法不支援'''
    pass

# ========================
# Exceptions End
# ========================

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
        if key not in self.cookie:
            return None
        return self.cookie[key]
    
    def __setitem__(self, key, value):
        self.cookie[key] = value

    def __str__(self):
        cookie_str = ''
        for key, value in self.cookie.items():
            cookie_str += f'{key}={value}; '
        return cookie_str[:-2]

class HTTPServer:
    def __init__(self, config):
        self.config = config

    @staticmethod
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

    @staticmethod
    def parse_request(request):
        """解析請求訊息"""
        request_lines = request.split("\r\n")
        method, path, version = request_lines[0].split(" ")
        headers = {}

        # Check HTTP version
        if version != "HTTP/1.1":
            raise HTTPVersionNotSupportedError

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

    @staticmethod
    def parse_body(body, content_type):
        """解析 body"""
        if body is None or content_type is None:
            raise BadRequestError
        data = {}
        if content_type.startswith('multipart/form-data'):
            boundary = content_type.split('; ')[1].split('=')[1]
            # parse form data
            raw_form_data = body.strip().split(f'--{boundary}')[1:-1]
            file_regex = rf'\r\nContent-Disposition: form-data; name="file"; filename="(?P<filename>.*)"\r\nContent-Type: (?P<content_type>.*)\r\n\r\n(?P<content>.*)\r\n'
            para_regex = rf'\r\nContent-Disposition: form-data; name="(?P<name>.*)"\r\n\r\n(?P<value>.*)\r\n'

            for raw_data in raw_form_data:
                content_match = re.match(file_regex, raw_data)
                if content_match:
                    filename = content_match.group('filename')
                    content_type = content_match.group('content_type')
                    content = content_match.group('content')
                    data['name'] = filename
                    data['content'] = content
                    data['content_type'] = content_type
                    continue
                content_match = re.match(para_regex, raw_data)
                if content_match:
                    name = content_match.group('name')
                    value = content_match.group('value')
                    data[name] = value
        else:
            filename = str(uuid.uuid4())
            data['name'] = filename
            data['content'] = body
            data['content_type'] = content_type

        data['update_list'] = [] if 'update_list' not in data else data['update_list'].split(',')

        if 'name' not in data or 'content' not in data:
            raise BadRequestError
        if 'content_type' not in data:
            data['content_type'] = 'text/plain'
        
        return data

    def auth(self, cookie):
        """驗證 token"""
        if cookie:
            return cookie['token'] == self.config.token
        return False

    def handle_request(self, request):
        try:
            method, path, headers, body = HTTPServer.parse_request(request)
            if self.config.debug:
                print(colored(f"method: {method}", "green"))
                print(colored(f"path: {path}", "blue"))
                print(colored(f"headers: {headers}", "yellow"))
                print(colored(f"body: {body}", "white"))
            
            cookie = Cookie(cookie_str=headers['Cookie']) if 'Cookie' in headers else None
            
            if method == 'GET':
                return self.handle_get(path, cookie)
            
            elif method == 'HEAD':
                return self.handle_head(path, cookie)
            
            elif method == 'POST':
                return self.handle_post(path, headers, cookie, body)
            
            elif method == 'PUT':
                return self.handle_put(path, headers, cookie, body)

            elif method == 'DELETE':
                return self.handle_delete(path, cookie)

            else:
                raise NotImplementError

        except Exception as e:
            return self.handle_exception(e)

    def handle_get(self, path, cookie):
        if path == '/':
            return HTTPServer.create_response(301, [('Location', '/index.html')]), 301
        
        if path == '/token':
            c = Cookie(token=config.token, expires=time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + 3600)), path='/')
            return HTTPServer.create_response(301, [('Location', '/'), ('Set-Cookie', str(c)), ('Content-Type', 'text/html'), ('Cookie', str(c))]), 301
        
        elif path.startswith('/download'):
            if self.auth(cookie):
                path = path.replace('/download/', f'{config.upload_folder}/')
                filename = path.split('/')[-1]
                with open(path, 'rb') as download_file:
                    file_data = download_file.read()
                headers = [(f"Content-Disposition", "attachment; filename={}".format(filename)), ('Content-Type', 'application/octet-stream'), ('Content-Length', os.path.getsize(os.path.join(config.upload_folder, filename)))]
                return HTTPServer.create_response(200, headers, file_data), 200
            else:
                raise PermissionError
        
        elif path == '/file-list':
            data = {}
            if self.auth(cookie):
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
            return HTTPServer.create_response(200, [('Content-Type', 'application/json')], json.dumps(body)), 200

        else:
            path = path[1:]
            type = path.split('.')[-1]
            
            if type in CONTENT_TYPE:
                headers = [('Content-Type', CONTENT_TYPE[type])]
            else:
                headers = [('Content-Type', 'text/plain')]

            if type in ['html', 'js', 'css']:
                path = os.path.join(type, path)
            elif type in ['jpg', 'jpeg', 'png', 'gif', 'ico']:
                path = os.path.join('images', path)
            elif not self.auth(cookie):
                raise PermissionError
            else:
                path = os.path.join('upload', path)

            with open(os.path.join(config.static_folder, path), 'rb') as static_file:
                file_data = static_file.read()

            return HTTPServer.create_response(200, headers, file_data), 200

    def handle_head(self, path, cookie):
        if path == '/auth':
            return (HTTPServer.create_response(200, []), 200) if self.auth(cookie) else (HTTPServer.create_response(403, []), 403)
        else:
            # 回傳檔案資訊
            if not self.auth(cookie):
                return HTTPServer.create_response(403, []), 403
            
            filename = path.split('/')[-1]
            if os.path.exists(os.path.join(config.upload_folder, filename)):
                headers = [('Content-Length', os.path.getsize(os.path.join(config.upload_folder, filename))), ('Content-Type', CONTENT_TYPE[filename.split('.')[-1]])]
                return HTTPServer.create_response(200, headers, ''), 200
            else:
                return HTTPServer.create_response(404, []), 404

    def handle_post(self, path, headers, cookie, body):
        '''上傳檔案'''
        if not self.auth(cookie):
            raise PermissionError
        
        data = HTTPServer.parse_body(body, headers['Content-Type'] if 'Content-Type' in headers else None)
        # check file exist
        if os.path.exists(os.path.join(config.upload_folder, data['name'])):
            res = {
                'ok': False,
                'name': data['name'],
                'size': len(data['content']),
                'path': f'/file/{data["name"]}',
                'error': 'File exists'
            }
            return HTTPServer.create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200
        else:
            path = os.path.join(config.upload_folder, data['name'])
            with open(path, 'w') as upload_file:
                upload_file.write(data['content'])
            
            res = {
                'ok': True,
                'name': data['name'],
                'size': len(data['content']),
            }
            return HTTPServer.create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200

    def handle_delete(self, path, cookie):
        '''刪除檔案'''
        if not self.auth(cookie):
            raise PermissionError
        
        filename = path.split('/')[-1]
        if os.path.exists(os.path.join(config.upload_folder, filename)):
            os.remove(os.path.join(config.upload_folder, filename))
            res = {
                'ok': True,
                'name': filename,
            }
            return HTTPServer.create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200
        else:
            res = {
                'ok': False,
                'name': filename,
                'error': 'File not exists'
            }
            return HTTPServer.create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200

    def handle_put(self, path, headers, cookie, body):
        '''更新檔案'''
        if not self.auth(cookie):
            raise PermissionError
        data = HTTPServer.parse_body(body, headers['Content-Type'] if 'Content-Type' in headers else None)
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
        return HTTPServer.create_response(200, [('Content-Type', 'application/json')], json.dumps(res)), 200
    
    def handle_exception(self, e):
        if isinstance(e, FileNotFoundError):
            return HTTPServer.create_response(404, []), 404
        elif isinstance(e, PermissionError):
            return HTTPServer.create_response(403, []), 403
        elif isinstance(e, BadRequestError):
            return HTTPServer.create_response(400, []), 400
        elif isinstance(e, HTTPVersionNotSupportedError):
            return HTTPServer.create_response(505, []), 505
        elif isinstance(e, NotImplementError):
            return HTTPServer.create_response(501, []), 501
        else:
            return HTTPServer.create_response(500, []), 500

    def run(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.config.host, self.config.port))
        self.server.listen(5)
        print(f'Running on http://{config.host}:{config.port}')
        print('Press Ctrl + C to quit')

        try:
            while True:
                client, addr = self.server.accept()
                try:
                    request = client.recv(1024).decode('utf-8')            
                    method, path, headers, body = self.parse_request(request)
                    if 'Content-Length' in headers:
                        content_length = int(headers['Content-Length'])
                        while len(body or '') < content_length:
                            request = request + client.recv(1024).decode()
                            _, _, headers, body = HTTPServer.parse_request(request)
                    response, status_code = self.handle_request(request)

                    print(f'{addr[0]} - - [{time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time()))}]', end=' ')
                    print(colored(f' "{method} {path} HTTP/1.1"', 'cyan'), end=' ')
                    print(colored(f' {status_code} -', 'white'))
                    
                    client.send(response)
                except UnicodeDecodeError:
                    pass
                except Exception as e:
                    response, status_code = self.handle_exception(e)
                    client.send(response)
                client.close()

        except KeyboardInterrupt:
            self.server.close()
            print(colored('Server is successfully shut down', 'green'))
        

if __name__ == '__main__':
    args_cli = OmegaConf.from_cli()
    config = OmegaConf.load("./settings/config.yml")
    config = OmegaConf.merge(config, args_cli)
    config.token = hashlib.sha256(config.token.encode()).hexdigest()
    server = HTTPServer(config)
    server.run()
