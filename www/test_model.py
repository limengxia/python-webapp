
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#可以在MySQL客户端命令行查询，看看数据是不是正常存储到MySQL里面了。
import orm,asyncio
from models import User, Blog, Comment

@asyncio.coroutine
def test(loop):
    yield from orm.create_pool(loop=loop,user='root', password='password', db='awesome')

    u = User(name='test1', email='test1@qq.com', passwd='12345', image='about:blank')

    yield from u.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()