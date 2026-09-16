#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def generate_mtsx(max_chars=10000, output_file="column_pg.mtsx"):
    """
    生成 MT 语法文件，实现：
      - 每行从 || 后独立计数，每 8 字符一组
      - 组内前4字符 blueFg，后4字符 greenFg
      - 遇全角字符停止着色（使用 [\x00-\x7f] 半角限定）
      - 非 8 倍数行末尾多余字符不着色，不错位
    max_chars: 每行最大支持的半角字符数（必须是 8 的倍数）
    """
    groups = max_chars // 8
    styles_block = '''styles: [
    "blueFg", #FFFFFF#00FFFF, #FFFFFF#00FFFF
    "greenFg", #000000#FFFF00, #000000#FFFF00
]'''

    # 构造超长正则：每组 ([\x00-\x7f]{4})([\x00-\x7f]{4})
    group_pairs = []
    for _ in range(groups):
        group_pairs.append(r"([\x00-\x7f]{4})([\x00-\x7f]{4})")
    regex_str = "/" + "".join(group_pairs) + "/"

    # 构造 match 匹配器中的捕获组序号映射
    captures = []
    for i in range(groups * 2):
        group_num = i + 1
        color = "blueFg" if i % 2 == 0 else "greenFg"
        captures.append(f'{group_num}: "{color}"')
    captures_str = ",\n                    ".join(captures)

    content = f'''// require MT>= 2.16.0
{{
    name: ["列前景示例", ".colfg"],
    ignoreCase: false,

    {styles_block},

    contains: [
        {{
            start: {{match: /\\|\\|/}},
            end: {{match: /(?m)$/}},
            contains: [
                {{
                    match: {regex_str},
                    {captures_str}
                }}
            ]
        }}
    ]
}}
'''
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"已生成 {output_file}，每行最多 {max_chars} 字符")

if __name__ == "__main__":
    generate_mtsx(max_chars=10000)  # 250组 = 2000字符，可按需调整
