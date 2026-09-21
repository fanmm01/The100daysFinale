#!/usr/bin/env python3
"""
replace_lyrics_filtered.py

交互式输入歌词段落，过滤标点、空白、括号及括号内内容，
然后按字符逐个替换 USTX 文件中所有音符的 lyric 字段，
并将替换后的歌词序列输出到标准输出。

输入 'quit' 单独一行时停止输入。

用法：
    python replace_lyrics_filtered.py
"""

import sys
import re
import os
import yaml


def read_text_from_stdin():
    """从标准输入逐行读取，直到 'quit'，返回合并后的字符串。"""
    print("请输入歌词段落（可包含标点、括号等），输入 'quit' 单独一行结束：")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "quit":
            break
        lines.append(line)
    return '\n'.join(lines)


def clean_text(text):
    """
    过滤文本：
    1. 删除所有成对括号及其内部内容（支持 ()[]{}（）【】「」『』<> 等）
    2. 删除所有中英文标点符号和空白字符
    """
    # 第一步：删除括号及括号内内容（非贪婪，不支持嵌套）
    bracket_pattern = r'\(.*?\)|\[.*?\]|\{.*?\}|（.*?）|【.*?】|「.*?」|『.*?』|<.*?>'
    text = re.sub(bracket_pattern, '', text)

    # 第二步：删除所有标点符号和空白字符
    # 包含 ASCII 标点 + 常见中文标点
    punct_whitespace = r'[\s!"#$%&\'()*+,\-./:;<=>?@[\\\]^_`{|}~，。、？！；：“”‘’（）【】《》〈〉「」『』…—～·　]'
    text = re.sub(punct_whitespace, '', text)

    return text


def load_ustx(filepath):
    """加载 USTX 文件（YAML 格式）。"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data


def save_ustx(data, filepath):
    """保存 USTX 文件。"""
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    print(f"已保存至：{filepath}")


def replace_lyrics_with_chars(data, chars):
    """用字符列表替换所有音符的 lyric 字段。"""
    if not chars:
        print("错误：过滤后没有剩余任何歌词字符。")
        sys.exit(1)

    # 收集所有音符
    all_notes = []
    for track in data.get('tracks', []):
        for vp in track.get('voice_parts', []):
            for note in vp.get('notes', []):
                all_notes.append(note)

    if not all_notes:
        print("警告：未找到任何音符。")
        return

    total_notes = len(all_notes)
    total_chars = len(chars)

    if total_chars < total_notes:
        print(f"提示：有效歌词字符数 ({total_chars}) 少于音符数 ({total_notes})，将循环使用字符。")
        for i, note in enumerate(all_notes):
            note['lyric'] = chars[i % total_chars]
    elif total_chars > total_notes:
        print(f"提示：有效歌词字符数 ({total_chars}) 多于音符数 ({total_notes})，多余的字符将被忽略。")
        for i, note in enumerate(all_notes):
            note['lyric'] = chars[i]
    else:
        for i, note in enumerate(all_notes):
            note['lyric'] = chars[i]

    print(f"成功替换了 {total_notes} 个音符的歌词。")


def main():
    # 获取输入文件路径
    filepath = input("请输入 USTX 文件路径（直接回车使用当前目录下第一个 .ustx 文件）：").strip()
    if not filepath:
        files = [f for f in os.listdir('.') if f.endswith('.ustx')]
        if not files:
            print("错误：当前目录下未找到 .ustx 文件。")
            sys.exit(1)
        filepath = files[0]
        print(f"自动选择文件：{filepath}")

    if not os.path.exists(filepath):
        print(f"错误：文件不存在 - {filepath}")
        sys.exit(1)

    # 读取原始文本
    raw_text = read_text_from_stdin()

    # 过滤
    cleaned = clean_text(raw_text)
    if not cleaned:
        print("过滤后没有有效歌词字符，程序退出。")
        sys.exit(0)

    # 输出过滤后的歌词序列到标准输出
    print("\n===== 过滤后的歌词序列（将用于替换）=====")
    print(cleaned)
    print("===========================================\n")

    # 加载 USTX
    try:
        data = load_ustx(filepath)
    except Exception as e:
        print(f"读取 USTX 文件失败：{e}")
        sys.exit(1)

    # 替换歌词
    replace_lyrics_with_chars(data, list(cleaned))

    # 保存新文件
    base, ext = os.path.splitext(filepath)
    out_path = f"{base}_new{ext}"
    save_ustx(data, out_path)

    print("完成！请用 OpenUTAU 打开新文件，并点击“重新生成音素”以获得正确读音。")


if __name__ == '__main__':
    main()
