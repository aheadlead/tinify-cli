#!/usr/bin/env python
# coding=utf-8

'''
tinify-cli
~~~~~~~~~~

基于 Tinify 的批量图片压缩工具. 支持多线程, 支持正则匹配文件名, 多 API Key ,
以及除上传到 AWS S3 以外的全部的记载于 https://tinypng.com/developers/reference
的功能。

:copyright: (c) 2015 by aheadlead
:license: MIT

'''

import argparse
import functools
import logging
from multiprocessing.dummy import Pool as ThreadPool
import os
import platform
import re
import signal
import sys

from prettytable import PrettyTable

from .key_holder import TinifyCliKeyHolder, EmptyKeyHolderException
from .worker import compress
from .display import TinifyCliDisplay

from .function_call_trace import tracecall

from . import shared_var

__title__ = 'tinify-cli'
__author__ = 'aheadlead'
__license__ = 'MIT'
__copyright__ = 'Copyright 2015 aheadlead'
__version__ = '1.1'

LOGGER = logging.getLogger('tinify-cli')

def sigint_handler(_, dummy):
    ''' 处理 SIGINT 信号的函数 '''
    if shared_var.key_loading_thread_pool is not None:
        LOGGER.warning(u'关闭线程池')
        shared_var.key_loading_thread_pool.close()
        shared_var.key_loading_thread_pool.terminate()

    if shared_var.worker_thread_pool is not None:
        LOGGER.warning(u'关闭线程池')
        shared_var.worker_thread_pool.close()
        shared_var.worker_thread_pool.terminate()

    LOGGER.critical(u'依你的要求退出程序')
    sys.exit(1)
signal.signal(signal.SIGINT, sigint_handler)

