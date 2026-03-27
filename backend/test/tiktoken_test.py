# create_tiktoken_cache.py

import tiktoken
import os

# === 1. 设置你想要的缓存目录（推荐放在项目里） ===
cache_dir = os.path.join(os.getcwd(), "tiktoken_cache")
os.makedirs(cache_dir, exist_ok=True)

# === 2. 告诉 tiktoken 使用这个目录作为缓存 ===
os.environ["TIKTOKEN_CACHE_DIR"] = cache_dir

print(f"📌 缓存目录已设置为: {cache_dir}")

# === 3. 加载你想要的 encoding ===
encoding_name = "o200k_base"

try:
    enc = tiktoken.get_encoding(encoding_name)
    print(f"✅ 成功加载: {encoding_name}")

    # === 4. 检查文件是否生成 ===
    cache_file = os.path.join(cache_dir, f"{encoding_name}.tiktoken")
    if os.path.exists(cache_file):
        print(f"🎉 缓存文件已生成: {cache_file}")
        print(f"📊 文件大小: {os.path.getsize(cache_file)} 字节")
    else:
        print(f"⚠️  文件未生成: {cache_file}")
        print("   可能原因：tiktoken 使用内存缓存，未写入磁盘")

except Exception as e:
    print(f"❌ 加载失败: {e}")
    import traceback
    traceback.print_exc()