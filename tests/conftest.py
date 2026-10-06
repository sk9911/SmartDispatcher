import os

from regret import offline


def pytest_configure(config):
    # nbmake kernels inherit the environment, so notebooks get the fixture config too.
    os.environ.setdefault("REGRET_CONFIG", "fixture")
    offline.install_if_requested()
