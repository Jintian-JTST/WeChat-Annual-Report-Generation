# -*- coding: utf-8 -*-
import os, shutil, subprocess, sqlite3, pandas as pd, time, re
from pathlib import Path

# ================= 你的配置 =================
WXDUMP_EXE = r"C:\Python311\Scripts\wxdump.exe"
KEY = "fbbbcbf171b74d52aa4d049cc9a7483eea6bec66e47543708b1b5faeec96424d"
# 微信原始路径
MSG_ROOT = r"D:\Users\JTST\Documents\WeChat 3.9\WeChat Files\wxid_1tis6tixepi712\Msg"
# ===========================================

CUR_DIR = os.path.abspath(os.getcwd())
TEMP_DIR = os.path.join(CUR_DIR, "temp_copy")

def run_cmd(cmd):
    """运行命令，忽略乱码报错"""
    try:
        # 使用 shell=True 有时能更好处理 Windows 路径
        subprocess.run(cmd, capture_output=True, text=True, encoding='gbk', errors='ignore')
    except:
        subprocess.run(cmd, capture_output=True)

def safe_decrypt(source_path, output_name):
    """安全解密策略：先复制，再解密"""
    if not os.path.exists(source_path):
        print(f"⚠️ 源文件不存在: {source_path}")
        return False
    
    # 1. 创建临时副本
    if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)
    temp_file = os.path.join(TEMP_DIR, os.path.basename(source_path))
    
    try:
        shutil.copy2(source_path, temp_file)
    except PermissionError:
        print(f"❌ 无法复制 {os.path.basename(source_path)}，请彻底关闭微信！")
        return False
        
    # 2. 解密副本
    output_path = os.path.join(CUR_DIR, output_name)
    print(f"🔓 正在解密: {output_name} ...")
    
    cmd = [WXDUMP_EXE, "decrypt", "-i", temp_file, "-k", KEY, "-o", output_path]
    run_cmd(cmd)
    
    # 3. 检查结果
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024: # 大于1KB才算成功
        return True
    else:
        print(f"❌ 解密失败，生成的文件为空: {output_name}")
        return False

def get_name_map():
    """获取名字映射"""
    # 尝试解密 MicroMsg.db
    source = os.path.join(MSG_ROOT, "MicroMsg.db")
    success = safe_decrypt(source, "de_MicroMsg.db")
    
    name_map = {}
    db_path = os.path.join(CUR_DIR, "de_MicroMsg.db")
    
    if success and os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query("SELECT UserName, Nickname, Remark FROM Contact", conn)
            for _, row in df.iterrows():
                # 优先显示备注，其次昵称
                name = row['Remark'] if row['Remark'] else row['Nickname']
                if name:
                    name_map[row['UserName']] = name
            conn.close()
            print(f"✅ 通讯录加载成功：获取到 {len(name_map)} 个名字")
        except Exception as e:
            print(f"⚠️ 通讯录读取出错: {e}")
    else:
        print("⚠️ 未能获取通讯录，聊天记录将只显示 ID。")
    return name_map

def clean_content(content):
    if not content or pd.isna(content): return ""
    s = str(content)
    if "<msg>" in s or "revokemsg" in s: return ""
    # 去除 wxid 前缀
    return re.sub(r'^wxid_[a-z0-9]+:\n', '', s).strip()

def main():
    print("🚀 启动安全导出模式...")
    
    # 1. 准备名字库
    name_map = get_name_map()
    
    # 2. 处理 MSG0, MSG1, MSG2...
    multi_dir = os.path.join(MSG_ROOT, "Multi")
    db_files = [f for f in os.listdir(multi_dir) if f.startswith("MSG") and f.endswith(".db")]
    
    all_dfs = []
    
    for db_file in db_files:
        source = os.path.join(multi_dir, db_file)
        out_name = f"de_{db_file}"
        
        # 执行解密
        if safe_decrypt(source, out_name):
            try:
                conn = sqlite3.connect(out_name)
                # 读取聊天记录
                query = "SELECT StrTalker, CreateTime, IsSender, StrContent FROM MSG WHERE Type = 1"
                df = pd.read_sql_query(query, conn)
                
                # --- 数据清洗与汉化 ---
                print(f"   📊 正在处理 {out_name} ({len(df)} 条记录)...")
                
                def process_row(row):
                    content = str(row['StrContent'])
                    talker = row['StrTalker']
                    
                    # 1. 确定发言人
                    sender_name = "我"
                    if row['IsSender'] != 1:
                        # 如果是群聊，尝试从内容前缀找人
                        if str(talker).endswith("@chatroom"):
                            match = re.match(r'^(wxid_[a-z0-9]+):\n', content)
                            if match:
                                real_id = match.group(1)
                                sender_name = name_map.get(real_id, real_id) # 查不到就用ID
                        else:
                            # 私聊，发言人就是对话目标
                            sender_name = name_map.get(talker, talker)
                    
                    # 2. 确定群名/对方名字
                    chat_name = name_map.get(talker, talker)
                    
                    return chat_name, sender_name

                # 应用逻辑
                processed = df.apply(process_row, axis=1, result_type='expand')
                df['聊天对象'] = processed[0]
                df['发言人'] = processed[1]
                
                df['时间'] = pd.to_datetime(df['CreateTime'], unit='s') + pd.Timedelta(hours=8)
                df['内容'] = df['StrContent'].apply(clean_content)
                
                # 过滤无效内容
                valid_df = df[df['内容'] != ""][['聊天对象', '发言人', '时间', '内容']]
                all_dfs.append(valid_df)
                conn.close()
                
            except Exception as e:
                print(f"   ❌ 读取数据失败: {e}")

    # 3. 最终导出
    if all_dfs:
        print("🔗 正在合并所有记录...")
        final_df = pd.concat(all_dfs).sort_values(by='时间')
        csv_path = f"微信聊天记录_完整版_{int(time.time())}.csv"
        final_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        
        # 清理临时文件
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
            
        print("\n" + "="*30)
        print(f"🎉 成功！成功！成功！")
        print(f"📁 结果文件: {csv_path}")
        print(f"📊 总计记录: {len(final_df)} 条")
        print("="*30)
    else:
        print("❌ 没有提取到数据。请确认：微信是否已关闭？Key是否正确？")

if __name__ == "__main__":
    main()