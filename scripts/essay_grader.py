#!/usr/bin/env python3
"""
小学作文评分系统 - 统一格式版本
支持普通模式（单模型）和专家模式（多模型评审+仲裁）
"""

import json
import time
import re
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
    "doubao-1.5-lite": {
        "provider": "doubao",
        "model": "doubao-1-5-lite-32k-250115",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": "ark-2f247cd4-5d9c-42c0-8d7d-86ee87a398dd-06d89"
    },
    "doubao-seed": {
        "provider": "doubao",
        "model": "doubao-seed-2-0-lite-260215",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": "ark-2f247cd4-5d9c-42c0-8d7d-86ee87a398dd-06d89"
    },
    "kimi": {
        "provider": "joybuilder",
        "model": "Kimi-K2.5",
        "base_url": "https://modelservice.jdcloud.com/coding/openai/v1",
        "api_key": "pk-ad5e8fc9-6548-485a-b886-31e872a1dded"
    }
}

# 评分标准
GRADING_CRITERIA = """
## 评分标准（满分30分）

| 维度 | 分值 | 评分要点 |
|------|------|----------|
| 内容质量 | 10分 | 切合题意、中心明确、内容充实、情感真实 |
| 语言表达 | 8分 | 语句通顺、用词准确、表达生动、无语病 |
| 结构层次 | 6分 | 条理清晰、段落分明、过渡自然、首尾呼应 |
| 书写规范 | 4分 | 字迹工整、标点正确、格式规范、错别字少 |
| 字数要求 | 2分 | 达到字数要求 |

## 等级划分
- 27-30分: 一类文·优秀
- 24-26分: 二类文·良好
- 18-23分: 三类文·中等
- 12-17分: 四类文·及格
- 0-11分: 五类文·不及格
"""


def get_client(model_name):
    """获取对应模型的 OpenAI 客户端"""
    config = MODELS[model_name]
    return OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"]
    ), config["model"]


def count_chars(text):
    """统计中文字符数（去除空格和标点）"""
    # 只统计汉字和字母数字
    chars = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]', text)
    return len(chars)


def grade_with_model(model_name, essay_text, requirements=None, essay_title=None, word_requirement=400):
    """使用指定模型进行作文评分"""
    client, model = get_client(model_name)
    
    char_count = count_chars(essay_text)
    word_status = "✅ 符合要求" if char_count >= word_requirement else f"❌ 不足（差{word_requirement - char_count}字）"
    
    prompt = f"""你是一位资深的小学语文教研员，请对以下作文进行专业评分，并给出详细的分析和建议。

{GRADING_CRITERIA}

## 作文要求
{requirements or '未提供具体要求'}

## 字数统计
- 实际字数：约 {char_count} 字
- 要求字数：{word_requirement} 字左右
- {word_status}

## 作文内容
标题：{essay_title or '(未提供标题)'}

正文：
{essay_text}

---

请完成以下评分任务，严格按照要求的JSON格式返回：

1. **符合题意检查**：检查作文是否符合题目要求，包括：
   - 是否切合题意
   - 是否使用了要求的写作手法（如动作描写、语言描写等）
   - 是否选择了合适的题材

2. **分项评分**：给出各维度评分和详细的扣分原因

3. **详细点评**：
   - 列出优点（具体到句子或段落）
   - 列出不足之处（具体到句子或段落，并说明扣分）
   - 给出修改建议和示例

请按以下JSON格式返回（只返回JSON，不要其他内容）：
{{
    "conformity_check": {{
        "is_on_topic": true/false,
        "writing_techniques_used": ["<已使用的写作手法>"],
        "writing_techniques_missing": ["<缺少的写作手法>"],
        "topic_analysis": "<题意分析>"
    }},
    "scores": {{
        "内容质量": {{"score": <0-10>, "deduction_reasons": ["<扣分原因1>", "<扣分原因2>"]}},
        "语言表达": {{"score": <0-8>, "deduction_reasons": ["<扣分原因1>", "<扣分原因2>"]}},
        "结构层次": {{"score": <0-6>, "deduction_reasons": ["<扣分原因1>", "<扣分原因2>"]}},
        "书写规范": {{"score": <0-4>, "deduction_reasons": ["<扣分原因1>", "<扣分原因2>"]}},
        "字数要求": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}}
    }},
    "total_score": <总分>,
    "grade": "<等级，如：三类文·中等>",
    "highlights": [
        {{"point": "<亮点标题>", "detail": "<详细说明，引用原文>", "example": "<原文引用>"}}
    ],
    "issues": [
        {{"point": "<问题标题>", "detail": "<详细说明>", "deduction": "<扣分说明>", "example": "<有问题的原文>"}}
    ],
    "suggestions": [
        {{"original": "<原文>", "revised": "<修改后>", "reason": "<修改理由>"}}
    ],
    "summary": "<总结评语，包括预计得分和等级>"
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
        
        # 解析响应
        content = response.choices[0].message.content
        
        # 尝试提取 JSON
        import re
        # 先去掉代码块标记（如 ```json ... ```）
        content = re.sub(r'^```(?:json)?\s*', '', content.strip())
        content = re.sub(r'\s*```$', '', content)
        content = content.strip()
        
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"error": "无法解析JSON", "raw_response": content}
        
        return {
            "model": model_name,
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
            "model": model_name,
            "error": str(e),
            "char_count": char_count,
            "elapsed_seconds": time.time() - start_time
        }


def arbitrate_with_kimi(glm_result, second_result, essay_text, requirements, second_model_name="豆包"):
    """使用 Kimi-K2.5 对两个模型的评分结果进行仲裁"""
    client, model = get_client("kimi")
    
    prompt = f"""你是一位资深的小学语文教研员，现在需要对两个AI模型的作文评分结果进行仲裁，给出最终评分和详细分析。

