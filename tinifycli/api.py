# coding=utf-8

''' Tinify API 层 '''

import os
import platform
import logging
import traceback

import requests

from .function_call_trace import tracecall

LOGGER = logging.getLogger('tinify-cli')

class TinifyCliClient(object):
    ''' API 客户端 '''
    API_ENDPOINT = 'https://api.tinify.com'
    USER_AGENT = 'Tinify/{0} Python/{1} ({2})'\
            .format('1.1.0',  # 模拟官方的 SDK
                    platform.python_version(),
                    platform.python_implementation())

    def __init__(self, key):
        self.key = key

        self.compression_count = None
        self.image_width = None
        self.image_height = None
        self.src_size = None
        self.dest_size = None

        self.session = requests.sessions.Session()
        self.session.auth = ('api', self.key)
        self.session.headers = {'user-agent': self.USER_AGENT}
        self.session.verify = \
                os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cacert.pem')

    @tracecall
    def request(self, method, url, body=None):
        url = url if url.lower().startswith('https://') else self.API_ENDPOINT + url
        params = {}
        if isinstance(body, dict):
            if body:
                params['json'] = body
        elif body:
            params['data'] = body

        try:
            response = self.session.request(method, url, timeout=120.0, **params)
        except requests.exceptions.Timeout as err:
            LOGGER.error('连接服务器超时 (' + str(err) + ')')
            raise ConnectionError(str(err))
        except Exception as err:
            LOGGER.error('连接服务器时发生了错误 (' + str(err) + ')')
            traceback.print_exc()
            raise ClientError(str(err))

        count = response.headers.get('compression-count')
        if count:
            self.compression_count = int(count)

        if not response.ok:
            details = None
            try:
                details = response.json()
            except Exception as err:
                details = {
                    'message': 'Error while parsing response: {0}'.format(err),
                    'error': 'ParseError'
                }
            raise Error.create(details.get('message'), \
                    details.get('error'), \
                    response.status_code)

        return response

    def validate(self):
        try:
            self.request('POST', '/shrink')
        except ClientError:
            pass

    @staticmethod
    def _append_unit_suffix(bytes_num):
        UNIT = ['B', 'KiB', 'MiB', 'GiB']
        bytes_num = float(bytes_num)
        for unit in UNIT:
            if bytes_num >= 1024.0:
                bytes_num /= 1024.0
            else:
                break
        return '%.1f%s' % (bytes_num, unit)

    @tracecall
    def compress(self, src, dest, resize=None):
        filename = os.path.basename(src)

        LOGGER.debug("上传 " + src)
        # 上传
        with open(src, 'rb') as fp:
            image_bin = fp.read()
        self.src_size = len(image_bin)
        response = self.request('POST', '/shrink', image_bin)

        download_url = response.headers.get('location')
        r = response.json()

        LOGGER.debug('下载 ' + download_url)
        # 处理尺寸问题 & 下载
        if resize is None:  # 压缩但不改变尺寸
            response = self.request('GET', download_url)
        else:  # 压缩且改变尺寸
            method, width, height = resize
            payload = {"resize": {"method": method}}
            if width is not None:
                payload['resize']['width'] = width
            if height is not None:
                payload['resize']['height'] = height
            response = self.request('GET', download_url, body=payload)

            LOGGER.debug('保存到文件 ' + dest)
            image_bin = response.content
        self.dest_size = len(image_bin)
        with open(dest, 'wb') as fp:
            fp.write(image_bin)

        LOGGER.info('文件 ' + filename +
                    ' (' + str(r['output']['width']) + 'x' +
                    str(r['output']['height']) + ') ' +
                    self._append_unit_suffix(self.src_size) + ' => ' +
                    self._append_unit_suffix(self.dest_size) + ' ' +
                    '压缩比: ' + 
                    '%.1f' % (100.0*self.dest_size/self.src_size) + '%')

class Error(Exception):
    @staticmethod
    def create(message, kind, status):
        klass = None
        if status == 401 or status == 429:
            klass = AccountError
        elif status >= 400 and status <= 499:
            klass = ClientError
        elif status >= 400 and status < 599:
            klass = ServerError
        else:
            klass = Error

        if not message: message = 'No message was provided'
        return klass(message, kind, status)

    def __init__(self, message, kind=None, status=None, cause=None):
        self.message = message
        self.kind = kind
        self.status = status
        if cause:
            # Equivalent to 'raise err from cause', also supported by Python 2.
            self.__cause__ = cause

    def __str__(self):
        if self.status:
            return '{0} (HTTP {1:d}/{2})'.format(self.message, self.status, self.kind)
        else:
            return self.message

class AccountError(Error): pass
class ClientError(Error): pass
class ServerError(Error): pass
class ConnectionError(Error): pass

