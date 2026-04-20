#!/usr/bin/env python3
"""
小学作文评分系统 v2.0
- 普通模式：KIMI-2.5 多模态识图直接评分
- 专家模式：KIMI识图评分 + 豆包评分 + DeepSeek-V3.2仲裁
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
    "deepseek": {
        "provider": "joybuilder",
        "model": "DeepSeek-V3.2",
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

# 评分标准（满分30分，无卷面分）
GRADING_CRITERIA = """
## 评分标准（满分30分）

| 维度 | 分值 | 评分要点 |
|------|------|----------|
| 内容质量 | 10分 | 切合题意、中心明确、内容充实、情感真实 |
| 语言表达 | 8分 | 语句通顺、用词准确、表达生动、无语病 |
| 结构层次 | 6分 | 条理清晰、段落分明、过渡自然、首尾呼应 |
| 书写规范 | 4分 | 字迹工整、标点正确、格式规范、错别字少 |
| 字数要求 | 2分 | 达到字数要求（400字以上） |

## 等级划分
- 27-30分: 一类文·优秀
- 23-26分: 二类文·良好
- 17-22分: 三类文·中等
- 11-16分: 四类文·及格
- 0-10分: 五类文·不及格
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
    """解析 JSON 响应，处理代码块包裹和各种格式问题"""
    # 去掉代码块标记
    content = re.sub(r'^```(?:json)?\s*', '', content.strip())
    content = re.sub(r'\s*```$', '', content)
    content = content.strip()
    
    # 尝试提取 JSON 对象
    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        json_str = json_match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # 尝试修复常见的 JSON 格式问题
            json_str_fixed = json_str.replace("'", '"')
            json_str_fixed = re.sub(r',\s*}', '}', json_str_fixed)
            json_str_fixed = re.sub(r',\s*]', ']', json_str_fixed)
            json_str_fixed = re.sub(r'(\w+)\s*:', r'"\1":', json_str_fixed)
            try:
                return json.loads(json_str_fixed)
            except Exception as e2:
                print(f"JSON 解析失败，原始响应前500字符:\n{content[:500]}")
                return {"error": f"JSON解析失败: {e}, {e2}", "raw_response": content}
    print(f"未找到 JSON 对象，原始响应前500字符:\n{content[:500]}")
    return {"error": "无法解析JSON", "raw_response": content}


def kimi_grade_image(image_path, requirements=None, essay_title=None):
    """使用 KIMI-2.5 多模态识图并评分"""
    client, model = get_client("kimi")
    
    image_base64 = encode_image(image_path)
    title_req = f'题目为"**{essay_title}**"，{requirements or "请根据题目要求进行评分"}'
    
    prompt = f"""你是一位资深的小学语文教研员，请对图片中的手写作文进行评分。

{GRADING_CRITERIA}

## 作文要求
{title_req}

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
        "字数要求": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}}
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
    """使用豆包 Vision 识图并评分"""
    client, model = get_client("doubao-vision")
    
    image_base64 = encode_image(image_path)
    title_req = f'题目为"**{essay_title}**"，{requirements or "请根据题目要求进行评分"}'
    
    prompt = f"""你是一位资深的小学语文教研员，请对图片中的手写作文进行评分。

{GRADING_CRITERIA}

## 作文要求
{title_req}

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
        "字数要求": {{"score": <0-2>, "deduction_reasons": ["<扣分原因>"]}}
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


