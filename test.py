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
        fd = os.open('/dev/ttyACM0', os.O_RDWR|os.O_NOCTTY)#|os.O_NONBLOCK)
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

# get preloader version
preloader_version = cmd(0xfe, 'B', expect_echo=False)
print('Device preloader version:', hex(preloader_version))

# get chip id info
hw_code, unk1 = cmd(0xfd, 'HH')
hw_subcode, hw_version, unk2, unk3 = cmd(0xfc, 'HHHH')
# sw_ver is a 2-byte value, one of the unks.
print(f'hw_code={hex(hw_code)} unk1={hex(unk1)} hw_subcode={hex(hw_subcode)} hw_version={hex(hw_version)} unk2={hex(unk2)} unk3={hex(unk3)}')
    # logfile implies all chip names are in flasher binary, chip_mapping.cpp cflashtool_api.cpp

# send DA data to boot rom (Download Agent)
cmd(0xd7)
cmd(b'\x00\x20\x00\x00') # blocksize = 0x2000, unknown zeros
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
# setup environment cmd 0x10100
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   00 01 01 00
#     ef ee ee fe 01 00 00 00 14 00 00 00   02 00 00 00 01 00 00 00 01 00 00 00 00 00 00 00
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 status_ok

# setup hw init params cmd=0x10101
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   01 01 01 00
#     ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 status_ok

# rx: ef ee ee fe 01 00 00 00 04 00 00 00   53 59 4e 43 wait for sync reply

# device ctrl cmd=0x10009 
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   09 00 01 00
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   11 00 04 00 CC_GET_EXPIRE_DATE=0x40011
# rx: "                                 "   04 00 01 c0
#    device ctrl code not support. DA expired date 2099.1.1

# device ctrl cmd=0x10009 
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   09 00 01 00
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   04 00 02 00 CC_SET_RESET_KEY=0x20004
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 
#   support does support this conrtol code
#   send parameters
# tx: ef ee ee fe 01 00 00 00 04 00 00 00   68 00 00 00 # setting 0x68. default0x0. 1 key[0x560]. 2 key[0x68]
# rx: ef ee ee fe 01 00 00 00 04 00 00 00   00 00 00 00 
#   status_ok

# CC_SET_BATTERRY_OPT=0x20002 . battery=0x0, usb power=0x1, auto=0x2. 0x2. sent as 4 bytes just like SET_REST_KEY

# CC_SET_CHECKSUM_LEVEL=0x20003.  none=0x0, USB=0x1, storage=0x2, both=0x3. 0x0. 

# CC_GET_CONNECTION_AGENT=0x4000a . a working getting. replies with data after initial 00 00 00 00, length in sync prefix, 9 bytes.
#       70 72 65 6c 6f 61 64 65 72
#       then a further status ok.
#       so basically with getters, the device sends in the third packet, rather than the host.

# CMD_BOOT_TO=0x10008 at_address 0x40000000 length=0x4e61c
#   the address and length are sent as 0x10 bytes, two 64 bit numbers
#   00 00 00 40 00 00 00 00 1c e6 04 00 00 00 00 00

#   then a packet is sent with the passed length of 0x04e61c.
#   it starts with 07 00 00 ea 94 00 00 ea 9a 00 00 ea a0 00 00 ea ...

# device replies with another sync data ef ee ee fe 01 00 00 00 04 00 00 00 53 59 4e 43

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

# unmapping device ctrl code: 0x10f
# CC_GET_SLA_ENABLED_STATUS=0x40016
#  it looks like no data is sent either way for this subcommand, just success. i'm looking at a filtered log; it could be missing
#  or maybe boolean results are returned as simple status codes. status_ok

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