# coding=utf-8

''' Key 管理 '''

import logging
from multiprocessing.dummy import Pool as ThreadPool
import os
import random
import sys
import threading

from . import api

from . import shared_var

LOGGER = logging.getLogger('tinify-cli')

class EmptyKeyHolderException(Exception):
    pass

class TinifyCliKeyHolder(object):
    KEY_HOLDER_PATH = None

    @staticmethod
    def set_key_holder_path(path):
        TinifyCliKeyHolder.KEY_HOLDER_PATH = os.path.expanduser(path)

    def validate_key(self, key):
        tinify = api.TinifyCliClient(key)
        try:
            tinify.validate()
            LOGGER.info("Key " + key +
                        " 已使用 " + str(tinify.compression_count) + " 次")
            ret = True
        except api.AccountError, e:
            # alternatives of message:
            #   * "Your monthly limit has been exceeded
            #     (HTTP429/TooManyRequests)"
            #   * "Credentials are invalid (HTTP 401/Unauthorized)"
            if "exceeded" in e.message:
                LOGGER.warn("Key " + key + " 已超过用量限制")
                ret = True
            elif "invalid" in e.message:
                LOGGER.warn("Key " + key + " 是未经授权的")
                ret = False
        return ret

    def load_keys_from_file(self):
        # 检查文件存在
        if not os.path.exists(TinifyCliKeyHolder.KEY_HOLDER_PATH):
            LOGGER.critical("请创建文件 " +
                            TinifyCliKeyHolder.KEY_HOLDER_PATH +
                            ", 并将 Tinify API Key 存放于此文件中, 每个 Key "
                            "一行. ")
            sys.exit(1)

        with open(TinifyCliKeyHolder.KEY_HOLDER_PATH, 'r') as fp:
            keys_from_file = [key.strip() for key in fp]

            if not shared_var.is_no_validate:
                if shared_var.thread_num == 1:
                    # 方便调试
                    validity = map(self.validate_key, keys_from_file)
                else:
                    p = ThreadPool(shared_var.thread_num)
                    shared_var.key_loading_thread_pool = p  # 全局引用
                    validity = p.map_async(self.validate_key, keys_from_file)
                    while not validity.ready():
                        validity.wait(timeout=1)
                    p.close()
                    p.join()
                    shared_var.key_loading_thread_pool = None
                    validity = validity.get()
            else:
                # 如果要求跳过验证阶段, 这里生成一个虚假的全为 True 的 Key
                # 可用性 List , 以欺骗后段程序
                validity = [True] * len(keys_from_file)

            t0 = zip(validity, keys_from_file)  # 把可用性和 key 绑回来
            t1 = filter(lambda x: x[0] is True, t0)  # 过滤掉不可用的 key
            if len(t1) > 0:  # 如果过滤完后, 还有 key 的话
                t2 = zip(*t1)  # 提取出可用的 key 的 list
                _, self.keys = t2
                self.keys = list(self.keys)
            else:  # 如果没有 key 可用的话
                raise EmptyKeyHolderException()

    def __init__(self):
        self.keys_lock = threading.Lock()

    def acquire_key(self):
        with self.keys_lock:
            if len(self.keys) <= 0:
                raise EmptyKeyHolderException()
            return random.choice(self.keys)

    def remove_key(self, key):
        with self.keys_lock:
            try:
                self.keys.remove(key)
            except ValueError, e:
                # 如果同一时间, 多个 worker 拿到了同一把失效的 key , 此时可能
                # key 不存在于 key 箱中
                pass

