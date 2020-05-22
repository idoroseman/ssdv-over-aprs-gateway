import threading
import socket
import time

class APRSISClient(threading.Thread):
    def __init__(self, addr="euro.aprs2.net", port=14580, callsign="N0CALL", filter="u/APE6UB"):
        threading.Thread.__init__(self)
        self.port = port
        self.addr = addr
        self.callsign = callsign
        self.filter = filter
        self.callbacks = []
        self.timeout = 200
        self.isRunning = True

    @property
    def onReceive(self):
        return None

    @onReceive.setter
    def onReceive(self, client):
        self.callbacks.append(client)

    def connect(self):
        connected=False
        while not connected:
          try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.addr, self.port))
            self.send("user %s-TS pass -1 vers aprs2ssdv 1.0 filter %s" % (self.callsign, self.filter))
            connected = True
          except Exception as x:
            time.sleep(5)

    def run(self):
        self.connect()
        while self.isRunning:
            try:
                data = self.socket.recv(1024)
                for cb in self.callbacks:
                    cb(data.decode('utf-8'))
            except socket.timeout as msg:
                print(msg)
                self.socket.close()
                self.connect()
            except TypeError as x:
                print(x)
            except Exception as x:
                print("listener error:", x)
                try:
                    if x.errno == 107:
                       self.socket.connect((self.addr, self.port))
                except:
                    time.sleep(1)

    # 
    def send(self, msg):
        msg += "\r\n"
        self.socket.send(msg.encode())

    def close(self):
        print ("closing connection to aprsis")
        self.isRunning = False
        self.socket.close()

########################################################################################################################

def onMessage(msg):
    # 4X6UB-11>APE6UB,WIDE1-1,WIDE2-1,qAO,4X6UB:{{KAAJt7FN/C"Kb^{/!R=^:POi#r4J_;x-"RsP68s%/xuXwLt{[p*b}S?bYy4Wu-u/4<h&QOTzP(NY3q`?ubP]KT3RPo%wi2SF)$W$Cb,X_j;awulms{iIap(~;;;HWK^Fw]VM*ntFFxE
    # 4X6UB-11>APE6UB,WIDE1-1,WIDE2-1,qAO,4X6UB:{{IAANt7F5FuWKA,os%rHvWZn[sY30`:J5&#E1enIE&K_^,q8b{-!Wl[${G,uR5WsaYpz;s+]xUA,FW0^tdO{(Gx-!bxwFL-/NX$wZZurY*.xuc0D<?e}/:&Hs~x9}l&=/~K}&?<3}:ZE
    # 4X6UB-11>APE6UB,WIDE1-1,WIDE2-1,qAO,4X6UB:{{JAANt7F5FuWJ^levb2Y0?6`<7qSxX1S2~b{;u2<RlXn"[%hR{mKPWg{1D3U.W.~d2Yll(Am+oG9esBbI7"a>Q[sY3Do:gY-P}k/#0d{87oi#V{FpqoOZY5%j)KaW_+rq~;64-c+/3FA
    if msg == '' :
        return
    if msg.startswith("#"):
        print(msg)
        return
    header, payload = msg.split(":", 1)
    tokens = header.split(',')
    src, dest = tokens[0].split(">")
    if dest == 'APE6UB':
        print("data:", payload)

if __name__ == "__main__":
    client = APRSISClient(callsign="4X6UB")
    client.onReceive = onMessage
    client.start()
    print("started")
    while True:
        try:
            pass
        except KeyboardInterrupt:  # If CTRL+C is pressed, exit cleanly
            break
        except Exception as x:
            client.close()
            client = APRSISClient(callsign="4X6UB")
            client.onReceive = onMessage
            client.start()
    client.stop()
    print("done")
