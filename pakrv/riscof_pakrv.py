import os
import re
import shutil
import subprocess
import shlex
import logging
import random
import string
from string import Template
import sys

import riscof.utils as utils
import riscof.constants as constants
from riscof.pluginTemplate import pluginTemplate

logger = logging.getLogger()

class pakrv(pluginTemplate):
    __model__   = "pakrv"
    __version__ = "1.0"

    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        config = kwargs.get('config')

        if config is None:
            print("Please enter input file paths in configuration.")
            raise SystemExit(1)
        
        self.dut_exe = os.path.join(config['PATH'] if 'PATH' in config else "","pakrv")
        self.num_jobs = str(config['jobs'] if 'jobs' in config else 1)
        self.pluginpath=os.path.abspath(config['pluginpath'])
        self.isa_spec = os.path.abspath(config['ispec'])
        self.platform_spec = os.path.abspath(config['pspec'])
        if 'target_run' in config and config['target_run']=='0':
            self.target_run = False
        else:
            self.target_run = True

    def initialise(self, suite, work_dir, archtest_env):
       
       self.work_dir = work_dir
       self.suite_dir = suite
       self.compile_cmd = 'riscv32-unknown-elf-gcc -march={0} \
         -static -mcmodel=medany -fvisibility=hidden -nostdlib -nostartfiles -g\
         -T '+self.pluginpath+'/env/link.ld\
         -I '+self.pluginpath+'/env/\
         -I ' + archtest_env + ' {1} -o {2} {3}'
       
       self.objcopy_cmd = 'riscv32-unknown-elf-objcopy -O binary {0} {1}.bin'
       self.objdump_cmd = 'riscv32-unknown-elf-objdump -D {0} > {1}.disasm'
       self.hexgen_cmd  = 'python3 makehex.py {0}/{1}.bin > {0}/{1}.hex'

       # build simulation model
       self.toplevel = 'tb_pakrv'
       self.buidldir = 'verilator_work'
       comp_pakrv = './verilator --Mdir {0} +define+COMPLIANCE=1 -cc  \
        ../../src/*.sv ../../sub/src/*.sv ../src/{1}.sv             \
        -Wno-TIMESCALEMOD -Wno-WIDTHEXPAND -Wno-WIDTHTRUNC          \
        -I../../include/ -I../../sub/include/ --top-module {1}      \
        --exe ../src/{1}.cpp --trace --trace-structs --timing'.format(self.buidldir, self.toplevel)
       utils.shellCommand(comp_pakrv).run()
       build_pakrv = 'make -C {0} -f V{1}.mk'.format(self.buidldir, self.toplevel)
       utils.shellCommand(build_pakrv).run()

       # Simulate
       self.sim_pakrv = './{0}/V{1} \
        +imem={2}/{3}.hex           \
        +time_out=1000000'

    def build(self, isa_yaml, platform_yaml):

      ispec = utils.load_yaml(isa_yaml)['hart0']
      self.xlen = ('64' if 64 in ispec['supported_xlen'] else '32')
      self.isa = 'rv' + self.xlen
      if "I" in ispec["ISA"]:
          self.isa += 'i'
      if "M" in ispec["ISA"]:
          self.isa += 'm'
      if "C" in ispec["ISA"]:
          self.isa += 'c'

      self.compile_cmd = self.compile_cmd+' -mabi='+('lp64 ' if 64 in ispec['supported_xlen'] else 'ilp32 ')

    def runTests(self, testList):
      for testname in testList:
          testentry  = testList[testname]
          test       = testentry['test_path']
          test_dir   = testentry['work_dir']
          file_name  = 'pakrv'

          elf            = '{0}.elf'.format(file_name)
          compile_macros = ' -D' + " -D".join(testentry['macros'])
          marchstr = testentry['isa'].lower()
          compile_run    = self.compile_cmd.format(marchstr, test, elf, compile_macros)
          utils.shellCommand(compile_run).run(cwd=test_dir)

          objcopy_run    = self.objcopy_cmd.format(elf,file_name)
          utils.shellCommand(objcopy_run).run(cwd=test_dir)

          objdump_run    = self.objdump_cmd.format(elf,file_name)
          utils.shellCommand(objdump_run).run(cwd=test_dir)

          hexgen_run     = self.hexgen_cmd.format(test_dir,file_name)
          utils.shellCommand(hexgen_run).run()

          run_sim        = self.sim_pakrv.format(self.buidldir,self.toplevel,test_dir,file_name)
          utils.shellCommand(run_sim).run()
          
          cp_sig = 'cp -f DUT-{0}.signature {1}/.'.format(file_name, test_dir)
          utils.shellCommand(cp_sig).run()

      utils.shellCommand('rm DUT-{0}.signature'.format(file_name)).run()

      if not self.target_run:
          raise SystemExit

    
