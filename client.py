import socket
import time

HOST = '127.0.0.1'  #server的ip
PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

received = 0
buffer = 4096

start = time.time()
while True:
    chunk = client.recv(buffer)
    if not chunk:
        break
    received += len(chunk)
end = time.time()

client.close()

print(f"接收資料量：{received / (1024*1024):.2f} MB")
print(f"接收時間：{end - start:.4f} 秒")
print(f"接收速度：約 {(received/1024/1024) / (end - start):.2f} MB/s")