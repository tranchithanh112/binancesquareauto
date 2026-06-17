from unittest.mock import patch, MagicMock
from src.runners.ai_image import build_image_prompt, generate_image


def test_build_image_prompt_fallback_no_claude():
    p = build_image_prompt("BTC tăng mạnh", "BTC", "nội dung", claude_fn=None)
    assert "BTC" in p
    assert "NO text" in p


def test_build_image_prompt_uses_claude():
    def fake(ask):
        return "a golden bull charging through a neon city", None
    p = build_image_prompt("title", "ETH", "content", claude_fn=fake)
    assert p.startswith("a golden bull charging")
    assert "NO text" in p


def test_build_image_prompt_claude_error_fallback():
    def fake(ask):
        return None, "boom"
    p = build_image_prompt("t", "SOL", "c", claude_fn=fake)
    assert "SOL" in p


def test_generate_image_writes_png(tmp_path):
    out = tmp_path / "img.png"
    resp = MagicMock(ok=True, content=b"\x89PNG\r\n\x1a\n", status_code=200,
                     headers={"Content-Type": "image/png"})
    with patch("src.runners.ai_image.requests.get", return_value=resp):
        path, err = generate_image("a scene", out_path=str(out))
    assert err is None
    assert out.read_bytes().startswith(b"\x89PNG")


def test_generate_image_non_image_errors(tmp_path):
    resp = MagicMock(ok=True, content=b"<html>", status_code=200,
                     headers={"Content-Type": "text/html"})
    with patch("src.runners.ai_image.requests.get", return_value=resp):
        path, err = generate_image("x")
    assert path is None and "not an image" in err
