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

        # da da 73 81 00 00 00 ca  00 00 00 00 00 10 00 00 
        dada, unk1, unk2, unk3, unk4, unk5 = read('<HHHHLL')
        print(f'dada={hex(dada)} unk1={hex(unk1)} unk2={hex(unk2)} unk3={hex(unk3)} unk4={hex(unk4)} unk5={hex(unk5)}')
        # 00 00 03 00 44 1a 10 00  70 02 00 00 00 00 21 00 
        unk6, offset1, unk7, unk8 = read('<LLLL')
        print(f'unk6={hex(unk6)} offset1={hex(offset1)} unk7={hex(unk7)} unk8={hex(unk8)}')
        # 00 00 00 00 00 00 00 00  b4 1c 10 00 d0 76 01 00 
        unk9, unk10, offset2, unk12 = read('<LLLL')
        print(f'unk9={hex(unk9)} unk10={hex(unk10)} offset2={hex(offset2)} unk12={hex(unk12)}')
        # 00 00 0c 00 d0 75 01 00  00 01 00 00 84 93 11 00 
        unk13, unk14, unk15, unk16 = read('<LLLL')
        print(f'unk13={hex(unk13)} unk14={hex(unk14)} unk15={hex(unk15)} unk16={hex(unk16)}')
        # 30 71 03 00 00 00 00 40  30 70 03 00 00 01 00 00 
        unk17, unk18, unk19, unk20 = read('<LLLL')
        print(f'unk17={hex(unk17)} unk18={hex(unk18)} unk19={hex(unk19)} unk20={hex(unk20)}')
        # 00000350  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
        # *
        # 000003d0  00 00 00 00 00 00 00 00  00 00 00 00
        zeros = dabin.read(0xdc-0x50)
        zeros_trimmed = zeros.rstrip(b'\0')
        print(f'zeros={zeros_trimmed}')
