from base91 import encode, decode
import requests
import datetime
import base64
import binascii
from aprsis import APRSISClient
from kiss import KISS
import json
import time
import os

# code based on work by
#   https://github.com/DL7AD/pecanpico9/blob/3008ff27fe6a80bf22438779077a0475d33bd389/decoder/decoder.py
#   https://github.com/fsphil/ssdv
#   http://www.aprs-is.net/connecting.aspx

# Offset	Name	Size	Description
# 0	    Sync Byte	    1	0x55 - May be preceded by one or more sync bytes
# 1	    Packet Type	    1	0x66 - Normal mode (224 byte packet + 32 byte FEC)
#                           0x67 - No-FEC mode (256 byte packet)
# 2	    Callsign	    4	Base-40 encoded callsign. Up to 6 digits
# 6	    Image ID	    1	Normally beginning at 0 and incremented by 1 for each new image
# 7	    Packet ID	    2	The packet number, beginning at 0 for each new image (big endian)
# 9	    Width	        1	Width of the image in MCU blocks (pixels / 16) 0 = Invalid
# 10	Height	        1	Height of the image in MCU blocks (pixels / 16) 0 = Invalid
# 11	Flags	        1	00qqqexx: 00 = Reserved, qqq = JPEG quality level (0-7 XOR 4), e = EOI flag (1 = Last Packet), xx = Subsampling Mode
# 12	MCU offset  	1	Offset in bytes to the beginning of the first MCU block in the payload, or 0xFF if none present
# 13	MCU index	    2	The number of the MCU pointed to by the offset above (big endian), or 0xFFFF if none present
# 15	Payload         205	Payload data
# 220	Checksum	    4	32-bit CRC
# 224	FEC	            32	Reed-Solomon forward error correction data. Normal mode only (0x66)

class aprs2ssdv():
    def __init__(self, callsign):
        self.packets = {}
        self.headers = {}
        self.receivers = {}
        self.callsign = callsign
        self.ssdv_url = "http://ssdv.habhub.org/api/v0/packets"
        self.count = 0

    def merge(self, header, i, j):
        pre = bytearray([0x55, 0x66])
        cs = bytearray([0x02, 0x6B, 0x55, 0x8D ])
        data = pre+cs+header+i+j[:-1]
        crc = binascii.crc32(data[1:])
        data += crc.to_bytes(4, 'big')
        data += bytearray([0] * 32) # fec
        return data

    def upload(self, packet, receivers):
        self.count += 1
        packet_dict = {
            "type": "packet",
            "packet": base64.b64encode(packet).decode('ASCII'),
            "encoding": "base64",
            # Because .isoformat() doesnt give us the right format... (boo)
            "received": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "receiver": receivers[self.count % len(receivers)],
        }
        r = requests.post(self.ssdv_url, json=packet_dict)
        print(r,r.text)

    def process_aprs(self, msg):
        # 4X6UB-11>APE6UB,WIDE1-1,WIDE2-1,qAO,4X6UB:{{KAAJt7FN/C"Kb^{/!R=^:POi#r4J_;x-"RsP68s%/xuXwLt{[p*b}S?bYy4Wu-u/4<h&QOTzP(NY3q`?ubP]KT3RPo%wi2SF)$W$Cb,X_j;awulms{iIap(~;;;HWK^Fw]VM*ntFFxE
        # 4X6UB-11>APE6UB,WIDE1-1,WIDE2-1,qAO,4X6UB:{{IAANt7F5FuWKA,os%rHvWZn[sY30`:J5&#E1enIE&K_^,q8b{-!Wl[${G,uR5WsaYpz;s+]xUA,FW0^tdO{(Gx-!bxwFL-/NX$wZZurY*.xuc0D<?e}/:&Hs~x9}l&=/~K}&?<3}:ZE
        # 4X6UB-11>APE6UB,WIDE1-1,WIDE2-1,qAO,4X6UB:{{JAANt7F5FuWJ^levb2Y0?6`<7qSxX1S2~b{;u2<RlXn"[%hR{mKPWg{1D3U.W.~d2Yll(Am+oG9esBbI7"a>Q[sY3Do:gY-P}k/#0d{87oi#V{FpqoOZY5%j)KaW_+rq~;64-c+/3FA
        if msg == '':
            return
        if msg.startswith("#"):
            if msg.startswith("# aprsc"):
                pass
            else:
                print("server:", msg.strip())
            return
        header, payload = msg.split(":", 1)
        tokens = header.split(',')
        src, dest = tokens[0].split(">")
        receiver = tokens[-1]
        if dest == 'APE6UB' :
            print("data:", payload.strip())
            if payload.startswith("{{"):
              with open("log/ssdv.log","a+") as f:
                 f.write(msg);
              packet, image_id = self.process_line(receiver, payload)
              if packet is not None:
                  self.upload(packet, self.receivers[image_id])
            else:
              with open("log/aprs.log","a+") as f:
                 f.write(msg)

    def process_line(self, receiver, line):
        data = decode(line[6:])
        packet_type = line[2]
        image_id = data[0]
        packet_id = data[1] * 0x100 + data[2]
        w = data[3]
        h = data[4]
        flags = data[5]
        mcu_offset = data[6]
        mcu_index = data[7] * 0x100 + data[8]
        print("-> got packet %4s %4s %s" % ( image_id, packet_id, packet_type))
        hash = "%04s%02s" % (image_id, packet_id)
        if hash not in self.packets:
            self.packets[hash] = {}
        if hash not in self.headers:
            self.headers[hash] = data[0:9]
        elif data[0:9] != self.headers[hash]:
            print("header error", data[0:9], self.headers[hash])
        if image_id not in self.receivers:
                self.receivers[image_id] = ['SSDV over APRS']
        self.packets[hash][packet_type] = data[9:]
        if receiver not in self.receivers[image_id]:
            self.receivers[image_id] += [receiver]
        keys = "".join(list(self.packets[hash].keys()))
        if keys == "IJ":
            packet = self.merge(self.headers[hash], self.packets[hash]['I'], self.packets[hash]['J'])
            return packet, image_id
        elif keys == "IK":
            data = ''.join([chr(self.packets[hash]['I'][i] ^ self.packets[hash]['K'][i]) for i in range(len(self.packets[hash]['K']))])
            packet = self.merge(self.headers[hash], self.packets[hash]['I'], data)
            return packet, image_id
        elif keys == "KJ":
            data = ''.join([chr(self.packets[hash]['J'][i] ^ self.packets[hash]['K'][i]) for i in range(len(self.packets[hash]['K']))])
            packet = self.merge(self.headers[hash], data, self.packets[hash]['J'])
            return packet, image_id
        elif len(keys) == 3:
            # verify crc
            pass
        return None, 0


########################################################################################################################

if __name__ == "__main__":
    try:
        os.mkdir("log")
    except:
        pass
    a2s = aprs2ssdv('4x6ub')
    # connect to aprs-is network
    client = APRSISClient(callsign="4X6UB")
    client.onReceive = a2s.process_aprs
    client.start()
    # connect to local tnc
#    kiss = KISS(host='aprs-igate.local')
#    kiss.onReceive = a2s.process_aprs
#    kiss.start()

    print("started")
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly
            print("QRT")
            break
        except Exception as x:
            print("unhandled exception")
            print(x)
            print("restarting")
            client.close()
            client = APRSISClient(callsign="4X6UB")
            client.onReceive = a2s.process_aprs
            client.start()

    client.close()
    print("done")
