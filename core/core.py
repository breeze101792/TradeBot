import threading
from multiprocessing import Process, Pipe, current_process, Queue
import time
import traceback

from utility.debug import *
from core.ipc import IPCMessageQueue

# class MessageElement:
#     Message=""
#     Content=None
#     def __init__(self):
#         self.Message()
#

class ChildProcess(Process):
    def __init__(self, *args, **kwargs):

        # Queue
        self.in_queue = kwargs.pop('in_queue')
        self.out_queue = kwargs.pop('out_queue')
        self.parent_handler = kwargs.pop('parent_handler', None)

        # Start in mainprocess
        self.out_queue_ipc = IPCMessageQueue(queue=self.out_queue, handler=self.parent_handler)
        self.out_queue_ipc.startRcev()

        # Start in childprocess
        # self.in_queue_ipc = None
        self.in_queue_ipc = IPCMessageQueue(queue=self.in_queue, handler=self.message_handler)

        super().__init__(*args, **kwargs)

    def message_handler(self, message):
        dbg_info('[{}] Message: '.format(current_process().name, message))
    def sendtoMsgQ(self, content, need_replay=False, blocking=False):
        tmp_message = {
            'action':1,
            'need_replay':need_replay,
            'content':content
        }
        self.in_queue.put(tmp_message)

        return True

    def run(self):
        p = current_process()
        dbg_info("New process -> [%s] %s" % (p.pid, p.name))

        self.in_queue_ipc = IPCMessageQueue(queue=self.in_queue, handler=self.message_handler)
        self.in_queue_ipc.startRcev()

    def quit(self):
        dbg_info('Quiting {}.'.format(self.name))

        if self.in_queue_ipc is not None:
            self.in_queue_ipc.stopRecev()

        # Terminate process incase it stuck.
        self.terminate()


class Core:
    def __init__(self):

        self.parent_p = current_process()
        dbg_info("Core process init -> [%s] %s" % (self.parent_p.pid, self.parent_p.name))

        self.processes = []
        self.proc_sg_queue = {}

        self.msg_queue = Queue()
        self.proc_sg_queue = {self.parent_p.name: self.msg_queue}
        ## Start Child process
        ################################################################
        # Test process
        in_queue = Queue()
        out_queue = Queue()

        self.test_cp = ChildProcess(parent_handler=self.message_handler, in_queue=in_queue, out_queue=out_queue, name='TestCP')
        self.test_cp.start()
        self.processes.append(self.test_cp)

        # self.out_queue_ipc = IPCMessageQueue(queue=out_queue, handler=self.message_handler)
        # self.out_queue_ipc.startRcev()

        ## Database
        in_queue = Queue()
        out_queue = Queue()

        self.database_cp = ChildProcess(in_queue=in_queue, out_queue=out_queue, name='Database')
        self.database_cp.start()
        self.processes.append(self.database_cp)

    # def createChildProcess(self, name):
    #     child_process = ChildProcess(in_queue=in_queue, out_queue=out_queue, name='TestCP')
    #     child_process.start()
    #
    #     self.processes.append(self.test_cp)
    def message_handler(self, message):
        # FIXME, impl routeer.
        dbg_info('[{}] Message: '.format(current_process().name, message))

    def selftest(self):
        test_result=True
        dbg_info("Run self test.")
        # start_message = {'action':1, 'message':'IPC Test'}
        # self.parent_conn.send(start_message)
        # self.database_cp.in_queue.put(start_message)

        # self.test_cp.sendtoMsgPipe('IPC test, Pipe')
        # self.test_cp.sendtoMsgQ('IPC test, MsgQueue')
        self.test_cp.in_queue_ipc.send('IPC test, MsgQueue')

        dbg_info("Test finished.")
        return test_result
    def heatbeat(self):
        # TODO Impl heatbeat
        heart_beat_time=10
        while True:
            try:
                dbg_trace('heart beatting every {}s'.format(heart_beat_time))
                time.sleep(heart_beat_time)
            except KeyboardInterrupt:
                break;
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                break
    def start(self):
        # NOTE. before running thread1
        if self.selftest() is False:
            raise("Self test fail.")

        self.heatbeat()

    def quit(self):
        dbg_info('Quiting core. Process:{}'.format(len(self.processes)))

        for each_process in self.processes:
            # dbg_info('Start terminate {}.'.format(each_process.name))
            each_process.quit()
            # each_process.terminate()
        self.processes = []

