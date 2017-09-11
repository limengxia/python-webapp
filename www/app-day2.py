#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#由于我们的Web App建立在asyncio的基础上，因此用aiohttp写一个基本的app.py：
__anthor__='limengxia'
'''
async web application.

由文档可知，运用aiohttp异步模块，制作简单的服务器响应：

1.可先制作响应函数

2.再制作响应函数集合

3.最后创建服务器(连接网址、端口，绑定handler)

服务器完成的是接受http请求 返回响应的html 。用浏览器请求http://127.0.0.1:9000
'''
import logging; logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from datetime import datetime
from aiohttp import web #aiohttp则是基于asyncio实现的HTTP框架

#可先制作响应函数
def index(request): #返回内容  
    return web.Response(body=b'<h1>Awesome</h1>',content_type='text/html')#返回的网页内容

@asyncio.coroutine
def init(loop):#Web app服务器初始化
    app = web.Application(loop=loop)#制作响应函数集合  #用aiohttp web框架创建一个app
    app.router.add_route('GET', '/', index)#把响应函数添加到响应函数集合   #给webpp加地址（方法，地址，返回函数）
	#采用异步IO开启服务器连接
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)##创建服务器(连接网址、端口，绑定handler)
    logging.info('server started at http://127.0.0.1:9000...')#日志??
    return srv
'''	
async def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv
'''
loop = asyncio.get_event_loop()#创建事件 #申请一个get_event_loop
loop.run_until_complete(init(loop)) #运行  #把协程init放进去
loop.run_forever()#服务器不关闭

#嗯，不写loop参数没有影响是因为当前只有一个人连接web后端，一个loop代表一个用户，假设有1000个人同时连上该服务器，这时候就要处理高并发的情况了，这也就是@asyncio.coroutine出现的原因，这个时候loop1正在处理一些问题，而loop2可以不需要等loop1处理完就处理自己的事件，说白了，加入loop就是传入用户的参数，欢迎有不同意见，一起谈论