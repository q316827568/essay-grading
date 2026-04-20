# 工作流程详解

## 第零步：识别作文要求（如有）

如果用户提供了作文要求图片，先识别要求内容：

```python
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
result, elapse = ocr(requirement_image_path)

if result:
    requirements = '\n'.join([line[1] for line in result])
```

**作文要求通常包含：**
- 作文题目/主题
- 字数要求
- 内容要求（如：写人、记事、状物、写景等）
- 结构要求（如：分段、首尾呼应等）
- 特殊要求（如：使用比喻、心理描写等）

**根据要求评分时需要：**
1. 检查是否符合题目要求
2. 检查是否达到字数要求
3. 检查是否包含指定的写作手法
4. 按要求权重调整评分标准

## 第一步：识别作文内容

使用 OCR 工具从图片中提取文字内容：

```python
# 使用 RapidOCR 进行中文手写体识别
# 需要先安装: pip install rapidocr_onnxruntime

from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
result, elapse = ocr(image_path)  # 注意：使用 __call__ 方法，不是 .ocr()

# 提取文字
if result:
    text_content = '\n'.join([line[1] for line in result])
else:
    text_content = ""  # OCR识别失败
```

**注意事项**：
- 手写体识别可能存在误差，需要人工校正
- 常见误识别：音近字、形近字、潦草字
- 需要根据上下文推断正确内容

## 第二步：整理作文内容

将 OCR 识别结果整理为：
1. **标题**
2. **正文段落**
3. **标注OCR误识别并修正**

## 第三步：评分分析

参考 `references/scoring-criteria.md` 中的评分标准进行评分。

## 第四步：详细点评

### 亮点分析（✨）

1. **立意**：分析主题是否深刻、积极
2. **比喻/修辞**：找出精彩的比喻、拟人等修辞手法
3. **心理描写**：分析心理变化的层次感
4. **环境描写**：分析环境烘托的作用
5. **结构**：分析首尾呼应、过渡自然

### 不足之处（⚠️）

1. 指出具体的语句问题
2. 分析结构上的缺陷
3. 指出内容上的不足
4. 分析书写问题

## 第五步：修改建议

**格式**：

**原文**：
> 引用原文

**建议修改**：
> 修改后的内容

**修改理由**：
- 说明为什么这样改
- 改后的效果

## 第六步：总结

- 总分及等级
- 主要优点
- 主要改进方向
- 鼓励语
