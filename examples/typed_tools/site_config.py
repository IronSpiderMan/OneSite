from onesite.config import SiteConfig, Theme

from app.tools.text_transform import TextTransformTool


config = SiteConfig(
    project_name="TypedTools",
    style=Theme.INDUSTRIAL,
    tools=[TextTransformTool],
)
