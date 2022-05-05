#!/usr/bin/env python3
import os, struct

with open('MTK_AllInOne_DA.bin', 'rb') as dabin:
    def readstr(len):
        return dabin.read(len).rstrip(b'\0').decode()
    def read(fmt):
        size = struct.calcsize(fmt)
        data = struct.unpack(fmt, dabin.read(size))
        if len(data) == 1:
            data = data[0]
        return data

    da_description = readstr(32) # MTK_DOWNLOAD_AGENT
    da_identifier = readstr(64)
    info_ver, info_22668899 = read('<LL')
    print(f'description={da_description} identifier={da_identifier} ver={hex(info_ver)} 22668899={hex(info_22668899)}')

    da_count = read('<L')
    print(da_count, "download agents")

    das = []

    for idx in range(da_count):

        print(f'index={hex(idx)}')

        dada, hw_code, hw_subcode, hw_ver = read('<HHHH') # 0xdada, 0x7381, 0x00, 0xca00
        print(f'dada={hex(dada)} hw_code={hex(hw_code)} hw_subcode={hex(hw_subcode)} hw_ver={hex(hw_ver)}')
        # sw_ver (16 bit = 0) and entry_region_index( = 0) may be somewhere here
        unk4, unk5, unk6, unk7, unk8 = read('<HHHHH') # 00 00 00 00 00 10 00 00 00 00

        load_regions_count = read('<H') # 03 00
        print(f'unk4={hex(unk4)} unk5={hex(unk5)} unk6={hex(unk6)} unk7={hex(unk7)} unk8={hex(unk8)} regions_count={hex(load_regions_count)}')

        regions =[]

        for region in range(10):
            off, length, start_addr, sig_offset, sig_len = read('<LLLLL')
            if off != 0 or length != 0:
                print(f' region {region}: off={hex(off)} length={hex(length)} start_addr={hex(start_addr)} sig_offset={hex(sig_offset)} sig_len={hex(sig_len)}')
                regions.append((region, off, length, start_addr, sig_offset, sig_len))
        das.append((hw_code, hw_subcode, hw_ver, regions))
    for hw_code, hw_subcode, hw_ver, regions in das:
        name=os.path.join(da_identifier.replace('/','_'),f'{hex(hw_code)[2:]}-{hex(hw_ver)[2:]}-{hex(hw_subcode)[2:]}')
        print(f'Writing {name} ...')
        os.makedirs(name, exist_ok=True)
        for index, offset, length, start_addr, sig_offset, sig_len in regions:
            region_name = os.path.join(name, f'{index}-{hex(start_addr)[2:]}')
            if sig_offset == 0:
                dabin.seek(offset + sig_len)
            elif sig_offset + sig_len == length:
                dabin.seek(offset)
            else:
                sig_len = 0
                sig_offset = 0
            with open(region_name, 'wb') as region:
                region.write(dabin.read(length - sig_len))
            if sig_offset != 0 or sig_len != 0:
                dabin.seek(offset + sig_offset)
                with open(region_name + '.sig', 'wb') as region_sig:
                    region_sig.write(dabin.read(sig_len))
