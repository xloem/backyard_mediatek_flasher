import fcntl, os, struct, termios, time
DEV = '/dev/ttyACM0'
if os.path.exists(DEV):
    print(f'Please disconnect {DEV} by holding the power button for 10 seconds.')
    while os.path.exists(DEV):
        time.sleep(0.5)
    print(f'Thank you.')

print(f'Please connect {DEV} .')
while True:
    try:
        fd = os.open(DEV, os.O_RDWR|os.O_NOCTTY)#|os.O_NONBLOCK)
        break
    except FileNotFoundError:
        time.sleep(0.5)
    except PermissionError:
        time.sleep(0.5)

# tcgetattr
# $ stty -F /dev/ttyACM0 --save
# 1804:0:10b2:a20:3:1c:7f:15:1:1:0:0:11:13:1a:0:12:f:17:16:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0:0    
# $ stty -F /dev/ttyACM0 --all
# speed 115200 baud; rows 0; columns 0; line = 0;
# intr = ^C; quit = ^\; erase = ^?; kill = ^U; eof = ^A; eol = <undef>; eol2 = <undef>; swtch = <undef>; start = ^Q; stop = ^S; susp = ^Z; rprnt = ^R; werase = ^W; lnext = ^V; discard = ^O;
# min = 0; time = 1;

# incomplete
iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(fd)
iflag = 0x1804
oflag = 0
cflag = 0x10b2
lflag = 0xa20
cc[:19] = b"\x03\x1c\x7f\x15\x01\x01\x00\x00\x11\x13\x1a\x00\x12\x0f\x17\x16\x00\x00\x00"
termios.tcsetattr(fd, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
# tcsetattr

# stop any nul break bytes and flush
TIOCCBRK = 0x5428
fcntl.ioctl(fd, TIOCCBRK)
termios.tcflush(fd, termios.TCIOFLUSH)

# set DTR and RTS modem flags
fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack('@i', termios.TIOCM_DTR | termios.TIOCM_RTS))

# serial port open

def rx(ct):
    data = b''
    while len(data) < ct:
        subdata = os.read(fd, ct - len(data))
        #print('rx <-', subdata) 
        data += subdata
    return data
def tx(data):
    len = os.write(fd, data)
    #print('tx ->', data[:len])
    return len

print(f'Handshaking with boot rom...')

# 'READY', then the bit inverse of 4 bytes
sends = [0xa0, 0x0a, 0x50, 0x05] 
connected = False
while not connected:
    for send in sends:
        tx(bytes([send]))
        while True:
            try:
                recv = rx(1)
                connected = False
                break
            except BlockingIOError:
                continue
        if recv == b'R':
            recv += rx(4)
            if recv == b'READY':
                print(recv)
                break
        if recv != bytes([~send & 0xff]):
            raise Exception(f'Unexpected handshake byte: {hex(send)} -> {recv}. Remove battery and rehandshake with volume down held.')
        connected = True
    
connected = True

def cmd(code, fmt=None, expect_echo=True):
    if type(code) is bytes:
        cmd = code
        code = cmd[0]
    else:
        cmd = bytes([code])
    tx(cmd)
    if expect_echo:
        repl = rx(1)
        if repl != cmd:
            raise Exception(f'Unexpected reply: {hex(code)} -> {hex(repl[0])}')
    if fmt is None:
        return None
    fmt = '>' + fmt
    data = rx(struct.calcsize(fmt))
    data = struct.unpack(fmt, data)
    if len(data) == 1:
        data = data[0]
    return data