{GRADING_CRITERIA}

## 作文要求
{requirements or '未提供具体要求'}

## 作文内容
{essay_text}

## 模型A（GLM-5）的评分结果：
{json.dumps(glm_result, ensure_ascii=False, indent=2)}

## 模型B（{second_model_name}）的评分结果：
{json.dumps(second_result, ensure_ascii=False, indent=2)}

---

请分析两个模型的评分差异，给出你的仲裁意见和详细分析。要求：
1. 比较两个模型的评分，指出哪些评分更合理
2. 对作文进行详细分析，包括符合题意检查、优点、不足
3. 给出具体的修改建议和示例
4. 给出最终评分

请按以下JSON格式返回（只返回JSON）：
{{
    "comparison": {{
        "glm5_analysis": "<GLM-5评分合理性分析>",
        "second_model_analysis": "<{second_model_name}评分合理性分析>",
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
        "字数要求": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}}
    }},
    "final_total": <总分>,
    "final_grade": "<等级>",
    "highlights": [
        {{"point": "<亮点标题>", "detail": "<详细说明>", "example": "<原文引用>"}}
    ],
    "issues": [
        {{"point": "<问题标题>", "detail": "<详细说明>", "deduction": "<扣分说明>", "example": "<有问题的原文>"}}
    ],
    "suggestions": [
        {{"original": "<原文>", "revised": "<修改后>", "reason": "<修改理由>"}}
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
        
        # 解析响应
        content = response.choices[0].message.content
        
        # 尝试提取 JSON
        import re
        # 先去掉代码块标记（如 ```json ... ```）
        content = re.sub(r'^```(?:json)?\s*', '', content.strip())
        content = re.sub(r'\s*```$', '', content)
        content = content.strip()
        
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"error": "无法解析JSON", "raw_response": content}
        
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


