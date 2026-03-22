# 使用 zhihu(5.63k) 重新训练并按现有思路部署的调整方案

本文档说明：如果要改用本地仓库中的 `zhihu(5.63k)` 语料重新训练一个微调模型，并继续沿用当前这套

`LlamaFactory -> LoRA SFT -> merge -> vLLM -> SSH 隧道 -> 本地 AGENT -> 前端页面`

的部署方式，需要改哪些地方。

## 1. 先说结论

如果你要按“相同思路”重新训练并接入项目，核心只需要调整 4 层：

1. 数据集注册
2. 训练输出目录
3. merge 导出目录
4. 部署脚本和本地模型名

最重要的原则是：

- 不要覆盖当前在线模型目录
- 新模型单独用一套 `output_dir / export_dir / served-model-name`

这样即使新实验效果不好，也不会影响现在已经能跑通的版本。

## 2. 当前可直接使用的数据文件

我已经整理好一份可直接给 LlamaFactory 使用的 `json`：

- [zhihu_5631_merged_clean.json](/Users/bluem/Projects/Web/industrial_chain/data/xbase-candidates/COIG-CQIA/zhihu/zhihu_5631_merged_clean.json)

这个文件的特点是：

- 已经把 4 份 `jsonl` 合并成一个 `json` 列表
- 保留了 `instruction / input / output`
- 做了轻量清洗
- 去掉了部分控制字符
- 对 `instruction + input + output` 做了去重

当前结果：

- 原始合计：`5631`
- 清洗去重后：`5629`

## 3. 第一步：把新数据集接入远端 LlamaFactory

### 3.1 复制数据到远端

你需要把：

- `zhihu_5631_merged_clean.json`

复制到远端：

- `/root/workspace/LlamaFactory/data/`

建议远端文件名保持一致，例如：

- `/root/workspace/LlamaFactory/data/zhihu_5631_merged_clean.json`

### 3.2 修改 dataset_info.json

远端当前训练入口依赖：

- `LlamaFactory/data/dataset_info.json`

增加一个数据集注册项，例如：

```json
"zhihu_5631": {
  "file_name": "zhihu_5631_merged_clean.json"
}
```

这样后续训练 YAML 就可以直接写：

```yaml
dataset: zhihu_5631
```

## 4. 第二步：新建一份训练 YAML，不要覆盖旧版

不要直接改现有线上实验配置，建议复制一份新的训练 YAML。

当前参考模板是：

- `/root/workspace/LlamaFactory/examples/train_lora/qwen3-14B_lora_sft.yaml`

建议新建为类似：

- `/root/workspace/LlamaFactory/examples/train_lora/qwen3-14B_lora_sft_zhihu5631.yaml`

### 4.1 建议修改项

至少改这几项：

```yaml
### model
model_name_or_path: /root/autodl-tmp/Qwen3-14B
trust_remote_code: true

### method
stage: sft
do_train: true
finetuning_type: lora
lora_rank: 8
lora_alpha: 16
lora_target: q_proj,k_proj,v_proj,o_proj

### dataset
dataset: zhihu_5631
template: qwen3_nothink
cutoff_len: 1024
preprocessing_num_workers: 16
dataloader_num_workers: 4

### output
output_dir: /root/autodl-tmp/qwen3-14b/lora/sft_zhihu5631
logging_steps: 10
save_steps: 100
plot_loss: true
overwrite_output_dir: true
save_only_model: false
report_to: none

### train
per_device_train_batch_size: 1
gradient_accumulation_steps: 8
learning_rate: 2.0e-5
num_train_epochs: 2
lr_scheduler_type: cosine
warmup_steps: 100
bf16: true
ddp_timeout: 180000000
resume_from_checkpoint: null

### eval
val_size: 0.1
per_device_eval_batch_size: 1
eval_strategy: steps
eval_steps: 100
```

### 4.2 为什么建议先跑 2 epoch

你现在从远端那版 `1000` 条入口数据，改成 `5629` 条数据，样本规模扩大了很多。

因此第一版不建议一上来就把 epoch 拉太高，原因是：

- 更容易把回答风格拉偏
- 更容易把某些知乎表达方式学得过重
- 如果数据内部噪声还在，训练更久只会把噪声学得更牢

所以第一版更稳妥的建议是：

- 先 `2 epoch`
- 先看 loss
- 再看几组真实业务问题的回复质量

如果效果偏弱，再考虑上到 `3 epoch`

## 5. 第三步：先测试 LoRA 版，不要急着 merge

训练完成后，建议先保留一轮“基座模型 + LoRA adapter”的验证。

参考当前远端已有推理配置：

- `/root/workspace/LlamaFactory/examples/inference/qwen3-14B_lora_sft.yaml`

建议新建：

- `/root/workspace/LlamaFactory/examples/inference/qwen3-14B_lora_sft_zhihu5631.yaml`

内容大致如下：

```yaml
model_name_or_path: /root/autodl-tmp/Qwen3-14B
adapter_name_or_path: /root/autodl-tmp/qwen3-14b/lora/sft_zhihu5631
template: qwen3_nothink
finetuning_type: lora
infer_backend: huggingface
trust_remote_code: true
temperature: 0.7
top_p: 0.9
```

