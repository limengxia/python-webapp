#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#ORM（Object-Relational Mapping），作用是：把关系数据库的表结构 映射到对象上。 

__author__ = 'limengxia'


'''
在协程中，不能调用普通的同步IO操作，因为所有用户都是由一个线程服务的，
协程的执行速度必须非常快，才能处理大量用户的请求。
而耗时的IO操作不能在协程中以同步的方式调用，否则，等待一个IO操作时，系统无法响应任何其他用户。 
这就是异步编程的一个原则：一旦决定使用异步，则系统每一层都必须是异步。
'''
import asyncio, logging
import aiomysql #aiomysql为mysql数据库提供了异步IO的驱动。建立一个web访问的ORM，使每一个web请求被连接之后都要接入数据库进行操作。

def log(sql, args=()):
    logging.info('SQL: %s' % sql)

#把常用的SELECT、INSERT、UPDATE和DELETE操作用函数封装起来。


#我们需要创建一个全局的连接池，每个HTTP请求都可以从连接池中直接获取数据库连接。使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。
#连接池由全局变量__pool存储，缺省情况下将编码设置为utf8，自动提交事务：
#创建连接池,每个http请求都从连接池连接到数据库
async def create_pool(loop, **kw):#字典传值#charset参数是utf8# **kw参数可以包含所有连接需要用到的关键字参数
    logging.info('create database connection pool...')#和前面的SQLAlchemy用一个字符串表示连接信息类比下：'数据库类型+数据库驱动名称://用户名:口令@机器地址:端口号/数据库名'
    global __pool
    __pool = await aiomysql.create_pool(#aiomysql为MySQL数据库提供了异步IO的驱动。
        host=kw.get('host', 'localhost'),   # 默认本机IP
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),#配置自动提交
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop# 接收一个event_loop实例
    )#创建连接所需要的参数
    
# 销毁连接池  后加上去的
async def destory_pool():
    global __pool
    if __pool is not None:
        __pool.close()
        await __pool.wait_closed()

        
# select语句'select * from user where id = %s', ('1',)
async def select(sql, args, size=None):#（SQL语句,SQL参数，请求数据大小）
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs #返回的是结果集,结果集是一个list，每个元素都是一个tuple，对应一行记录。
        
'''   
# 封装SQL_SELECT语句为select函数
async def select(sql,args,size=None):
    log(sql)
    global __pool #引入全局变量
    with await __pool as conn: #打开pool的方法,或-->async with __pool.get() as conn:
        cur = await conn.cursor(aiomysql.DictCursor) #创建游标,aiomysql.DictCursor的作用使生成结果是一个dict
        await cur.execute(sql.replace('?',"%s"),args or ()) #执行sql语句，sql语句的占位符是'?',而Mysql的占位符是'%s'
        if size:#如果传入size参数，就通过fetchmany()获取最多指定数量的记录，否则，通过fetchall()获取所有记录。
            rs = await cur.fetchmany(size)
        else:
            rs = await cur.fetchall()
    await cur.close()
    logging.info('rows returned: %s'%len(rs))
    return rs
'''    


# insert,update,deleta语句
#这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数，所以定义一个函数就够了	
async def execute(sql, args, autocommit=True):
    log(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        finally:
            conn.close()
        return affected
        
'''       
#封装INSERT、UPDATE、DELETE语句
@asyncio.coroutine
def execute(sql, args):
    log(sql)
    with (yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount
            yield from cur.close()
        except BaseException as e:
            raise
        finally:
            conn.close()
        return affected
'''

#用于输出元类中创建sql_insert语句中的占位符	
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)# 以', '为分隔符，将列表合成字符串

    
#有了基本的select()和execute()函数，我们就可以开始编写一个简单的ORM了。
#ORM就是把数据库表的行与相应的对象建立关联，互相转换。


#在创建User类之前，最好就得先封装数据库表中的每一列的属性（包含名字、类型、是否为表的主键、默认值），以便调用，这里的做法是定义一个Field类来保存每一列的属性。 

# 定义Field类，负责保存（数据库）表的字段名和字段类型
#以及Field和各种Field子类：
class Field(object):
     # 表的字段包括名字，类型，是否为主键，默认值
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
     # 输出类名，字段类型和名字
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)
		
# 定义不同类型的衍生Field，表的不同列的字段的类型不一样	
class StringField(Field):
    # ddl表示数据定义语言，
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)
		
#注意到Model只是一个基类，如何将具体的子类如User的映射信息读取出来呢？答案就是通过metaclass：ModelMetaclass：		
#这样，任何继承自Model的类（比如User），会自动通过ModelMetaclass扫描映射关系，并存储到自身的类属性如__table__、__mappings__中。

# ModelMetaclass的工作主要是为一个数据库表映射成一个封装的类做准备
# 读取具体子类（user）的映射信息
# 创建类时，排除对Model的修改
# 在当前类中查找所有的类属性（attrs），如果找到Field属性，就将其保存到__mappings__的dict中
# 同时从类属性中删除Field(防止实例属性遮住类的同名属性)
# 将数据库表名保存到__table__中

# 完成这些工作就可以在Model中定义各种数据库的操作方法