def deepseek_arbitrate(kimi_result, doubao_result, essay_text, requirements=None, essay_title=None):
    """DeepSeek-V3.2 仲裁 KIMI 和豆包的评分"""
    client, model = get_client("deepseek")
    
    prompt = f"""你是一位教育专家，现在需要对两个AI模型的小学作文评分结果进行仲裁，给出最终评分。

{GRADING_CRITERIA}

## 作文要求
题目为"**{essay_title}**"，{requirements or '以"追"为话题，写一篇记叙文'}

## 作文内容
{essay_text[:1500]}

## 模型A（KIMI-2.5，多模态识图评分）的评分结果：
{json.dumps(kimi_result, ensure_ascii=False, indent=2)}

## 模型B（豆包 Vision）的评分结果：
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
    
    scores = r.get("scores", {})
    
    lines = []
    lines.append(f"## 评分结果\n")
    lines.append(f"**题目**: {r.get('essay_title', 'N/A')}")
    lines.append(f"**字数**: 约 {char_count} 字")
    lines.append(f"**总分**: {r.get('total_score', 'N/A')} 分 ({r.get('grade', 'N/A')})")
    lines.append("")
    lines.append("### 各项得分")
    
    max_scores = {"内容质量": 10, "语言表达": 8, "结构层次": 6, "书写规范": 4, "字数要求": 2}
    for dim, max_s in max_scores.items():
        score_info = scores.get(dim, {})
        score = score_info.get("score", "N/A")
        reasons = score_info.get("deduction_reasons", [])
        lines.append(f"- **{dim}**: {score}/{max_s}")
        for reason in reasons:
            lines.append(f"  - {reason}")
    
    lines.append("")
    lines.append("### 亮点")
    for h in r.get("highlights", []):
        lines.append(f"- **{h.get('point', 'N/A')}**: {h.get('detail', 'N/A')}")
    
    lines.append("")
    lines.append("### 不足之处")
    for issue in r.get("issues", []):
        lines.append(f"- **{issue.get('point', 'N/A')}** ({issue.get('deduction', 'N/A')}): {issue.get('detail', 'N/A')}")
    
    lines.append("")
    lines.append(f"### 总结评语\n{r.get('summary', 'N/A')}")
    
    return "\n".join(lines)


def format_expert_report(results):
    """格式化专家模式最终报告（简洁版，给普通用户看）"""
    kimi_result = results.get("kimi", {}).get("result", {})
    doubao_result = results.get("doubao", {}).get("result", {})
    arbitration = results.get("arbitration", {}).get("result", {})
    
    char_count = results.get("essay_length", 0)
    
    lines = []
    lines.append(f"## 📊 评分结果\n")
    lines.append(f"**题目**: {arbitration.get('conformity_check', {}).get('topic_analysis', kimi_result.get('essay_title', 'N/A'))}")
    lines.append(f"**字数**: 约 {char_count} 字")
    lines.append(f"**最终评分**: {arbitration.get('final_total', 'N/A')} 分 ({arbitration.get('final_grade', 'N/A')})")
    lines.append("")
    
    # 仲裁评分详情
    final_scores = arbitration.get("final_scores", {})
    lines.append("### 各项得分")
    max_scores = {"内容质量": 10, "语言表达": 8, "结构层次": 6, "书写规范": 4, "字数要求": 2}
    for dim, max_s in max_scores.items():
        score_info = final_scores.get(dim, {})
        score = score_info.get("score", "N/A")
        lines.append(f"- **{dim}**: {score}/{max_s}")
    
    lines.append("")
    lines.append("### ✨ 亮点")
    for h in arbitration.get("highlights", []):
        lines.append(f"- **{h.get('point', 'N/A')}**: {h.get('detail', 'N/A')}")
    
    lines.append("")
    lines.append("### ⚠️ 不足之处")
    for issue in arbitration.get("issues", []):
        lines.append(f"- **{issue.get('point', 'N/A')}** (扣分: {issue.get('deduction', '')}): {issue.get('detail', 'N/A')}")
    
    lines.append("")
    lines.append(f"### 📝 总结\n{arbitration.get('summary', 'N/A')}")
    
    return "\n".join(lines)


def normal_grade_image(image_path, requirements=None, essay_title=None):
    """普通模式：单模型 KIMI 识图评分"""
    result = kimi_grade_image(image_path, requirements, essay_title)
    
    if "error" in result:
        return f"评分失败：{result['error']}"
    
    return format_single_report(result, requirements)


def expert_grade_image(image_path, requirements=None, essay_title=None):
    """专家模式：KIMI识图评分 + 豆包Vision评分 → DeepSeek仲裁"""
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
    
    # 获取作文正文
    essay_text = kimi_result.get("result", {}).get("essay_text", "")
    if not essay_text:
        essay_text = doubao_result.get("result", {}).get("essay_text", "")
    results["essay_length"] = len(essay_text) if essay_text else 0
    
    # DeepSeek 仲裁
    print("⚖️ DeepSeek-V3.2 仲裁中...")
    arbitration = deepseek_arbitrate(
        kimi_result.get("result", {}),
        doubao_result.get("result", {}),
        essay_text,
        requirements,
        essay_title
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
    """发送飞书卡片消息"""
    import os
    from pathlib import Path
    
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


def send_feishu_message(token, receive_id, message):
    """发送飞书纯文本消息（自动判断是否需要卡片格式）"""
    has_table = ('|' in message and ('---' in message or '───' in message)) or \
                ('维度' in message and 'KIMI' in message and '豆包' in message)
    
    if has_table:
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "📊 评分结果"},
                "template": "blue"
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": message}}
            ]
        }
        msg_type = "interactive"
        content = json.dumps(card)
    else:
        msg_type = "text"
        content = json.dumps({"text": message})
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    data = json.dumps({
        "receive_id": receive_id,
        "msg_type": msg_type,
        "content": content
    }).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        if result.get('code') == 0:
            print("飞书消息发送成功" + ("（卡片格式）" if has_table else "（纯文本）"))
            return True
        else:
            print(f"飞书消息发送失败: {result}")
            return False
    except Exception as e:
        print(f"发送飞书消息出错: {e}")
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
    
    # 3、各项得分（仲裁结果）
    final_scores = arbitration.get("final_scores", {})
    max_scores = {"内容质量": 10, "语言表达": 8, "结构层次": 6, "书写规范": 4, "字数要求": 2}
    lines.append("**3、各项得分（仲裁）**")
    
    score_table = "| 维度 | 分值 | 得分 |\n|------|------|------|"
    detail_lines = []
    for dim, max_s in max_scores.items():
        score_info = final_scores.get(dim, {})
        score = score_info.get("score", "N/A")
        score_table += f"\n| {dim} |/{max_s} | {score} |"
        reasons = score_info.get("deduction_reasons", [])
        if reasons:
            detail_lines.append(f"**{dim}** 扣分原因：{'；'.join(reasons)}")
    
    lines.append(score_table)
    lines.append("")
    
    for dl in detail_lines:
        lines.append(dl)
    lines.append("")
    
    # 4、总分
    lines.append(f"**4、总分**\n最终评分：**{arbitration.get('final_total', 'N/A')}** 分（{arbitration.get('final_grade', 'N/A')}）")
    lines.append("")
    
    # 5、亮点
    highlights = arbitration.get("highlights", kimi_result.get("highlights", []))
    if highlights:
        lines.append("**5、✨ 亮点**")
        for h in highlights[:2]:
            lines.append(f"- **{h.get('point', '')}**：{h.get('detail', '')}")
        lines.append("")
    
    # 6、不足之处
    issues = arbitration.get("issues", kimi_result.get("issues", []))
    if issues:
        lines.append("**6、⚠️ 不足之处**")
        for issue in issues[:3]:
            lines.append(f"- **{issue.get('point', '')}**（扣分：{issue.get('deduction', '')}）")
        lines.append("")
    
    # 7、仲裁说明
    if arbitration.get("arbitration_reason"):
        lines.append(f"**7、⚖️ 仲裁说明**\n{arbitration.get('arbitration_reason', '')}")
        lines.append("")
    
    # 8、总结评语
    if arbitration.get("summary"):
        lines.append(f"**8、📝 总结评语**\n{arbitration.get('summary', '')}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python essay_grader_v2.py <作文图片路径> [题目标题]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    essay_title = sys.argv[2] if len(sys.argv) > 2 else "我身边的英雄"
    
    report, results = expert_grade_image(image_path, essay_title=essay_title)
    print("\n" + report)