def main():
    ''' 主函数, 命令行 tinify-cli 的入口点 '''
    parser = argparse.ArgumentParser(
        add_help=False,
        description=u'''基于 Tinify 的批量图片压缩工具. 支持多线程,
        支持正则匹配文件名, 多 API Key , 以及除上传到 AWS S3 以外的全部的记载于
        https://tinypng.com/developers/reference 的功能。''',
        epilog=u'''获取最新版本、反馈问题或建议, 请在
        http://www.github.com/aheadlead/tinify-cli 查阅或提出 issue . ''',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='tinify-cli')

    group1 = parser.add_argument_group(u'压缩')
    group1.add_argument(
        'src_dir',
        action='store',
        default='.',
        nargs='?',  # 使得这个参数变为非必须的
        help=u'装有待压缩图片的目录的路径')
    group1.add_argument(
        '-o', '--dest_dir',
        action='store',
        dest='dest_dir',
        default='.',
        help=u'输出路径')
    group1.add_argument(
        '--filename-pattern',
        action='store',
        dest='filename_pattern',
        default=r'^(.*\.(jpeg|JPEG|jpg|JPG|png|PNG))$',
        help=u'''通过此正则表达式匹配文件名, 并按照 --filename-replace
        所描述的字符串替换. ''')
    group1.add_argument(
        '--filename-replace',
        action='store',
        dest='filename_replace',
        default=r'tinify-\1',
        help=u'见 --filename-pattern ')
    group1.add_argument(
        '-p', '--preview-filename',
        action='store_true',
        dest='is_preview_filename',
        help=u'仅显示匹配上的文件名, 及其变化情况, 而不实际压缩')
    group1.add_argument(
        '-r', '--resize',
        action='store_true',
        dest='is_resize',
        help=u'调整图片的尺寸')
    group1.add_argument(
        '-m', '--resize-method',
        action='store',
        choices=['scale', 'fit', 'cover'],
        dest='resize_method',
        default='scale',
        help=u'''调整图片尺寸的方式. 一共有三种方式可选. 方式 scale ,
        将图片按原比例缩放, 宽度变为给定的宽度 (--width)
        或高度变为给定的高度 (--height) , 宽度或高度只能给定其一; 方式 fit
        , 将图片按原比例缩放, 宽度和高度均不超过给定的宽度 (--width) 和高度
        (--height) , 宽度和高度必须都给定; 方式 cover 会压缩图片的大小,
        但不压缩图片的尺寸, 而是直接将图片裁剪至给定的宽度和高度,
        裁剪的部位是根据 tinify 的智慧算法决定的,
        它自动的裁剪图片中最重要的部位.''')
    group1.add_argument(
        '--width',
        action='store',
        dest='width',
        help=u'见 --resize-method',
        type=int)
    group1.add_argument(
        '--height',
        action='store',
        dest='height',
        help=u'见 --resize-method',
        type=int)
    group1.add_argument(
        '--override',
        action='store_true',
        dest='is_override',
        help=u'''默认情况下, 如果一个文件处理之后的文件名,
        在输出目录已经存在同名文件, 那么这个文件不会被处理. 但开启此开关后,
        会变为直接覆盖目标文件.''')

    group2 = parser.add_argument_group(u'API Key')
    group2.add_argument(
        '-K', '--key-holder-path',
        action='store',
        default='~/.tinify-cli/keys',
        dest='key_holder_path',
        help=u'指定存放 API Key 的文件的路径')
    group2.add_argument(
        '-V', '--only-validate',
        action='store_true',
        dest='is_only_validate_key',
        help=u'仅验证 API Key 的可用性')
    group2.add_argument(
        '--no-validate',
        action='store_true',
        dest='is_no_validate',
        help=u'不验证 API Key 的可用性直接干活')

    group3 = parser.add_argument_group(u'杂项')
    group3.add_argument(
        '-h', '--help',
        action='help',
        help=u'显示本帮助信息')
    group3.add_argument(
        '-t', '--thread-num',
        action='store',
        dest='thread_num',
        default=1,
        help=u'指定工作线程数',
        type=int)
    group3.add_argument(
        '--debug',
        action='store_true',
        dest='is_debug',
        help=u'输出本程序的调试信息')
    group3.add_argument(
        '--debug-requests',
        action='store_true',
        dest='is_debug_requests',
        help=u'输出 requests 库的调试信息')
    group3.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s ' + __version__)

    args = parser.parse_args()

    shared_var.is_debug = args.is_debug
    shared_var.is_debug_requests = args.is_debug_requests
    shared_var.is_no_validate = args.is_no_validate
    shared_var.is_only_validate_key = args.is_only_validate_key
    shared_var.is_override = args.is_override
    shared_var.is_preview_filename = args.is_preview_filename
    shared_var.is_resize = args.is_resize

    shared_var.thread_num = args.thread_num

    # 为 '~' 提供支持
    shared_var.src_dir = os.path.abspath(
        os.path.expanduser(args.src_dir))  # 为 '~' 提供了支持
    shared_var.dest_dir = os.path.abspath(
        os.path.expanduser(args.dest_dir))
    shared_var.filename_pattern = args.filename_pattern
    shared_var.filename_replace = args.filename_replace
    shared_var.resize_method = args.resize_method
    shared_var.width = args.width
    shared_var.height = args.height



    TinifyCliKeyHolder.set_key_holder_path(args.key_holder_path)

    if shared_var.is_resize is True:
        if shared_var.width is None and shared_var.height is None:
            logging.critical('尺寸调整要求给定宽度和高度, 详细请查看帮助')
            sys.exit(1)

        if shared_var.resize_method == 'scale':
            if shared_var.width is not None and shared_var.height is not None:
                logging.critical(
                    '尺寸调整方式 scale 要求宽度和高度最多只给定一个')
                sys.exit(1)
        elif shared_var.resize_method in ['fit', 'cover']:
            if shared_var.width is None or shared_var.height is None:
                logging.critical(
                    '尺寸调整方式 fit 要求宽度和高度都给定')
                sys.exit(1)

    # 暂时我们用不到他, 以后加进度条可以用上
    TinifyCliDisplay(log_to_stderr=True)

    if not shared_var.is_debug_requests:
        # 屏蔽大部分低级别的 requests 的日志
        logging.getLogger('requests').setLevel(logging.CRITICAL)

    LOGGER.info('在 ' + TinifyCliKeyHolder.KEY_HOLDER_PATH + ' 寻找 Key')

    LOGGER.info('工作线程数为 ' + str(shared_var.thread_num))

    if shared_var.is_only_validate_key:  # 验证 API Key
        proc_validate_key()
        sys.exit(0)

    LOGGER.info('在 ' + shared_var.src_dir + ' 寻找图片文件')
    LOGGER.info('处理后将输出到 ' + shared_var.dest_dir)
    LOGGER.info('将按这样的规则匹配文件名: ' +
                shared_var.filename_pattern)
    LOGGER.info('文件名按这样的规则修改: ' + shared_var.filename_replace)

    if platform.system() == 'Darwin':
        LOGGER.info('按 Control+C 可以退出程序')
    else:
        LOGGER.info('按 Ctrl+C 可以退出程序')

    proc_compress()

