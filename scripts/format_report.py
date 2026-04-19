#!/usr/bin/env python3
"""
生成作文评分报告模板
用法: python format_report.py --title "xxx" --score 25 --grade "良好"
"""

import argparse
from datetime import datetime

def generate_report(title, essay_text, scores, total_score, grade, 
                    highlights=None, issues=None, suggestions=None,
                    requirements=None, char_count=None):
    """生成评分报告"""
    
    report = []
    report.append("# 📝 小学作文评分分析")
    report.append("")
    
    # 作文要求（如有）
    if requirements:
        report.append("## 一、作文要求")
        report.append("")
        if requirements.get('title'):
            report.append(f"**题目**：{requirements['title']}")
        if requirements.get('min_chars'):
            char_str = f"{requirements['min_chars']}"
            if requirements.get('max_chars'):
                char_str += f"-{requirements['max_chars']}"
            report.append(f"**字数要求**：{char_str}字")
        if requirements.get('techniques'):
            report.append(f"**写作要求**：{', '.join(requirements['techniques'])}")
        report.append("")
    
    # 作文原文
    report.append("## 二、作文原文")
    report.append("")
    report.append(f"**标题**：{title}")
    report.append("")
    report.append("**正文**：")
    report.append(f"> {essay_text}")
    report.append("")
    
    # 字数统计
    if char_count:
        report.append(f"**字数统计**：{char_count}字")
        if requirements and requirements.get('min_chars'):
            if char_count >= requirements['min_chars']:
                report.append("✅ 字数达标")
            else:
                report.append(f"❌ 字数不足（少{requirements['min_chars'] - char_count}字）")
        report.append("")
    
    # 评分表
    report.append("## 三、评分标准（满分30分）")
    report.append("")
    report.append("| 评分项目 | 满分 | 得分 | 扣分 | 说明 |")
    report.append("|---------|------|------|------|------|")
    
    for item in scores:
        report.append(f"| {item['name']} | {item['max']}分 | {item['score']}分 | -{item['max']-item['score']}分 | {item['note']} |")
    report.append("")
    
    # 总分
    report.append("## 四、总分")
    report.append("")
    report.append("| 项目 | 分数 |")
    report.append("|------|------|")
    report.append(f"| **总分** | **{total_score}分 / 30分** |")
    report.append(f"| **等级** | **{grade}** |")
    report.append("")
    
    # 亮点
    if highlights:
        report.append("## 五、亮点分析 ✨")
        report.append("")
        for h in highlights:
            report.append(f"- {h}")
        report.append("")
    
    # 不足
    if issues:
        report.append("## 六、不足之处 ⚠️")
        report.append("")
        for i in issues:
            report.append(f"- {i}")
        report.append("")
    
    # 修改建议
    if suggestions:
        report.append("## 七、修改建议")
        report.append("")
        for s in suggestions:
            report.append(f"**原文**：")
            report.append(f"> {s['original']}")
            report.append("")
            report.append(f"**建议修改**：")
            report.append(f"> {s['suggested']}")
            report.append("")
            report.append(f"**理由**：{s['reason']}")
            report.append("")
    
    # 总结
    report.append("## 八、总结")
    report.append("")
    report.append(f"- 总分：{total_score}分（{grade}）")
    if highlights:
        report.append(f"- 优点：{highlights[0] if highlights else '无'}")
    if issues:
        report.append(f"- 改进方向：{issues[0] if issues else '无'}")
    report.append("")
    report.append("---")
    report.append(f"*评分时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    
    return '\n'.join(report)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='生成作文评分报告')
    parser.add_argument('--title', default='待填写', help='作文标题')
    parser.add_argument('--text', default='待填写', help='作文正文')
    parser.add_argument('--score', type=int, default=0, help='总分')
    parser.add_argument('--grade', default='待评', help='等级')
    parser.add_argument('--output', '-o', help='输出文件路径')
    
    args = parser.parse_args()
    
    # 默认评分项
    scores = [
        {'name': '内容质量', 'max': 10, 'score': 0, 'note': '待评'},
        {'name': '语言表达', 'max': 8, 'score': 0, 'note': '待评'},
        {'name': '结构层次', 'max': 6, 'score': 0, 'note': '待评'},
        {'name': '书写规范', 'max': 4, 'score': 0, 'note': '待评'},
        {'name': '字数要求', 'max': 2, 'score': 0, 'note': '待评'},
    ]
    
    report = generate_report(
        title=args.title,
        essay_text=args.text,
        scores=scores,
        total_score=args.score,
        grade=args.grade
    )
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"✅ 报告已保存: {args.output}")
    else:
        print(report)
