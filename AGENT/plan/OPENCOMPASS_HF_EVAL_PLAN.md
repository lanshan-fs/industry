# 使用 OpenCompass 评测 merged 模型（HuggingFaceCausalLM 版）的操作说明

本文档记录：如果要对当前微调后的 merged 模型使用 OpenCompass 做横向评测，并且采用

- `HuggingFaceCausalLM`

这一条评测路径，应该怎么做。

目标模型默认指向当前已部署模型目录：

- `/root/autodl-tmp/Qwen3-14B_sft_merged`

本文档只写“怎么评”，不展开讲 OpenCompass 的榜单体系和数据集设计。

## 1. 先说结论

你可以直接把 merged 模型目录当成一个本地 HuggingFace 模型，交给 OpenCompass 的

- `HuggingFaceCausalLM`

进行评测。

对你这个项目来说，这比先走 API 版更合适，因为：

- 结果更容易复现
- 不依赖 SSH 隧道和在线服务稳定性
- 参数控制更统一
- 更适合和基座模型、别的微调版本做公平对比

## 2. 推荐在什么环境里跑

推荐直接在 AutoDL 上评测，而不是本地机器。

原因很简单：

- 你的模型规模是 `Qwen3-14B`
- OpenCompass 评测时不仅要加载模型，还要持续跑生成任务
- 本地 Mac 基本不适合做这类正式评测

因此更稳的方案是：

- 在 AutoDL 上安装或使用 OpenCompass 环境
- 直接读取远端模型目录

## 3. 当前可直接评测的模型目录

当前 merged 模型目录是：

- `/root/autodl-tmp/Qwen3-14B_sft_merged`

对应 tokenizer 更建议优先使用：

- `/root/autodl-tmp/Qwen3-14B`

原因是当前线上部署已经验证过：

- `merged model + 原始 tokenizer`

这套组合更稳。

## 4. 两种做法：先 smoke test，再正式配置

最推荐的顺序是：

1. 先用命令行做一个最小 smoke test
2. 再写正式的 OpenCompass 配置文件

不要一上来就跑大规模全量数据集。

## 5. 第一步：先做一个最小 smoke test

OpenCompass 官方支持命令行直接评自定义 HuggingFace 模型。

建议你先在 AutoDL 上用一两个小数据集确认：

- 模型能加载
- tokenizer 没问题
- prompt 模式没问题
- 显存能扛住

可以先尝试类似命令：

```bash
python run.py \
  --datasets siqa_gen winograd_ppl \
  --hf-type chat \
  --hf-path /root/autodl-tmp/Qwen3-14B_sft_merged \
  --tokenizer-path /root/autodl-tmp/Qwen3-14B \
  --tokenizer-kwargs padding_side='left' truncation_side='left' trust_remote_code=True \
  --model-kwargs device_map='auto' trust_remote_code=True \
  --max-seq-len 2048 \
  --max-out-len 256 \
  --batch-size 1 \
  --hf-num-gpus 2 \
  -w outputs/qwen3_14b_sft_smoke \
  --debug
```

### 5.1 这里各项参数的含义

- `--hf-type chat`
  适合当前这种指令微调模型

- `--hf-path`
  指向 merged 模型目录

- `--tokenizer-path`
  建议优先指向原始 `Qwen3-14B`

- `--model-kwargs device_map='auto'`
  先交给 HuggingFace 自动分配设备

- `--hf-num-gpus 2`
  表示这个模型至少需要 2 张卡资源

- `--debug`
  首次一定建议打开，便于定位报错

## 6. 第二步：正式评测更推荐配置文件方式

如果你后面要做横评，就不建议一直手写命令行。

更好的方式是：

- 写一份 OpenCompass 配置文件
- 在配置里同时放多个模型
- 后面每次只换数据集或模型配置

## 7. OpenCompass 配置文件的基本写法

官方文档给出的 `HuggingFaceCausalLM` 形式，大致是下面这种结构：

```python
from mmengine.config import read_base

with read_base():
    from opencompass.configs.datasets.ceval.ceval_gen import ceval_datasets
    from opencompass.configs.datasets.cmmlu.cmmlu_gen import cmmlu_datasets

from opencompass.models import HuggingFaceCausalLM

datasets = [*ceval_datasets, *cmmlu_datasets]

models = [
    dict(
        type=HuggingFaceCausalLM,
        abbr='qwen3-14b-sft-merged',
        path='/root/autodl-tmp/Qwen3-14B_sft_merged',
        tokenizer_path='/root/autodl-tmp/Qwen3-14B',
        tokenizer_kwargs=dict(
            padding_side='left',
            truncation_side='left',
            trust_remote_code=True,
        ),
        model_kwargs=dict(
            device_map='auto',
            trust_remote_code=True,
        ),
        max_seq_len=2048,
        max_out_len=256,
        batch_size=1,
        batch_padding=False,
        run_cfg=dict(num_gpus=2),
    )
]
```

