import sys
import selectors
import json
import io
import struct

class Message:
    def __init__(self, selector, sock, addr, request):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._json_header_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False
        
    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()
            
    def read(self):
        self._read()
        
        if self._json_header_len is None:
            self.process_protoheader()
            
        if self._json_header_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()
                
        if self.jsonheader:
            if self.request is None:
                self.process_request()
                
    def write(self):
        if self.request:
            if not self.response_created:
                self.create_response()
                
            self._write()
            
    def process_protoheader(self):
        hdrlen = 2
        
        if len(self._recv_buffer) >= hdrlen:
            self._json_header_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]
            
    def process_jsonheader(self):
        hdrlen = self._json_header_len
        if len(self._recv_buffer) >= hdrlen:
            self.jsonheader = self._json_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f"Missing required header {reqhdr}")
                
    def process_request(self):
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[content_len:]
        if self.jsonheader["content-type"] == "text/json":
            encoding = self.jsonheader["content-encoding"]
            self.request = self._json_encode(data, encoding)
            print(f"Received request {self.request!r} from {self.addr}")
        else:
            self.request = data
            print(
                f"Received {self.jsonheader['content-type']} "
                f"request from {self.addr}"
            )
        # Set selector to listen for write events, we're done reading.
        self._set_selector_events_mask("w")
        
    def create_response(self):
        if self.jsonheader["content-type"] == "text/json":
            response = self._create_response_json_content()
        else:
            response = self._create_response_binary_content()
        message = self._create_message(**response)
        self.response_created = True
        self._send_buffer += message
        
    def _write(self):
        if self._send_buffer:
            print(f"Sending {self._send_buffer!r} to {self.addr}")
            try:
                # Should be ready to write
                sent = self.sock.send(self._send_buffer)
            except BlockingIOError:
                pass
            else:
                self._send_buffer = self._send_buffer[sent:]
                # Close when the buffer is drained
                if sent and not self._send_buffer:
                    self.close()