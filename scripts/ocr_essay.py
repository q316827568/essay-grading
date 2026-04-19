#!/usr/bin/env python3
"""
OCR识别作文图片
用法: python ocr_essay.py <image_path> [--output output.txt]
"""

import argparse
import sys

def ocr_image(image_path):
    """使用 RapidOCR 识别图片中的文字"""
    try:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        result, elapse = ocr(image_path)
        
        if result:
            lines = []
            for line in result:
                text = line[1]
                lines.append(text)
            return '\n'.join(lines)
        else:
            return None
    except ImportError:
        print("错误: 请先安装 rapidocr_onnxruntime")
        print("pip install rapidocr_onnxruntime")
        sys.exit(1)

def ocr_with_vision(image_path):
    """使用视觉模型识别（备用方案）"""
    # 这个需要 API 调用，暂时返回提示
    return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OCR识别作文图片')
    parser.add_argument('image', help='作文图片路径')
    parser.add_argument('--output', '-o', help='输出文件路径（默认打印到屏幕）')
    parser.add_argument('--method', '-m', choices=['rapidocr', 'vision'], default='rapidocr', help='识别方法')
    
    args = parser.parse_args()
    
    if args.method == 'rapidocr':
        text = ocr_image(args.image)
    else:
        text = ocr_with_vision(args.image)
    
    if text:
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"✅ 识别完成，保存到: {args.output}")
        else:
            print("=== 识别结果 ===")
            print(text)
    else:
        print("❌ 识别失败")
        sys.exit(1)
