#!/usr/bin/env python3
"""
小学作文评分系统 v2.0
- 普通模式：KIMI-2.5 多模态识图直接评分
- 专家模式：KIMI识图评分 + 豆包评分 + GLM-5仲裁
"""

import json
import time
import re
import base64
import urllib.request
from datetime import datetime
from openai import OpenAI

# 模型配置
MODELS = {
    "glm-5": {
        "provider": "joybuilder",
        "model": "GLM-5",
        "base_url": "https://modelservice.jdcloud.com/coding/openai/v1",
        "api_key": "pk-ad5e8fc9-6548-485a-b886-31e872a1dded"
    },
    "kimi": {
        "provider": "joybuilder",
        "model": "Kimi-K2.5",
        "base_url": "https://modelservice.jdcloud.com/coding/openai/v1",
        "api_key": "pk-ad5e8fc9-6548-485a-b886-31e872a1dded"
    },
    "doubao": {
        "provider": "doubao",
        "model": "doubao-1-5-lite-32k-250115",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": "ark-2f247cd4-5d9c-42c0-8d7d-86ee87a398dd-06d89"
    },
    "doubao-vision": {
        "provider": "doubao",
        "model": "doubao-1-5-vision-pro-32k-250115",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": "ark-2f247cd4-5d9c-42c0-8d7d-86ee87a398dd-06d89"
    }
}

# 评分标准（含卷面分）
GRADING_CRITERIA = """
## 评分标准（满分32分）

| 维度 | 分值 | 评分要点 |
|------|------|----------|
| 内容质量 | 10分 | 切合题意、中心明确、内容充实、情感真实 |
| 语言表达 | 8分 | 语句通顺、用词准确、表达生动、无语病 |
| 结构层次 | 6分 | 条理清晰、段落分明、过渡自然、首尾呼应 |
| 书写规范 | 4分 | 字迹工整、标点正确、格式规范、错别字少 |
| 字数要求 | 2分 | 达到字数要求（400字以上） |
| 卷面分 | 2分 | 书写整洁、卷面干净、无涂改痕迹 |

## 等级划分
- 29-32分: 一类文·优秀
- 25-28分: 二类文·良好
- 19-24分: 三类文·中等
- 13-18分: 四类文·及格
- 0-12分: 五类文·不及格
"""


def get_client(model_name):
    """获取对应模型的 OpenAI 客户端"""
    config = MODELS[model_name]
    return OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"]
    ), config["model"]


def encode_image(image_path):
    """将图片编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def parse_json_response(content):
    """解析 JSON 响应，处理代码块包裹"""
    # 去掉代码块标记
    content = re.sub(r'^```(?:json)?\s*', '', content.strip())
    content = re.sub(r'\s*```$', '', content)
    content = content.strip()
    
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        return json.loads(json_match.group())
    return {"error": "无法解析JSON", "raw_response": content}


def kimi_grade_image(image_path, requirements=None, essay_title=None):
    """使用 KIMI-2.5 多模态识图并评分"""
    client, model = get_client("kimi")
    
    # 编码图片
    image_base64 = encode_image(image_path)
    
    prompt = f"""你是一位资深的小学语文教研员，请对图片中的手写作文进行评分。

{GRADING_CRITERIA}

## 作文要求
{requirements or '以"追"为话题，写一篇记叙文，通过具体的事例讲述你追逐的往事。字数400字以上。'}

请完成以下任务：
1. 识别并提取作文的全部文字内容（标题和正文）
2. 对作文进行专业评分
3. 给出详细的点评

