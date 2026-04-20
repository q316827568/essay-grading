# 模型配置与资源消耗

## 可用模型

### 多模态视觉模型（识图评分）
| 模型 | Provider | 说明 |
|------|----------|------|
| `Kimi-K2.5` | joybuilder | 中文识别准确，评分专业 |
| `doubao-1-5-vision-pro-32k-250115` | doubao | 豆包视觉模型，支持识图 |

### 文本模型
| 模型 | Provider | 说明 |
|------|----------|------|
| `GLM-5` | joybuilder | 智谱旗舰，适合仲裁 |
| `doubao-1-5-lite-32k-250115` | doubao | ⚡ 最快，适合批量评分 |
| `doubao-seed-2-0-lite-260215` | doubao | 输出详细，修改建议具体 |

## 专家模式并行策略（v3.0）

```
旧版（串行）：
KIMI识图 → 豆包文本评分 → GLM-5仲裁
耗时：约 50-70 秒

新版（并行）：
KIMI识图 ∥ 豆包Vision识图 → GLM-5仲裁
耗时：约 35-45 秒（提升 ~30%）
```

**并行实现**：
```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    kimi_future = executor.submit(kimi_grade_image, image_path)
    doubao_future = executor.submit(doubao_vision_grade_image, image_path)
    
    kimi_result = kimi_future.result()
    doubao_result = doubao_future.result()
```

### 豆包模型对比（实测数据）

| 对比项 | 1.5 Lite | Seed 2.0 Lite |
|--------|----------|---------------|
| 耗时 | ⚡ 11-18秒 | 54-90秒 |
| Token | ~1300 | ~3800 |
| 评分风格 | 严格 | 宽容（+5分左右） |
| 输出详细度 | 简洁 | 详细 |
| 修改示例 | 概括性 | 逐句修改 |

**推荐**：
- 批量评分用 **1.5 Lite**
- 精细点评用 **Seed 2.0 Lite**

## 专家模式资源消耗

| 模型 | 耗时 | Token | 说明 |
|------|------|-------|------|
| 豆包 1.5 Lite | ~11s | ~1200 | ⚡ 最快 |
| GLM-5 | ~80s | ~2900 | 智谱旗舰 |
| Kimi-K2.5（仲裁） | ~25s | ~2600 | 深度推理 |

**专家模式推荐配置**：
- GLM-5 + 豆包 1.5 Lite + Kimi 仲裁
- 总耗时约 40-50 秒

## 豆包可用模型列表（90+）

**Lite 系列（快速）**：
- `doubao-1-5-lite-32k-250115` ⭐推荐
- `doubao-lite-32k-240828`

**Pro 系列（高性能）**：
- `doubao-1-5-pro-256k-250115`
- `doubao-1-5-pro-32k-250115`

**Seed 系列（新一代）**：
- `doubao-seed-2-0-lite-260215`

**视觉模型**：
- `doubao-1-5-vision-pro-32k-250115`
- `doubao-vision-pro-32k-241028`

**推理模型**：
- `doubao-1-5-thinking-pro-250415`

## API 调用方式

```python
# 豆包可以直接使用模型名调用
from openai import OpenAI

client = OpenAI(
    api_key="ark-xxx",
    base_url="https://ark.cn-beijing.volces.com/api/v3"
)
response = client.chat.completions.create(
    model="doubao-1-5-lite-32k-250115",  # 直接用模型名
    messages=[{"role": "user", "content": "..."}]
)
```

## 注意事项

1. **GLM-5 JSON 解析**：GLM-5 可能返回被 \`\`\`json...\`\`\` 代码块包裹的 JSON，需要先去除标记：
   ```python
   content = re.sub(r'^```(?:json)?\s*', '', content.strip())
   content = re.sub(r'\s*```$', '', content)
   ```

2. **错误处理**：当模型返回错误时，在专家模式报告中应显示 "N/A" 而非 0 分
