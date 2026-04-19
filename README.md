# Essay Grading Skill

<div align="center">

📝 **小学作文评分** - AI 辅助作文批改与点评

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

## 简介

小学作文评分分析技能，从图片中识别手写作文内容，进行专业的评分分析，并提供详细的点评和修改建议。

## ✨ 新功能：按作文要求评分

支持两种评分模式：
- 📋 **标准评分**：无作文要求时，使用通用评分标准
- 🎯 **按要求评分**：有作文要求图片时，根据要求针对性评分

## 功能特点

- 📷 **OCR 识别**：支持手写作文图片识别
- 📋 **作文要求识别**：支持识别作文题目要求图片
- 🎯 **符合题意检查**：检查是否切题、字数是否达标
- 📊 **专业评分**：30 分制标准化评分
- ✨ **亮点分析**：发现作文中的精彩之处
- ⚠️ **问题诊断**：指出需要改进的地方
- 💡 **修改建议**：提供具体的修改方案

## 快速开始

### 示例一：标准评分

```python
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
result, _ = ocr("essay.jpg")
essay_text = '\n'.join([line[1] for line in result])

# 使用标准评分
score = standard_score(essay_text)
```

### 示例二：按要求评分

```python
# 同时提供作文和要求图片
essay_result, _ = ocr("essay.jpg")
req_result, _ = ocr("requirement.jpg")

essay_text = '\n'.join([line[1] for line in essay_result])
requirements = '\n'.join([line[1] for line in req_result])

# 根据要求评分
score = score_with_requirements(essay_text, requirements)
```

## 评分标准

### 标准评分（无要求）

| 项目 | 满分 |
|------|------|
| 内容与立意 | 10分 |
| 结构与条理 | 8分 |
| 语言表达 | 8分 |
| 书写与卷面 | 4分 |

### 按要求评分（有要求）

| 项目 | 满分 |
|------|------|
| 符合题意 | 10分 |
| 内容与立意 | 8分 |
| 结构与条理 | 6分 |
| 语言表达 | 4分 |
| 书写与卷面 | 2分 |

## 等级划分

| 分数 | 等级 |
|------|------|
| 27-30 分 | 优秀（A） |
| 24-26 分 | 良好（B） |
| 18-23 分 | 中等（C） |
| 12-17 分 | 及格（D） |
| 0-11 分 | 不及格（F） |

## 使用场景

- 👨‍👩‍👧‍👦 家长辅导：快速了解孩子作文水平
- 👩‍🏫 教师批改：辅助批量作文评分
- 📚 课外辅导：作文培训班教学辅助
- 🎓 自我提升：学生自主练习

## 依赖安装

```bash
pip install rapidocr_onnxruntime
```

## 详细文档

见 [SKILL.md](./SKILL.md)

## 许可证

MIT License

---

**Hermes Agent Skill** - 让 AI 成为学习好帮手
