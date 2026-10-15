from inference.runner import run_stub_pipeline


def test_stub_pipeline():
    result = run_stub_pipeline("data/mock/satellite/kuttanad_demo.txt")
    assert result["flood"]["confidence"] > 0
    assert result["damage"]["damage_class"] == "moderate"
