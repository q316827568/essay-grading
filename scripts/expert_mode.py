#!/usr/bin/env python3
"""
作文评分专家模式 - 多模型评审系统
使用 GLM-5、豆包、Kimi-K2.5 三个模型进行评审，最终由 Kimi 仲裁
"""

import json
import time
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
    "doubao": {
        "provider": "doubao",
        "model": "doubao-seed-2-0-lite-260215",  # 豆包Seed 2.0 lite
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": "ark-2f247cd4-5d9c-42c0-8d7d-86ee87a398dd-06d89"
    },
    "deepseek": {
        "provider": "joybuilder",
        "model": "DeepSeek-V3.2",  # DeepSeek作为备选评审模型
        "base_url": "https://modelservice.jdcloud.com/coding/openai/v1",
        "api_key": "pk-ad5e8fc9-6548-485a-b886-31e872a1dded"
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
- 27-30分: 优秀（A）
- 24-26分: 良好（B）
- 18-23分: 中等（C）
- 12-17分: 及格（D）
- 0-11分: 不及格（F）
"""


def get_client(model_name):
    """获取对应模型的 OpenAI 客户端"""
    config = MODELS[model_name]
    return OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"]
    ), config["model"]


def grade_with_model(model_name, essay_text, requirements=None, essay_title=None):
    """使用指定模型进行作文评分"""
    client, model = get_client(model_name)
    
    # 构建评分提示
    prompt = f"""你是一位资深的小学语文教师，请对以下作文进行专业评分。

{GRADING_CRITERIA}

"""
    
    if requirements:
        prompt += f"""## 作文要求
{requirements}

请特别注意：
1. 是否符合题目要求
2. 是否达到字数要求
3. 是否使用了指定的写作手法

"""
    
    prompt += f"""## 作文内容
标题：{essay_title or '(未提供标题)'}

正文：
{essay_text}

---

请按以下JSON格式返回评分结果（只返回JSON，不要其他内容）：
{{
    "scores": {{
        "内容质量": <0-10分>,
        "语言表达": <0-8分>,
        "结构层次": <0-6分>,
        "书写规范": <0-4分>,
        "字数要求": <0-2分>
    }},
    "total_score": <总分>,
    "grade": "<等级>",
    "highlights": ["<亮点1>", "<亮点2>", ...],
    "issues": ["<问题1>", "<问题2>", ...],
    "suggestions": ["<建议1>", "<建议2>", ...],
    "brief_comment": "<简短评语，50字以内>"
}}
"""
    
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        
        elapsed = time.time() - start_time
        
        # 解析响应
        content = response.choices[0].message.content
        
        # 尝试提取 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"error": "无法解析JSON", "raw_response": content}
        
        return {
            "model": model_name,
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
            "model": model_name,
            "error": str(e),
            "elapsed_seconds": time.time() - start_time
        }


def arbitrate_with_kimi(glm_result, second_result, essay_text, requirements=None, second_model_name="DeepSeek"):
    """使用 Kimi-K2.5 对两个模型的评分结果进行仲裁"""
    client, model = get_client("kimi")
    
    req_section = f"## 作文要求\n{requirements}\n" if requirements else ""
    
    prompt = f"""你是一位教育专家，现在需要对两个AI模型的小学作文评分结果进行仲裁，给出最终评分。

{GRADING_CRITERIA}

## 作文内容
{essay_text}

{req_section}

## 模型A（GLM-5）的评分结果：
{json.dumps(glm_result, ensure_ascii=False, indent=2)}

## 模型B（{second_model_name}）的评分结果：
{json.dumps(second_result, ensure_ascii=False, indent=2)}

---

请分析两个模型的评分差异，给出你的仲裁意见：

1. 比较两个模型的评分，指出哪些评分更合理
2. 分析两个模型的优缺点
3. 给出你的最终评分

请按以下JSON格式返回（只返回JSON）：
{{
    "comparison": {{
        "glm5_analysis": "<GLM-5评分分析>",
        "deepseek_analysis": "<DeepSeek评分分析>",
        "key_differences": ["<差异1>", "<差异2>", ...]
    }},
    "final_scores": {{
        "内容质量": <0-10分>,
        "语言表达": <0-8分>,
        "结构层次": <0-6分>,
        "书写规范": <0-4分>,
        "字数要求": <0-2分>
    }},
    "final_total": <总分>,
    "final_grade": "<等级>",
    "arbitration_reason": "<仲裁理由>",
    "improvement_suggestions": ["<对GLM-5的评价改进建议>", "<对DeepSeek的评价改进建议>"],
    "final_comment": "<最终评语>"
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
        
        import re
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


def expert_grade_essay(essay_text, requirements=None, essay_title=None, second_model="doubao"):
    """专家模式作文评分主函数
    
    Args:
        essay_text: 作文文本
        requirements: 作文要求（可选）
        essay_title: 作文标题（可选）
        second_model: 第二评审模型，可选 "doubao" 或 "deepseek"，默认 "doubao"
    """
    
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
    second_model_name = "豆包" if second_model == "doubao" else "DeepSeek"
    print(f"📝 {second_model_name} 评分中...")
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
        second_model_name
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
    
    return results


def format_report(results):
    """格式化输出报告"""
    report = []
    report.append("=" * 60)
    report.append("📊 作文评分专家模式报告")
    report.append("=" * 60)
    report.append(f"\n📅 时间: {results['timestamp']}")
    report.append(f"📝 标题: {results.get('essay_title', '未提供')}")
    report.append(f"📏 字数: {results['essay_length']} 字")
    
    if results.get('requirements'):
        req_text = results['requirements']
        report.append(f"\n📋 作文要求:\n{req_text}")
    
    # 模型评分对比
    report.append("\n" + "-" * 60)
    report.append("📈 评分对比")
    report.append("-" * 60)
    
    glm5 = results["model_results"].get("glm-5", {}).get("result", {})
    second_model = results.get("second_model", "deepseek")
    second = results["model_results"].get(second_model, {}).get("result", {})
    second_name = "豆包" if second_model == "doubao" else "DeepSeek"
    
    report.append(f"\n| 维度 | GLM-5 | {second_name} |")
    report.append(f"|------|-------|{'-' * len(second_name)}|")
    
    for dim in ["内容质量", "语言表达", "结构层次", "书写规范", "字数要求"]:
        glm5_score = glm5.get("scores", {}).get(dim, "N/A")
        second_score = second.get("scores", {}).get(dim, "N/A")
        report.append(f"| {dim} | {glm5_score} | {second_score} |")
    
    report.append(f"| **总分** | **{glm5.get('total_score', 'N/A')}** | **{second.get('total_score', 'N/A')}** |")
    report.append(f"| **等级** | **{glm5.get('grade', 'N/A')}** | **{second.get('grade', 'N/A')}** |")
    
    # 仲裁结果
    arbitration = results.get("arbitration", {}).get("result", {})
    
    report.append("\n" + "-" * 60)
    report.append("⚖️ Kimi-K2.5 仲裁结果")
    report.append("-" * 60)
    
    if "final_scores" in arbitration:
        report.append("\n**最终评分：**")
        for dim, score in arbitration["final_scores"].items():
            report.append(f"- {dim}: {score}分")
        report.append(f"\n**总分: {arbitration.get('final_total', 'N/A')}分 / 30分**")
        report.append(f"**等级: {arbitration.get('final_grade', 'N/A')}**")
    
    if arbitration.get("arbitration_reason"):
        report.append(f"\n**仲裁理由：**\n{arbitration['arbitration_reason']}")
    
    if arbitration.get("final_comment"):
        report.append(f"\n**最终评语：**\n{arbitration['final_comment']}")
    
    # 资源消耗
    report.append("\n" + "-" * 60)
    report.append("💰 资源消耗统计")
    report.append("-" * 60)
    
    summary = results["summary"]
    report.append(f"\n- **总耗时**: {summary['total_time_seconds']} 秒")
    report.append(f"- **总Token**: {summary['total_tokens']} tokens")
    
    # 各模型详情
    second_model = results.get("second_model", "deepseek")
    for model in ["glm-5", second_model]:
        model_data = results["model_results"].get(model, {})
        if "tokens" in model_data:
            model_label = "GLM-5" if model == "glm-5" else ("豆包" if model == "doubao" else model.upper())
            report.append(f"- **{model_label}**: {model_data['tokens']['total']} tokens, {model_data['elapsed_seconds']}s")
    
    arb_data = results.get("arbitration", {})
    if "tokens" in arb_data:
        report.append(f"- **Kimi仲裁**: {arb_data['tokens']['total']} tokens, {arb_data['elapsed_seconds']}s")
    
    return "\n".join(report)


if __name__ == "__main__":
    # 测试用例
    test_essay = """
我的妈妈

我的妈妈是一个普通的家庭主妇，但她在我心中是最伟大的人。

每天早上，妈妈总是第一个起床，为我们准备早餐。她的手很粗糙，因为常年做家务，但在我眼里，这双手是最温暖的。

记得有一次，我生病发烧，妈妈整夜没有睡觉，一直守在我床边，给我量体温、喂药、擦汗。第二天早上，我看到妈妈的眼睛红红的，布满血丝，但她还是笑着问我："好点了吗？"

妈妈不仅照顾我的生活，还教导我做人的道理。她常说："做人要诚实，要善良。"这些话，我一直记在心里。

我爱我的妈妈，她是我心中最美的英雄。
"""
    
    test_requirements = """
题目：我身边的英雄
要求：写一个身边的人，通过具体事例表现他/她的品质
字数：400字以上
写作手法：动作描写、语言描写
"""
    
    print("开始专家模式评分测试...\n")
    results = expert_grade_essay(
        essay_text=test_essay.strip(),
        requirements=test_requirements.strip(),
        essay_title="我的妈妈"
    )
    
    print("\n" + format_report(results))
    
    # 保存JSON结果
    with open("/tmp/essay_expert_result.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细结果已保存至 /tmp/essay_expert_result.json")