# from http://www.lieberbiber.de/2015/07/04/mediatek-details-partitions-and-preloader/
CMD_GET_BL_VER        = 0xfe #   Get Preloader version (seems to be always “1”)
CMD_GET_HW_SW_VER     = 0xfc #   Return hardware subcode, hardware version and software version
CMD_GET_HW_CODE       = 0xfd #   Return hardware code and status
CMD_SEND_DA           = 0xd7 #   Send a special “Download Agent” binary to the SoC, signed with a key.
CMD_JUMP_DA           = 0xd5 #   Set boot mode to DOWNLOAD_BOOT and start execution of the Download Agent sent in the previous step.
CMD_GET_TARGET_CONFIG = 0xd8 #   Get supported Preloader configuration flags
CMD_READ16            = 0xa2 #   Read data from the SoC memory (16 bit length parameter)
CMD_WRITE16           = 0xd2 #   Write data into SoC memory (16 bit length parameter)
CMD_READ32            = 0xd1 #   Read data from the SoC memory (32 bit length parameter)
CMD_WRITE32           = 0xd4 #   Write data into SoC memory (32 bit length parameter)
CMD_PWR_INIT          = 0xc4 #   Initialise the power management controller (effectively a null op because it is already on)
CMD_PWR_DEINIT        = 0xc5 #   Shut down the power management controller (effectively a null o)
CMD_PWR_READ16        = 0xc6 #   Read 16 bits of data from the power management controller interface memory
CMD_PWR_WRITE16       = 0xc7 #   Write 16 bits of data to the power management controller interface memory

bootloader_version = cmd(CMD_GET_BL_VER, 'B', expect_echo=False)
print('Device preloader version:', hex(bootloader_version))

hw_code, hw_code_status = cmd(CMD_GET_HW_CODE, 'HH')
hw_subcode, hw_version, sw_version, hw_sw_ver_status = cmd(CMD_GET_HW_SW_VER, 'HHHH')
# sw_ver is a 2-byte value, one of the unks.
print(f'hw_code={hex(hw_code)} hw_code_status={hex(hw_code_status)} hw_subcode={hex(hw_subcode)} hw_version={hex(hw_version)} sw_version={hex(sw_version)} hw_sw_ver_status?={hex(hw_sw_ver_status)}')
    # logfile implies all chip names are in flasher binary, chip_mapping.cpp cflashtool_api.cpp

chip2platform = {
    0x0279: 0x6797,
    0x0326: 0x6755,
    0x0551: 0x6757,
    0x0562: 0x6799,
    0x0601: 0x6750,
    0x0633: 0x6570,
    0x0688: 0x6758,
    0x0690: 0x6763,
    0x0699: 0x6739,
    0x0707: 0x6768,
    0x0717: 0x6761,
    0x0725: 0x6779,
    0x0766: 0x6765,
    0x0788: 0x6771,
    0x0813: 0x6785,
    0x0816: 0x6885,
    0x0886: 0x6873,
    0x0908: 0x8696,
    0x0930: 0x8195,
    0x0950: 0x6893,
    0x0959: 0x6877,
    0x0989: 0x6833,
    0x0996: 0x6853,
    0x1066: 0x6781,
}

# send DA data to boot rom (Download Agent)
cmd(0xd7)
cmd(b'\x00\x20\x00\x00') # either block size or address?
cmd(b'\x00\x03\x8c\x18') # total data size = 0x38c18
cmd(b'\x00\x00\x01\x00', 'H') # replies with 00 00
# writes 8192 bytes starting with \377\377\377\352\210\16\0\372\0\0\17 = ff ff ff ea 88 0e 00 fa 00 00 0f e1 c0 10 a0 e3 [log line 359, 0 = 358]
    # meanwhile 18606524 bytes were read from a file, starting with MTK_DOWNLOAD_AGENT
    # this file was searched for MT6771, finding MTK_AllInOne_DA_v3.3001.02/20/2022.04:57_58686
    # finding DA index 0x12, and sending the 1st data
# writes another 0x2000 starts with 02 45 1e e0 d3 e9 04 45 1b e0 d3 e9 06 45 18 e0
# then a8 ea 00 2f 40 46 14 bf 04 23 02 23 02 a9 04 94
# continues writing 8k blocks thru log line 386, so 28 total blocks
# then log line 387 shows a write of 0xc18 data
# so 0x38c18 bytes of data were written total, in blocks of 8k

# replies with 39 97 then 00 00

cmd(0xd5) # jump to download agent data
cmd(b'\x00\x20\x00\x00', 'H') # replies with 00 00
# receives 0xc0 as 'sync char'

