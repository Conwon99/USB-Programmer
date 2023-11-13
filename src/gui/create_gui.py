import subprocess

command = "pyuic5 gui.ui > gui.py" 
subprocess.call(command, shell=True, stderr=subprocess.STDOUT)
        

