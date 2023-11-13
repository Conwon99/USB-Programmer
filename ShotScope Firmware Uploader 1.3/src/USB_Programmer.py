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
#                    1.2 - changed starting ui log message for customer version                      
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
import subprocess

from Device import Device

from PyQt5.QtWidgets import QMessageBox





class AppWindow(QDialog):
    overall_result = True

    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("ShotScope Firmware Uploader 1.3")

        self.file_names = ()
        self.device_name= ""
        self.firmware = ""
        self.com_port = ""
        self.mcu_serial = ""
        self.pcb_serial = ""
        self.pcb_revision ="" 
        self.map_preload = "" 
        self.bootloader= ""
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
        self.disable_buttons(False)      



    def display_status(self):

        # Send GPI command to get FW and Dev name
            self.com_port = self.conn.com_port # take com port value from ConnectionHandler

            if self.com_port =="":
                self.firmware= ""
                self.device_name= ""
                self.mcu_serial= ""
                self.pcb_serial= ""
                self.pcb_revision= ""
                self.map_preload= ""
                self.bootloader= ""

            else:
                
                device_data = self.get_device_data()
                print(device_data)
                self.firmware = device_data[0]
                self.mcu_serial = device_data[1]
                self.pcb_serial = device_data[2]
                self.device_name = device_data[3] 
                self.pcb_revision = device_data[4]
                self.map_preload = device_data[5]
                self.bootloader = device_data[6]   

            print("FW=",self.firmware)
            print("device=",self.device_name)

            #update GUI boxes
            self.ui.com_port.setText(self.com_port)
            self.ui.firmware.setText(self.firmware)
            self.ui.device_name.setText(self.device_name)
            self.ui.mcu_serial.setText(self.mcu_serial)
            self.ui.pcb_serial.setText(self.pcb_serial)
            self.ui.pcb_revision.setText(self.pcb_revision)
            self.ui.map_preload.setText(self.map_preload)
            self.ui.bootloader.setText(self.bootloader)

        


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

            if suffix== ".fw" or suffix== ".fwg":
                self.ui.file_selection.append(name) # append file names to box
            else:
                msg="Incorrect File Type Selected. Only .fw and .fwg allowed."
                print(msg)
                self.append_log(msg)
                self.ui.file_selection.setText("") # clear box 
                self.file_names = ""

  
    def disable_buttons(self,logic):
        self.ui.programButton.setDisabled(logic)
        self.ui.browseButton.setDisabled(logic)
        self.ui.gamelogButton.setDisabled(logic)
        self.ui.debuglogButton.setDisabled(logic)


    def append_log(self,str):
        self.ui.log.append("> "+ str)

    def stop_connection(self):

        while True:

            if self.conn.conn_called:
                    self.conn.terminate()
                    break

    def restart_connection(self,showMessage):
        print("restart connection")
        self.conn = ConnectionHandler(device)

        if showMessage is None:
            print("none")

        elif showMessage:
            self.conn.update_log.connect(self.append_log)

        self.conn.update_status.connect(self.display_status)
        self.conn.start()

        # Enable buttons
        time.sleep(1)     
        self.disable_buttons(False) 

            


    def get_game_log(self):
        err, size = device.check_file("0:/log")

        print("err=",err)
        print("size",size)

    
        if err or size == 0:
            msg = "File check failed - the log likely doesn't exist"
            print(msg)
            self.append_log(msg)
            return False
        
        msg = "Game Log File Size: " + str(size)
        print(msg)
        self.append_log(msg)
        
        err = device.get_performance_log("0:/log", "game.log")

        if not err:
            err = device.delete_file("0:/log")
            if not err:
                
                return True
        else:
            msg = "error getting game log"
            self.append_log(msg)
            print(msg)
            return False


    def get_debug_log(self):
        err, size = device.check_file("0:/dbglog")

        if err or size == 0:
            msg = "File check failed - the log likely doesn't exist"
            return False, msg
        
        msg = "Debug Log Size=" + str(size)
        self.append_log(msg)

        print("Fetching debug log file ({} bytes) - please wait..".format(size))
        #err, resp = device.get_file("0:/dbglog", "dbglog.log")

        result, msg = device.get_debug_file() # returns True if succesful

        if result:
            err = device.delete_file("0:/dbglog")

            if not err:
                return True, ""
            else:
                msg = "Failed to delete file - please disconnect device, reboot and try again"
                return False, msg
            
        return False, msg


            

        


        #print("err=",err)


        # if err: # 
        #     msg = "Error getting debug log - please disconnect cable, reboot device and try again"
        #     print(msg)
        #     self.append_log(msg)
        #     # err = device.delete_file("0:/DBGLOG")
        #     # if not err:
        #     #     self.append_log("debug log succesfully deleted from device")
        #     #     return True
        #     return False
        # else:
        #     print("True!!!")
        #     return True

        

    # def startgps_clicked(self):
    #     print("startgps_clicked")
    #             # Turn on DAC with value 0
    #     if self.gnss_start(self.device_name):
    #         print("SUCCESS")

    #     else:
    #         print("NOT SUCCESS")


    # def downloadgps_clicked(self):
    #     print("downloadgps_clicked")

    #     if self.gnss_download():
    #         print("Log downloaded and deleted")
    #     else:
    #         print("Problem downloading log")



    def gamelog_clicked(self):
        print("gamelog clicked")

        self.disable_buttons(True)

        #Get the current working directory
        cwd = os.getcwd()


        self.stop_connection()
            
        print("Thread Status: ",self.conn.isRunning() )

        if self.get_game_log():
            msg = "Gamelog downloaded to " + cwd + "\\game.log"
            print(msg)
            self.append_log(msg)
            self.append_log("File succesfully deleted from device")

            file_path = cwd + "/game.log"
            subprocess.Popen(["notepad.exe", file_path])

        self.restart_connection(False) # restart COnnectionHandler with device connected msg set to false
        

        

    def debuglog_clicked(self):

        self.stop_connection()
        print("Thread Status: ",self.conn.isRunning() )

        msg = "Retreiving Debug Log..."
        print(msg)
        self.append_log(msg)

        self.disable_buttons(True)

        #Get the current working directory
        cwd = os.getcwd()

        result, msg = self.get_debug_log()


        if result:

            msg = "Debug log downloaded to " + cwd + "\\debuglog.log"
            print(msg)
            self.append_log(msg)
            self.append_log("File succesfully deleted from device")

            file_path = cwd + "\\debuglog.log"
            subprocess.Popen(["notepad.exe", file_path])

        else:
            print(msg)
            self.append_log(msg)

        self.restart_connection(False) # restart COnnectionHandler with device connected msg set to false
        


    def browse_clicked(self):

        response = QFileDialog.getOpenFileNames(self, 'Open file')

        print("response=",response)
        file_names = response[0]

        print("file_names=",file_names)
        self.file_names = file_names
        self.batch_transfer.file_names = self.file_names # give batch_transfer objects dir_name attribute the directory 
        self.display_files()


    def program_clicked(self, user_text):

        print("self.file_names",self.file_names)

        if not self.file_names:
            print("Please Select Files to upload")
            self.append_log("Please select file(s) to upload")
            return

        self.disable_buttons(True)

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
        

    # def gnss_start(self,device_name):

    #     result =True

    #     if device_name == "g5" or device_name == "v3" or device_name == "h4":
    #         err, response = device.send_cmd("GPS,2")
    #         print("not a n x5")
    #         print(response)
    #     else: 
    #         #for x5
    #         print("X5 device identified")
    #         err, response = device.send_cmd("TST,GPS_OFF")
    #         err, response = device.send_cmd("TST,GPS_ON")
    #         if not err:
    #             err, response = device.send_cmd("TST,GPS_LOG_ON")
    #         if err:
    #             print("GPS command error")
    #             return False
    #         else:
    #             return True # success


    #     print("gnns start")

    
    # def gnss_download(self):
    #     print("gnss download")
    #     try:
    #         err, response = device.send_cmd("TST,GPS_LOG_OFF")

    #         if err:
    #             return False
            
    #         err, size = device.check_file("0:/gnss")

    #         if err or size == 0:
    #             print("File check failed - the log likely doesn't exist")
    #             return

    #         print("Fetching log file ({} bytes) - please wait..".format(size))
    #         err, resp = device.get_file("0:/gnss", "gnss.log")

    #         if not err:
    #                 err = device.delete_file("0:/gnss")

    #                 if err:
    #                     print("there was a problem deleting the log")
    #                 else:
    #                     print("log deleted")
    #                     return True
                        
    #         else:
    #             print("Error: {}. Resp: {}".format(err, resp))
    #             return False
                
    #     except:
    #         print("gnss download exception")
    #         return False




## Thread Required to prevent GUI from not responding and to enable log updates during file transfer

class BatchTransfer(QThread):

    append_log = pyqtSignal(str)

    restart_connection = pyqtSignal(bool)

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
        self.restart_connection.emit(True)

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
