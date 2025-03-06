
# system file
import traceback
import time
import threading

# Local file
from utility.debug import *

class Core:
    def __init__(self):
        dbg_info('Core Initialising.')

        # Flags
        self.flag_core_running = False
        self.flag_heatbeat_running = False
        self.flag_service_running = False

        # Vars
        self.var_threading_delay = 0.1

        # Threading
        self.service_thread = None
        self.heatbeat_thread = None

        self.__initcheck()

    def __initcheck(self):
        # Check env setup is okay or not.
        pass
    def __sanitycheck(self):
        # Check sanity check on heart beat okay or not.
        dbg_info('Sanity Check.')
        pass

    def __heatbeat(self):
        dbg_info('Heatbeat Start.')
        self.flag_heatbeat_running = True

        # TODO Impl heatbeat
        heart_beat_interval_time=10
        while self.flag_core_running and self.flag_heatbeat_running:
            try:
                dbg_trace('heart beatting every {}s'.format(heart_beat_interval_time))
                self.__sanitycheck()
                time.sleep(heart_beat_interval_time)
            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                break;
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_heatbeat_running = False
        dbg_warning('Heatbeat End.')

    def __service(self):
        dbg_info('Service Start.')
        self.flag_service_running = True
        # TODO Impl heatbeat
        service_interval_time=1
        while True:
            try:
                dbg_trace('Service running in every {}s'.format(service_interval_time))
                time.sleep(service_interval_time)
            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                self.flag_service_running = False
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                self.flag_service_running = False

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_service_running = False
        dbg_warning('Service End.')
    def start(self):
        dbg_info('Core Start.')
        thread_list = []
        self.flag_core_running = True
        try:
            self.service_thread = threading.Thread(target=self.__service)
            self.service_thread.start()
            thread_list.append(self.service_thread)

            # Monitor Thread
            # self.heatbeat_thread = threading.Thread(target=self.__heatbeat, daemon=True)
            self.heatbeat_thread = threading.Thread(target=self.__heatbeat)
            self.heatbeat_thread.start()
            thread_list.append(self.heatbeat_thread)

            # wait for threading.
            for each_thread in thread_list:
                each_thread.join()

        except KeyboardInterrupt:
            dbg_warning("Keyboard Interupt.")
        except Exception as e:
            dbg_error(e)
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)

            self.flag_core_running = False

        finally:
            if self.flag_service_running and self.service_thread is not None:
                self.flag_service_running = False
                self.service_thread.join()
                self.service_thread = None

            if self.flag_heatbeat_running and self.heatbeat_thread is not None:
                self.flag_heatbeat_running = False
                self.heatbeat_thread.join()
                self.heatbeat_thread = None

            self.flag_core_running = False

        dbg_warning('Core End.')

    def quit(self):
        dbg_info('Core Quit.')
        # TODO, do final check.

