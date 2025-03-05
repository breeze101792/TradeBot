import threading
from multiprocessing import Process, Pipe, current_process, Queue
import time
import traceback

from utility.debug import *

class IPCRouting:
    def __init__(self, *args, **kwargs):
        pass
    def addQueue(self, name, queue):
        pass

class IPCBase:
    def __init__(self, *args, **kwargs):
        self.handler_fn = kwargs.pop('handler', None)
        self.send_fn = kwargs.pop('send', None)
        self.recv_fn = kwargs.pop('recv', None)

        self.task_name = 'message recv task'
        self.task_running = None
        self.task_thread = None
    def recv(self):
        if self.recv_fn is not None:
            return self.recv_fn()
        else:
            return None
    def send(self, content, need_replay = False):
        tmp_message = {
            'action':1,
            'sender':current_process().name,
            'need_replay':need_replay,
            'content':content
        }
        self.send_fn(tmp_message)
        return True
    def handler(self, message):
        dbg_debug(" message: %s" % ( message))
        if self.handler_fn is not None:
            self.handler_fn(message['content'])

    def recvTask(self):
        self.task_running = True

        process_name = current_process().name
        thread_name = threading.current_thread().name

        dbg_info("[P %s][T %s] Task Start" % (process_name, thread_name))
        while self.task_running is True:
            try:
                message = self.recv()

                if message is not None:
                    self.handler(message)
            except KeyboardInterrupt:
                break
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                continue
            finally:
                time.sleep(0.1)

    def startRcev(self):
        self.task_thread = threading.Thread(target=self.recvTask, name=self.task_name)
        self.task_thread.start()

    def stopRecev(self):
        self.task_running = False
        if self.task_thread is not None:
            self.task_thread.join()
            self.task_thread = None

class IPCMessageQueue(IPCBase):
    def __init__(self, *args, **kwargs):

        # Queue
        self.queue = kwargs.pop('queue')
        # self.handler = kwargs.pop('handler', None)

        super().__init__(send=self.queue.put, recv=self.__recv, *args, **kwargs)
    def __recv(self):
        if self.queue.qsize() > 0:
            return self.queue.get()
        else:
            return None


class IPCMessagePipe(IPCBase):
    def __init__(self, *args, **kwargs):

        # Queue
        self.pipe = kwargs.pop('pipe')
        # self.handler = kwargs.pop('handler', None)

        super().__init__(send=self.pipe.send, recv=self.pipe.recv, *args, **kwargs)
