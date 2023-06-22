# test

import setuptools

setuptools.setup(
    name="crcsim",
    version="0.0.1",
    packages=setuptools.find_packages(),
    description="Simulation engine for the colorectal cancer screening model",
    python_requires=">=3.6",
    install_requires=["fire", "pandas"],
    entry_points={
        "console_scripts": [
            "crc-simulate = crcsim.__main__:main",
            "crc-analyze = crcsim.analysis:main",
        ]
    },
)
