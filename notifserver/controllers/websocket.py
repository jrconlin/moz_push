# Websocket Server

# see http://tools.ietf.org/html/draft-ietf-hybi-thewebsocketprotocol-12
IETF_VERSION = "DRAFT-12"

import socket
import os
import struct

class WebSocket:


    class WebSocketException(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)


    class Server:

        # defined in draft IETF doc
        WEBSOCKET_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

        def __init__(self,
                     config = None,
                     socket = None,
                     remote_address = None):
            if socket is None:
                raise WebSocketException("No socket")
            self.socket = socket
            if remote_address is not None:
                self.remote = remote_address
            if config is None:
                config = {}
            self.config = config

        def _parse_raw_request(self, raw_request):
            lines = request.splitlines()
            request = {}
            for line in lines:
                if len(line) == 0:
                    continue
                if ':' in line:
                    key, value = line.split(':', 1)
                    request[key.lower()] = value
            return request

        def _gen_accept_key(self, request):
            websocket_key = request.get('sec-websocket-key')
            if websocket_key is None:
                return ''
            base = "%s%s" % (websocket_key, self.WEBSOCKET_GUID)

        def send_handshake(self, raw_request, additional_headers = None):
            request = self._parse_raw_request(raw_request)
            try:
                handshake = ["HTTP/1.1 101 Web Socket Protocol Handshake",
                    "Upgrade: Websocket",
                    "Connection: Upgrade"]
                handshake.append("WebSocket-Origin: %s:%s\r\n" % self.remote)
                handshake.append("WebSocket-Location: %s\r\n" % \
                        self.config.get("local_address","ws://localhost"))
                if 'sec-websocket-key' in request:
                    handshake.append(self._gen_accept_key(request))
                for h in additional_headers:
                    h.replace("\r",'').replace("\n",'')
                    if len(h):
                        handshake += h + "\r\n"
                handshake += "\r\n"
                self.socket.send(handshake)
                ack = self.socket.read(4)
                #if ack != "\r\n\r\n"
