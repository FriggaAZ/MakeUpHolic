from django.core.files.storage import Storage
from django.conf import settings
from fdfs_client.client import Fdfs_client


class FDFSStorage(Storage):
    '''fast dfs文件存储类'''
    def __init__(self, client_conf=None, base_url=None):
        '''初始化'''
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_config = client_conf

        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def _open(self, name, mode='rb'):
        '''打开文件'''
        pass

    def _save(self, name, content):
        '''保存文件的时候使用'''
        # name：选择的上传文件的名字
        # content：包含你上传文件内容的File类对象

        # 创建一个Fdfs_client对象
        client = Fdfs_client(self.client_config)

        # 上传文件到FDFS
        res = client.upload_appender_by_buffer(content.read())

        # return dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        # }

        if res.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception('上传文件到FastDFS失败')

        # 获取返回的文件ID
        filename = res.get('Remote file_id')
        return filename

    def exists(self, name):
        '''判断文件名是否可用'''
        # 文件内容没有保存在Django服务器上，所以名字永远可用
        return False

    def url(self, name):
        '''返回访问文件的url路径'''
        return self.base_url + name