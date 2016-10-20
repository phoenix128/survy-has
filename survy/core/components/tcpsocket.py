import json
import socketserver
import threading

from survy.core.component import Component
from survy.core.intercom import Reply, Message
from survy.core.log import Log


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    _lock = threading.Lock()

    def _on_line(self, line):
        if len(line) == 0:
            return

        try:
            message = json.loads(line)

            if 'payload' not in message:
                message['payload'] = {}

            reply = TCPSocketManager.get_instance().send_intercom_message(
                message_type=message['message'],
                message_payload=message['payload']
            )

        except Exception as e:
            reply = Reply(Reply.INTERCOM_STATUS_FAILURE, {'message': str(e)})

        self._lock.acquire()
        self.request.sendall(bytes(json.dumps(reply.to_dict()) + "\n", 'utf-8'))
        self._lock.release()

    def send_message(self, message: Message):
        self._lock.acquire()
        self.request.sendall(bytes(json.dumps(message.to_dict()) + "\n", 'utf-8'))
        self._lock.release()

    def handle(self):
        line = ''

        (host, port) = self.client_address

        Log.info("TCP socket client connected from " + host + ':' + str(port))
        TCPSocketManager.get_instance().handlers[threading.current_thread()] = self

        while True:
            try:
                b = self.request.recv(1)
            except Exception:
                break

            if b == b'':
                break

            c = b.decode('utf-8')
            if c in ['\n', '\r']:
                self._on_line(line.strip())
                line = ''

            else:
                line += c

        del TCPSocketManager.get_instance().handlers[threading.current_thread()]
        Log.info("TCP socket client disconnected from " + host + ':' + str(port))


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class TCPSocketManager(Component):
    handlers = {}

    def _on_intercom_message(self, message: Message) -> Reply:
        for thread_id, handler in self.handlers.items():
            handler.send_message(message)

        return Component._on_intercom_message(self, message)

    def start(self):
        Component.start(self)

        server = ThreadedTCPServer((self._params['host'], self._params['port']), ThreadedTCPRequestHandler, False)
        server.allow_reuse_address = True
        server.server_bind()
        server.server_activate()
        server.serve_forever()
