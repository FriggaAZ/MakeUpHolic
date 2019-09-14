# 使用celery
from celery import Celery
from django.core.mail import send_mail
import time
from django.conf import settings

# 创建一个celery对象
app = Celery('celery_tasks.tasks', broker='redis://192.168.115.131:6379/8')

# 定义任务函数
@app.task
def send_register_active_email(to_email, username, token):
    '''发送激活邮件'''
    subject = '天天生鲜欢迎您'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = '<h1>%s,欢迎您</h1>请点击下方链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>' % (
    username, token, token)
    send_mail(subject, message, settings.EMAIL_FROM, receiver, html_message=html_message)
    # send_mail(subject, message, sender, receiver)
    # 返回应答, 跳转到首页
    time.sleep(5)