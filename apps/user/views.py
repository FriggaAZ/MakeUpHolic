from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from celery_tasks.tasks import send_register_active_email
from user.models import User, Address
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from utils.mixin import LoginRequiredMixin
from django_redis import get_redis_connection
from goods.models import GoodsSKU
from django.core.mail import send_mail
import re
# Create your views here.

# /user/register
# def register(request):
#     '''显示注册页面'''
#     if request.method == 'GET':
#         return render(request, 'register.html')
#     else:
#         '''注册处理'''
#         # 视图处理流程
#         # 接受数据
#         username = request.POST.get('user_name')
#         password = request.POST.get('pwd')
#         email = request.POST.get('email')
#         allow = request.POST.get('allow')
#         # 进行校验
#         if not all([username, password, email]):
#             # 数据不完整
#             return render(request, 'register.html', {'errmsg': "数据不完整"})
#         # 校验邮箱
#         if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
#             return render(request, 'register.html', {'errmsg': "邮箱不正确"})
#
#         if allow != 'on':
#             return render(request, 'register.html', {'errmsg': "请同意协议"})
#
#         # 校验用户名是否重复
#         try:
#             user = User.objects.get(username=username)
#         except User.DoesNotExist:
#             # 用户名不存在， 可以注册
#             user = None
#
#         if user:
#             # 用户名已经存在
#             return render(request, 'register.html', {'errmsg': '用户名已经存在'})
#         # 进行业务处理：进行用户注册
#         user = User.objects.create_user(username, email, password)
#         # 不激活
#         user.is_active = 0
#         user.save()
#         # 返回应答, 跳转到首页
#         return redirect(reverse('goods:index'))

# 合并register和register_handle为同一个url地址
# def register_handle(request):
#     '''注册处理'''
#     # 视图处理流程
#     # 接受数据
#     username = request.POST.get('user_name')
#     password = request.POST.get('pwd')
#     email = request.POST.get('email')
#     allow = request.POST.get('allow')
#     # 进行校验
#     if not all([username, password, email]):
#         # 数据不完整
#         return render(request, 'register.html', {'errmsg': "数据不完整"})
#     # 校验邮箱
#     if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
#         return render(request, 'register.html', {'errmsg': "邮箱不正确"})
#
#     if allow != 'on':
#         return render(request, 'register.html', {'errmsg': "请同意协议"})
#
#     # 校验用户名是否重复
#     try:
#         user = User.objects.get(username=username)
#     except User.DoesNotExist:
#         # 用户名不存在， 可以注册
#         user = None
#
#     if user:
#         # 用户名已经存在
#         return render(request, 'register.html', {'errmsg': '用户名已经存在'})
#     # 进行业务处理：进行用户注册
#     user = User.objects.create_user(username, email, password)
#     # 不激活
#     user.is_active = 0
#     user.save()
#     # 返回应答, 跳转到首页
#     return redirect(reverse('goods:index'))


# 使用类视图
class RegisterView(View):
    '''注册'''
    def get(self, request):
        '''显示注册页面'''
        return render(request, 'register.html')
    def post(self, request):
        '''进行注册处理'''
        # 视图处理流程
        # 接受数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行校验
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': "数据不完整"})
        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': "邮箱不正确"})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': "请同意协议"})

        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在， 可以注册
            user = None

        if user:
            # 用户名已经存在
            return render(request, 'register.html', {'errmsg': '用户名已经存在'})
        # 进行业务处理：进行用户注册
        user = User.objects.create_user(username, email, password)
        # 不激活
        user.is_active = 0
        user.save()

        # 发送激活邮件，包含激活链接：http://127.0.0.1:8000/user/active/加密信息
        # 激活链接中需要包含用户的身份信息,并且要加密处理

        # 加密用户身份信息，生成token
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        token = token.decode('utf8')

        # 发邮件
        send_register_active_email.delay(email, username, token)

        return redirect(reverse('goods:index'))


class ActiveView(View):
    '''用户激活'''
    def get(self, request, token):
        '''进行用户激活'''
        # 进行解密，获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取待激活用户ID
            user_id = info['confirm']

            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 跳转到登录页面
            # 反向解析，并重定向至user这个app的name=login的url
            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            # 激活链接已经过期
            return HttpResponse('激活链接已经过期！')

