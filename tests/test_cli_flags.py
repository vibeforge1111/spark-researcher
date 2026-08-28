import subprocess
def test_researcher_json():
    r = subprocess.run(["python3","-m","spark_researcher.cli","--help"], capture_output=True, timeout=5)
    assert r.returncode == 0
