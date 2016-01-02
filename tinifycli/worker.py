# coding=utf-8

''' 压缩 '''

import logging
import traceback

from . import api as tf

from . import shared_var

LOGGER = logging.getLogger('tinify-cli')

def compress((src, dest, resize)):
    try:
        key = shared_var.key_holder.acquire_key()
        try:
            tinify = tf.TinifyCliClient(key)
            tinify.compress(src, dest, resize)
        except tf.AccountError, e:
            LOGGER.warn("Key " + key + " 不正确或用量耗尽, 移除本 Key 并重试")
            shared_var.key_holder.remove_key(key)
            return ("accountError", [src, dest, resize])
        except tf.ConnectionError, e:
            LOGGER.error("网络连接出错, 重试" + e.message)
            return ("netError", [src, dest, resize])
        except tf.ClientError, e:
            LOGGER.error("谜之错误, 请报告开发者" + e.message)
            traceback.print_exc()
            return ("clientError", [key, src, dest, resize])
        except tf.ServerError, e:
            LOGGER.error("服务器错误, 请稍后重试" + e.message)
            return ("serverError", [key, src, dest, resize])
    except AttributeError as err:
        # 在使用信号 SIGINT 终止程序时, 偶尔会抛出这个异常, 但原因未知
        LOGGER.info('发生了错误 ' + str(err))

    return "success",

