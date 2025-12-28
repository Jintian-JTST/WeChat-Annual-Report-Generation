import subprocess
import sys

def run(cmd):
    print(f"\n🚀 正在运行: {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        text=True
    )
    if result.returncode != 0:
        print("❌ 出错了，流程中断")
        sys.exit(result.returncode)

if __name__ == "__main__":
    print("=== 微信年度报告生成器 ===")

    run("python step1_analyze.py")
    run("python step2_render.py")

    print("\n✅ 全部完成！报告已生成")
