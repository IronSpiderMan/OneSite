# 重构方案：webui.py 模块化拆分

## 问题分析

当前 `webui.py` 共5472行，其中：
- **ASSETS字典（前端资源）**: 4314行（78.8%）- Base64+gzip编码的JS/CSS
- **业务逻辑代码**: ~1143行（21.2%）

虽然业务逻辑不算庞大，但单文件结构缺乏清晰的模块边界。

## 方案选项

### 方案A：模块化重构（推荐）

创建 `webui/` 包目录，拆分为多个模块：

```
webui/
├── __init__.py              # 包初始化
├── __main__.py              # 支持 python -m webui 运行
├── exceptions.py            # EditorError (~5行)
├── constants.py             # 常量定义 (~60行)
├── utils.py                 # 通用工具函数 (~50行)
├── parsers.py               # Python AST解析 (~250行)
├── file_utils.py            # 文件操作 (~50行)
├── security.py              # 安全验证 (~80行)
├── job.py                   # Job类 (~80行)
├── studio.py                # Studio类 (~380行)
├── handler.py               # Handler类 (~160行)
├── routes.py                # 路由分发 (~70行)
└── assets.py                # 前端资源 (~4320行)
```

**优势：**
- 清晰的职责分离（高内聚）
- 易于测试和维护
- 符合200-400行最佳实践
- 支持并行开发

**劣势：**
- 需要更新导入路径
- 部署时需要打包

### 方案B：保持单文件 + 注释分区

将现有代码用明确的注释分区，提取到独立函数/类，但保持单文件。

**优势：**
- 零迁移成本
- 保持单文件部署便利性

**劣势：**
- 文件仍然庞大
- 缺乏真正的模块边界

## 实施步骤（方案A）

### 阶段1：创建基础结构
1. 创建 `webui/` 目录和 `__init__.py`
2. 提取常量到 `constants.py`
3. 提取异常类到 `exceptions.py`

### 阶段2：提取工具函数
4. 提取通用工具到 `utils.py`
5. 提取文件操作到 `file_utils.py`
6. 提取安全函数到 `security.py`

### 阶段3：提取核心模块
7. 提取解析器到 `parsers.py`
8. 提取Job类到 `job.py`
9. 提取Studio类到 `studio.py`

### 阶段4：重构Handler
10. 提取路由逻辑到 `routes.py`
11. 简化Handler类到 `handler.py`

### 阶段5：资源和入口
12. 提取ASSETS到 `assets.py`
13. 重构 `webui.py` 为入口点
14. 创建 `__main__.py` 支持模块化运行

## 向后兼容性

保留原 `webui.py` 作为薄包装器：
```python
"""向后兼容的入口点."""
from webui.__main__ import main

if __name__ == "__main__":
    main()
```

这样：
- 旧命令 `python webui.py` 仍然有效
- 新命令 `python -m webui` 也可用
- 内部代码完全模块化

## 文件大小估算

| 模块 | 估算行数 | 符合规范？ |
|------|----------|-----------|
| exceptions.py | ~5 | ✓ |
| constants.py | ~60 | ✓ |
| utils.py | ~50 | ✓ |
| parsers.py | ~250 | ✓ |
| file_utils.py | ~50 | ✓ |
| security.py | ~80 | ✓ |
| job.py | ~80 | ✓ |
| studio.py | ~380 | ✓ |
| handler.py | ~160 | ✓ |
| routes.py | ~70 | ✓ |
| assets.py | ~4320 | ❌ (特殊：资源数据) |
| **总计（不含assets）** | **~1185** | **✓** |

注意：`assets.py` 包含静态资源数据，虽然超过800行，但这是不可压缩的二进制数据，属于合理例外。

## 测试策略

1. **单元测试**：每个模块独立测试
2. **集成测试**：通过原始API端点测试
3. **回归测试**：确保所有功能正常
