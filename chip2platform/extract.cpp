#include <iostream>
#include <fstream>
#include <iomanip>

#include <boost/container/map.hpp>

// the built boost with v5.2208 appears to be 1.67.0 or 1.68.0

using tree_t = boost::container::map<unsigned short, unsigned short>;

extern "C"
void dumptree(tree_t * tree)
{
    std::ofstream dumpfile("chip2platform.py");

    std::cout << "chip2platform = {" << std::hex << std::setfill('0') << std::endl;
    dumpfile << "chip2platform = {" << std::hex << std::setfill('0') << std::endl;

    for (auto & item : *tree) {
        std::cout << "\t0x" << std::setw(4) << item.first << ": " << item.second << "," << std::endl;
        dumpfile << "\t0x" << std::setw(4) << item.first << ": " << item.second << "," << std::endl;
    }

    std::cout << "}" << std::endl;
    dumpfile << "}" << std::endl;
}
