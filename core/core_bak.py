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
        # Pipe, allocate via Pipe
        # self.parent_conn, child_conn = Pipe()
        self.parent_conn = kwargs.pop('parent_conn', None)
        self.child_conn = kwargs.pop('child_conn', None)
        # Queue
        self.in_queue = kwargs.pop('in_queue')
        self.out_queue = kwargs.pop('out_queue')

        # Others
        self.parent_handler = kwargs.pop('parent_handler', None)
        dbg_error(self.parent_handler)

        # Settings
        self.pipe_task_running = False
        self.pipe_task_thread = None
        #
        # self.in_ipc_queue = IPCMessageQueue(queue=self.in_queue, handler=self.parent_handler)
        # self.in_ipc_queue.start()

        self.out_ipc_queue = None

        super().__init__(*args, **kwargs)

    def sendtoMsgQ(self, content, need_replay=False):
        tmp_message = {
            'action':1,
            'need_replay':need_replay,
            'content':content
        }
        self.in_queue.put(tmp_message)

        return True
    def message_handler(self, message):
        dbg_info('[{}] Message: '.format(current_process().name, message))
        self.out_ipc_queue.send(message)
    def run(self):
        proc = current_process()
        dbg_info("Run Process: [%s] %s" % (proc.pid, proc.name))

        self.out_ipc_queue = IPCMessageQueue(queue=self.out_queue, handler=self.message_handler)
        self.out_ipc_queue.start()

    def quit(self):
        dbg_info('Quiting {}.'.format(self.name))

        self.in_ipc_queue.stop()
        self.out_ipc_queue.stop()

        # Terminate process incase it stuck.
        # self.terminate()


class Core:
    def __init__(self):

        self.parent_p = current_process()
        dbg_info("Core process init -> [%s] %s" % (self.parent_p.pid, self.parent_p.name))

        self.processes = []

        ## Start Child process
        ################################################################
        # Test process
        parent_conn, child_conn = Pipe()
        in_queue = Queue()
        out_queue = Queue()

        self.test_cp = ChildProcess(name='TestCP', parent_handler=self.message_handler, parent_conn=parent_conn, child_conn=child_conn, in_queue=in_queue, out_queue=out_queue)
        self.test_cp.start()
        self.processes.append(self.test_cp)

        ## Database
        in_queue = Queue()
        out_queue = Queue()

        self.database_cp = ChildProcess(name='Database', parent_handler=self.message_handler, in_queue=in_queue, out_queue=out_queue)
        self.database_cp.start()
        self.processes.append(self.database_cp)

    def message_handler(self, message):
        dbg_info('[{}] Message: '.format(current_process().name, message))
    def selftest(self):
        test_result=True
        dbg_info("Run self test.")
        # start_message = {'action':1, 'message':'IPC Test'}
        # self.parent_conn.send(start_message)
        # self.database_cp.in_queue.put(start_message)

        # self.test_cp.sendtoMsgPipe('IPC test, Pipe')
        self.test_cp.sendtoMsgQ('IPC test, MsgQueue')
        # self.test_cp.in_ipc_queue.send('IPC test, Pipe')

        dbg_info("Test finished.")
        return test_result
    def heatbeat(self):
        # TODO Impl heatbeat
        heart_beat_time=10
        while True:
            try:
                dbg_info('heart beatting every {}s'.format(heart_beat_time))
                self.selftest()
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