def format_single_report(result, requirements=None, essay_title=None):
    """格式化普通模式报告"""
    r = result["result"]
    char_count = result.get("char_count", 0)
    
    # 字数状态
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
    max_scores = {"内容质量": 10, "语言表达": 8, "结构层次": 6, "书写规范": 4, "字数要求": 2}
    for dim in ["内容质量", "语言表达", "结构层次", "书写规范", "字数要求"]:
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
    
    # 优点
    lines.append("✅ 优点")
    for h in r.get("highlights", []):
        if isinstance(h, dict):
            lines.append(f"• {h.get('point', '亮点')}：{h.get('detail', '')}")
            if h.get("example"):
                lines.append(f"  > {h['example']}")
        else:
            lines.append(f"• {h}")
    lines.append("")
    
    # 不足之处
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
    lines.append(f"**{final_total} / 30 分（{final_grade}）**")
    lines.append("")
    
    # 总结
    if r.get("summary"):
        lines.append(r["summary"])
    
    lines.append("")
    lines.append(f"---")
    lines.append(f"⏱️ {result.get('elapsed_seconds', 0)}秒 | {result.get('model', 'unknown')}")
    
    return "\n".join(lines)


def format_expert_report(results):
    """格式化专家模式报告"""
    lines = []
    lines.append("📝 小学作文评分分析（专家模式）")
    lines.append("")
    
    # 1、字数统计
    char_count = results.get("essay_length", 0)
    word_status = "✅ 符合要求" if char_count >= 400 else f"❌ 不足（差{400 - char_count}字）"
    lines.append("1、字数统计")
    lines.append(f"约 {char_count} 字（要求 400 字左右）{word_status}")
    lines.append("")
    
    # 2、符合题意检查
    arb = results.get("arbitration", {}).get("result", {})
    lines.append("2、符合题意检查")
    if "conformity_check" in arb:
        cc = arb["conformity_check"]
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
    
    glm5 = results["model_results"].get("glm-5", {}).get("result", {})
    second_key = results.get("second_model", "doubao-1.5-lite")
    second = results["model_results"].get(second_key, {}).get("result", {})
    second_name = "豆包" if "doubao" in second_key else second_key.upper()
    
    final_scores = arb.get("final_scores", {})
    
    # 检查 GLM-5 是否有有效结果
    glm5_has_result = "scores" in glm5 or "total_score" in glm5
    second_has_result = "scores" in second or "total_score" in second
    
    lines.append(f"{'维度':<8} {'GLM-5':>6} {'豆包':>6} {'最终':>6}")
    lines.append("-" * 30)
    
    for dim in ["内容质量", "语言表达", "结构层次", "书写规范", "字数要求"]:
        if glm5_has_result:
            g5 = glm5.get("scores", {}).get(dim, {})
            g5_val = g5.get("score", 0) if isinstance(g5, dict) else g5
            g5_str = str(g5_val)
        else:
            g5_str = "N/A"
        
        if second_has_result:
            s2 = second.get("scores", {}).get(dim, {})
            s2_val = s2.get("score", 0) if isinstance(s2, dict) else s2
            s2_str = str(s2_val)
        else:
            s2_str = "N/A"
        
        fs = final_scores.get(dim, {})
        fs_val = fs.get("score", 0) if isinstance(fs, dict) else fs
        
        lines.append(f"{dim:<8} {g5_str:>6} {s2_str:>6} {fs_val:>6}")
    
    lines.append("")
    
    # 4、详细点评
    lines.append("4、详细点评")
    lines.append("")
    
    # 优点
    lines.append("✅ 优点")
    for h in arb.get("highlights", []):
        if isinstance(h, dict):
            lines.append(f"• {h.get('point', '亮点')}：{h.get('detail', '')}")
            if h.get("example"):
                lines.append(f"  > {h['example']}")
        else:
            lines.append(f"• {h}")
    lines.append("")
    
    # 不足之处
    lines.append("⚠ 不足之处")
    for issue in arb.get("issues", []):
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
    final_total = arb.get("final_total", 0)
    final_grade = arb.get("final_grade", "三类文·中等")
    lines.append("5、总分及总结")
    lines.append(f"GLM-5：{glm5.get('total_score', 'N/A')}分 | 豆包：{second.get('total_score', 'N/A')}分")
    lines.append(f"**最终得分：{final_total} / 30 分（{final_grade}）**")
    lines.append("")
    
    # 总结
    if arb.get("summary"):
        lines.append(arb["summary"])
    
    lines.append("")
    
    # 6、不同专家的打分及差异及评审意见
    lines.append("6、不同专家的打分及差异及评审意见")
    lines.append("")
    
    # GLM-5 评审意见
    glm5_score = glm5.get('total_score', 'N/A')
    lines.append(f"【GLM-5】评分：{glm5_score}分")
    if glm5_has_result and glm5_score != 'N/A':
        if glm5.get("brief_comment"):
            lines.append(f"评语：{glm5['brief_comment']}")
        elif glm5.get("issues"):
            lines.append("主要问题：")
            for issue in glm5.get("issues", [])[:3]:
                if isinstance(issue, dict):
                    lines.append(f"  • {issue.get('point', '')}：{issue.get('detail', '')}")
                else:
                    lines.append(f"  • {issue}")
        elif glm5.get("highlights"):
            lines.append("亮点：")
            for h in glm5.get("highlights", [])[:2]:
                if isinstance(h, dict):
                    lines.append(f"  • {h.get('point', '')}：{h.get('detail', '')}")
    else:
        lines.append("（未返回有效评分结果）")
    lines.append("")
    
    # 豆包评审意见
    second_score = second.get('total_score', 'N/A')
    lines.append(f"【豆包】评分：{second_score}分")
    if second_has_result and second_score != 'N/A':
        if second.get("brief_comment"):
            lines.append(f"评语：{second['brief_comment']}")
        elif second.get("issues"):
            lines.append("主要问题：")
            for issue in second.get("issues", [])[:3]:
                if isinstance(issue, dict):
                    lines.append(f"  • {issue.get('point', '')}：{issue.get('detail', '')}")
                else:
                    lines.append(f"  • {issue}")
        elif second.get("highlights"):
            lines.append("亮点：")
            for h in second.get("highlights", [])[:2]:
                if isinstance(h, dict):
                    lines.append(f"  • {h.get('point', '')}：{h.get('detail', '')}")
    else:
        lines.append("（未返回有效评分结果）")
    lines.append("")
    
    # 评分差异分析
    comparison = arb.get("comparison", {})
    if comparison:
        lines.append("【差异分析】")
        if comparison.get("key_differences"):
            for diff in comparison.get("key_differences", []):
                lines.append(f"  • {diff}")
        elif comparison.get("glm5_analysis") or comparison.get("second_model_analysis"):
            if comparison.get("glm5_analysis"):
                lines.append(f"  GLM-5观点：{comparison['glm5_analysis']}")
            if comparison.get("second_model_analysis"):
                lines.append(f"  豆包观点：{comparison['second_model_analysis']}")
    
    lines.append("")
    
    # Kimi仲裁意见
    if arb.get("arbitration_reason"):
        lines.append("【Kimi仲裁意见】")
        lines.append(arb["arbitration_reason"])
    
    lines.append("")
    lines.append("---")
    summary = results.get("summary", {})
    lines.append(f"⏱️ {summary.get('total_time_seconds', 0)}秒 | {summary.get('total_tokens', 0)} tokens")
    
    return "\n".join(lines)


