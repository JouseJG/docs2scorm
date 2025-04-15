from setuptools import setup, find_packages
from pathlib import Path

def _read_content(path: str) -> str:
    return (Path(__file__).parent / path).read_text(encoding="utf-8")

requirements = _read_content("requirements.txt").splitlines()

setup(
    name="doc2scorm",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "doc2scorm=doc2scorm.cli:main"
        ]
    },
    package_data={
        "doc2scorm": ["templates/*.html"]
    },
    author="Jose Ramon Jimenez",
    description="Convierte documentos .docx/.odt en paquetes SCORM.",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: GPL-3.0"
    ],
    python_requires='>=3.7',
)