# sends 'sync signal': ef ee ee fe 01 00 00 00 04 00 00 00   53 59 4e 43
# doesn't read reply yet

#                             datalen
# SPECIAL_CMD_SETUP_ENVIRONMENT=0x10100
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   00 01 01 00
#     ef ee ee fe 01 00 00 00 14 00 00 00   02 00 00 00 01 00 00 00 01 00 00 00 00 00 00 00
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 status_ok

# SPECIAL_CMD_SETUP_HW_INIT_PARAMS=0x10101
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   01 01 01 00
#     ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 status_ok

# rx: ef ee ee fe 01 00 00 00 04 00 00 00   53 59 4e 43 wait for sync reply

# CMD_DEVICE_CTRL=0x10009 
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   09 00 01 00
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   11 00 04 00 CC_GET_EXPIRE_DATE=0x40011
# rx: "                                 "   04 00 01 c0
#    device ctrl code not support. DA expired date 2099.1.1

# CMD_DEVICE_CTRL=0x10009 
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   09 00 01 00
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   04 00 02 00 CC_SET_RESET_KEY=0x20004
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 
#   support does support this conrtol code
#   send parameters
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   68 00 00 00 # setting 0x68. default0x0. 1 key[0x50]. 2 key[0x68]
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 
#   status_ok

# CC_SET_BATTERY_OPT=0x20002 . battery=0x0, usb power=0x1, auto=0x2. 0x2. sent as 4 bytes just like SET_REST_KEY

# CC_SET_CHECKSUM_LEVEL=0x20003.  none=0x0, USB=0x1, storage=0x2, both=0x3. 0x0. 

# CC_GET_CONNECTION_AGENT=0x4000a . a working getting. replies with data after initial 00 00 00 00, length in sync prefix, 9 bytes.
#    <-   "preloader"
#       then a further status ok.
#       so basically with getters, the device sends in the third packet, rather than the host.
# preloader alive. skip initializing external dram

# jump to 2nd DA
# CMD_BOOT_TO=0x10008 at_address 0x40000000 length=0x4e61c
#   the address and length are sent as 0x10 bytes, two 64 bit numbers
#   00 00 00 40 00 00 00 00 1c e6 04 00 00 00 00 00

#   then a packet is sent with the passed length of 0x04e61c.
#   it starts with 07 00 00 ea 94 00 00 ea 9a 00 00 ea a0 00 00 ea ...

# device sends another sync data ef ee ee fe 01 00 00 00 04 00 00 00 53 59 4e 43

# optional server security check
# CMD_DEVICE_CTRL=0x10009 CC_SET_ALL_IN_ONE_SIGNATURE=0x2000c
#  sends a packet with 09 00 01 00
#  recvs status_ok
#  sends 0c 00 02 00
#  recvs status_ok: device support this control code
#  sends empty data
#  receives status_ok

# CC_GET_DEV_FW_SEC_INFO=0x40013
#  just like CMD_DEVICE_CTRL for the first two exchanges
#  but as a getter, the device rather than host sends data for the third. it's 0x44 bytes, starting with 00 00 01 00 79 07 5e 07 12 35 3f f0 48 87 e9 1a
#  second go-around the bytes start with 00 00 01 00 ab d5 8c d5 12 35 3f f0 48 87 e9 1a : the second 4 bytes differ

# unmapping device ctrl code: 0x10f
# CC_GET_SLA_ENABLED_STATUS=0x40016
#  it looks like no data is sent either way for this subcommand, just success. i'm looking at a filtered log; it could be missing
#  or maybe boolean results are returned as simple status codes. status_ok
## second time around i'm seeing two status_oks. might have glossed over one.

# CC_SET_REMOTE_SEC_POLICY=0x2000b
# -> 53 4c 41 00

# end of optional security check

# CC_GET_RAM_INFO=0x4000c
#  <- 0x30 bbytes starting with 02 00 00 00 00 00 00 00 00 00 20 00 00 00 
#  sram type=0x2 base_address=0x200000 size=0x39000
#  dram type=0x1 base_address=0x40000000 size=0x180000000

