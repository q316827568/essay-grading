# OCR 识别指南

## OCR 工具选择

| 工具 | 特点 | 推荐场景 |
|------|------|----------|
| **RapidOCR** | 中文印刷体效果好，手写体一般 | 印刷体、工整手写 |
| **Tesseract** | 需要安装语言包 | 备选方案 |
| **视觉大模型** | 效果最好但需要 API | 潦草手写、复杂排版 |

## RapidOCR 使用

```python
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
result, elapse = ocr(image_path)

if result:
    text = '\n'.join([line[1] for line in result])
```

## Tesseract 使用

```bash
# 安装语言包
sudo apt-get install tesseract-ocr-chi-sim

# 识别
tesseract image.jpg stdout -l chi_sim+eng
```

## 常见问题

### OCR 识别不出来怎么办？

1. 使用多个 OCR 工具交叉验证
2. 对图片进行预处理（二值化、去噪）
3. 手动提示用户提供文字版

### 字迹太潦草无法识别？

在评分中注明：
- 书写与卷面扣分
- 建议加强书写练习

### 作文内容不完整？

根据识别到的部分内容进行评分，并在点评中说明情况。

## 推荐顺序

RapidOCR > Tesseract > 视觉大模型
