# -*- coding: utf-8 -*-
import os
import sys

# 1. 屏蔽那个烦人的 protobuf 红色警告
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

try:
    # 2. 导入核心工具
    from pywxdump import get_wx_info
    
    print("正在扫描运行中的微信，请稍候...")
    
    # 3. 获取信息
    infos = get_wx_info()
    
    if not infos:
        print("\n❌ 未检测到登录状态的微信！")
        print("请确认：")
        print("1. 微信 PC 版 (3.9.x) 是否已登录？")
        print("2. 是否以【管理员身份】运行了此命令行？")
    else:
        print(f"\n✅ 成功检测到 {len(infos)} 个账号！\n")
        for i, info in enumerate(infos):
            print(f"-------- 账号 {i+1} 信息 --------")
            print(f"【昵称】: {info.get('name', '未知')}")
            print(f"【微信ID】: {info.get('wxid')}")
            print(f"【数据库路径】: {info.get('db_path')}")
            print(f"【密钥 (Key)】: {info.get('key')}")  # <--- 这是最重要的！
            print("--------------------------------\n")
            
            # 为了方便您，自动把 Key 保存到文件里
            with open("key_result.txt", "w", encoding="utf-8") as f:
                f.write(info.get('key'))
            print("💡 提示：密钥已自动保存到当前目录的 key_result.txt 文件中。")

except ImportError:
    print("❌ 错误：未安装 pywxdump 库，请运行 pip install pywxdump")
except Exception as e:
    print(f"❌ 发生未知错误: {e}")