请按以下JSON格式返回（只返回JSON，不要其他内容）：
{{
    "essay_title": "<作文标题>",
    "essay_text": "<作文正文，完整提取>",
    "char_count": <字数>,
    "conformity_check": {{
        "is_on_topic": true/false,
        "writing_techniques_used": ["<已使用的写作手法>"],
        "writing_techniques_missing": ["<缺少的写作手法>"],
        "topic_analysis": "<题意分析>"
    }},
    "scores": {{
        "内容质量": {{"score": <0-10>, "deduction_reasons": ["<扣分原因>"]}},
        "语言表达": {{"score": <0-8>, "deduction_reasons": ["<扣分原因>"]}},
        "结构层次": {{"score": <0-6>, "deduction_reasons": ["<扣分原因>"]}},
        "书写规范": {{"score": <0-4>, "deduction_reasons": ["<扣分原因>"]}},
        "字数要求": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}},
        "卷面分": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}}
    }},
    "total_score": <总分>,
    "grade": "<等级>",
    "highlights": [
        {{"point": "<亮点标题>", "detail": "<详细说明>", "example": "<原文引用>"}}
    ],
    "issues": [
        {{"point": "<问题标题>", "detail": "<详细说明>", "deduction": "<扣分说明>", "example": "<有问题的原文>"}}
    ],
    "summary": "<总结评语>"
}}
"""

    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }],
            temperature=0.3,
            max_tokens=4000
        )
        
        elapsed = time.time() - start_time
        content = response.choices[0].message.content
        result = parse_json_response(content)
        
        return {
            "model": "kimi",
            "result": result,
            "elapsed_seconds": round(elapsed, 2),
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        return {
            "model": "kimi",
            "error": str(e),
            "elapsed_seconds": time.time() - start_time
        }


def doubao_vision_grade_image(image_path, requirements=None, essay_title=None):
    """使用豆包视觉模型识图并评分"""
    client, model = get_client("doubao-vision")
    
    # 编码图片
    image_base64 = encode_image(image_path)
    
    prompt = f"""你是一位资深的小学语文教研员，请对图片中的手写作文进行评分。

{GRADING_CRITERIA}

## 作文要求
{requirements or '以"追"为话题，写一篇记叙文，通过具体的事例讲述你追逐的往事。字数400字以上。'}

请完成以下任务：
1. 识别并提取作文的全部文字内容（标题和正文）
2. 对作文进行专业评分
3. 给出详细的点评

请按以下JSON格式返回（只返回JSON，不要其他内容）：
{{
    "essay_title": "<作文标题>",
    "essay_text": "<作文正文，完整提取>",
    "char_count": <字数>,
    "conformity_check": {{
        "is_on_topic": true/false,
        "writing_techniques_used": ["<已使用的写作手法>"],
        "writing_techniques_missing": ["<缺少的写作手法>"],
        "topic_analysis": "<题意分析>"
    }},
    "scores": {{
        "内容质量": {{"score": <0-10>, "deduction_reasons": ["<扣分原因>"]}},
        "语言表达": {{"score": <0-8>, "deduction_reasons": ["<扣分原因>"]}},
        "结构层次": {{"score": <0-6>, "deduction_reasons": ["<扣分原因>"]}},
        "书写规范": {{"score": <0-4>, "deduction_reasons": ["<扣分原因>"]}},
        "字数要求": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}},
        "卷面分": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}}
    }},
    "total_score": <总分>,
    "grade": "<等级>",
    "highlights": [
        {{"point": "<亮点标题>", "detail": "<详细说明>", "example": "<原文引用>"}}
    ],
    "issues": [
        {{"point": "<问题标题>", "detail": "<详细说明>", "deduction": "<扣分说明>", "example": "<有问题的原文>"}}
    ],
    "summary": "<总结评语>"
}}
"""

    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }],
            temperature=0.3,
            max_tokens=4000
        )
        
        elapsed = time.time() - start_time
        content = response.choices[0].message.content
        result = parse_json_response(content)
        
        return {
            "model": "doubao-vision",
            "result": result,
            "elapsed_seconds": round(elapsed, 2),
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        return {
            "model": "doubao-vision",
            "error": str(e),
            "elapsed_seconds": time.time() - start_time
        }


def kimi_extract_and_grade(image_path, requirements=None, essay_title=None):
    """KIMI-2.5 识图提取正文 + 评分（专家模式用）"""
    return kimi_grade_image(image_path, requirements, essay_title)


def doubao_grade_text(essay_text, requirements=None, essay_title=None):
    """豆包评分（文本输入）"""
    client, model = get_client("doubao")
    
    char_count = len(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]', essay_text))
    
    prompt = f"""你是一位资深的小学语文教研员，请对以下作文进行专业评分。