def discover_file():
    ''' 根据 shared_var 里面描述的条件, 搜索符合条件的图片,
    返回一个满是文件名的 list .
    '''
    _0 = re.compile(shared_var.filename_pattern)  # 预先编译正则表达式, 提速
    # t1 = 源目录下符合正则的图片 list
    _1 = filter(_0.match, os.listdir(shared_var.src_dir))
    return _1

def filenames_convert(filenames):
    ''' 将给定的源文件名 list 转换为目标文件名的 list , 且一一对应 '''
    r = re.compile(shared_var.filename_pattern)
    ret = map(functools.partial(r.sub, shared_var.filename_replace), filenames)
    return ret

def print_filename_change(src_filenames, dest_filenames):
    ''' 用一个漂亮的表格打印出文件名的变化 '''
    table = PrettyTable()
    table.field_names = ['原文件名', '目标文件名']
    [table.add_row(row) for row in zip(src_filenames, dest_filenames)]
    LOGGER.info(os.linesep + table.get_string())

def proc_validate_key():
    ''' 过程: 验证 API Key '''
    LOGGER.info('验证 API Key')

    key_holder = TinifyCliKeyHolder()
    shared_var.key_holder = key_holder
    key_holder.load_keys_from_file()

def proc_compress():
    ''' 过程: 压缩 '''
    LOGGER.info('')

    key_holder = TinifyCliKeyHolder()
    shared_var.key_holder = key_holder
    if shared_var.is_no_validate:
        LOGGER.info('你要求跳过验证 API Key')
    key_holder.load_keys_from_file()

    src_filenames = discover_file()
    dest_filenames = filenames_convert(src_filenames)

    LOGGER.info('发现了 ' + str(len(src_filenames)) + ' 张图片')

    if shared_var.is_preview_filename:
        print_filename_change(src_filenames, dest_filenames)
        sys.exit(0)

    src_file_paths = \
            [os.path.join(shared_var.src_dir, filename) \
            for filename in src_filenames]
    dest_file_paths = \
            [os.path.join(shared_var.dest_dir, filename) \
            for filename in dest_filenames]

    file_paths = zip(src_file_paths, dest_file_paths)

    if not shared_var.is_override:  # 如果不要求强行覆盖
        def filter_fileexists((_, dest_file_path)):
            ''' 判断路径 dest_file_path 是否已经有一个文件 '''
            if os.path.isfile(dest_file_path):
                LOGGER.warn('目标文件 ' + dest_file_path +
                            ' 已存在, 将跳过此图片')
                return False
            return True
        file_paths = filter(filter_fileexists, file_paths)

    if shared_var.is_resize is True:
        resize_param = shared_var.resize_method, \
                shared_var.width, shared_var.height
    else:
        resize_param = None

    task_list = [(path[0], path[1], resize_param)
                 for path in file_paths]

    while True:
        if shared_var.thread_num == 1:  # 单线程方便调试
            ret = map(compress, task_list)
        else:
            # 多线程
            thread_pool = ThreadPool(shared_var.thread_num)
            # 全局的线程池引用, 方便程序收到 SIGINT 快速退出
            shared_var.worker_thread_pool = thread_pool
            ret = thread_pool.map_async(compress, task_list)
            while not ret.ready():
                ret.wait(timeout=2)
            thread_pool.close()
            thread_pool.join()
            ret = ret.get()
            shared_var.worker_thread_pool = None

        LOGGER.debug('完成了一次 mapping ')

        # 过滤掉执行成功的任务
        failed_task_list = filter(lambda reason: reason[0] != 'success', ret)
        if len(failed_task_list) == 0:  # 全部执行完毕?
            LOGGER.info('任务执行完毕')
            sys.exit(0)

        new_task_list = []  # 准备一个新的任务列表
        for failed_task in failed_task_list:  # 处理失败的任务
            failed_reason = failed_task[0]  # 失败的原因
            args = failed_task[1]  # 拿到任务的参数

            def just_retry_handler():
                ''' '''
                new_task_list.append(args)

            {
                "accountError": just_retry_handler,
                "netError": just_retry_handler,
                "clientError": just_retry_handler,
                "serverError": just_retry_handler
            }[failed_reason]()

        task_list = new_task_list

