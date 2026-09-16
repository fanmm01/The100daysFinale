import time
import sys

records = []  # 每条记录: (timestamp, interval)


def now_str(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def main():
    print("=== 时间记录器 ===")
    print("规则：每次【换行】或【空格】即记录一次时刻与间隔")
    print("      输入 q 结束并保存\n")

    start = time.time()
    records.append((start, 0.0))
    print(f"[起始] {now_str(start)}  间隔: 0.000s")

    last = start
    buf = ""

    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)

            # 判定"换行"或"空格"
            if ch in ("\n", "\r", " "):
                ts = time.time()
                interval = ts - last
                records.append((ts, interval))
                print(f"[记录] {now_str(ts)}  间隔: {interval:.3f}s")
                last = ts
                buf = ""
            elif ch in ("q", "Q"):
                print("\n收到退出指令 q")
                break
            else:
                # 其他字符追加到缓冲区（可选：忽略）
                buf += ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    # 组装数组
    result = [
        {"time": now_str(ts), "timestamp": ts, "interval": round(iv, 3)}
        for ts, iv in records
    ]

    # 控制台输出数组
    print("\n=== 记录结果数组 ===")
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 保存到文件
    with open("time_records.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n已保存到 time_records.json")


if __name__ == "__main__":
    main()
