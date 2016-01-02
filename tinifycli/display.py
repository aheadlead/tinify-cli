# coding=utf-8

''' 显示层 '''

import logging
import Queue
import time
import threading

from . import shared_var

class TinifyCliDisplay(object):
    def __init__(self, log_to_stderr=False, log_to_file=False):
        self.logger = logging.getLogger('tinify-cli')
        hndl = logging.StreamHandler()
        if shared_var.is_debug:
            hndl.setFormatter(
                logging.Formatter(
                    fmt='[%(levelname)s] %(filename)s:%(lineno)s %(funcName)s'
                    ' @ %(asctime)s => %(message)s',
                    datefmt='%H:%M:%S'))
            hndl.setLevel(logging.DEBUG)
        else:
            hndl.setFormatter(
                logging.Formatter(
                    fmt='[%(levelname)s] %(asctime)s : %(message)s',
                    datefmt='%H:%M:%S'))
            hndl.setLevel(logging.INFO)

        if log_to_stderr:
            self.logger.addHandler(hndl)
            self.logger.setLevel(logging.DEBUG)
        if log_to_file:
            filename = time.strftime(
                'tinify-cli.%Y-%m-%d-%H-%M-%S.log',
                time.gmtime())
            self.logger.addHandler(
                logging.FileHandler(
                    filename,
                    encoding='utf-8'))

        self.mailbox = Queue.Queue()  # for progress_bar_view

    def set_logging_level(self, level):
        '''
        level 可以取 "NOTSET", "DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"
        中的任何一个
        '''
        self.logger.setLevel(level=eval("logging." + level))

    #def start_progress_bar(self):
        #self.progress_bar_thread = threading.Thread(
            #target=self.progress_bar,
            #name="progress_bar")
        #self.progress_bar_thread.setDaemon(True)
        #self.progress_bar_thread.start()

    #def progress_bar(self):
        #pass
