import argparse
import socket
import threading
import time
import statistics

HOST = "127.0.0.1"
PORT = 5000

def recv_all(conn: socket.socket, bufsize: int) -> int:
    """一直收直到 EOF，回傳總共收到的 bytes。"""
    total = 0
    while True:
        chunk = conn.recv(bufsize)
        if not chunk:
            break
        total += len(chunk)
    return total

def run_one_trial(total_bytes: int, streams: int, bufsize: int) -> tuple[float, int]:
    """
    單次測試：
    - 先開第一條連線送 TEST
    - 再開 streams-1 條連線
    - 同時接收所有連線的資料
    - 回傳 (seconds, received_bytes)
    """
    # 第1條：控制 + 也是資料流之一
    ctrl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ctrl.connect((HOST, PORT))
    ctrl.sendall(f"TEST {total_bytes} {streams}\n".encode("utf-8"))
    ok = ctrl.recv(64)
    if not ok.startswith(b"OK"):
        ctrl.close()
        raise RuntimeError("Server did not accept TEST")

    conns = [ctrl]

    # 其餘資料流
    for _ in range(streams - 1):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        s.sendall(b"STREAM\n")
        ok2 = s.recv(64)
        if not ok2.startswith(b"OK"):
            s.close()
            raise RuntimeError("Server did not accept STREAM")
        conns.append(s)

    received_list = [0] * streams

    def worker(i: int):
        received_list[i] = recv_all(conns[i], bufsize)

    threads = []
    start = time.time()
    for i in range(streams):
        t = threading.Thread(target=worker, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
    end = time.time()

    received_total = sum(received_list)
    seconds = end - start

    # 這裡先不 close ctrl，因為要回傳結果給 server
    # 先把其他連線關掉
    for c in conns[1:]:
        c.close()

    return seconds, received_total, ctrl

def main():
    ap = argparse.ArgumentParser(description="Mini iperf demo (loopback)")
    ap.add_argument("--size-mb", type=int, default=50, help="傳輸大小 (MB)，例如 10/50/200")
    ap.add_argument("--trials", type=int, default=5, help="每組跑幾次")
    ap.add_argument("--buf-kb", type=int, default=64, help="recv buffer (KB)，例如 4/16/64")
    ap.add_argument("--streams", type=int, default=1, help="同時幾條 TCP 連線 (1/2/4)")
    args = ap.parse_args()

    total_bytes = args.size_mb * 1024 * 1024
    bufsize = args.buf_kb * 1024
    trials = args.trials
    streams = args.streams

    speeds = []  # MB/s

    print(f"[Client] size={args.size_mb}MB, trials={trials}, recv_buf={args.buf_kb}KB, streams={streams}")

    for i in range(1, trials + 1):
        seconds, received, ctrl = run_one_trial(total_bytes, streams, bufsize)

        mb = received / (1024 * 1024)
        mbps = mb / seconds if seconds > 0 else 0.0
        speeds.append(mbps)

        # 回傳單次結果給 server（更漂亮）
        msg = f"RESULT trial={i}/{trials} size={args.size_mb}MB streams={streams} buf={args.buf_kb}KB time={seconds:.4f}s speed={mbps:.2f}MB/s\n"
        ctrl.sendall(msg.encode("utf-8"))
        ctrl.close()

        print(msg.strip())

    avg = statistics.mean(speeds)
    std = statistics.pstdev(speeds)  # 母體標準差（也可用 stdev）
    final = f"FINAL avg={avg:.2f}MB/s std={std:.2f}MB/s (n={trials}) size={args.size_mb}MB streams={streams} buf={args.buf_kb}KB"
    print(final)

    # 把最終摘要也回傳給 server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.sendall(f"TEST 0 1\n".encode("utf-8"))
    _ = s.recv(64) # 等待 server 回應 OK
    
    # --- 修正順序 ---
    s.sendall((final + "\n").encode("utf-8"))
    s.shutdown(socket.SHUT_WR)               
    s.close()                              #關閉連線

if __name__ == "__main__":
    main()
"""enter this
python client_demo.py --size-mb 50 --trials 5 --buf-kb 64 --streams 1



python client_demo.py --size-mb 10  --trials 5 --buf-kb 64 --streams 1

python client_demo.py --size-mb 50  --trials 5 --buf-kb 64 --streams 1

python client_demo.py --size-mb 200 --trials 5 --buf-kb 64 --streams 1



python client_demo.py --size-mb 50 --trials 5 --buf-kb 4  --streams 1

python client_demo.py --size-mb 50 --trials 5 --buf-kb 16 --streams 1

python client_demo.py --size-mb 50 --trials 5 --buf-kb 64 --streams 1



python client_demo.py --size-mb 200 --trials 5 --buf-
"""