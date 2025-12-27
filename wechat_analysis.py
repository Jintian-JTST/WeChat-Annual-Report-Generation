import subprocess
import sys

def run(cmd):
    print(f"\n🚀 Running: {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        text=True
    )
    if result.returncode != 0:
        print("❌ 出错了，流程中断")
        sys.exit(result.returncode)

if __name__ == "__main__":
    print("=== WeChat Annual Report Pipeline ===")

    run("python step1_analyze.py")
    run("python step2_render.py")

    print("\n✅ 全部完成！报告已生成")
