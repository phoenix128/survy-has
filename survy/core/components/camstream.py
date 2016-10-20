import re

from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import io
import cv2
import time
from PIL import Image

from survy.core.component import Component
from survy.core.components.cam import CamRepo, Cam
from survy.core.log import Log


class CamThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class CamStreamHandler(BaseHTTPRequestHandler):
    def send404(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes('<html><head></head><body>', 'utf-8'))
        self.wfile.write(bytes('<h1>Not found</h1>', 'utf-8'))
        self.wfile.write(bytes('</body></html>', 'utf-8'))

    def send_mjpeg(self, cam: Cam):
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
        self.end_headers()

        while True:
            img = cam.image
            if img is None:
                time.sleep(5)
                continue

            try:
                imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                jpg = Image.fromarray(imgRGB)
                tmpFile = io.BytesIO()

                jpg.save(tmpFile, 'JPEG')
                self.wfile.write(bytes("--jpgboundary", 'utf-8'))
                self.send_header('Content-type', 'image/jpeg')
                # self.send_header('Content-length', str(tmpFile.len))
                self.end_headers()
                jpg.save(self.wfile, 'JPEG')
            except:
                Log.info("Closing camera stream for " + cam.code)
                break

    def send_html(self, cam: Cam):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes('<html><head></head><body>', 'utf-8'))
        self.wfile.write(bytes('<img src="/' + cam.code + '.mjpg"/>', 'utf-8'))
        self.wfile.write(bytes('</body></html>', 'utf-8'))

    def do_GET(self):
        m = re.search(r'^/(?P<cam>[\w+\-_]+)\.(?P<mode>mjpg|html)$', self.path)

        if m:
            cam = m.group('cam')
            mode = m.group('mode')

            Log.info('Cam HTTP request for "' + cam + '" (mode ' + mode + ')')

            cam_instance = CamRepo.get_by_code(cam)

            if cam_instance is not None:
                if mode == 'mjpg':
                    self.send_mjpeg(cam_instance)
                    return
                elif mode == 'html':
                    self.send_html(cam_instance)
                    return

        self.send404()


class CamStreamManager(Component):
    COMPONENT_TYPE = 'cam-stream-manager'

    _server = None

    def start(self):
        Component.start(self)

        self._server = CamThreadedHTTPServer((self._params['host'], int(self._params['port'])), CamStreamHandler)
        self._server.serve_forever()
