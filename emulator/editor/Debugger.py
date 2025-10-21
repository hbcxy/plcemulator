# -*- coding: utf-8 -*-
from ValidateInput import validate_input
from ValidateInput import examples


class PLCDebugger:
    def __init__(self, var_status = None, log = None):
        self.setting = {'Subscribe':None,'Unsubscribe':None,'Force':None,'Release':None}
        self.defaultsetting={'Subscribe':None,'Unsubscribe':None,'Force':None,'Release':None}
        self.var_table = var_status
        self.IECPathToIdx = None
        self.logger = log
        
    def show_vars(self):
        print("current variables list:")
        for tuple in self.var_table:
            print(f'{tuple["idx"]}: {tuple["IEC_path"]}  {tuple["iec_type"]} {tuple["variable_status"]}   {tuple["fvalue"]}')

    def add_debug_var(self, name):
        if name in self.IECPathToIdx:
            idx, _ = self.IECPathToIdx[name]
            if self.var_table[idx]['variable_status'] == 'Registered':
                self.setting['Subscribe'] = self.var_table[idx]['IEC_path']
                print(f'variable {self.var_table[idx]["IEC_path"]} add to the debug list')
            else:
                print(f'variable {self.var_table[idx]["IEC_path"]} is already in the debug list')
        else:
            self.logger.write(f'variable {name} does not exist')

    def remove_debug_var(self, name):
        if name in self.IECPathToIdx:
            idx, _ = self.IECPathToIdx[name]
            if self.var_table[idx]['variable_status'] == 'Registered' or self.var_table[idx]['variable_status'] == 'Forced':
                self.setting['Unsubscribe'] = self.var_table[idx]['IEC_path']
                print(f'variable {self.var_table[idx]["IEC_path"]} is removed')
        else:
            print(f'variable {name} does not exist')

    def force_var(self, name, value):
        if name in self.IECPathToIdx:
            idx, _ = self.IECPathToIdx[name]
            if self.var_table[idx]['variable_status'] == 'Registered' or self.var_table[idx]['variable_status'] == 'Forced':
                iec_type = self.var_table[idx]['iec_type']
                is_valid, result = validate_input(iec_type, value)
                if is_valid :
                    self.setting['Force'] = (self.var_table[idx]['IEC_path'],result)
                    print(f'variable {self.var_table[idx]["IEC_path"]} has been forced as {value}')
                else :
                    print(f"Error: {result}. Example valid values for {iec_type}: {examples.get(iec_type, 'No examples available')}")
        else:
            print(f'variable {name} does not exist')

    def release_var(self, name):
        if name in self.IECPathToIdx:
            idx, _ = self.IECPathToIdx[name]
            if self.var_table[idx]['variable_status'] == 'Forced':
                self.setting['Release'] = self.var_table[idx]['IEC_path']
                print(f'variable {self.var_table[idx]["IEC_path"]} has been released')
            else:
                print(f'variable {self.var_table[idx]["IEC_path"]} has not been forced')
        else:
            print(f'variable {name} does not exist')

    def update(self, var_status, IECPathToIdx = None):
        self.var_table = var_status
        if IECPathToIdx is not None:
            self.IECPathToIdx = IECPathToIdx
        self.setting = self.defaultsetting.copy()