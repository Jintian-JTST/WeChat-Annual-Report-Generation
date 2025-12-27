# -*- coding: utf-8 -*-
import subprocess
import re

# 你的工具路径
WXDUMP_EXE = r"C:\Python311\Scripts\wxdump.exe"

print("🔍 正在尝试从微信内存抓取 Key...")
print("⚠️ 请确保微信已经登录并在运行中！\n")

try:
    # 尝试多种常用的获取信息指令
    cmd = [WXDUMP_EXE, "info"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='gbk', errors='ignore')
    
    output = result.stdout + result.stderr
    print("--------------------------------------------------")
    print(output)
    print("--------------------------------------------------")
    
    # 尝试自动帮你找 Key
    # 常见的 Key 格式是 64位 16进制字符串
    keys = re.findall(r'[a-f0-9]{64}', output)
    if keys:
        print(f"\n✅ 找到疑似 Key: {keys[0]}")
        print("👉 请复制上面这个 Key，替换掉之前脚本里的旧 Key！")
    else:
        print("\n❌ 没自动提取到。请人工看上面打印的信息，找 'key': 'xxxx' 这一行。")

except Exception as e:
    print(f"运行出错: {e}")