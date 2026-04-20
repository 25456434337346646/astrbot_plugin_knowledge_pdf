import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def test_font():
    font_path = "/System/Library/Fonts/STHeiti Light.ttc"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont("TestHeiti", font_path))
            print(f"SUCCESS: 字体 {font_path} 注册成功。")
            return 0
        except Exception as e:
            print(f"FAILURE: 字体注册失败: {e}")
            return 1
    else:
        print(f"WARNING: 字体文件 {font_path} 不存在。")
        return 0 # 不报错，因为这只是环境检测

if __name__ == "__main__":
    exit(test_font())