{GRADING_CRITERIA}

## 作文要求
{requirements or '以"追"为话题，写一篇记叙文，通过具体的事例讲述你追逐的往事。字数400字以上。'}

## 字数统计
- 实际字数：约 {char_count} 字
- 要求字数：400 字左右
- {"✅ 符合要求" if char_count >= 400 else f"❌ 不足（差{400 - char_count}字）"}

## 作文内容
标题：{essay_title or '(未提供标题)'}

正文：
{essay_text}

---

请按以下JSON格式返回（只返回JSON，不要其他内容）：
{{
    "conformity_check": {{
        "is_on_topic": true/false,
        "writing_techniques_used": ["<已使用的写作手法>"],
        "writing_techniques_missing": ["<缺少的写作手法>"],
        "topic_analysis": "<题意分析>"
    }},
    "scores": {{
        "内容质量": {{"score": <0-10>, "deduction_reasons": ["<扣分原因>"]}},
        "语言表达": {{"score": <0-8>, "deduction_reasons": ["<扣分原因>"]}},
        "结构层次": {{"score": <0-6>, "deduction_reasons": ["<扣分原因>"]}},
        "书写规范": {{"score": <0-4>, "deduction_reasons": ["<扣分原因>"]}},
        "字数要求": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}},
        "卷面分": {{"score": <0-2>, "deduction_reasons": ["<扣分原因，根据文本推测>"]}}
    }},
    "total_score": <总分>,
    "grade": "<等级>",
    "highlights": [
        {{"point": "<亮点标题>", "detail": "<详细说明>", "example": "<原文引用>"}}
    ],
    "issues": [
        {{"point": "<问题标题>", "detail": "<详细说明>", "deduction": "<扣分说明>", "example": "<有问题的原文>"}}
    ],
    "summary": "<总结评语>"
}}
"""

    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000
        )
        
        elapsed = time.time() - start_time
        content = response.choices[0].message.content
        result = parse_json_response(content)
        
        return {
            "model": "doubao",
            "result": result,
            "char_count": char_count,
            "elapsed_seconds": round(elapsed, 2),
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        return {
            "model": "doubao",
            "error": str(e),
            "elapsed_seconds": time.time() - start_time
        }


def glm5_arbitrate(kimi_result, doubao_result, essay_text, requirements=None):
    """GLM-5 仲裁 KIMI 和豆包的评分"""
    client, model = get_client("glm-5")
    
    prompt = f"""你是一位教育专家，现在需要对两个AI模型的小学作文评分结果进行仲裁，给出最终评分。

{GRADING_CRITERIA}

## 作文要求
{requirements or '以"追"为话题，写一篇记叙文'}

## 作文内容
{essay_text[:1500]}

## 模型A（KIMI-2.5，多模态识图评分）的评分结果：
{json.dumps(kimi_result, ensure_ascii=False, indent=2)}

## 模型B（豆包）的评分结果：
{json.dumps(doubao_result, ensure_ascii=False, indent=2)}

---

请分析两个模型的评分差异，给出你的仲裁意见：

