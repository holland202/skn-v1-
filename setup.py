from setuptools import setup, find_packages

setup(
    name="skn-v1",
    version="1.7.0",
    description="Sovereign Kinematic Node",
    packages=find_packages(),
    install_requires=["numpy", "scipy"],
    python_requires=">=3.9",
)

