from unittest.mock import patch, MagicMock
from src.runners.ai_image import build_image_prompt, generate_image


def test_build_image_prompt_includes_coin_and_style():
    p = build_image_prompt("BTC tăng mạnh", "BTC", "nội dung", claude_fn=None)
    assert "BTC" in p
    assert "NO text" in p


def test_build_image_prompt_themes_by_keyword():
    rally = build_image_prompt("Bitcoin surge to new ATH", "BTC", "")
    assert "rocket" in rally
    hack = build_image_prompt("Major exploit drains protocol", "ETH", "")
    assert "breach" in hack
    etf = build_image_prompt("BlackRock ETF inflow record", "BTC", "")
    assert "vaults" in etf


def test_build_image_prompt_vietnamese_keyword():
    p = build_image_prompt("Thị trường lao dốc, BTC giảm mạnh", "BTC", "")
    assert "red descent" in p


def test_build_image_prompt_default_scene():
    p = build_image_prompt("some neutral partnership update", "SOL", "")
    assert "SOL" in p and "NO text" in p


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
