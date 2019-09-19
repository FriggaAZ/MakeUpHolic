# 使用celery
from celery import Celery
from django.core.mail import send_mail
import time
import os
from django.template import loader, RequestContext
from django.conf import settings
from goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
from django_redis import get_redis_connection

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


@app.task
def generate_sttic_index_html():
    '''产生首页静态页面'''
    # 获取商品的种类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for type in types:  # GoodsType
        # 获取type种类首页分类商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')

        # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banners
        type.title_banners = title_banners


    # 组织模板上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners}

    # 使用模板
    # return render(request, 'index.html', context)  # HttpResponse
    # 1. 加载模板文件,返回模板对象
    temp = loader.get_template('static_index.html')
    # # 2. 定义模板上下文
    # RequestContext(request, context)
    # 3. 模板渲染
    static_index_html = temp.render(context)
    # 生成首页对应静态页面文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)