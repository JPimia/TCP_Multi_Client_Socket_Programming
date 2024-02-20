import socket

host = "127.0.0.1" # server's hostname or ip
port = 3000 # server's port

with socket.socket(socket.AF_INET, socket.SOCK_STREAM)as s:
    s.connect((host, port))
    s.sendall(b"hello world")
    data = s.recv(1024)
    
print(f"received {data!r}")