def normal_grade(essay_text, requirements=None, essay_title=None, model="doubao-1.5-lite"):
    """普通模式：单模型评分"""
    print(f"📝 正在使用 {model} 进行评分...")
    
    result = grade_with_model(model, essay_text, requirements, essay_title)
    
    if "error" in result:
        return f"评分失败：{result['error']}"
    
    return format_single_report(result, requirements, essay_title)


def expert_grade(essay_text, requirements=None, essay_title=None, second_model="doubao-1.5-lite"):
    """专家模式：多模型评审 + Kimi仲裁"""
    
    start_time = time.time()
    results = {
        "timestamp": datetime.now().isoformat(),
        "essay_title": essay_title,
        "essay_length": len(essay_text),
        "requirements": requirements,
        "second_model": second_model,
        "model_results": {},
        "arbitration": None,
        "summary": {}
    }
    
    # 1. GLM-5 评分
    print("📝 GLM-5 评分中...")
    glm_result = grade_with_model("glm-5", essay_text, requirements, essay_title)
    results["model_results"]["glm-5"] = glm_result
    print(f"   完成，耗时 {glm_result.get('elapsed_seconds', 0)}s")
    
    # 2. 第二模型评分
    second_name = "豆包" if "doubao" in second_model else second_model.upper()
    print(f"📝 {second_name} 评分中...")
    second_result = grade_with_model(second_model, essay_text, requirements, essay_title)
    results["model_results"][second_model] = second_result
    print(f"   完成，耗时 {second_result.get('elapsed_seconds', 0)}s")
    
    # 3. Kimi 仲裁
    print("⚖️ Kimi-K2.5 仲裁中...")
    arbitration = arbitrate_with_kimi(
        glm_result.get("result", {}),
        second_result.get("result", {}),
        essay_text,
        requirements,
        second_name
    )
    results["arbitration"] = arbitration
    print(f"   完成，耗时 {arbitration.get('elapsed_seconds', 0)}s")
    
    # 4. 汇总
    total_time = time.time() - start_time
    total_tokens = sum(
        r.get("tokens", {}).get("total", 0)
        for r in [glm_result, second_result, arbitration]
        if "tokens" in r
    )
    
    results["summary"] = {
        "total_time_seconds": round(total_time, 2),
        "total_tokens": total_tokens,
        "glm5_score": glm_result.get("result", {}).get("total_score", "N/A"),
        "second_model_score": second_result.get("result", {}).get("total_score", "N/A"),
        "final_score": arbitration.get("result", {}).get("final_total", "N/A"),
        "final_grade": arbitration.get("result", {}).get("final_grade", "N/A")
    }
    
    return format_expert_report(results), results


