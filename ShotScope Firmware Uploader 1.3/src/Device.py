#!/usr/bin/python3

# *******************************************************************************
#      _____ __          __
#     / ___// /_  ____  / /_______________  ____  ___
#     \__ \/ __ \/ __ \/ __/ ___/ ___/ __ \/ __ \/ _ \
#    ___/ / / / / /_/ / /_(__  ) /__/ /_/ / /_/ /  __/
#   /____/_/ /_/\____/\__/____/\___/\____/ .___/\___/
#                                       /_/
#
#   @author:            Sean Lannon
#   @co-author          Connor Dorward
#   @description:       An attempt to start putting the band Python functionality
#                       into a nice re-usable object
#   @co-author edits :  Change class name from ShotScopeV3 to 'device' which means that 
#                        the class can be applied to all shotscope products to avoid confusion
#   
#
#
# *******************************************************************************

import os
import time
import serial
from serial.tools.list_ports import grep
from pathlib import Path
import binascii
from binascii import unhexlify, hexlify
from zlib import crc32
from struct import pack, unpack

# *******************************************************************************


class Device:

    RX_ERRORS = {
        "TIMEOUT": "The connection timed out",
        "MEM": "eMMC / File system error",
        "PKT": "Bad packet length",
        "RAM": "Memory error",
        "SUM": "Bad checksum reported by band",
        "CRC": "Bad checksum received",
        "SS": "Unexpected header in response",
        "NOF": "File doesn't exist",
        "ERROR": "Unspecified error",
        "BAD_CMD": "The command failed due to invalid command or bad syntax/ parameter(s)",
        "FAIL": "The command failed due to system error",
        "UNKNOWN": "Undefined error"
    }

    HWID = "0483:5740"  # ST USB VID & PID
    BREAM_PATCH_TMP = "./.bream_hex.patch"
    BREAM_PATCH_REMOTE_NAME = "bream"

    # File types:
    # type info [file_type_id, type name, destination path, crc_required] is stored by file extension

    FILE_TYPES = {
        ".cmap": [0, "map", "1:/", False],
        ".index": [1, "index", "0:/", True],
        ".fw": [2, "firmware", "2:/", True],
        ".fwg": [3, "golden firmware", "2:/", True],
        ".sys": [13, "system file", "0:/", True],
        ".patch": [13, "patch file", "0:/", True]
    }

    FILE_CHUNK_MAX_BYTES = 256
    TX_CHUNK_RETRY = 4

    """ 
    @brief:   calculate and return a 1 byte XOR crc of the provided data
    @param:   string of data
    @param:   optional start value
    @return:  the 1 BYTE crc as a hex string
    """
    @staticmethod
    def get_crc(
        data,
        start_value=0
    ):
        crc = start_value
        for i in range(0, len(data)):
            if type(data) is str:
                crc ^= ord(data[i])
            else:
                crc ^= data[i]
        return format(crc, '02X')

    """
    @brief:   create object
    @param:   debug_mode      when True will output useful info to console
    @param:   baudrate        of serial connection
    @param:   timeout         of serial connection
    """
    def __init__(
            self,
            debug_mode=False,
            baudrate=115200,
            timeout=0.5
    ):
        self.debug = debug_mode
        self.baudrate = baudrate
        self.timeout = timeout
        self.fw_rc = 0  # release candidate or hotfix number
        self.tx_cmd = ""
        self._sp = None
        self._rx_header = None
        self.index_timestamp = None
        self.com_port = ""

    '''
    @brief:     object string representation
    '''
    def __str__(self):
        return "Shot Scope V3"

    '''
    @brief:     Simple connection test
    @param:     Returns True if connected else False
    '''
    def is_connected(self):
        if self._sp:
            return True
        else:
            return False

    '''
    @brief:     attempt to auto connect to the first STMicro device found connected to a
                COM port. If a connection is established, do a sanity check of the firmware
                build date to make sure the connection is good.
    @param:     silent - if True, will suppress error messages if VCOM port found but
                connection fails
    @return:    True if a good connection has been established, else False
    '''

    #this function still returning true when disconnected
    def connect(
            self,
            silent=False,
            timeout_seconds=1
    ):
        # if self.is_connected():
        #     return True

        while True:
            #print(timeout_seconds)
            if self._connect(silent):
                # print("Connection made")
                 return True
   
            if timeout_seconds == 0:
               # print("Timeout=0")
                return False

            else:
                timeout_seconds -= 1

            time.sleep(1)

    def _connect(
            self,
            silent=False
    ):
        for x in grep(self.HWID):
            # first match is used..

            self.com_port = x.device
          #  print("COM Port=",x.device )

            try:
                self._sp = serial.Serial(
                    x.device,
                    parity='N',
                    baudrate=self.baudrate,
                    timeout=self.timeout
                )

            except serial.serialutil.SerialException as e:
                #print("Serial Exception")
                self._sp = None
                return False

            return True

        # failed to detect..
        if self.debug and not silent:
            print("connect(): No devices found, is band plugged in?")

        return False

    '''
    @brief:     close an open serial connection if it exists
    '''
    def disconnect(
        self,
        wait_on_band=False
    ):
        if self._sp:
            self._sp.close()
            self._sp = None

        if wait_on_band:
            while grep(self.HWID):
                time.sleep(0.01)

        self._set_defaults()
        print("Disconnected..")

    '''
        @brief:     Format the data partition on the band. Rebuilds default system files.
                    All map data will be lost. Will not touch the firmware backup partition.
                    This can take half a minute.
    '''
    def format(self):
        _timeout_cache = self._sp.timeout
        self._sp.timeout = 40
        err, response = self.send_cmd("FMT")
        self._sp.timeout = _timeout_cache

        if err:
            print("Format Failed")

        return err

    '''
        @brief:     Check size of file
        @param:     absolute path on the band file system
        @return:    Tuple - True if error else False, file size in bytes - None if no file
    '''
    def check_file(
        self,
        abs_path
    ):
        size = None
        err, response = self.send_cmd("CHF,{}".format(abs_path))

        if not err and len(response):
            size = int(response[0])

        return err, size

    '''
        @brief:     Delete file
        @param:     absolute path on the band file system
        @return:    True if error else False
    '''

    def delete_file(
        self,
        abs_path
    ):
        err, response = self.send_cmd("DEL,{}".format(abs_path))
        return err

    '''
        @brief:     Make sure GPS is on
        @return:    True if error else False
    '''
    def gnss_start(
        self,
        cold_start = False
    ):
        if cold_start is True:
            print("GNSS cold start")
            err, response = self.send_cmd("GPS,2")
        else:
            print("GNSS hot start")
            err, response = self.send_cmd("GPS,1")
        
        return err

    '''
        @brief:     Make sure GPS is in standby state
        @return:    True if error else False
    '''
    def gnss_stop(
        self
    ):
        err, response = self.send_cmd("GPS,0")
        return err

    '''
        @brief:     Make sure GPS is on
        @return:    True if error else False
    '''
    def gps_clear_auto_backup_data(
        self,
    ):
        print("Clear Auto Backup Data Gps.\n To check that the data has been erased, you need to reboot the device after this command to clear the RAM in GPS")
        err, response = self.send_cmd("GPS,3")
       
        return err
        
    '''
        @brief:     Enable or disable show information on Display
        @param:     False - disable, True - enable
        @return:    True if error else False
    '''
    def gps_show_info(
        self,
        status = False
    ):
        if status is True:
            print("Enable Gps show information on display")
            err, response = self.send_cmd("GPS,4")
        else:
            print("Display Gps show information on display")
            err, response = self.send_cmd("GPS,5")
        
        return err

    '''
    @brief:   Send all files from the dir_path directory as CXD5605 FW.
              Files are transmitted in 32-byte chunks (64 bytes after conversion to ascii hex string).
              The order is the following:
              .ebin1
              .ebin2
              .ebin3
              .ebin4

    @param:   packet  string of data to send, usually in the form of <CMD>,<ARGS>
    @param:   boolean if False, defer getting a response
    @return:  Tuple - (bool, response) bool is True on error, response will contain error message
              or the actual response
    '''
    def send_cxd5605_fw(
        self,
        dir_path
    ):
        
        files = os.listdir(dir_path)

        sleepTime = 0.5
        status = True

        for f in files:
            if not os.path.exists(os.path.join(dir_path, f)):
                print("No such file: %s" % os.path.join(dir_path, f))
                status = False

        if not status:
            print("Can't find binaries")
            return

        for f in files:
            filepath = os.path.join(dir_path, f)
            #print("Send file %s" % filepath)
            ext = filepath.split('.')[-1] # the last element

            fileType = ""
            if ext == "ebin1":
                fileType = "H1"
            elif ext == "ebin2":
                fileType = "F1"
            elif ext == "ebin3":
                fileType = "H2"
            elif ext == "ebin4":
                fileType = "F2"
            else:
                print("Ignoring unsupported file: *.%s" % ext)

            if fileType:
                result = self.send_cxd5605_file(fileType, filepath)
                if not result:
                    print("Can't send %s" % fileType)
                    return
            time.sleep(1)

        return
            
    def send_cxd5605_file(
        self,
        filetype,
        filename
        ):
        command = "GFW"
        chunk_size = 64
        print("Sending file: %s" % filename)

        try:
            with open(filename, 'rb') as f:
                source_size = os.path.getsize(filename)
                print("Total size: %u" % source_size)
    
                time.sleep(0.05)

                # Initiate transmission
                cmd = "%s,%s,%u" % (command, filetype, source_size)
                print("Send Cmd: %s" % cmd)
                err, resp = self.send_cmd(cmd)
    
                if err:
                    print("Error: {}".format(err))
                    return False

                #print("!!! Return early")
                #return True

                # Send entire file
                # print() # One empty line for better readability
                bytes_sent = 0
                packet_cnt = 0
                total_size = source_size
                while source_size > 0:
                    chunkBin = 0
                    if source_size > chunk_size:
                        chunkBin = f.read(chunk_size)
                    else:
                        chunkBin = f.read(source_size)

                    bytes_sent += len(chunkBin)
                    packet_cnt += 1
                    print("Sending file: %u%%" % (float(bytes_sent) * 100/float(total_size)), end = '\r')

                    chunkHex = ""
                    for b in chunkBin:
                        chunkHex += "%02X" % b

                    cmd = ""
                    if source_size > chunk_size:
                        cmd = "%s,%u,%s" % (command, chunk_size, chunkHex)
                    else:
                        cmd = "%s,%u,%s" % (command, source_size, chunkHex)
                    
                    # print(chunkHex)
                    # print("Send Cmd: %s" % cmd)
                    err, resp = self.send_cmd(cmd)

                    if err :
                        print("Error occured")
                        print("Error: {}".format(err))
                        return False

                    if source_size > chunk_size:
                        source_size -= chunk_size
                    else:
                        source_size = 0


                print("File sent")
                return True

                print() # One empty line for better readability
        except IOError as e:
            print("Exception:")
            print(str(e))
            return False






    '''
        @brief:     Send bream patch file to band - patch is binary so hex string version is created 
                    for transport. Note that no attempt is made to chunk the file during conversion - 
                    this function will use up to 3x file size bytes of memory during conversion. 
        @param:     absolute path to source file to send
        @return:    Tuple - True if error else False
    '''

    def send_bream_patch(
        self,
        fp
    ):
        try:
            with open(fp, 'rb') as f:
                bin_data = f.read()

                if not len(bin_data):
                    raise IOError("empty file!")

                with open(self.BREAM_PATCH_TMP, "w+b") as hf:
                    hf.write(hexlify(bin_data))

            return self.send_file(
                Path(self.BREAM_PATCH_TMP),
                name_override=self.BREAM_PATCH_REMOTE_NAME
            )

        except IOError as e:
            print(str(e))
            return True

    '''
        @brief:     Send file to band
        @param:     absolute path to source file to send
        @return:    Tuple - True if error else False
    '''

    def send_file(
        self,
        fp,
        name_override=None
    ):
        if type(fp) is str:
            fp = Path(fp)

        if fp.suffix not in Device.FILE_TYPES:
            return True
        
        print("transferring {} file: {}.. {}".format(
            self.FILE_TYPES[fp.suffix][1],
            fp,
            "(as {})".format(name_override) if name_override is not None else ''
        ))

        # file meta..
        source_size = os.path.getsize(fp)
        file_name = fp.name.split('.')[0]
        crc = ','

        if name_override is not None:
            file_name = name_override

        if source_size % 2:
            print("file size should be even")
            return True

        if self.FILE_TYPES[fp.suffix][3]:
            # calculate crc
            crc += self.crc32(
                fp,
                convert_from_hex=True
            )

        err, response = self.send_cmd(
            "BGN,{},{},{}{}".format(
                self.FILE_TYPES[fp.suffix][0],
                int(source_size / 2),
                self.FILE_TYPES[fp.suffix][2] + file_name,
                crc
            )
        )

        if err:
            print("file meta fail")
            return err

        # ..loop through the file in chunks, tx'ing over serial to the band..

        total_tx = 0
        total_chunks = 0
        percentage_before = 0

        try:
            with open(fp, encoding='UTF-8') as f:

                # calculate file size
                pos_bk = f.tell()
                f.seek(0, 2)
                size = f.tell()
                f.seek(pos_bk)

                print ("File size: {}".format(size))

                chunks_to_send = size / self.FILE_CHUNK_MAX_BYTES
                #print("chunks to send", chunks_to_send)
                #time.sleep(10)

                while True:
                    chunk = f.read(self.FILE_CHUNK_MAX_BYTES)
                    
                    if not chunk:
                        print("No data left to send, band has not verified file")
                        self.send_cmd("END")
                        return True

                    total_chunks = total_chunks + 1
                    err, response = self.send_cmd(
                        "DAT," + chunk
                    )

                    #print(chunk)

                    if err:
                        print("DAT fail ({} bytes sent. {} chunks.)".format(total_tx, total_chunks))
                        return err
                    
                    total_tx = total_tx + len(chunk)
                    
                    
                    percentage = (total_chunks/chunks_to_send)*100
                    if percentage >= percentage_before +10:

                        print(percentage, "%\n")
                        percentage_before = percentage


                    if len(response):
                        # Good response when file verified, double check:
                        if total_tx != source_size or f.read(self.FILE_CHUNK_MAX_BYTES):
                            print("band seems to have prematurely verified file, are sizes correct?")
                            return True
                        else:
                            # GOOD FILE TRANSFER
                            return False

        except (IOError, OSError, ValueError) as e:
            print("Failed to open file - is file a UTF-8 encoded hex string? - {}".format(e))
            return True

    '''
        @brief:     get performance log from band
        @param:     remote file path - usually 0:/log
        @param:     local save path - ignore to use remote file name in current directory
        @return:    True if error else False
    '''

    def get_performance_log(self, remote_path, local_path = None):
    
        if local_path is None:
            local_path = Path(remote_path).name
            
        #Get total number of entries
        err, resp = self.send_cmd("GAE", return_response=True)
        
        entries_count = 0
        if not err:
            entries_count = int(resp[0], 16)

        #Get entries 10 at a time
        fileUtf8 = ""
        fileToUnhex = ""
        entries_offset = 0
        
        print("Total entries in log {}".format(entries_count))
        
        if entries_count <= 0:
            return False
        
        while entries_count > entries_offset:
                
            packet = "GDE,%X" % entries_offset
            # print("Packet: {}".format(packet))
            err, resp = self.send_cmd(packet, return_response = True)
            
            if err:
                print("Error. Response {}".format(resp))
                return True
            
            for entry in resp:
                #print("Entry {}".format(entry))
                #print(len(entry))
                fileUtf8 += entry + "\n"
                fileToUnhex += entry
                
            entries_offset += 10
        
        #print(fileUtf8)
        print("Received {} entries ({} bytes)".format(int(len(fileToUnhex) / 2 / 17), int(len(fileToUnhex) / 2)))
        
        #Save response to file
        fileHexified = open(local_path, "w")

        fileHexified.write(fileUtf8)
        fileHexified.flush()

        # file = open("bin_" + local_path, "wb")
        
        # file.write(unhexlify(fileToUnhex))
        # file.flush()
            
        return False
    




    def get_file_bin(
        self,
        remote_path,
        local_path=None
    ):
        if local_path is None:
            local_path = Path(remote_path).name

        try:
            with open(local_path, 'wb+') as loc:

                err, resp = self.send_cmd(
                    "GET,{}".format(
                        remote_path
                    ),
                    return_response=False
                )

                if err:
                    if len(resp):
                        print(resp)
                        
                    print("Send command error: {}".format(err))
                    return err

                resp = bytes()
                header_checked = False
                payload_bytes = 0
                total_received = 0
                running_checksum = 0

                '''
                    Receive data - check for error or fail response first, if header OK
                    check data payload length (param1) and if not all data received, 
                    keep receiving until all data has been read.
                '''
                while True:
                    try:
                        resp += self._sp.readline()
                        # print("GET resp: {}".format(resp))
                    except serial.SerialTimeoutException:
                        print("\t<-- TIMEOUT")
                        return True, ['Serial Timeout']
                    except serial.SerialException as e:
                        return True, ["Connection error: {}".format(e)]

                    if resp[-2:].decode('utf-8') != "\r\n":
                        # print("Continue.")
                        continue

                    print(resp)

                    # Divide message to header, payload and CRC
                    
                    header = resp[0:16].decode('utf-8')
                    payload = resp[16:len(resp) - 5]
                    tail = resp[len(resp) - 5: len(resp)].decode('utf-8')

                    print("MESSAGE DIVIDED")
                    print(header)
                    print(payload)
                    print(tail)

                    # Make sure parts are OK
                    if len(header) < 15:
                        print("Header is too short")
                        return True
                    
                    if len(payload) == 0:
                        print("File is empty")
                        return True

                    if len(tail) != 5:
                        print("End of message must contain 5 bytes")
                        return True
       
                    # Check for errors
                    if resp[2] == 'e':
                        return self._rx_error("BAD_CMD")
                    elif resp[2] == 'f':
                        return self._rx_error("FAIL")

                    # validate length parameter
                    if header[6] != ',' or header[15] != ',':
                        print("Payload size parameter malformed")
                        return True

                    payload_bytes = int(resp[7:15], 16)

                    print("Payload size: %u" % payload_bytes)

                    if payload_bytes == 0:
                        print("data size is 0 bytes!")
                        return True

                    header_checked = True

                    # Calculate CRC
                    running_checksum = self.get_crc(header[1:16])
                    running_checksum = self.get_crc(payload, int(running_checksum, 16))
                    
                    crc_get = tail[1:3]

                    print("CRC calc: %s, CRC get: %s" % (running_checksum, crc_get))

                    if running_checksum != crc_get:
                        print("Bad CRC")
                        return True

                    loc.write(payload)
                    print("File %s received" % local_path)
                    return False, ''

        except (IOError, TypeError) as e:
            print(str(e))
            return True, str(e)

    '''
        @brief:     get file from band
        @param:     remote file path
        @param:     local save path - ignore to use remote file name in current directory
        @return:    True if error else False
    '''

    def get_file(
            self,
            remote_path,
            local_path=None
        ):
            if local_path is None:
                local_path = Path(remote_path).name

            try:
                with open(local_path, 'w+', encoding='UTF-8') as loc:

                    err, resp = self.send_cmd(
                        "GET,{}".format(
                            remote_path
                        ),
                        return_response=False
                    )

                    if err:
                        if len(resp):
                            print(resp)
                            
                        print("Send command error: {}".format(err))
                        return err

                    resp = bytes()
                    header_checked = False
                    payload_bytes = 0
                    total_received = 0
                    running_checksum = 0

                    '''
                        Receive data - check for error or fail response first, if header OK
                        check data payload length (param1) and if not all data received, 
                        keep receiving until all data has been read.
                    '''
                    while True:
                        try:
                            resp += self._sp.readline()
                            # print("GET resp: {}".format(resp))
                        except serial.SerialTimeoutException:
                            print("\t<-- TIMEOUT")
                            return True, ['Serial Timeout']
                        except serial.SerialException as e:
                            return True, ["Connection error: {}".format(e)]

                        if resp[-2:].decode('utf-8') != "\r\n":
                            # print("Continue.")
                            continue

                        #print(resp)

                        resp = resp.decode('utf-8')

                        if not header_checked:
                            # \r\n could appear in data stream, so check header then use data
                            # length if no error
                            if len(resp) < 6:
                                print("Bad header received")
                                return True

                            elif resp[2] == 'e':
                                return self._rx_error("BAD_CMD")
                            elif resp[2] == 'f':
                                return self._rx_error("FAIL")

                            # validate length parameter
                            if len(resp) < 18 or resp[6] != ',' or resp[15] != ',':
                                print("Payload size parameter malformed")
                                return True

                            payload_bytes = int(resp[7:15], 16)

                            if payload_bytes == 0:
                                print("data size is 0 bytes!")
                                return True

                            print("Payload len: {}, Header: '{},{}'".format(payload_bytes, resp.split(",")[0],resp.split(",")[1]))
                            header_checked = True
                            running_checksum = self.get_crc(resp[1:16])  # start checksum calculation
                            resp = resp[16:]  # drop the header + payload size parameter
                            

                        total_received += len(resp)

                        if total_received > payload_bytes:
                            # we must have the CRC + \r\n..
                            running_checksum = self.get_crc(resp[:-5], int(running_checksum, 16))
                            print("CRC calc {}".format(running_checksum))
                            # store last chunk of data..
                            loc.write(resp[:-5])
                            if self.debug:
                                print(resp[:-5])
                            # CRC OK?
                            if running_checksum != resp[-4:-2]:
                                return self._rx_error("CRC")
                            else:
                                #time.sleep(2)
                                print("CRC match")
                                return False, ''
                        else:
                            running_checksum = self.get_crc(resp, int(running_checksum, 16))
                            # store data..
                            loc.write(resp)
                            if self.debug:
                                print(resp)
                            resp = bytes()

            except (IOError, TypeError) as e:
                print(str(e))
                return True, str(e)
            


    def get_debug_file(
        self
    ):
        try:
            command = "$SSGET,0:/DBGLOG*5A\r\n"
            print(command)
            self._sp.write(command.encode())

            # Save the response to a file
            response_file = "debuglog.log"
            with open(response_file, 'w') as file:
                serial_line = self._sp.readline().decode()
                print(serial_line)
                if str(serial_line) == "$SSeee*65\r\n":
                    msg = "Unable to get debug log - disconnect device, reboot and try again"
                    print(msg)
                    return False, msg
                file.write((str(serial_line)))
                while (len(serial_line) != 0):
                    serial_line = self._sp.readline().decode()
                    file.write((str(serial_line)))
            return True, ""
        except:
            msg = "Failed getting data from device, disconnect device, reboot and try again"
            print(msg)
            return False , msg

        
    """**************************************************************************"""

    """
    @brief:   Reset all internal variables to default
    """
    def _set_defaults(self):
        self.tx_cmd = ""

    '''
    @brief:   Send a packet of data to the band via the VCOM serial interface
              Takes care of the prepended header and simple 1 byte XOR checksum
              along with the termination sequence '\r\n'
    @param:   packet  string of data to send, usually in the form of <CMD>,<ARGS>
    @param:   boolean if False, defer getting a response
    @return:  Tuple - (bool, response) bool is True on error, response will contain error message
              or the actual response
    '''
    def send_cmd(
            self,
            packet,
            return_response=True
    ):
        if self._sp:
            packet = '$SS' + packet

            # cache the command being sent, can be used to verify valid response
            self.tx_cmd = packet.split(',')[0]

            crc = self.get_crc(packet[1:])  # exclude the $
            packet += '*' + crc + '\r\n'

            print("Command: {}".format(packet))

            if self.debug:
                print("\t--> {}".format(packet[:-2]))

            try:
                # print("Request: {}".format(str.encode(packet)))
                self._sp.write(str.encode(packet))
            except (serial.SerialTimeoutException, serial.SerialException):
                return True, "Connection error"

            if return_response:
                #print("send_cmd : getting response..")
                resp = self.get_response()
                #print("Response[{}]: {}".format(len(resp), resp))
                return resp
            else:
                print("here4")
                return False, ''
                

        else:
            print("send_packet(): Not connected..")

        return True, "No connection"

    '''
    @brief:   Read response lines from the serial interface
    @param:   expected    a string to look for in the comma separated list read
                          back from the band

    @return:  A tuple whose first value indicates an rx error, the second value
              is an array of the comma separated response not including the returned
              command
    
    @TODO:    Verify the return string against it's checksum!
    '''
    def get_response(
            self
    ):
        resp = bytes()
        self._rx_header = None

        while True:
            try:
                resp += self._sp.readline()
            except serial.SerialTimeoutException:
                print("\t<-- TIMEOUT")
                return True, ['Serial Timeout']
            except serial.SerialException as e:
                return True, ["Connection error: {}".format(e)]

            if resp[-2:].decode('utf-8') == "\r\n":
                break

        #print("Respbefore: {}".format(resp))
        resp = resp[:-2].decode('utf-8')
        #print("Append after: {}".format(resp))
        #print("get_response :",resp)

        if self.debug:
            if len(resp):
                print("\t<-- " + resp)
            else:
                print("\t<-- *NO RESPONSE*")

        # split and validate the payload..
        fields = resp.split('*')

        # validate CRC..
        if len(fields) < 2 or self.get_crc(fields[0][1:]) != fields[1]:
           # print("get_response crc validation fail")
            return self._rx_error("CRC")

        fields = fields[0].split(',')

        # check header length..
        if len(fields[0]) < len("$SSXYZ") or fields[0][:3] != "$SS":
            return self._rx_error("SS")

        # check for errors
        if fields[0][3] == 'e':
            return self._rx_error("BAD_CMD")

        elif fields[0][3] == 'f':
            return self._rx_error("FAIL")

        # everything seems in order..
        return False, fields[1:]

    '''
    @brief:     set a receive error value, print to console
    @return:    a tuple - True indicating rx error, and a list with the error message
    '''
    def _rx_error(
            self,
            error
    ):
        err = "Can't interpret error '{}'".format(error)

        #print("booty")
        print("Error: {}".format(error))
        
        try:
            err = self.RX_ERRORS[error]
        except KeyError:
            pass

        print(err)
        return True, err

    """
    # @brief:   This function assumes a file in hex format - the file is converted back 
    #           to raw binary in order for it's checksum to be calculated.
    """
    @staticmethod
    def crc32(
        path_to_file,
        convert_from_hex=True
    ):
        rv = "00000000"

        try:
            with open(path_to_file, 'rb') as f:

                _crc = 0xFFFFFFFF
                word_count = 0

                while True:
                    word = f.read(64)

                    if convert_from_hex:
                        word = unhexlify(word)

                    word = bytearray(word)

                    if len(word):
                        if len(word) % 4:
                            print("padding data with {} bytes..".format(4 - (len(word) % 4)))
                            word.extend([0x00]*(4 - (len(word) % 4)))

                        # convert bytes to array of Big-endian integers..
                        unpack_fmt = '>{}I'.format(int((len(word)/4)))
                        unpacked = unpack(unpack_fmt, bytes(word))
                        # reverse the bit order of each 32-bit integer..
                        _reversed = list(map(
                            lambda x: int('{:032b}'.format(x)[::-1], 2),
                            unpacked
                        ))
                        # convert back into Big-endian byte array..
                        _words = pack('>{}I'.format(len(_reversed)), *_reversed)

                        # calculate the running crc on the bytes (as unsigned value, hence the bitwise AND)
                        if word_count:
                            _crc = crc32(_words, _crc) & 0xFFFFFFFF
                        else:
                            _crc = crc32(_words) & 0xFFFFFFFF

                        word_count += 1
                    else:
                        break

                # with the final CRC, reverse bit order..
                bstring = '{:032b}'.format(_crc, 2)[::-1]
                # convert binary back to int..
                crc32_int = int(bstring, 2)
                # Invert bits..
                crc32_int ^= 0xFFFFFFFF
                # convert to hex string..
                rv = '{:08X}'.format(crc32_int)
                # reverse bloody bytes!!!!
                # rv = rv[6:8] + rv[4:6] + rv[2:4] + rv[0:2]
                print("CRC32 = 0x" + rv)
                f.close()

        except (OSError, IOError, binascii.Error) as e:
            print("_crc32(): " + str(e))

        return rv
