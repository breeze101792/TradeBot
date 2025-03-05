
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

        self.message_queue_task_running = False
        self.message_queue_task_thread = None

        # Queue
        self.in_queue = kwargs.pop('in_queue')
        self.out_queue = kwargs.pop('out_queue')

        self.pipe_task_running = False
        self.pipe_task_thread = None

        self.in_ipc_queue = IPCMessageQueue(queue=self.in_queue, callback=None)
        self.in_ipc_queue.start()

        self.out_ipc_queue = IPCMessageQueue(queue=self.out_queue, callback=None)
        self.out_ipc_queue.start()

        super().__init__(*args, **kwargs)

    def recvtoMsgPipe(self):
        if self.parent_conn is None:
            dbg_error('This process not support MsgPipe.')
            return False
        content = self.child_conn.recv()
        return content

    def sendtoMsgPipe(self, content, need_replay=False):
        if self.parent_conn is None:
            dbg_error('This process not support MsgPipe.')
            return False

        tmp_message = {
            'action':1,
            'need_replay':need_replay,
            'content':content
        }

        self.parent_conn.send(tmp_message)
        return True
    def sendtoMsgQ(self, content, need_replay=False):
        tmp_message = {
            'action':1,
            'need_replay':need_replay,
            'content':content
        }
        self.in_queue.put(tmp_message)

        return True

    def pipe_task(self):
        self.pipe_task_running = True
        process_name = current_process().name
        thread_name = threading.current_thread().name

        dbg_info("[P %s][T %s] Task Start" % (process_name, thread_name))
        while self.pipe_task_running is True:
            # dbg_info("process task -> [%s] %s" % (p.pid, p.name))
            try:
                job = self.child_conn.recv()

                if job is None:
                    dbg_warning("[P %s][T %s] got None" % (process_name, thread_name))
                    self.quit()
                    continue
                else:
                    dbg_debug("[P %s][T %s] job: %s" % (process_name, thread_name, job))
            except KeyboardInterrupt:
                break
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                break
            finally:
                time.sleep(1)
    def message_queue_task(self):
        self.message_queue_task_running = True
        process_name = current_process().name
        thread_name = threading.current_thread().name

        dbg_info("[P %s][T %s] Task Start" % (process_name, thread_name))
        while self.message_queue_task_running is True:
            # dbg_info("process task -> [%s] %s" % (p.pid, p.name))
            try:
                if self.in_queue.qsize() > 0:
                    # dbg_info("[P %s][T %s] job: %s" % (process_name, thread_name, self.in_queue.get()))
                    dbg_debug("[P %s][T %s] job: %s" % (process_name, thread_name, self.in_queue.get()))
            except KeyboardInterrupt:
                break
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                break
            finally:
                time.sleep(1)

        dbg_info("[P %s][T %s] Task terminated" % (process_name, thread_name))

    def run(self):
        p = current_process()
        dbg_info("New process -> [%s] %s" % (p.pid, p.name))

        if self.child_conn is not None:
            self.pipe_task_thread = threading.Thread(target=self.pipe_task, name="pipe_task")
            self.pipe_task_thread.start()

        # self.message_queue_task_thread = threading.Thread(target=self.message_queue_task, name="message_queue_task")
        # self.message_queue_task_thread.start()

    def quit(self):
        dbg_info('Quiting {}.'.format(self.name))
        if self.parent_conn is not None:
            self.parent_conn.close()
        if self.child_conn is not None:
            self.child_conn.close()

        self.pipe_task_running = False
        if self.pipe_task_thread is not None:
            self.pipe_task_thread.join()

        self.message_queue_task_running = False
        if self.message_queue_task_thread is not None:
            self.message_queue_task_thread.join()

        self.in_ipc_queue.stop()
        self.out_ipc_queue.stop()
        # Terminate process incase it stuck.
        self.terminate()
