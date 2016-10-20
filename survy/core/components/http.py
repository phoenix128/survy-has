import json
import re

from survy.core.component import Component
from http.server import BaseHTTPRequestHandler, HTTPServer

from survy.core.intercom import Reply


class WebServiceReqHandler(BaseHTTPRequestHandler):
    def on_message(self):
        m = re.search(r'^/(?P<component>.+?)/(?P<task>.+)$', self.path)
        if m:
            if 'Content-Length' in self.headers:
                content_len = int(self.headers['Content-Length'])
            else:
                content_len = 0

            if content_len > 0:
                raw_data = self.rfile.read(content_len)
                payload = json.loads(raw_data.decode('utf-8'))
            else:
                payload = None

            component = m.group('component')
            task = m.group('task')

            return HttpManager.get_instance().create_intercom_message(component, task, payload).send()

        return Reply(status=Reply.INTERCOM_STATUS_FAILURE, payload={'message': 'Incorrect format'})

    def do_GET(self):
        self.do_POST()

    def do_POST(self):
        res = self.on_message()

        self.send_response(res.get_http_status())
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        self.wfile.write(bytes(json.dumps(res.get_payload()), 'utf-8'))


class HttpManager(Component):
    COMPONENT_TYPE = 'http-manager'
    server = None

    def start(self):
        try:
            self.server = HTTPServer((self._params['host'], self._params['port']), WebServiceReqHandler)
            self.server.serve_forever()
        except KeyboardInterrupt:
            if self.server is not None:
                self.server.socket.close()
