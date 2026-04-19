#!/usr/bin/env python3
"""
统计作文字数并检查是否达标
用法: python count_chars.py <text_file|text> --min 400
"""

import argparse
import re
import os

def count_chinese_chars(text):
    """统计中文字符数（不含标点）"""
    # 匹配中文字符
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    return len(chinese_chars)

def count_all_chars(text):
    """统计所有字符（含标点）"""
    # 去除空白字符后统计
    text = re.sub(r'\s+', '', text)
    return len(text)

def check_requirement(count, min_chars, max_chars=None):
    """检查字数是否达标"""
    result = {
        'count': count,
        'min': min_chars,
        'max': max_chars,
        'passed': count >= min_chars,
        'message': ''
    }
    
    if count < min_chars:
        shortage = min_chars - count
        result['message'] = f"❌ 字数不足，少 {shortage} 字"
    elif max_chars and count > max_chars:
        excess = count - max_chars
        result['message'] = f"⚠️ 字数超标，多 {excess} 字"
    else:
        result['message'] = f"✅ 字数达标"
    
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='统计作文字数')
    parser.add_argument('input', help='文本文件路径或直接输入文本')
    parser.add_argument('--min', type=int, default=400, help='最少字数要求（默认400）')
    parser.add_argument('--max', type=int, help='最多字数要求（可选）')
    parser.add_argument('--all', action='store_true', help='统计所有字符（含标点）')
    
    args = parser.parse_args()
    
    # 判断是文件还是直接文本
    if os.path.exists(args.input):
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = args.input
    
    # 统计字数
    if args.all:
        count = count_all_chars(text)
    else:
        count = count_chinese_chars(text)
    
    # 检查达标
    result = check_requirement(count, args.min, args.max)
    
    print(f"字数统计: {count} 字")
    print(f"要求范围: {args.min}" + (f"-{args.max}" if args.max else "+") + " 字")
    print(result['message'])
    
    # 返回退出码
    import sys
    sys.exit(0 if result['passed'] else 1)
