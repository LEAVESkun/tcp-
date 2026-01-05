# server_demo.py
import socket
import threading

HOST = "127.0.0.1"
PORT = 5000

CHUNK_SIZE = 256 * 1024  # 256KB 固定chunk
CHUNK = b"a" * CHUNK_SIZE

def send_n_bytes(conn, nbytes: int) :
    """只送出nbytes的資料，送完關閉寫入端讓client收到EOF。"""
    remaining = nbytes
    try:
        while remaining > 0:
            to_send=CHUNK if remaining>=CHUNK_SIZE else CHUNK[:remaining]
            conn.sendall(to_send)
            remaining -= len(to_send)
        # 送完了
        conn.shutdown(socket.SHUT_WR)
    except Exception:
        #client 中斷、連線被關，直接結束
        pass

def recv_line(conn) -> str:
    """接收一行以 \\n 結尾的文字（UTF-8）。"""
    data = bytearray()
    while True:
        b = conn.recv(1)
        if not b:
            break
        if b == b"\n":
            break
        data += b
    return data.decode("utf-8", errors="replace").strip()

def handle_one_test(server_sock: socket.socket) -> None:
    """
    一次測試流程：
    1) accept 第1條連線（控制+也會當作其中一條資料流）
    2) client 送: TEST <bytes> <streams>
    3) server 回: OK
    4) accept 其餘 streams-1 條連線（每條回 OK）
    5) 多執行緒同時送資料
    6) 等 client 回傳 RESULT / FINAL 給第1條連線，server 印出
    """
    ctrl_conn, addr = server_sock.accept()

    line = recv_line(ctrl_conn)
    # 期待: TEST <bytes> <streams>
    parts = line.split()
    if len(parts) != 3 or parts[0] != "TEST":
        ctrl_conn.sendall(b"ERR\n")
        ctrl_conn.close()
        return

    total_bytes = int(parts[1])
    streams = int(parts[2])
    if streams <= 0:
        ctrl_conn.sendall(b"ERR\n")
        ctrl_conn.close()
        return

    ctrl_conn.sendall(b"OK\n")

    conns = [ctrl_conn]
    # accept 其餘資料流連線
    for _ in range(streams - 1):
        c, _ = server_sock.accept()
        _ = recv_line(c)  # 期待 STREAM
        c.sendall(b"OK\n")
        conns.append(c)

    # 分配每條連線要送多少 bytes
    per = total_bytes // streams
    sizes = [per] * streams
    sizes[-1] += total_bytes - per * streams  # 把餘數丟給最後一條

    threads = []
    for i in range(streams):
        t = threading.Thread(target=send_n_bytes, args=(conns[i], sizes[i]), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    # 送完後，等待 client 回傳結果（在 ctrl_conn 上）
    result_line = recv_line(ctrl_conn)
    if result_line:
        print(result_line)  # 直接顯示 client 回傳的 RESULT/FINAL

    # 關閉所有連線
    for c in conns:
        try:
            c.close()
        except Exception:
            pass

def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(50)

    print(f"[Server] Listening on {HOST}:{PORT}")
    print("[Server] 等待 Client 測試...（Ctrl+C 結束）")

    try:
        while True:
            handle_one_test(server_sock)
    except KeyboardInterrupt:
        print("\n[Server] Bye.")
    finally:
        server_sock.close()

if __name__ == "__main__":
    main()
