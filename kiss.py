import threading
import socket

FEND = b'\xC0'  # Marks START and END of a Frame
FESC = b'\xDB'  # Escapes FEND and FESC bytes within a frame

class KISS(threading.Thread):
    def __init__(self, host='localhost', port=8001):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.callbacks = []
        self.isRunning = True

    @property
    def onReceive(self):
        return None

    @onReceive.setter
    def onReceive(self, client):
        self.callbacks.append(client)


    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.socket.settimeout(self.timeout)
        self.socket.connect((self.host, self.port))

    def run(self):
        self.connect()
        while self.isRunning:
            data = self.socket.recv(1024)
            packets = data.split(FEND)
            for packet in packets:
                if packet == '':
                    continue
                if packet[0] == '\x00':
                    p = self.decode_ax25(packet)
                    for cb in self.callbacks:
                        cb(p)

    def decode_ax25(self, packet):
        dest_callsign, dest_ssid = self.decode_callsign(packet[1:8])
        src_callsign, src_ssid = self.decode_callsign(packet[8:15])
        path1, ttl1 = self.decode_callsign(packet[15:22])
        path2, ttl2 = self.decode_callsign(packet[22:29])
        return "%s-%d>%s-%d,%s-%d,%s-%d:%s" % (src_callsign, src_ssid, dest_callsign, dest_ssid, path1, ttl1, path2, ttl2, packet[31:])

    def decode_callsign(self, param):
        cs = ''
        for i in range(6):
            cs += chr(ord(param[i]) >> 1)
        ssid = (ord(param[6]) >> 1)-48
        return cs.strip(), ssid


########################################################################################################################

def onMessage(msg):
    print(msg)

if __name__ == "__main__":
    kiss = KISS(host='aprs-igate.local')
    kiss.onReceive = onMessage
    kiss.start()
