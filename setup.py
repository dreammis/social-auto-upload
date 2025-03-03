from setuptools import setup, find_packages

setup(
    name="social-auto-upload",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "playwright",
        "openai",
        # 其他依赖...
    ],
) 