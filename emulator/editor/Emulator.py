#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import signal
from threading import Lock
from threading import Thread
os.environ['PYTHONIOENCODING'] = 'utf-8'
from LocalRuntimeMixin import LocalRuntimeMixin
from ProjectController import ProjectController


class Emulator(LocalRuntimeMixin):
    
    def __init__(self, parent, projectPath=None, buildpath=None, ctr=None, debug=True, log=None):
        self.logger = log
        LocalRuntimeMixin.__init__(self, self.logger)

        if projectPath is not None and os.path.isdir(projectPath):
            self.CTR = ProjectController(self, self.logger)
            self.Controler = self.CTR
            result, _err = self.CTR.LoadProject(projectPath, buildpath)
            if result is not None:
                self.logger.write_error(result)
        else:
            self.CTR = ctr
            self.Controler = ctr
            if ctr is not None:
                ctr.SetAppFrame(self, self.logger)

        signal.signal(signal.SIGTERM,self.signalTERM_handler)
    
    def signalTERM_handler(self, sig, frame):
        print ("Signal TERM caught: kill local runtime and quit, no save")
        self.KillLocalRuntime()
        sys.exit()

    
    def operate(self, meth, arg = None):
        self.methodLock = Lock()
        if self.CTR is not None:
            if self.methodLock.acquire(False):
                try:
                    self.CTR.CallMethod('_'+meth, arg)
                finally:
                    self.methodLock.release()