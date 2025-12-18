import socket
import time

HOST = '0.0.0.0'
PORT = 5000

# socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(1)

print("等待Client連線...")
conn, addr = server.accept()
print("已連線：", addr)

# 建立10MB的資料 
data = b'a' * (10 * 1024 * 1024)

#計時
start = time.time()
conn.sendall(data)
end = time.time()

conn.close()
server.close()

print(f"傳送時間：{end - start:.4f} 秒")
print(f"傳送速度：約 {(10 / (end - start)):.2f} MB/s")