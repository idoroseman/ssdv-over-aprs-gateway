from unittest import TestCase
import gateway
import base64

class Test_aprs2ssdv(TestCase):
    def prep_line(self, msg):
        header, payload = msg.split(":", 1)
        tokens = header.split(',')
        src, dest = tokens[0].split(">")
        receiver = tokens[-1]
        return receiver, payload

    def test_process_line(self):
        a2s = gateway.aprs2ssdv('4x6ub')
        line1 = u'{{I000BABt7FAAAA<<>4RP/W{<z@+y9u7Ds[!CF{04#B2YlK:Ck,^)%L>7X.%Q@XstUWmbL$mlwUX4ik"4}ngEqj9Ta^g7B_"MSVcjB=!J,ru1<K&Zb6vS%IvIaS#PQoNL$GZS:a._A0aSfA'
        line2 = u'{{J001BABt7FAAAAMcsW}D,5i0!f{e#:.d;*Z2~>g+N)7OqKmmxDEM!w_q*34_-JhzOB5dT"MIF"uva4&KkQon$D-tvq0_Pb_%sSS>@hdC[F5Mc/^p7#GOFEmUk)+V=Z0?Ark_PJx:C@KrA'
        result = {"received": "2020-05-19T14:34:41Z", "receiver": "4X6UB", "type": "packet",
         "packet": "VWYCa1WNAQAAFBAAAAAAtW2oWdlAWnuUM8hLyBTuOT249BxUE/ii2QEQwvIfViFH9TXHlz60As3Pb1q2TY3p/E93JkRrHGPYZP5ms2fU7u5JEk8jA9txA/IVTO1RknJppckYBwPQUBYkZz/ExJ9BTCSeTwKaD6D8T1pQpJ5yaAGsRn2ppPHSnOACOQfXFNyB2oQCEnGKQk96UnjFISTTAKKKAMnFADgOBSj0oC4FLipYwY4H4VHT25U0zHuBTQMM0UcetLkDtQAlLggdKNx7YFIST3oAXmj8aTk+9QwNWUsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==",
         "encoding": "base64"}
        receiver = "test"

        packet, image_id = a2s.process_line(receiver, line1)
        self.assertIsNone(packet)

        packet, image_id = a2s.process_line(receiver, line2)
        encoded = base64.b64encode(packet).decode('ASCII')
        self.assertEqual(encoded, result['packet'])
