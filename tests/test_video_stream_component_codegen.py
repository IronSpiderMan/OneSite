"""Regression coverage for the generated video-stream field component."""

from pathlib import Path
from typing import Optional

import pytest
from jinja2 import Environment, FileSystemLoader
from sqlmodel import Field, SQLModel

from onesite.codegen.introspect import get_model_fields
from onesite.codegen.phases.introspect_models import _build_model_dict


class Camera(SQLModel, table=True):
    __tablename__ = "test_video_stream_camera"
    __onesite__ = {"page_edit": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    stream_url: str = Field(
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "component": "video_stream",
                    "stream": {
                        "protocol": "hls",
                        "autoplay": True,
                        "muted": True,
                        "controls": False,
                        "reconnect": True,
                    },
                }
            }
        }
    )


class InvalidCamera(SQLModel, table=True):
    __tablename__ = "test_invalid_video_stream_camera"

    id: Optional[int] = Field(default=None, primary_key=True)
    stream_url: int = Field(
        sa_column_kwargs={
            "info": {"site_props": {"component": "video_stream"}}
        }
    )


class RtspCamera(SQLModel, table=True):
    __tablename__ = "test_explicit_rtsp_video_stream_camera"

    id: Optional[int] = Field(default=None, primary_key=True)
    stream_url: str = Field(
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "component": "video_stream",
                    "stream": {"protocol": "rtsp"},
                }
            }
        }
    )


class InvalidProtocolCamera(SQLModel, table=True):
    __tablename__ = "test_invalid_video_stream_protocol_camera"

    id: Optional[int] = Field(default=None, primary_key=True)
    stream_url: str = Field(
        sa_column_kwargs={
            "info": {
                "site_props": {
                    "component": "video_stream",
                    "stream": {"protocol": "webrtc"},
                }
            }
        }
    )


def _rendered_pages():
    result = get_model_fields(Camera, "camera")
    model = _build_model_dict("Camera", "camera", "camera", result)
    template_dir = (
        Path(__file__).parents[1] / "src" / "onesite" / "templates" / "codegen"
    )
    environment = Environment(loader=FileSystemLoader(template_dir))
    pages = {
        name: environment.get_template(name).render(model=model)
        for name in (
            "frontend_page_create.tsx.j2",
            "frontend_page_list.tsx.j2",
            "frontend_page_detail.tsx.j2",
            "singleton_page.tsx.j2",
        )
    }
    pages["profile.tsx.j2"] = environment.get_template("profile.tsx.j2").render(
        model=model
    )
    pages["register_page.tsx.j2"] = environment.get_template(
        "register_page.tsx.j2"
    ).render(model=model)
    pages["settings_page.tsx.j2"] = environment.get_template(
        "settings_page.tsx.j2"
    ).render(system_model=model, custom_model=None)
    return result, pages


def test_video_stream_metadata_and_generated_model_pages():
    result, pages = _rendered_pages()
    stream = next(field for field in result.fields if field.name == "stream_url")

    assert stream.type == "str"
    assert stream.ui_type == "video_stream"
    assert stream.stream_protocol == "hls"
    assert stream.stream_autoplay is True
    assert stream.stream_muted is True
    assert stream.stream_controls is False
    assert stream.stream_reconnect is True

    assert 'protocol="hls"' in pages["frontend_page_create.tsx.j2"]
    assert "video_stream.stream" in pages["frontend_page_list.tsx.j2"]
    assert "<VideoStreamPlayer" in pages["frontend_page_detail.tsx.j2"]
    assert "autoPlay={ true }" in pages["frontend_page_detail.tsx.j2"]
    assert "controls={ false }" in pages["frontend_page_detail.tsx.j2"]
    assert "<VideoStreamInput" in pages["singleton_page.tsx.j2"]
    assert "<VideoStreamInput" in pages["profile.tsx.j2"]
    assert "<VideoStreamPlayer" in pages["profile.tsx.j2"]
    assert "<VideoStreamInput" in pages["register_page.tsx.j2"]
    assert "<VideoStreamInput" in pages["settings_page.tsx.j2"]


def test_video_stream_rejects_invalid_field_and_protocol():
    with pytest.raises(ValueError, match="is not a string field"):
        get_model_fields(InvalidCamera, "invalid_camera")

    with pytest.raises(ValueError, match="stream.protocol must be one of"):
        get_model_fields(InvalidProtocolCamera, "invalid_protocol_camera")


def test_video_stream_accepts_explicit_rtsp_protocol():
    result = get_model_fields(RtspCamera, "rtsp_camera")
    stream = next(field for field in result.fields if field.name == "stream_url")
    assert stream.stream_protocol == "rtsp"


def test_video_stream_player_has_detection_fallback_and_cleanup_contract():
    component_root = (
        Path(__file__).parents[1]
        / "src"
        / "onesite"
        / "templates"
        / "frontend"
        / "src"
        / "components"
        / "ui"
    )
    player = (component_root / "video-stream-player.tsx").read_text()
    input_component = (component_root / "video-stream-input.tsx").read_text()

    assert "new URL(rawUrl, window.location.origin)" in player
    assert "url.pathname.toLowerCase()" in player
    assert "pathname.endsWith('.m3u8')" in player
    assert "Hls.isSupported()" in player
    assert "video.canPlayType('application/vnd.apple.mpegurl')" in player
    assert "hls?.destroy()" in player
    assert "rtsp:" in player and "rtmp:" in player and "srt:" in player
    assert "['rtsp', 'rtmp', 'srt'].includes(streamType)" in player
    assert "request.post('/video-streams/preview'" not in player
    assert "<VideoStreamPlayer" in input_component
    assert "video_stream.preview" in input_component
