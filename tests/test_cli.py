import subprocess


def test_run_script():
    """
    The package should be runnable from the shell as a script.
    """
    subprocess.run(["crc-simulate"], check=True)


def test_run_module():
    """
    The package should be runnable from the shell using python's -m option.
    """
    subprocess.run(["python", "-m", "crcsim"], check=True)