class ModelMetaclass(type):
    # __new__控制__init__的执行，所以在其执行之前
    # cls:代表要__init__的类，此参数在实例化时由Python解释器自动提供
    # bases: 代表继承父类的集合
    # atrrs: 类的方法集合
    def __new__(cls, name, bases, attrs):#当前准备创建的类的对象；类的名字；类继承的父类集合；类的方法集合类的属性,也就是table里的name id score之类的了。
        # 排除Model类本身的修改
        if name=='Model':
            return type.__new__(cls, name, bases, attrs)
        # 如果没设置__table__属性，tablename就是类的名字
        tableName = attrs.get('__table__', None) or name #拿到table的名字，比如User的user
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 获取所有的Field和主键名:
        mappings = {} #创建字典存放attrs.items()的值,保存映射关系
        fields = []#创建列表放非主键属性
        primaryKey = None
        # 键是列名，值是field子类
        for k, v in attrs.items():#取 attrs的字典
            if isinstance(v, Field):#判断v是不是Field
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v 
				# 此处打印的k是类的一个属性，v是这个属性在数据库中对应的Field列表属性
                if v.primary_key:#id varchar(20) primary key, name varchar(20) 如果id/name有主键
                    # 找到主键:
                    if primaryKey:#看主键真假，真
                        raise RuntimeError('Duplicate primary key for field: %s' % k)#field主键重复
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:#如果主键为0
            raise Exception('Primary key not found.')
		# 从类属性中删除Field属性，实例的属性会遮盖类的同名属性	
        for k in mappings.keys():#name、id、score
            attrs.pop(k)#pop？？？
		# 保存除主键外的属性名为``（运算出字符串）列表形式
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))#映射？？？？？？
        attrs['__mappings__'] = mappings # 保存属性和列的映射关系
        attrs['__table__'] = tableName# 保存表名
        attrs['__primary_key__'] = primaryKey # 主键属性名
        attrs['__fields__'] = fields # 除主键外的属性名
        # 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
		# ``反引号功能同repr()
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)#'select * from user where id = %s', ('1',)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))#'insert into user(id, name) values (%s, %s)', ['1', 'Michael']
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)
		
	
#设计ORM需要从上层调用者角度来设计。我们先考虑如何定义一个User对象，然后把数据库表users和它关联起来。		
#注意到定义在User类中的__table__、id和name是类的属性，不是实例的属性。所以，在类级别上定义的属性用来描述User对象和表的映射关系，而实例属性必须通过__init__()方法去初始化，所以两者互不干扰：
'''
理想用法
class User(Model):
    __table__ = 'users'

    id = IntegerField(primary_key=True)#类属性
    name = StringField()
	
# 创建实例:
user = User(id=123, name='Michael')
# 存入数据库:
user.insert()
# 查询所有User对象:
users = User.findAll()
'''

#定义Model。首先要定义的是所有ORM映射的基类Model：模仿sqlalchemy里的Base = declarative_base()
# Model类的任何子类可以映射为一个数据库表
# Model类可以看做是对所有数据库表操作的基本定义的映射
# Model从dict继承，所以具备所有dict的功能，同时又实现了特殊方法__getattr__()和__setattr__()，因此又可以像引用普通字段那样写：>>> user['id']>>> user.id

class Model(dict, metaclass=ModelMetaclass):#？？查下元类用法？？
    # 继承了字典，所以可以接受任意属性？ 实例取的是字典的值
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)#？？？？super（）函数，继承初始化？？
		
    # _getattr_用于查询不在__dict__系统中的属性
    # __dict__分层存储属性，每一层的__dict__只存储每一层新加的属性。子类不需要重复存储父类的属性。
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):  #？？？
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default#？？？？
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value
        
	#然后，我们往Model类添加class方法，就可以让所有子类调用class方法：	
	# 类方法的第一个参数是cls,而实例方法的第一个参数是self
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None) # 语句中是否有orderBy参数
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None) # 语句中是否有limit参数
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit) # extend 接收一个iterable参数
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        #调用select函数,返回值是从数据库里查找到的数据结果
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        '''find number by select and where. '''
		 # 这里的 _num_ 为别名，任何客户端都可以按照这个名称引用这个列，就像它是个实际的列一样
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
		 # rs[0]表示一行数据,是一个字典，而rs是一个列表
        return rs[0]['_num_']
        
    @classmethod
    async def find(cls, pk):
        ' find object by primary key. '
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None        
        # 1.将rs[0]转换成关键字参数元组，rs[0]为dict
        # 2.通过<class '__main__.User'>(位置参数元组)，产生一个实例对象
        return cls(**rs[0])
	
    '''
	User类现在就可以通过类方法实现主键查找：
    user = yield from User.find('123')
    '''	
    async def save(self):#调用时需要特别注意：user.save()没有任何效果，因为调用save()仅仅是创建了一个协程，并没有执行它。一定要用：yield from user.save()才真正执行了INSERT操作。
        # 获取所有value
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warning('failed to insert record: affected rows: %s' % rows)
    '''
	这样，就可以把一个User实例存入数据库：
	user = User(id=123, name='Michael')
	yield from user.save()
    '''
    
    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warning('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warning('failed to remove by primary key: affected rows: %s' % rows)

