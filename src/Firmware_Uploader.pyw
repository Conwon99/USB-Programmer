# *******************************************************************************
#      _____ __          __
#     / ___// /_  ____  / /_______________  ____  ___
#     \__ \/ __ \/ __ \/ __/ ___/ ___/ __ \/ __ \/ _ \
#    ___/ / / / / /_/ / /_(__  ) /__/ /_/ / /_/ /  __/
#   /____/_/ /_/\____/\__/____/\___/\____/ .___/\___/
#                                       /_/
#
#   @author:            Connor Dorward
#   @description:       Enables file upload to a ShotScope device via USB. Functionality taken from emmc_loader. 
#   
#   @version notes : 1.1 - added restart_connection signal/slot so that user doesnt need to close program to use again
#                     1.2 - changed starting ui log message for customer version                      
#
# *******************************************************************************

import sys
import os
from pathlib import PurePath
from PyQt5.QtCore import pyqtSignal, QObject, QThread
from PyQt5.QtWidgets import QDialog, QApplication, QFileDialog
from PyQt5 import QtGui
from gui.gui import Ui_Dialog
from PyQt5.QtGui import QIcon, QPixmap
from openpyxl.styles import Font, Color
import time


from Device import Device

from PyQt5.QtWidgets import QMessageBox





class AppWindow(QDialog):
    overall_result = True

    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("Shot Scope USB Firmware Uploader v1.2")

        self.file_names = ()
        self.device_name= ""
        self.firmware = ""
        self.com_port = ""
        self.conn_status =False
        self.connect_called = False  # this ensures .connect() function in ConnectionHandler is fully ran before sending files



        self.show()
        self.ui.log.setText("> Please connect device via USB and select your firmware file ending in .fw using the 'Browse' button and click 'Program Device'") 

        # Thread used for file transfer
        self.batch_transfer = BatchTransfer("",self.ui) # initialise with directory name
        self.batch_transfer.append_log.connect(self.append_log) # allows GUI to be changed within batch transfer thread (need signal and slot)

        self.batch_transfer.restart_connection.connect(self.restart_connection)
  
        global device, DEBUG_MODE

        DEBUG_MODE = False

        device = Device(debug_mode=DEBUG_MODE) ## device as an object

        # Thread used for continually checking COM port for device
        self.conn = ConnectionHandler(device)
        self.conn.update_status.connect(self.display_status)
        self.conn.update_log.connect(self.append_log)
        self.conn.start()


        # Enable buttons      
        self.ui.programButton.setDisabled(False)
        self.ui.browseButton.setDisabled(False)

    

    def display_status(self):

        # Send GPI command to get FW and Dev name
        self.com_port = self.conn.com_port # take com port value from ConnectionHandler

        if self.com_port =="":
            self.firmware= ""
            self.device_name= ""

        else:
            device_data = self.get_device_data()
            self.firmware = device_data[0]
            self.device_name = device_data[3]  

        print("FW=",self.firmware)
        print("device=",self.device_name)

        #update GUI boxes
        self.ui.com_port.setText(self.com_port)
        self.ui.firmware.setText(self.firmware)
        self.ui.device_name.setText(self.device_name)

        


    def display_files(self):

        self.ui.file_selection.setText("") # clear box 

        for i in self.file_names:

            name = os.path.basename(str(i))

            suffix = PurePath(str(name)).suffix

            print(type(suffix))
            print(len(suffix))

            print("Suffix=",suffix )

            suffix.split('.')  

            print(suffix)

            #if suffix != " .fw" or suffix != " .fwg":

            print(type(Device.FILE_TYPES))

 #           if suffix== ".fw" or suffix== ".fwg":
            self.ui.file_selection.append(name) # append file names to box
            # else:
            #     msg="Incorrect File Type Selected. Only .fw and .fwg allowed."
            #     print(msg)
            #     self.append_log(msg)
            #     self.ui.file_selection.setText("") # clear box 
            #     self.file_names = ""

  


    def append_log(self,str):
        self.ui.log.append("> "+ str)

    def restart_connection(self):
        print("restart connection")
        self.conn = ConnectionHandler(device)
        self.conn.update_status.connect(self.display_status)
        self.conn.update_log.connect(self.append_log)
        self.conn.start()

                # Enable buttons      
        self.ui.programButton.setDisabled(False)
        self.ui.browseButton.setDisabled(False)
            


    # def gui_wait_for_run(self):

    #     print("Waiting for run button to be pressed...")
    #     self.ui.programButton.setDisabled(False)
    #     self.ui.browseButton.setDisabled(False)
    #     self.i = 0


    def browse_clicked(self):

        response = QFileDialog.getOpenFileNames(self, 'Open file')
        file_names = response[0]
        self.file_names = file_names
        self.batch_transfer.file_names = self.file_names # give batch_transfer objects dir_name attribute the directory 
        self.display_files()


    def program_clicked(self, user_text):

        print("self.file_names",self.file_names)

        if not self.file_names:
            print("Please Select Files to upload")
            self.append_log("Please select file(s) to upload")
            return


        

        self.ui.programButton.setDisabled(True)
        self.ui.browseButton.setDisabled(True)

        #Stop Connection Handler thread as can't have two resources accessing COM port at same time
        #Ensure ConnectionHandler function .connect() is finished before terminating
        while True:

            if self.conn.conn_called:
                 self.conn.terminate()
                 break


        print("Thread Status: ",self.conn.isRunning() )
        self.batch_transfer.start()    # Send files


    
    def get_device_data(self):

        response=["","","",""]

        try:
                # $SSGPI*5E
                err, response = device.send_cmd("GPI")
                # print(err)
                print(response)
                if err:
                    print("Problem getting device data")

        except:
            print("Problem Connecting to device...check device is connected and COM Port is valid")


        return response


