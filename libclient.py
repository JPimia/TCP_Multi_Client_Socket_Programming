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
        self.request = None
        
    def write(self):
        if not self.request_queued:
            self.queue_request()
            
        self._write()
        
        if self.request.queued:
            if not self._send_buffer:
                # set selector to listen read events
                self._set_selector_events_mask("r")
                
        