然后先测试：

```bash
llamafactory-cli chat examples/inference/qwen3-14B_lora_sft_zhihu5631.yaml
```

这样做的好处是：

- 先验证 LoRA 本身是否正常
- 不用一上来就合并完整模型
- 如果效果不行，可以先回调训练参数

## 6. 第四步：新建 merge YAML，把 LoRA 合成完整模型

参考当前 merge 配置：

- `/root/workspace/LlamaFactory/examples/merge_lora/qwen3-14B_lora_sft.yaml`

建议新建：

- `/root/workspace/LlamaFactory/examples/merge_lora/qwen3-14B_lora_sft_zhihu5631.yaml`

内容建议如下：

```yaml
### model
model_name_or_path: /root/autodl-tmp/Qwen3-14B
adapter_name_or_path: /root/autodl-tmp/qwen3-14b/lora/sft_zhihu5631
template: qwen3_nothink
finetuning_type: lora
trust_remote_code: true

### export
export_dir: /root/autodl-tmp/Qwen3-14B_zhihu5631_sft_merged
export_size: 2
export_device: cpu
export_legacy_format: false
```

然后执行：

```bash
llamafactory-cli export examples/merge_lora/qwen3-14B_lora_sft_zhihu5631.yaml
```

## 7. 第五步：部署时改用新 merged 模型

当前远端部署脚本是：

- `/root/workspace/20260319_api/start_vllm.sh`

如果你要切到新模型，至少要改两项：

```bash
MODEL_PATH="/root/autodl-tmp/Qwen3-14B_zhihu5631_sft_merged"
TOKENIZER_PATH="/root/autodl-tmp/Qwen3-14B"
```

以及：

```bash
--served-model-name Qwen3-14B_zhihu5631_sft_merged
```

### 7.1 tokenizer 是否需要一起改

不建议。

当前更稳妥的做法还是沿用原始 tokenizer：

- `/root/autodl-tmp/Qwen3-14B`

因为现在线上方案已经明确踩过 tokenizer 坑，当前稳定组合就是：

- merged model
- 原始 tokenizer

## 8. 第六步：本地 AGENT 是否需要改

分两种情况。

### 8.1 如果你改了 served-model-name

那么本地 `AGENT` 要同步改模型名。

相关位置在：

- [config.py](/Users/bluem/Projects/Web/industrial_chain/AGENT/rag/config.py)

对应环境变量或默认值需要改成：

```bash
PRIMARY_LLM_MODEL=Qwen3-14B_zhihu5631_sft_merged
```

### 8.2 如果你远端仍然沿用旧名字

那本地可以不用改。

但我不建议这么做，因为会造成两个问题：

- 新旧模型难区分
- 之后排查日志时很容易混淆到底跑的是哪一版

所以更推荐：

- 新模型用新名字
- 本地 `PRIMARY_LLM_MODEL` 跟着改

## 9. 第七步：整体执行顺序建议

最稳的顺序如下：

1. 把 `zhihu_5631_merged_clean.json` 上传到远端 `LlamaFactory/data/`
2. 修改远端 `dataset_info.json`
3. 新建一份训练 YAML，不覆盖旧文件
4. 执行 `llamafactory-cli train ...`
5. 训练完成后，先用 inference YAML 测 LoRA 版
6. 确认效果可接受，再执行 `llamafactory-cli export ...`
7. 修改 `20260319_api/start_vllm.sh`
8. 重启远端 `vLLM`
9. 本地同步修改 `PRIMARY_LLM_MODEL`
10. 用 `/health` 验证是否真的切到新模型

## 10. 我建议你额外做的两件事

### 10.1 不要复用旧目录

不要直接复用：

- `/root/autodl-tmp/qwen3-14b/lora/sft`
- `/root/autodl-tmp/Qwen3-14B_sft_merged`

否则你会失去新旧实验对照能力。

最起码要单独使用：

- `/root/autodl-tmp/qwen3-14b/lora/sft_zhihu5631`
- `/root/autodl-tmp/Qwen3-14B_zhihu5631_sft_merged`

### 10.2 保存“真正执行过的配置”

之前远端已经出现过一个问题：

- 当前训练 YAML 写的是 `num_train_epochs: 1`
- 但产物日志显示真实训练跑到了 `3 epoch`

所以这次建议你一定要保留：

- 实际执行过的 train YAML
- 实际执行过的 merge YAML
- shell 命令历史

最好单独放到一个带日期的目录，例如：

- `examples/train_lora/archive/20260320_qwen3-14B_lora_sft_zhihu5631.yaml`

## 11. 最终可复用的工程表述

如果要把这次改造总结成一句工程描述，最稳妥的写法是：

“将本地整理后的 `zhihu(5.63k)` 指令数据注册到远端 LlamaFactory 数据集配置中，基于 Qwen3-14B 重新执行 LoRA 监督微调，并将训练后的适配器权重合并导出为独立的 merged 模型目录，随后沿用现有 `vLLM + SSH 隧道 + 本地 AGENT` 的部署链路完成系统接入。”