## Thread Required to prevent GUI from not responding and to enable log updates during file transfer

class BatchTransfer(QThread):

    append_log = pyqtSignal(str)

    restart_connection = pyqtSignal()

    def __init__(self,file_names,ui):
        QThread.__init__(self)

        self.file_names = file_names
        self.ui = ui 


    def reboot(self):
        self.append_log.emit("Rebooting device to update firmware...")
        
        try:
                # $SSGPI*5E
                err, response = device.send_cmd("RBT")
                # print(err)
                print(response)
                if err:
                    print("Problem rebooting device")

        except:
            print("Problem rebooting  device...")


    def run(self):


        verify= True

        tx_count = 0
        vpass = 0
        vfail = 0
        failed_files = []

        try:

            for f in self.file_names:
                print("Filename=",f)


                path = str(f)
                self.append_log.emit("Uploading File: "+ path)

                f = PurePath(str(f))

                print("f.suffix = ",f.suffix)

                
                if f.suffix not in Device.FILE_TYPES:
                    continue

                
                if device.send_file(f):
                    print("Send file Error ({})".format(f))
                    self.append_log.emit("Send file Error ({})".format(f))
                    return

                tx_count += 1

                if not tx_count % 1000:
                    print("{} files sent..".format(tx_count))
                    self.append_log.emit("{} files sent..".format(tx_count))

                if verify:
                    print("verifying file..")
                    self.append_log.emit("verifying file..")

                    #for f in Path(self.file_names).iterdir():
                    # its verifying twice here even though one file

                    # for f in self.file_names:

                       # f = PurePath(str(f))
                    if f.suffix not in Device.FILE_TYPES:
                        continue

                    source_size = os.path.getsize(f)
                    file_name = f.name.split('.')[0]

                    err, size = device.check_file(
                        "{}{}".format(
                            Device.FILE_TYPES[f.suffix][2],
                            file_name
                        )
                    )

                    if err or (size * 2) != source_size:
                        vfail += 1
                        failed_files.append(f.name)
                        print("Verify {} - fail".format(file_name))
                        self.append_log.emit("Verify {} - fail".format(file_name))

                    else:
                        
                        vpass += 1
                        self.append_log.emit("File Upload Succesfull!")
                        #print("VPASS=",vpass)

                    if not (vpass + vfail) % 1000:
                        print("{} maps verified..".format(vpass + vfail))

        except (OSError, IOError, TypeError) as e:
            print("Something went wrong with the file transfer")
            self.append_log.emit("Something went wrong with the file transfer")
            print(e)

        print("{} files transferred to band.".format(tx_count))
       # self.ui.log.append("{} files transferred to band.".format(tx_count))

        print("{} files verified".format(vpass))
        self.append_log.emit("{} file(s) succesfully uploaded.".format(vpass))


        if vfail:
            print("Verify: {} files failed:".format(vfail))
            self.append_log.emit("Verify: {} files failed:".format(vfail))
            for f in failed_files:
                print("\t" + f)

        self.reboot()
        time.sleep(3)
        #conn = ConnectionHandler(device)

        # send a signal to redo process
        self.restart_connection.emit()

        # send a signal to redo process

    


# Thread which continually attempts to make COM port connection. Terminated when files sent to prevent access to COM port

class ConnectionHandler(QThread):

    update_status = pyqtSignal() # 
    update_log = pyqtSignal(str)
    connect_called = pyqtSignal(bool)
    #setPause = pyqtSignal()

    def __init__(self,device):
        QThread.__init__(self)

        self.device = device
        self.com_port =""
        self.message = ""
        self.pause = False
        self.conn_called = False


    def run(self):

        conn_status=False
        prev_conn_status=False

        while True:
            

            self.conn_called = False # used to ensure .connect() doesn't interfere with other COM port functionality
            time.sleep(0.1)

            if not device.connect(silent=True):



                self.message = "Device Disconnected!"
                #print(self.message)
                conn_status=False
                self.com_port=""

            else:
                self.message = "Device Connected!"
                #print(self.message)
                conn_status=True
                self.com_port = device.com_port

            self.connect_called.emit(True)
            self.conn_called = True

            if conn_status != prev_conn_status:    # If change in connection status, update GUI
               # print("conn_status changed to = ", conn_status)
                print(self.message)
                prev_conn_status = conn_status
                self.update_status.emit() # Tell main window com port changed
                self.update_log.emit(self.message) # Update Log
                time.sleep(2) # allows GPI command to be sent without 

            
            
            time.sleep(0.1)
            
                


def main():
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
