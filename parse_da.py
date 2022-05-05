#!/usr/bin/env python3
import struct

with open('MTK_AllInOne_DA.bin', 'rb') as dabin:
    def readstr(len):
        return dabin.read(len).rstrip(b'\0').decode()
    def read(fmt):
        size = struct.calcsize(fmt)
        data = struct.unpack(fmt, dabin.read(size))
        if len(data) == 1:
            data = data[0]
        return data
    str1 = readstr(32) # MTK_DOWNLOAD_AGENT
    print(str1)
    str2 = readstr(64)
    print(str2)

    # unk1 may be the length of unk2
    unk1, unk2 = read('<LL')
    print(hex(unk1), hex(unk2))

    ct = read('<L')
    print(ct, "records")

    for idx in range(ct):

        # these look to be mostly offsets and lengths for each record and its parts

        print(f'index={hex(idx)}')

        dada, hw_code, hw_subcode, hw_ver, sw_ver, unk5, unk6 = read('<HHHHLLL') # 0xdada, 0x7381, 0x00, 0xca00, 0x00, 0x1000, 0x30000
        print(f'dada={hex(dada)} hw_code={hex(hw_code)} hw_subcode={hex(hw_subcode)} hw_ver={hex(hw_ver)} sw_ver={hex(sw_ver)} unk5={hex(unk5)} unk6={hex(unk6)}')
        for section in range(10):
            off, length, unk, startlen, endlen = read('<LLLLL')
            if off != 0 or length != 0:
                print(f' section {section}: off={hex(off)} length={hex(length)} unk={hex(unk)} startlen={hex(startlen)} endlen={hex(endlen)}')
