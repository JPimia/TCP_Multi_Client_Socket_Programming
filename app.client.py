import socket
import selectors
import libclient
import traceback

sel = selectors.DefaultSelector()

def start_connection(host, port, request):
    addr = (host, port)
    print(f"Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)
    
try:
    while True:
        events = sel.select(timeout=1)
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
            except Exception:
                print(
                    f"Main: Error: Exception for {message.addr}:\n"
                    f"{traceback.format_exc()}"
                )
                message.close()
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()
    
# host = "127.0.0.1" # server's hostname or ip
# port = 3000 # server's port

# with socket.socket(socket.AF_INET, socket.SOCK_STREAM)as s:
#     s.connect((host, port))
#     s.sendall(b"hello world")
#     data = s.recv(1024)
    
# print(f"received {data!r}")