# user/login
class LoginView(View):
    '''登录'''
    def get(self, request):
        # 判断是否记住了用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        # 使用木板

        return render(request, 'login.html', {'username': username, 'checked':checked})

    def post(self, request):
        '''登录校验'''
        # 接受数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        # 校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        # 业务处理：登录校验
        # user = User.objects.get(username=username, password=password)
        user = authenticate(username=username, password=password)
        print(user)
        if user is not None:
            # 用户名密码正确
            if user.is_active:
                # print("User is valid, active and authenticated")
                # 记录用户登录状态
                login(request, user)

                # 获取登录后所跳转到的地址
                # 如果没获取到next的值，就返回reverse(),默认跳转到首页
                next_url = request.GET.get('next', reverse('goods:index'))

                # 跳转到首页
                response = redirect(next_url)
                # response = redirect(reverse('goods:index'))
                # 判断是否需要记住用户名
                remember = request.POST.get('remember')
                if remember == 'on':
                    # 记住用户名
                    response.set_cookie('username', username, max_age=7*24*3600)
                else:
                    response.delete_cookie('username')

                return response
            else:
                return render(request, 'login.html', {'errmsg': '用户未激活，请检查您的收件箱'})

        else:
            # 用户名密码错误
            return render(request, 'login.html', {'errmsg': '用户名或密码错误或未激活'})

# user/logout
class LogoutView(View):
    '''退出登录'''
    def get(self, request):
        '''退出登录'''
        # 清除用户session信息
        logout(request)
        # 跳转到首页
        return redirect(reverse('goods:index'))


# /user
class UserInfoView(LoginRequiredMixin, View):
    '''用户中心-信息页面'''
    def get(self, request):
        '''显示 '''

        # 获取用户信息
        user = request.user
        address = Address.objects.get_default_address(user)
        # 用户历史浏览记录
        # from redis import StrictRedis
        # sr = StrictRedis(host='192.168.115.131', port='6379', db=9)
        con = get_redis_connection('default')

        # 取出浏览记录
        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的五条商品ID
        sku_ids = con.lrange(history_key, 0, 4)

        # 从数据库中查询用户浏览的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)

        # 排序方法1，sku_ids是用户浏览的顺序，通过它对取到的数据进行排序
        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)

        # 排序方法2
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)

        # 组织上下文
        context = {'page': 'user',
                   'address': address,
                   'goods_li': goods_li}

        # page='user'
        # request.user.is_authenticated()
        # 除了你给模板传递的模板变量之外，django框架会把request.user也传递给模板
        return render(request, 'user_center_info.html', context)


# /user/order
class UserOrderView(LoginRequiredMixin, View):
    '''用户中心-订单页面'''
    def get(self, request):

        # 获取用户订单信息



        '''显示 变黄'''
        # page='order'
        return render(request, 'user_center_order.html', {'page': 'order'})


# /user/address
class AddressView(LoginRequiredMixin, View):
    '''用户中心-地址'''
    def get(self, request):
        '''显示 '''

        # 获取默认收货地址
        # 获取登录用户对应的User对象
        user = request.user
        # try:
        #     # 通过user查询到地址，康康地址是不是默认的
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认地址
        #     address = None
        address = Address.objects.get_default_address(user)
        # page='address'
        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        '''地址的添加'''
        # 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})
        # 校验手机号
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机号码不正确'})

        # 业务处理：地址添加
        # 如果用户已经存在了默认收货地址，那么添加的地址不能作为默认收货地址， 否则作为默认收货地址
        # 能访问到这个页面表示用户已经登录了，获取登录用户对应的User对象
        user = request.user
        # try:
        #     # 通过user查询到地址，康康地址是不是默认的
        #     address = Address.objects.get(user=user, is_default = True)
        # except Address.DoesNotExist:
        #     # 不存在默认地址
        #     address = None

        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        # 添加地址
        Address.objects.create(user=user, receiver=receiver, addr=addr,
                               phone=phone, zip_code=zip_code, is_default=is_default)

        # 返回应答,刷新地址页面
        return redirect(reverse('user:address'))  # 这个是get方式的，所以





