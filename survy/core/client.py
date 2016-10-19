import http.client
import json


class Client:
    conn = None
    host = None
    port = None

    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port

    def send(self, message, payload=None):
        conn = http.client.HTTPConnection(self.host, self.port)

        if payload is None:
            conn.request("GET", '/' + message)
        else:
            conn.request("POST", '/' + message, bytes(json.dumps(payload), 'utf-8'))

        response = conn.getresponse()

        data = json.loads(response.read().decode('utf-8'))
        conn.close()

        return {'status': response.status, 'payload': data}
