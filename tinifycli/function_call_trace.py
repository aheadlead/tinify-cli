# coding=utf-8

import logging

LOGGER = logging.getLogger('tinify-cli')

def tracecall(func):
    ''' 在日志上打出函数呼叫和返回的情况 '''
    def new_func(*args, **kwargs):
        ''' 待返回的函数 '''
        LOGGER.debug(u'进入 ' + func.__name__)
        ret = func(*args, **kwargs)
        LOGGER.debug(u'离开 ' + func.__name__)
        return ret
    return new_func

