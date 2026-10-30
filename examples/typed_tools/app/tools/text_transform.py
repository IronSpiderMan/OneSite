from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from onesite_runtime.tools import BaseTool, ExecutionOptions, ToolContext


class TransformInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    __i18n__ = {
        "zh": {
            "fields": {"text": "原文", "mode": "转换方式"},
            "enums": {"mode": {"upper": "大写", "lower": "小写"}},
        },
    }

    text: str = Field(
        title="Text", min_length=1, max_length=10000,
        json_schema_extra={"site_props": {"component": "textarea"}},
    )
    mode: Literal["upper", "lower"] = Field(default="upper", title="Mode")


class TransformResult(BaseModel):
    __i18n__ = {"zh": {"fields": {"content": "处理结果", "length": "字符数"}}}

    content: str = Field(title="Content")
    length: int = Field(title="Length", ge=0)


class TextTransformTool(BaseTool):
    name = "text_transform"
    title = "Text transform"
    description = "Convert the letter case of text."
    permissions = ("admin", "developer")
    inputs = TransformInputs
    result = TransformResult
    execution = ExecutionOptions(timeout_seconds=120)
    translations = {
        "zh": {"title": "文本转换", "description": "将文本转换为大写或小写。"},
    }

    async def run(self, inputs: TransformInputs, context: ToolContext) -> TransformResult:
        await context.set_progress(50, "Processing")
        content = inputs.text.upper() if inputs.mode == "upper" else inputs.text.lower()
        return TransformResult(content=content, length=len(content))
