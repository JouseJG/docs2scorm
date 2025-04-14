from setuptools import setup, find_packages

setup(
    name="doc2scorm",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "python-docx",
        "mammoth",
        "odfpy",
        "jinja2",
        "beautifulsoup4"
    ],
    entry_points={
        "console_scripts": [
            "doc2scorm=doc2scorm.cli:main"
        ]
    },
    package_data={
        "doc2scorm": ["templates/*.html"]
    },
    author="Tu Nombre",
    description="Convierte documentos .docx/.odt en paquetes SCORM.",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: GPL-3.0"
    ],
    python_requires='>=3.7',
)
