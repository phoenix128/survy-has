import json
import socket

from survy.core.intercom import Reply


class Client:
    sock = None
    host = None
    port = None

    def __init__(self, host='127.0.0.1', port=2006):
        self.host = host
        self.port = port

    def _read_line(self):
        line = ''
        while True:
            b = self.sock.recv(1)
            if b == b'':
                break

            c = b.decode('utf-8')
            if c in ['\n', '\r']:
                return line.strip()

            line += c

        return None

    def send(self, message_type, message_payload=None, expect=None):
        if expect is None:
            expect = Reply.INTERCOM_MESSAGE_REPLY

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

        message = json.dumps({
            'message': message_type,
            'payload': message_payload
        })

        self.sock.sendall(bytes(message+"\n", 'utf-8'))
        while True:
            reply = self._read_line()
            if reply is None:
                return None

            message = json.loads(reply)
            if message['message'] in expect:
                return message
