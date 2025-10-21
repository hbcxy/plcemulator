#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import getopt
import json
from datetime import timedelta
from Emulator import Emulator
from Debugger import PLCDebugger
from runtime import PlcStatus
import zmq

from gettext import gettext as _

def custom_deserializer(dct):
    if '__timedelta__' in dct:
        # Convert dict with marker back to timedelta
        return timedelta(days=dct['days'], seconds=dct['seconds'], microseconds=dct['microseconds'])
    return dct


class Log:

    def __init__(self, logf):
        self.crlfpending = False
        self.logf = logf

    def write(self, s):
        if s:
            if self.crlfpending:
                sys.stdout.write("\n")
                if self.logf:
                    self.logf.write("\n")
                self.crlfpending = False

            s = s.encode('utf-8', errors='replace').decode('utf-8')

            sys.stdout.write(s)
            sys.stdout.flush()

        if self.logf is not None:
            self.logf.write(s)
            self.logf.flush()

    def write_error(self, s):
        if s:
            self.write("Error: "+s)

    def write_warning(self, s):
        if s:
            self.write("Warning: "+s)

    def write_file(self, s):
        if s and self.logf:
            if self.crlfpending:
                self.logf.write("\n")
                self.crlfpending = False

            s = s.encode('utf-8', errors='replace').decode('utf-8')
            
            self.logf.write(s)
            self.logf.flush()

    def flush(self):
        sys.stdout.flush()
        if self.logf:
            self.logf.flush()
        
    def isatty(self):
        return False

    def progress(self, s):
        if s:
            sys.stdout.write(s+"\r")
            self.crlfpending = True


class Laucher:
    def __init__(self, logf = None):
        self.projectPath = None
        self.buildpath = None

        self.logf = None
        if logf is not None:
            if isinstance(logf, str):
                try:
                    self.logf = open(logf, 'a', encoding='utf-8')
                    print(f"Logging to file: {logf}")
                except IOError as e:
                    print(f"Failed to open log file: {e}", file=sys.stderr)
            else:
                self.logf = logf
        self.logger = Log(self.logf)

        self.buffers = None
        self.PLCdebugger = PLCDebugger(log = self.logger)
        self.context = zmq.Context()
        self.router_socket = self.context.socket(zmq.ROUTER)
        self.router_socket.bind("tcp://*:5555")

    def __del__(self):
        if not self._closed and self.logf is not None:
            try:
                self.logf.close()
                self._closed = True
            except Exception as e:
                print(f"Log类关闭文件时出错: {e}")

    def Usage(self):
        print("Usage:")
        print("%s [Options] [Projectpath] [Buildpath]" % sys.argv[0])
        print("")
        print("Supported options:")
        print("-h --help                    print this help")
        print("-l --log path                write content of console info to given file")
        print("")
        print("")

    def SetCmdOptions(self):
        self.shortCmdOpts = "hl:"
        self.longCmdOpts = ["help", "log="]

    def ProcessOption(self, o, a):
        if o in ("-h", "--help"):
            self.Usage()
            sys.exit()
        if o in ("-l", "--log"):
            self.logf = open(a, 'a')
    
    def ProcessCommandLineArgs(self):
        self.SetCmdOptions()
        try:
            opts, args = getopt.getopt(sys.argv[1:], self.shortCmdOpts, self.longCmdOpts)
        except getopt.GetoptError:
            # print help information and exit:
            self.Usage()
            sys.exit(2)

        for o, a in opts:
            self.ProcessOption(o, a)

        if len(args) > 2:
            self.Usage()
            sys.exit()

        elif len(args) == 1:
            self.projectPath = args[0]
            self.buildpath = None
        elif len(args) == 2:
            self.projectPath = args[0]
            self.buildpath = args[1]
    
    def start(self):
        self.ProcessCommandLineArgs()
        self.emulator = Emulator(None, self.projectPath, self.buildpath, log = self.logger)
    
    def run(self):
        self.emulator.operate('Run')
        self.PLCdebugger.update(self.emulator.CTR.GetAllVariablesStatus(), self.emulator.CTR.GetIECPathToIdx())

    def build(self):
        self.emulator.operate("Build")

    def stop(self):
        self.emulator.operate('Stop')

    def subscribe(self, name):
        self.PLCdebugger.add_debug_var(name)
        self.emulator.operate('SetDebugData', self.PLCdebugger.setting)
        self.PLCdebugger.update(self.emulator.CTR.UpdateDebugVariablesStatus())

    def unsubscribe(self, name):
        self.PLCdebugger.remove_debug_var(name)
        self.emulator.operate('SetDebugData', self.PLCdebugger.setting)
        self.PLCdebugger.update(self.emulator.CTR.UpdateDebugVariablesStatus())

    def force(self, name, val):
        self.PLCdebugger.force_var(name, val)
        self.emulator.operate('SetDebugData', self.PLCdebugger.setting)
        self.PLCdebugger.update(self.emulator.CTR.UpdateDebugVariablesStatus())

    def release(self, name):
        self.PLCdebugger.release_var(name)
        self.emulator.operate('SetDebugData', self.PLCdebugger.setting)
        self.PLCdebugger.update(self.emulator.CTR.UpdateDebugVariablesStatus())


# 命令行调试
# if __name__ == '__main__':
#     with open('system.log', 'a') as logf:
#         laucher = Laucher(logf)
#         laucher.start()

#         while True:
#             command = input().strip()
#             command = command.lower()
#             if command == 'run':
#                 laucher.run()
#             elif command == 'build':
#                 laucher.build()
#             elif command == 'stop':
#                 laucher.stop()
#             elif command == 'subscribe':
#                 name = input("Enter name to subscribe: ").strip()
#                 laucher.subscribe(name)
#             elif command == 'unsubscribe':
#                 name = input("Enter name to unsubscribe: ").strip()
#                 laucher.unsubscribe(name)
#             elif command == 'force':
#                 name = input("Enter name to force: ").strip()
#                 value = input("Enter value: ").strip()
#                 laucher.force(name, value)
#             elif command == 'release':
#                 name = input("Enter name to release: ").strip()
#                 laucher.release(name)
#             else:
#                 print("Unknown command")


if __name__ == '__main__':
    with open('system.log', 'a') as logf:
        laucher = Laucher(logf)
        laucher.start()

        while True:
            client_id, _, msg_data = laucher.router_socket.recv_multipart()
            request = json.loads(msg_data.decode())
            request_type = request['type'].lower()
            
            if request_type == 'run':
                laucher.run()
            elif request_type == 'build':
                laucher.build()
            elif request_type == 'stop':
                laucher.stop()
            elif request_type == 'subscribe':
                laucher.subscribe(request['name'])
            elif request_type == 'unsubscribe':
                laucher.unsubscribe(request['name'])
            elif request_type == 'force':
                laucher.force(request['name'], request["value"])
            elif request_type == 'release':
                laucher.release(request['name'])