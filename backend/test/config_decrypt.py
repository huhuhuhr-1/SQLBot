from apps.datasource.utils.utils import aes_decrypt
from common.utils.utils import SQLBotLogUtil
import json

if __name__ == "__main__":
    data = "lALxGKFqFEr/kGdVSBWUHBfBTaAy0OIalD30epzAT1ElyOAvt/j7XJapAo3hiW3zlZyLBD6DLEL9NgGvdsVGVmwc1Kt/H8Kf0U45gzEdf8zVfxAkGUC8/QOjlm3f8zJcmKobZ26dSsF2YyhVFOzlmGqsN15BI5X7b1cLUtnuZutpB0QCwVDqBDzlLGKWBqugnz0AnbPEsgsVnYK/HnrB7zsElpV66KKEPVcFiNUYzqdxlIB5VLSpXmG3+l4iVICo6VHRQyVccosMVpSe77Xc+A=="

    decrypted_result = aes_decrypt(data)

    try:
        # 尝试解析为JSON并格式化输出
        json_data = json.loads(decrypted_result)
        formatted_json = json.dumps(json_data, indent=4, ensure_ascii=False)
        SQLBotLogUtil.info(formatted_json)
    except json.JSONDecodeError:
        # 如果不是JSON格式，直接输出原文
        SQLBotLogUtil.info(decrypted_result)
