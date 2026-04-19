#!/usr/bin/env python3
"""
从作文要求图片中提取关键信息
用法: python extract_requirements.py <image_path>
"""

import argparse
import re
import sys

def ocr_image(image_path):
    """OCR识别图片"""
    try:
        from rapidocr_onnxruntime import RapidOCR
        ocr = RapidOCR()
        result, _ = ocr(image_path)
        if result:
            return '\n'.join([line[1] for line in result])
        return None
    except ImportError:
        print("错误: 请先安装 rapidocr_onnxruntime")
        sys.exit(1)

def extract_requirements(text):
    """从文本中提取作文要求"""
    requirements = {
        'title': None,           # 作文题目
        'min_chars': None,       # 最少字数
        'max_chars': None,       # 最多字数
        'content_type': None,    # 内容类型（写人、记事、状物、写景）
        'techniques': [],        # 写作手法要求
        'examples': [],          # 题目示例
        'raw_text': text         # 原始文本
    }
    
    # 提取题目（常见格式：题目：xxx 或 以"xxx"为题）
    title_match = re.search(r'题目[：:]\s*[""「]?([^""」\n]+)[""」]?', text)
    if title_match:
        requirements['title'] = title_match.group(1).strip()
    
    # 另一种题目格式：以"xxx"为题
    title_match2 = re.search(r'以[""「]([^""」]+)[""」]为题', text)
    if title_match2:
        requirements['title'] = title_match2.group(1).strip()
    
    # 提取字数要求
    char_match = re.search(r'(\d+)\s*字', text)
    if char_match:
        requirements['min_chars'] = int(char_match.group(1))
    
    # 字数范围：xxx-xxx字
    char_range_match = re.search(r'(\d+)\s*[-~]\s*(\d+)\s*字', text)
    if char_range_match:
        requirements['min_chars'] = int(char_range_match.group(1))
        requirements['max_chars'] = int(char_range_match.group(2))
    
    # 提取内容类型
    content_types = ['写人', '记事', '状物', '写景', '议论', '说明', '想象', '应用文']
    for ct in content_types:
        if ct in text:
            requirements['content_type'] = ct
            break
    
    # 提取写作手法要求
    techniques_patterns = [
        r'动作[、，]语言[描写]*',
        r'语言[、，]动作[描写]*',
        r'心理描写',
        r'外貌描写',
        r'环境描写',
        r'比喻',
        r'拟人',
        r'排比',
        r'首尾呼应',
        r'详略得当'
    ]
    for pattern in techniques_patterns:
        if re.search(pattern, text):
            # 提取具体手法名称
            match = re.search(pattern, text)
            if match:
                requirements['techniques'].append(match.group())
    
    # 提取示例人物（如：如消防员、清洁工）
    example_match = re.search(r'[如例如]+[：:]?\s*([^。\n]+)', text)
    if example_match:
        examples_text = example_match.group(1)
        # 分割示例
        examples = re.split(r'[、，,]', examples_text)
        requirements['examples'] = [e.strip() for e in examples if e.strip()]
    
    return requirements

def format_output(req):
    """格式化输出"""
    print("=" * 50)
    print("📋 作文要求提取结果")
    print("=" * 50)
    
    if req['title']:
        print(f"📝 题目: {req['title']}")
    
    if req['min_chars']:
        char_range = f"{req['min_chars']}"
        if req['max_chars']:
            char_range += f"-{req['max_chars']}"
        print(f"📏 字数: {char_range}字")
    
    if req['content_type']:
        print(f"📂 类型: {req['content_type']}")
    
    if req['techniques']:
        print(f"✍️ 写作手法: {', '.join(req['techniques'])}")
    
    if req['examples']:
        print(f"💡 示例: {', '.join(req['examples'])}")
    
    print("\n--- 原始文本 ---")
    print(req['raw_text'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='提取作文要求')
    parser.add_argument('image', help='作文要求图片路径')
    parser.add_argument('--json', '-j', action='store_true', help='输出JSON格式')
    
    args = parser.parse_args()
    
    # OCR识别
    text = ocr_image(args.image)
    
    if text:
        # 提取要求
        requirements = extract_requirements(text)
        
        if args.json:
            import json
            # 移除 raw_text 用于 JSON 输出
            output = {k: v for k, v in requirements.items() if k != 'raw_text'}
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            format_output(requirements)
    else:
        print("❌ OCR识别失败")
        sys.exit(1)
