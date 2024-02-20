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