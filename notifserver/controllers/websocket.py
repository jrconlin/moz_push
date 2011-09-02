# Websocket Server

# see http://tools.ietf.org/html/draft-ietf-hybi-thewebsocketprotocol-12
IETF_VERSION = "DRAFT-12"


from io import BytesIO

import base64
import hashlib
import socket
import os
import struct
import string


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
            key = base64.b64encode(hashlib.sha1(base))
            return 'Sec-WebSocket-Accept: %s' % key

        def send_handshake(self, raw_request, additional_headers = None):
            request = self._parse_raw_request(raw_request)
            #Check Sec-WebSocket-Protocol: contains service protocol
            if 'protocol' in self.config:
                if (self.config.get('protocol') not in
                    request.get('sec-websocket-protocol','').lower()):
                    raise WebSocketException("Unsupported protocol" +
                       "requested: %s" % request.get('sec-websocket-protocol'))
            try:
                # preflight headers.
                handshake = ["HTTP/1.1 101 Web Socket Protocol Handshake",
                    "Upgrade: Websocket",
                    "Connection: Upgrade"]
                # remote is a tuple of (address, socket)
                handshake.append("WebSocket-Origin: %s:%s\r\n" % self.remote)
                handshake.append("WebSocket-Location: %s\r\n" % \
                        self.config.get("local_address","ws://localhost"))
                if 'sec-websocket-key' in request:
                    handshake.append(self._gen_accept_key(request))
                for h in additional_headers:
                    h.replace("\r",'').replace("\n",'')
                    if len(h):
                        handshake.append(h)
                self.socket.send("%s\r\n\r\n" % "\r\n".join(handshake))
                ack = self.socket.read(4)
                if ack != "\r\n\r\n":
                    raise WebSocketException("Incorrect ACK from client")
            except Exception,e:
                import pdb; pdb.set_trace()
                raise

        #TODO: Make this an passthrough filter.
        def _mask(self, raw_data, mask):
            io_stream = BytesIO(raw_data)
            # TODO: Check that this is correct (ideally mask ints)
            mbytes = [(mask & (0xFF << 0)) >> 0,
                      (mask & (0xFF << 8)) >> 8,
                      (mask & (0xFF << 16)) >> 16,
                      (mask & (0xFF << 24)) >> 24]
            output = BytesIO()
            pos = 0
            try:
                char = io_stream.read(1)
                while char:
                    output.write(char ^ (mask & mbytes[pos % 4]))
                    pos = pos + 1;
                    char = io_stream.read(1)
            except IOError:
                pass
            return output

        code2frame = {0x0: 'Continuation',
                      0x1: 'Text',
                      0x2: 'Binary',
                      0x8: 'Close',
                      0x9: 'Ping',
                      0xA:'Pong',
                      'Continuation': 0x0,
                      'Text': 0x1,
                      'Binary': 0x2,
                      'Close': 0x8,
                      'Ping': 0x9,
                      'Pong': 0xA,
                      }

        def read_frame(self):
            try:
                frame = {}
                byte = self.socket.read(1)
                flags = (0xF0 & byte) >> 4
                frame['is_finished'] = (0x8 & flags) > 0
                frame['type'] = code2frame.get((byte and 0x0F),'Undefined')
                byte = self.socket.read(1)
                frame['is_masked'] = (0x80 & byte) > 0
                byte = 0xF7 & byte
                if byte < 125:
                    frame['size'] = byte
                elif byte == 126:
                    frame['size'] = struct.unpack('!H', self.socket.read(2))
                elif byte == 127:
                    frame['size'] = struct.unpack('!Q', self.socket.read(8))
                if frame['is_masked']:
                    frame['mask'] = self.socket.read(4)
                data = self.socket.read(frame['size'])
                frame['data'] = self._mask(frame['mask'], data)
                return frame
            except IOError, e:
                raise WebSocketException('Error reading data from socket')

        def write_frame(self, frame):
            try:
                if frame is None:
                    return
                if not isinstance(frame, object):
                    raise WebSocketException('Frame should be a dictionary object')
                frame_size = len(frame['data'])
                has_mask = 0x80
                self.socket.write('0x82')
                if frame_size < 0x7D:
                    self.socket.write(has_mask | frame_size)
                elif frame_size < 0xFFFFFF:
                    self.socket.write(has_mask & 0x7E)
                    self.socket.write(struct.pack('!H', frame_size))
                else:
                    self.socket.write(has_mask & 0x7F)
                    self.socket.write(struct.pack('!Q', frame_size))
                if has_mask:
                    self.socket.write(self._mask(frame['data'], 0xFFFFFFFF))
                else:
                    self.socket.write(frame['data'])
                self.socket.flush()
                return True;
            except IOError, e:
                raise WebSocketException('Error writing data')

        def handle_socket(self, request):
            #TODO: Finish this.
            """ handle a new websocket request. See Tarek's redbarrel work
            along with gevent.socket.

            The goal here is to provide a poll-like response. Accept new
            data, return existing queued data, drop connection. client goes
            and waits for a bit. Repeat.

            """
            raise WebSocketException('Requires Implementation')