if __name__ == "__main__":
    import sys
    
    # 测试用例
    test_essay = """
追

追，追向光明，追向胜利，追向成功，追的事物有很多很多，追的姿态也各种各样，而我追的应该是一份让我满意的答卷吧。

那天夜晚，台灯照亮了我苍白的脸，此时的我正直愣愣的盯着那试卷上一个又一个大的红叉，像是夺了魂，窗外下着雨，雨水落在窗台上，发出声响，桌面旁的时钟一分一秒的过去，不知过了多久，我才缓缓收起试卷，眼神也从原来的迷蒙，变成了坚定，我拿起语文书，暗自下定了决心，下一次考试一定要得一个自己满意的成绩。

不知过去了多久，窗外的雨停了，风也停了，整个世界静悄悄，安静无比，好像只有我的笔在纸上摩擦发出"沙沙"的声响，困意越来越浓，我双眼闭起，在桌子上，睡了过去。

第二天的考场上，眼睛在一道又一道题目上略过，每一题，每一个空，如同一个又一个的朋友，熟悉无比，手握笔在一个个空上写下答案，终于写下了最后一个答案，嘴角再也藏不住那开心的笑容。那一刻，我知道，我成功了。

这时，我才了然，我追的从来不是一个满意的成绩，而是一个努力，奋发图强的动力罢了。
"""
    
    test_requirements = """题目：以"追"为话题，写一篇记叙文，通过具体的事例讲述你追逐的往事。
要求：通过具体事例讲述追逐的往事
字数：400字以上"""
    
    if len(sys.argv) > 1 and sys.argv[1] == "--expert":
        # 专家模式
        report, results = expert_grade(
            essay_text=test_essay.strip(),
            requirements=test_requirements.strip(),
            essay_title="追"
        )
        print("\n" + report)
        
        # 保存JSON
        with open("/tmp/essay_expert_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("\n详细结果已保存至 /tmp/essay_expert_result.json")
    else:
        # 普通模式
        report = normal_grade(
            essay_text=test_essay.strip(),
            requirements=test_requirements.strip(),
            essay_title="追"
        )
        print("\n" + report)