请按以下JSON格式返回（只返回JSON）：
{{
    "comparison": {{
        "kimi_analysis": "<KIMI评分合理性分析>",
        "doubao_analysis": "<豆包评分合理性分析>",
        "key_differences": ["<主要差异1>", "<主要差异2>"]
    }},
    "conformity_check": {{
        "is_on_topic": true/false,
        "writing_techniques_used": ["<已使用的写作手法>"],
        "writing_techniques_missing": ["<缺少的写作手法>"],
        "topic_analysis": "<题意分析>"
    }},
    "final_scores": {{
        "内容质量": {{"score": <0-10>, "deduction_reasons": ["<扣分原因>"]}},
        "语言表达": {{"score": <0-8>, "deduction_reasons": ["<扣分原因>"]}},
        "结构层次": {{"score": <0-6>, "deduction_reasons": ["<扣分原因>"]}},
        "书写规范": {{"score": <0-4>, "deduction_reasons": ["<扣分原因>"]}},
        "字数要求": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}},
        "卷面分": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}}
    }},
    "final_total": <总分>,
    "final_grade": "<等级>",
    "highlights": [
        {{"point": "<亮点标题>", "detail": "<详细说明>", "example": "<原文引用>"}}
    ],
    "issues": [
        {{"point": "<问题标题>", "detail": "<详细说明>", "deduction": "<扣分说明>", "example": "<有问题的原文>"}}
    ],
    "arbitration_reason": "<仲裁理由>",
    "summary": "<总结评语>"
}}
"""

    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4000
        )
        
        elapsed = time.time() - start_time
        content = response.choices[0].message.content
        result = parse_json_response(content)
        
        return {
            "result": result,
            "elapsed_seconds": round(elapsed, 2),
            "tokens": {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "elapsed_seconds": time.time() - start_time
        }


def format_single_report(result, requirements=None):
    """格式化普通模式报告"""
    r = result["result"]
    char_count = r.get("char_count", 0)
    
    word_status = "✅ 符合要求" if char_count >= 400 else f"❌ 不足（差{400 - char_count}字）"
    
    lines = []
    lines.append("📝 小学作文评分分析（按专业标准）")
    lines.append("")
    
    # 1、字数统计
    lines.append("1、字数统计")
    lines.append(f"约 {char_count} 字（要求 400 字左右）{word_status}")
    lines.append("")
    
    # 2、符合题意检查
    lines.append("2、符合题意检查")
    if "conformity_check" in r:
        cc = r["conformity_check"]
        lines.append(f"切合题意：{'✅ 是' if cc.get('is_on_topic', True) else '❌ 否'}")
        if cc.get("writing_techniques_used"):
            lines.append(f"已使用：{', '.join(cc['writing_techniques_used'])}")
        if cc.get("writing_techniques_missing"):
            lines.append(f"缺少：{', '.join(cc['writing_techniques_missing'])}")
        if cc.get("topic_analysis"):
            lines.append(f"分析：{cc['topic_analysis']}")
    lines.append("")
    
    # 3、分项评分
    lines.append("3、分项评分")
    scores = r.get("scores", {})
    total = 0
    max_scores = {"内容质量": 10, "语言表达": 8, "结构层次": 6, "书写规范": 4, "字数要求": 2, "卷面分": 2}
    for dim in ["内容质量", "语言表达", "结构层次", "书写规范", "字数要求", "卷面分"]:
        if dim in scores:
            s = scores[dim]
            score_val = s.get("score", 0) if isinstance(s, dict) else s
            total += score_val
            lines.append(f"{dim}：{score_val}/{max_scores[dim]}")
            if isinstance(s, dict) and s.get("deduction_reasons"):
                for reason in s["deduction_reasons"]:
                    lines.append(f"  - {reason}")
    lines.append("")
    
    # 4、详细点评
    lines.append("4、详细点评")
    lines.append("")
    
    lines.append("✅ 优点")
    for h in r.get("highlights", []):
        if isinstance(h, dict):
            lines.append(f"• {h.get('point', '亮点')}：{h.get('detail', '')}")
            if h.get("example"):
                lines.append(f"  > {h['example']}")
        else:
            lines.append(f"• {h}")
    lines.append("")
    
    lines.append("⚠ 不足之处")
    for issue in r.get("issues", []):
        if isinstance(issue, dict):
            lines.append(f"• {issue.get('point', '问题')}：{issue.get('detail', '')}")
            if issue.get("deduction"):
                lines.append(f"  扣分：{issue['deduction']}")
            if issue.get("example"):
                lines.append(f"  > {issue['example']}")
        else:
            lines.append(f"• {issue}")
    lines.append("")
    
    # 5、总分及总结
    final_total = r.get("total_score", total)
    final_grade = r.get("grade", "三类文·中等")
    lines.append("5、总分及总结")
    lines.append(f"**{final_total} / 32 分（{final_grade}）**")
    lines.append("")
    
    if r.get("summary"):
        lines.append(r["summary"])
    
    lines.append("")
    lines.append("---")
    lines.append(f"⏱️ {result.get('elapsed_seconds', 0)}秒 | KIMI-2.5 多模态识图评分")
    
    return "\n".join(lines)


def format_expert_report(results):
    """格式化专家模式报告"""
    lines = []
    lines.append("📝 小学作文评分分析（专家模式）")
    lines.append("")
    
    kimi_result = results.get("kimi", {}).get("result", {})
    doubao_result = results.get("doubao", {}).get("result", {})
    arbitration = results.get("arbitration", {}).get("result", {})
    
    # 1、字数统计
    char_count = kimi_result.get("char_count", 0) or results.get("essay_length", 0)
    word_status = "✅ 符合要求" if char_count >= 400 else f"❌ 不足（差{400 - char_count}字）"
    lines.append("1、字数统计")
    lines.append(f"约 {char_count} 字（要求 400 字左右）{word_status}")
    lines.append("")
    
    # 2、符合题意检查
    lines.append("2、符合题意检查")
    cc = arbitration.get("conformity_check", kimi_result.get("conformity_check", {}))
    lines.append(f"切合题意：{'✅ 是' if cc.get('is_on_topic', True) else '❌ 否'}")
    if cc.get("writing_techniques_used"):
        lines.append(f"已使用：{', '.join(cc['writing_techniques_used'])}")
    if cc.get("writing_techniques_missing"):
        lines.append(f"缺少：{', '.join(cc['writing_techniques_missing'])}")
    if cc.get("topic_analysis"):
        lines.append(f"分析：{cc['topic_analysis']}")
    lines.append("")
    
    # 3、分项评分
    lines.append("3、分项评分")
    
    kimi_has_result = "scores" in kimi_result or "total_score" in kimi_result
    doubao_has_result = "scores" in doubao_result or "total_score" in doubao_result
    
    final_scores = arbitration.get("final_scores", {})
    
    for dim in ["内容质量", "语言表达", "结构层次", "书写规范", "字数要求", "卷面分"]:
        if kimi_has_result:
            ks = kimi_result.get("scores", {}).get(dim, {})
            k_val = ks.get("score", 0) if isinstance(ks, dict) else ks
            k_str = str(k_val)
        else:
            k_str = "N/A"
        
        if doubao_has_result:
            ds = doubao_result.get("scores", {}).get(dim, {})
            d_val = ds.get("score", 0) if isinstance(ds, dict) else ds
            d_str = str(d_val)
        else:
            d_str = "N/A"
        
        fs = final_scores.get(dim, {})
        f_val = fs.get("score", 0) if isinstance(fs, dict) else fs
        
        lines.append(f"{dim}：KIMI {k_str}分 | 豆包 {d_str}分 | 最终 {f_val}分")
    
    lines.append("")
    
    # 4、详细点评
    lines.append("4、详细点评")
    lines.append("")
    
    lines.append("✅ 优点")
    for h in arbitration.get("highlights", kimi_result.get("highlights", [])):
        if isinstance(h, dict):
            lines.append(f"• {h.get('point', '亮点')}：{h.get('detail', '')}")
            if h.get("example"):
                lines.append(f"  > {h['example']}")
    lines.append("")
    
    lines.append("⚠ 不足之处")
    for issue in arbitration.get("issues", kimi_result.get("issues", [])):
        if isinstance(issue, dict):
            lines.append(f"• {issue.get('point', '问题')}：{issue.get('detail', '')}")
            if issue.get("deduction"):
                lines.append(f"  扣分：{issue['deduction']}")
            if issue.get("example"):
                lines.append(f"  > {issue['example']}")
    lines.append("")
    
    # 5、总分及总结
    final_total = arbitration.get("final_total", kimi_result.get("total_score", 0))
    final_grade = arbitration.get("final_grade", kimi_result.get("grade", "三类文·中等"))
    
    kimi_score = kimi_result.get("total_score", "N/A")
    doubao_score = doubao_result.get("total_score", "N/A")
    
    lines.append("5、总分及总结")
    lines.append(f"KIMI：{kimi_score}分 | 豆包：{doubao_score}分")
    lines.append(f"**最终得分：{final_total} / 32 分（{final_grade}）**")
    lines.append("")
    
    if arbitration.get("summary"):
        lines.append(arbitration["summary"])
    
    lines.append("")
    
    # 6、不同专家的打分及差异及评审意见
    lines.append("6、不同专家的打分及差异及评审意见")
    lines.append("")
    
    # KIMI 评审意见
    lines.append(f"【KIMI】评分：{kimi_score}分")
    if kimi_has_result and kimi_score != "N/A":
        if kimi_result.get("issues"):
            lines.append("主要问题：")
            for issue in kimi_result.get("issues", [])[:3]:
                if isinstance(issue, dict):
                    lines.append(f"  • {issue.get('point', '')}：{issue.get('detail', '')}")
        if kimi_result.get("highlights"):
            lines.append("亮点：")
            for h in kimi_result.get("highlights", [])[:2]:
                if isinstance(h, dict):
                    lines.append(f"  • {h.get('point', '')}：{h.get('detail', '')}")
    else:
        lines.append("（未返回有效评分结果）")
    lines.append("")
    
    # 豆包评审意见
    lines.append(f"【豆包】评分：{doubao_score}分")
    if doubao_has_result and doubao_score != "N/A":
        if doubao_result.get("issues"):
            lines.append("主要问题：")
            for issue in doubao_result.get("issues", [])[:3]:
                if isinstance(issue, dict):
                    lines.append(f"  • {issue.get('point', '')}：{issue.get('detail', '')}")
        if doubao_result.get("highlights"):
            lines.append("亮点：")
            for h in doubao_result.get("highlights", [])[:2]:
                if isinstance(h, dict):
                    lines.append(f"  • {h.get('point', '')}：{h.get('detail', '')}")
    else:
        lines.append("（未返回有效评分结果）")
    lines.append("")
    
    # 差异分析
    comparison = arbitration.get("comparison", {})
    if comparison:
        lines.append("【差异分析】")
        if comparison.get("key_differences"):
            for diff in comparison.get("key_differences", []):
                lines.append(f"  • {diff}")
    lines.append("")
    
    # Kimi 仲裁意见
    if arbitration.get("arbitration_reason"):
        lines.append("【GLM-5 仲裁意见】")
        lines.append(arbitration["arbitration_reason"])
    
    lines.append("")
    lines.append("---")
    summary = results.get("summary", {})
    lines.append(f"⏱️ {summary.get('total_time_seconds', 0)}秒 | {summary.get('total_tokens', 0)} tokens")
    
    return "\n".join(lines)


def normal_grade_image(image_path, requirements=None, essay_title=None):
    """普通模式：KIMI-2.5 多模态识图直接评分"""
    print(f"📝 KIMI-2.5 多模态识图评分中...")
    
    result = kimi_grade_image(image_path, requirements, essay_title)
    
    if "error" in result:
        return f"评分失败：{result['error']}"
    
    return format_single_report(result, requirements)


def expert_grade_image(image_path, requirements=None, essay_title=None):
    """专家模式：KIMI识图评分 || 豆包Vision识图评分 → GLM-5仲裁
    
    并行优化：KIMI和豆包Vision同时识图评分，最后GLM-5仲裁
    """
    import concurrent.futures
    
    start_time = time.time()
    results = {
        "timestamp": datetime.now().isoformat(),
        "requirements": requirements,
        "kimi": None,
        "doubao": None,
        "arbitration": None,
        "summary": {}
    }
    
    # 第一步：KIMI 和 豆包 Vision 并行识图评分
    print("📝 KIMI-2.5 和 豆包 Vision 并行识图评分中...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        kimi_future = executor.submit(kimi_grade_image, image_path, requirements, essay_title)
        doubao_future = executor.submit(doubao_vision_grade_image, image_path, requirements, essay_title)
        
        kimi_result = kimi_future.result()
        doubao_result = doubao_future.result()
    
    results["kimi"] = kimi_result
    results["doubao"] = doubao_result
    
    print(f"   KIMI 完成，耗时 {kimi_result.get('elapsed_seconds', 0)}s")
    print(f"   豆包 Vision 完成，耗时 {doubao_result.get('elapsed_seconds', 0)}s")
    
    # 获取作文正文（优先用 KIMI 的，因为中文识别可能更准确）
    essay_text = kimi_result.get("result", {}).get("essay_text", "")
    if not essay_text:
        essay_text = doubao_result.get("result", {}).get("essay_text", "")
    results["essay_length"] = len(essay_text) if essay_text else 0
    
    # 第二步：GLM-5 仲裁
    print("⚖️ GLM-5 仲裁中...")
    arbitration = glm5_arbitrate(
        kimi_result.get("result", {}),
        doubao_result.get("result", {}),
        essay_text,
        requirements
    )
    results["arbitration"] = arbitration
    print(f"   完成，耗时 {arbitration.get('elapsed_seconds', 0)}s")
    
    # 汇总
    total_time = time.time() - start_time
    total_tokens = sum(
        r.get("tokens", {}).get("total", 0)
        for r in [kimi_result, doubao_result, arbitration]
        if "tokens" in r
    )
    
    results["summary"] = {
        "total_time_seconds": round(total_time, 2),
        "total_tokens": total_tokens,
        "kimi_score": kimi_result.get("result", {}).get("total_score", "N/A"),
        "doubao_score": doubao_result.get("result", {}).get("total_score", "N/A"),
        "final_score": arbitration.get("result", {}).get("final_total", "N/A"),
        "final_grade": arbitration.get("result", {}).get("final_grade", "N/A")
    }
    
    return format_expert_report(results), results


def send_feishu_card(title, content, color="blue"):
    """发送飞书卡片消息
    
    Args:
        title: 卡片标题
        content: 卡片正文（支持 lark_md 格式）
        color: 标题栏颜色 (blue/green/red/orange/purple/grey)
    
    Returns:
        bool: 是否发送成功
    """
    import os
    from pathlib import Path
    
    # 从 .env 读取飞书配置
    env_vars = {}
    env_path = Path.home() / ".hermes" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    env_vars[k] = v
    
    app_id = env_vars.get('FEISHU_APP_ID', '')
    app_secret = env_vars.get('FEISHU_APP_SECRET', '')
    home_channel = env_vars.get('FEISHU_HOME_CHANNEL', '')
    
    if not all([app_id, app_secret, home_channel]):
        print("飞书配置缺失，跳过发送")
        return False
    
    try:
        # 获取 tenant_access_token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        token = json.loads(resp.read())['tenant_access_token']
        
        # 构建卡片消息
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": content}}
            ]
        }
        
        # 发送消息
        url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
        data = json.dumps({
            "receive_id": home_channel,
            "msg_type": "interactive",
            "content": json.dumps(card)
        }).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        
        if result.get('code') == 0:
            print("飞书卡片消息发送成功")
            return True
        else:
            print(f"飞书卡片消息发送失败: {result}")
            return False
            
    except Exception as e:
        print(f"发送飞书卡片消息出错: {e}")
        return False


def format_expert_report_for_feishu(results):
    """格式化专家模式报告为飞书卡片格式（lark_md）"""
    kimi_result = results.get("kimi", {}).get("result", {})
    doubao_result = results.get("doubao", {}).get("result", {})
    arbitration = results.get("arbitration", {}).get("result", {})
    summary = results.get("summary", {})
    
    lines = []
    
    # 1、字数统计
    char_count = kimi_result.get("char_count", 0) or results.get("essay_length", 0)
    word_status = "✅ 符合要求" if char_count >= 400 else f"❌ 不足（差{400 - char_count}字）"
    lines.append(f"**1、字数统计**\n约 {char_count} 字（要求 400 字左右）{word_status}\n")
    
    # 2、符合题意检查
    cc = arbitration.get("conformity_check", kimi_result.get("conformity_check", {}))
    lines.append(f"**2、符合题意检查**")
    lines.append(f"切合题意：{'✅ 是' if cc.get('is_on_topic', True) else '❌ 否'}")
    if cc.get("writing_techniques_used"):
        lines.append(f"已使用：{', '.join(cc['writing_techniques_used'])}")
    if cc.get("writing_techniques_missing"):
        lines.append(f"缺少：{', '.join(cc['writing_techniques_missing'])}")
    lines.append("")
    
    # 3、分项评分
    lines.append("**3、分项评分**")
    final_scores = arbitration.get("final_scores", {})
    
    kimi_score = kimi_result.get("total_score", "N/A")
    doubao_score = doubao_result.get("total_score", "N/A")
    
    for dim in ["内容质量", "语言表达", "结构层次", "书写规范", "字数要求", "卷面分"]:
        ks = kimi_result.get("scores", {}).get(dim, {})
        k_val = ks.get("score", 0) if isinstance(ks, dict) else ks
        
        ds = doubao_result.get("scores", {}).get(dim, {})
        d_val = ds.get("score", 0) if isinstance(ds, dict) else ds
        
        fs = final_scores.get(dim, {})
        f_val = fs.get("score", 0) if isinstance(fs, dict) else fs
        
        lines.append(f"• {dim}：KIMI {k_val}分 | 豆包 {d_val}分 | **最终 {f_val}分**")
    lines.append("")
    
    # 4、详细点评
    lines.append("**4、详细点评**\n")
    
    lines.append("✅ **优点**")
    for h in arbitration.get("highlights", kimi_result.get("highlights", []))[:3]:
        if isinstance(h, dict):
            lines.append(f"• {h.get('point', '')}：{h.get('detail', '')}")
    lines.append("")
    
    lines.append("⚠️ **不足之处**")
    for issue in arbitration.get("issues", kimi_result.get("issues", []))[:3]:
        if isinstance(issue, dict):
            lines.append(f"• {issue.get('point', '')}：{issue.get('detail', '')}")
    lines.append("")
    
    # 5、总分及总结
    final_total = arbitration.get("final_total", kimi_result.get("total_score", 0))
    final_grade = arbitration.get("final_grade", kimi_result.get("grade", "三类文·中等"))
    
    lines.append(f"**5、总分及总结**")
    lines.append(f"KIMI：{kimi_score}分 | 豆包：{doubao_score}分")
    lines.append(f"**最终得分：{final_total} / 32 分（{final_grade}）**\n")
    
    if arbitration.get("summary"):
        lines.append(arbitration["summary"])
    
    lines.append(f"\n---\n⏱️ {summary.get('total_time_seconds', 0)}秒 | {summary.get('total_tokens', 0)} tokens")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python essay_grader_v2.py <图片路径> [--expert] [--no-feishu]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    expert_mode = "--expert" in sys.argv
    no_feishu = "--no-feishu" in sys.argv
    
    if expert_mode:
        report, results = expert_grade_image(image_path)
        print("\n" + report)
        
        with open("/tmp/essay_expert_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("\n详细结果已保存至 /tmp/essay_expert_result.json")
        
        # 发送飞书卡片消息
        if not no_feishu:
            final_grade = results.get("summary", {}).get("final_grade", "三类文·中等")
            # 根据等级选择颜色
            color_map = {
                "一类文": "green",
                "二类文": "blue", 
                "三类文": "orange",
                "四类文": "red",
                "五类文": "red"
            }
            color = "blue"
            for key, c in color_map.items():
                if key in final_grade:
                    color = c
                    break
            
            card_content = format_expert_report_for_feishu(results)
            send_feishu_card("📝 小学作文评分分析（专家模式）", card_content, color)
    else:
        report = normal_grade_image(image_path)
        print("\n" + report)
