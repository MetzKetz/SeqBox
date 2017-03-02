#!/usr/bin/env python3

#--------------------------------------------------------------------------
# Name:        seqbox.py
# Purpose:     Sequenced Box container
#
# Author:      Marco Pontello
#
# Created:     10/02/2017
# Copyright:   (c) Mark 2017
# Licence:     GPL-something?
#--------------------------------------------------------------------------

import os
import sys
import hashlib
import argparse
import tempfile
import binascii
import random
from functools import partial

PROGRAM_VER = "0.03a"

def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        print("%s: error: %s" % (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)


def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="Sequenced Box container",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-/+')
    parser.add_argument('--version', action='version',
                        version='Sequenced Box container v%s' % PROGRAM_VER)
    parser.add_argument("filename", action="store", nargs='?',
                        help = "filename.", default="")
    res = parser.parse_args()
    return res

def getsha256(filename):
    with open(filename, mode='rb') as f:
        d = hashlib.sha256()
        for buf in iter(partial(f.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()

def banner():
    print("\nSeqBox - Sequenced Box Container v%s - (C) 2017 Marco Pontello\n"
           % (PROGRAM_VER))

def usage():
    print("""usage:

seqbox e file.sbx file encode file in file.sbx
seqbox d file.sbx file decode file from file.sbx
seqbox i file.sbx show information on file.sbx
seqbox t file.sbx test file.sbx for integrity
seqbox r [-d path] filenames [filenames ...] recover sbx files from filenames
         and store in path
    """)

def getcmdargs():
    res = {}

    if len(sys.argv) == 1:
        usage()
        errexit(1)
    elif sys.argv[1] in ["?", "-?", "-h", "--help"]:
        usage()
        errexit(0)

    res["cmd"] = sys.argv[1].lower()

    if res["cmd"] in ["e"]:
        if len(sys.argv) == 4:
            res["sbxfile"] = sys.argv[2]
            res["file"] = sys.argv[3]
        else:
            usage()
            errexit(1)
    else:
        errexit(1, "command %s not yet implemented." % res["cmd"])
    
    return res


class sbxBlock():
    """
    Implement a basic SBX block
    """
    def __init__(self, ver=0, uid="r"):
        self.ver = ver
        if ver in [0,1]:
            self.blocksize = 512
            self.hdrsize = 16
        else:
            raise version_not_supported #put in a proper exception
        self.datasize = self.blocksize - self.hdrsize
        self.magic = b'SBx' + ver.to_bytes(1, byteorder='big', signed=True)
        self.blocknum = 0

        if uid == "r":
            random.seed()
            self.uid = random.getrandbits(32)
        else:
            self.uid = 0

        self.parent_uid = 0
        self.metadata = {}
        self.data = b""

    def __str__(self):
        return "SBX Block ver: '%i', size: %i, hdr size: %i, data: %i" % \
               (self.ver, self.blocksize, self.hdrsize, self.datasize)

    def encode(self):
        if self.blocknum == 0:
            self.data = b""
            if "filename" in self.metadata:
                bb = self.metadata["filename"].encode()
                self.data += b"NM" + len(bb).to_bytes(1, byteorder='little') + bb
            if "filesize" in self.metadata:
                bb = self.metadata["filesize"].to_bytes(8, byteorder='little', signed=True)
                self.data += b"SZ" + len(bb).to_bytes(1, byteorder='little') + bb
            if "hash" in self.metadata:
                bb = self.metadata["hash"]
                self.data += b"HS" + len(bb).to_bytes(1, byteorder='little') + bb
        
        data = self.data + b'\x1A' * (self.datasize - len(self.data))
        buffer = (self.uid.to_bytes(6, byteorder='little') +
                  self.blocknum.to_bytes(4, byteorder='little') +
                  data)
        crc = binascii.crc_hqx(data,0).to_bytes(2,byteorder='little')
        return (self.magic + crc +buffer)


def main():

    banner()

    cmdline = getcmdargs()

    filename = cmdline["file"]
    sbxfilename = cmdline["sbxfile"]
    
    print("reading %s..." % filename)
    filesize = os.path.getsize(filename)
    sha256 = getsha256(filename)
    fin = open(filename, "rb")
    fout = open(sbxfilename, "wb")

    sbx = sbxBlock()
    
    #write block 0
    sbx.metadata = {"filesize":filesize,
                    "filename":filename,
                    "hash":sha256}
    fout.write(sbx.encode())
    
    #write all other blocks
    while True:
        buffer = fin.read(sbx.datasize)
        if len(buffer) < sbx.datasize:
            if len(buffer) == 0:
                break
        sbx.blocknum += 1
        sbx.data = buffer
        #print(fin.tell(), sbx.blocknum, " ",end = "\r")
        fout.write(sbx.encode())
                
        
    fout.close()
    fin.close()


    print("\nok!")



if __name__ == '__main__':
    main()
