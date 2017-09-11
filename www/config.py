#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#把config_default.py作为开发环境的标准配置，把config_override.py作为生产环境的标准配置，
#我们就可以既方便地在本地开发，又可以随时把应用部署到服务器上。
#应用程序读取配置文件需要优先从config_override.py读取。为了简化读取配置文件，可以把所有配置读取到统一的config.py中：

'''
Configuration  融合default和override 获得当前环境下正确的配置
'''

__author__ = 'limengxia'

import config_default

class Dict(dict):
    '''
    Simple dict but support access as x.y style. 
    dict转换成Dict后可以这么读取配置：configs.db.host就能读到host的值。
    当然configs[db][host]也可以读到
    '''
    def __init__(self, names=(), values=(), **kw):
        super(Dict, self).__init__(**kw)
        for k, v in zip(names, values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

def merge(defaults, override): #合并
    r = {}
    for k, v in defaults.items(): 
        if k in override: #若override有这个key
            if isinstance(v, dict): #若值为字典
                r[k] = merge(v, override[k])#嵌套merge
            else:
                r[k] = override[k]#覆盖
        else:
            r[k] = v #用默认值
    return r 

def toDict(d):#Simple dict but support access as x.y style. 
    D = Dict()
    for k, v in d.items():
        D[k] = toDict(v) if isinstance(v, dict) else v
    return D

configs = config_default.configs

try:
    import config_override
    configs = merge(configs, config_override.configs)
except ImportError:
    pass

configs = toDict(configs)