然后运行：

```bash
python run.py /path/to/your_config.py -w outputs/qwen3_14b_sft --debug
```

第一次成功后，再去掉 `--debug`。

## 8. 为什么要优先用配置文件

因为你真正需要的不是“评一次”，而是“可比较地评多次”。

比如后面至少会出现这些候选模型：

- 原始 `Qwen3-14B`
- 当前在线微调版 `Qwen3-14B_sft_merged`
- 未来用 `zhihu(5.63k)` 重训后的新 merged 版本

如果用配置文件，你就能很自然地把它们写成并列模型做横评。

## 9. 你这个项目最建议的横评对象

如果你的目标是回答“微调是否有效”，那至少应该放这 3 个：

1. 原始 `Qwen3-14B`
2. 当前在线微调版 `Qwen3-14B_sft_merged`
3. 后续用 `zhihu(5.63k)` 重训的新版本

这样你才能比较清楚地看出：

- 微调前后整体能力是否变化
- 当前 1k 训练入口版本和 5.6k 训练版本谁更稳
- 指令风格是否更贴近你的业务需求

## 10. 第一轮不要跑太大，先做小规模验证

不建议第一轮就跑大而全的 benchmark 集。

更稳妥的顺序是：

1. 先挑 1 到 2 个小数据集做 smoke test
2. 确认模型能正常加载
3. 确认生成格式正常
4. 再上正式横评

你当前最适合的第一轮，是先跑一些比较常见的小型中文或通用任务，例如：

- `ceval_gen`
- `cmmlu_gen`
- 其它你最关心的生成类数据集

## 11. 你大概率会遇到的几个坑

### 11.1 `trust_remote_code`

Qwen 系列一般建议打开：

- `trust_remote_code=True`

否则很容易在加载时出兼容问题。

### 11.2 tokenizer 目录选择

如果直接用 merged 目录里的 tokenizer 报错，优先改回：

- `/root/autodl-tmp/Qwen3-14B`

这也是你当前线上部署已经验证过的更稳方案。

### 11.3 首次一定要用 `--debug`

否则第一次报错时你会看不清是：

- 模型加载问题
- tokenizer 问题
- 数据集配置问题
- 资源不够

### 11.4 不要一开始就追求“大横评”

你现在最重要的不是一次性跑很多榜，而是先验证：

- 这版 merged 模型能不能被 OpenCompass 稳定加载
- 评测流程是否完整
- 输出是否正常

## 12. 为什么这里推荐 HF 版而不是 API 版

对于你当前这个项目，HF 版更适合做“研究型横评”。

原因是：

- 避开远端 `vLLM` 服务波动
- 不依赖本地 SSH 隧道
- 模型配置更透明
- 结果复现实验更方便
- 更适合论文里写“基于同一评测框架对多个模型版本进行比较”

API 版也能做，但更适合：

- 验证线上服务表现
- 或者评一个只能通过接口访问的模型

## 13. 推荐的实际执行顺序

最稳妥的操作顺序如下：

1. 在 AutoDL 上准备 OpenCompass 环境
2. 用当前 merged 模型目录先做 smoke test
3. 确认 tokenizer 选择是否正常
4. 再写正式配置文件
5. 把原始模型和微调模型一起放进配置里
6. 按相同数据集做横评
7. 保存输出目录，后续和新模型继续对比

## 14. 当前最适合你的做法

如果只考虑“先迈出第一步”，当前最合理的是：

- 先用当前在线微调版 `Qwen3-14B_sft_merged`
- 在 AutoDL 上做一个小规模 OpenCompass smoke test
- 确认这条评测链路打通
- 然后再决定是否把 base model 和 `zhihu(5.63k)` 重训版一起纳入正式横评

## 15. 对应的官方参考

OpenCompass 官方文档中关于配置文件和 HuggingFace 模型评测的参考：

- 学习配置文件：
  https://doc.opencompass.org.cn/zh_CN/user_guides/config.html

- 准备模型：
  https://doc.opencompass.org.cn/zh_CN/latest/user_guides/models.html

- 快速开始：
  https://doc.opencompass.org.cn/get_started/quick_start.html

如果后续你要把这件事真正落地，下一步最有价值的是：

- 直接写一份针对你当前 AutoDL 路径的 OpenCompass 配置文件

这样你就可以真正开始跑第一个可复现的横评实验。
