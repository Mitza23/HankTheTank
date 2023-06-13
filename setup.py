import setuptools

with open("README.md", "r", encoding="utf-8") as fhand:
    long_description = fhand.read()

setuptools.setup(
    name="Hank-The-Tank",
    version="1.0.0",
    author="Mihai Grebla",
    author_email="mitzagrebla@yahoo.com",
    description="Hank The Tank - CS:GO Aiming Assistant\n" +
                " A tool for automatically aiming and shooting in CS:GO\n" +
                "K - start/stop the program\n" +
                "F1 - change opponent team\n" +
                "F2 - change aiming strategy\n" +
                "F3 - toggle drawing mode(slows the process considerably)\n" +
                "F4 - change spray time",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Mitza23/HankTheTank",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'matplotlib>=3.2.2',
        'numpy>=1.18.5,<1.24.0',
        'opencv-python>=4.1.1',
        'Pillow>=7.1.2',
        'PyYAML>=5.3.1',
        'requests>=2.23.0',
        'scipy>=1.4.1',
        'tqdm>=4.41.0',
        'protobuf<4.21.3',
        'tensorboard',
        'pandas>=1.1.4',
        'seaborn>=0.11.0',
        'ipython',
        'psutil',
        'thop',
        'pywin32==228',
        'opencv-contrib-python==4.4.0.42',
        'pynput==1.7.1',
        'PyAutoGUI==0.9.50',
        'pygame==2.4.0',
        'mss==6.0.0',
        'keyboard==0.13.5',
        'mouse==0.7.1',
        'tensorflow-directml'
    ],
    package_data={'': ['best.pt']},
    include_package_data=True,
    packages=setuptools.find_packages(),
    python_requires="==3.7.7",
    entry_points={
        "console_scripts": [
            "hank = bot.cli:main",
        ]
    }
)