# CC_GET_EMMC_INFO=0x40001
#  <- 0x68 bytes starting with 01 00 00 00 00 02 00 00 00 00 40 00 00 00
#  emmc type=0x1 sizes: boot1=0x400000 boot2=0x400000 user=0x1d1ec00000 rpmb=0x1000000 gp1=0x0 gp2=0x0 gp3=0x0 gp4=0x0
#       cid: 0x33000115 0x4d433656 0x63d0242 0x33868c90, fwver=0x0

# CC_GET_NAND_INFO=0x40002
#  <- 0x30 bytes starting with zeros
#  nand type=0 size: page=0 block=0 spare=0 total=0 available=0
#       id: 0 0 0

# CC_GET_NOR_INFO=0x40003
#   <- 0x10 bytes of zeros
#  nor type=0 size: page=0 available=0

# CC_GET_UFS_INFO=0x40004
#  <- 0xd0 bytes starting with zeros
#  ufs type=0 size: lu0=0 lu1=0 lu2=0

# CC_GET_CHIP_ID=0x4000d
#  <- 88 07 00 8a 00 ca 00 00 00 00 00 00

# CC_GET_RANDOM_ID=0x40008
#  <- fa 84 dd 84 12 35 3f f0 48 87 e9 ..
#  four 32 bit values, the same in two runs.

# CC_GET_USB_SPEED=0x4000b 
#  <- "high-speed"

# CC_STOR_LIFE_CYCLE_CHECK=0x80007
#  <- status_ok

# CC_GET_PARTITION_TBL_CATA=0x40009 # cata for catagory
#  <- 64 00 00 00
#   GPT

# CC_GET_PACKET_LENGTH=0x40007
#  <- 00 00 20 00 00 00 01 00 
#  write_packet_length=0x200000
#  read_packet_length=0x10000

# CMD_READ_DATA=0x10005
#  -> 0x38 bytes: 01 00 00 00 08 00 00 00 00 00 00  00 00 00 00 00 00 10 00  00 00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
#     it looks like the size is 16 or 17 bytes in
#               this operation has 3 parameters: 64bit offset, 64bit length, and region (EMMC_BOOT_1, EMMC_BOOT_2, EMMC_USER)
#               the captured example operation had an offset of 0, a length of 0x1000, and was for EMMC_USER.
#  extra status_ok?
#  <- 0x10000 bytes starting with zeros
#  -> status_ok

# CMD_UPLOAD=0x10002
  # this probably transfers the partition table to the host.
#  -> "PGPT"
#  <- status_ok
#  <- 00 80 00 00 00 00 00 00
#     upload partition length: 0x8000
#       probably a 64 bit integer
#  <- status_ok
#  <- 0x8000 bytes starting with zeros
#  -> status_ok
#  <- status_ok

# CC_SET_HOST_INFO=0x20005
# not supported? 04 00 01 c0

# CC_START_DL_INFO=0x80001
# <- status_ok

# CMD_UPLOAD=0x10002
  # this probably transfers the partition table to the host.
#  -> "SGPT"
#  <- status_ok
#  <- 00 42 00 00 00 00 00 00
#     upload partition length: 0x4200
#       probably a 64 bit integer
#  <- status_ok
#  <- 0x4200 bytes starting with a2 a0 d0 eb e5 b9 33 44 87 c0 68 b6 b7 26 99 c7
#  -> status_ok
#  <- status_ok

# CMD_DOWNLOAD=0x10001
#   <- status_ok
#   -> "preloader"
#   -> ac 25 04 00 00 00 00 00 (partition file length)
#   <- status_ok
#  for every 0x200000 bytes:
#   -> status_ok
#   -> d3 26 00 00 (checksum)
#   -> 0x425ac bytes starting with 4d 4d 4d 01 38 00 00 00 46 49 4c 45 5f 49 4e 46
#   <- status_ok

#   <- status_ok

# preloader_backup,recovery len=0x10a33a0, md1img, spmfw, ..

# CMD_SHUTDOWN=0X10007
#  -> 0x1c bytes (zeros) is_dev_reboot, timeout_ms, async, bootup, dlbit, bNotResetRTCTime, bNotDisconnectUSB
