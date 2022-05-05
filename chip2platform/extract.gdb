break main
run

disable 1
break chip_mapping::init_mapping_tbl
cont

set $mapping_tbl = $rdi
fini

call (void*)dlopen("./extract.so",2)
call dumptree($mapping_tbl)

printf "====\n Chip to Platform Mapping Table Dumped \n====\n"

disable 2
cont

printf "====\n Chip to Platform Mapping Table Dumped \n====\n"
