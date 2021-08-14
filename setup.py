import setuptools
import sys
version = "0.1.0"

with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires=["pyunpack"]

setuptools.setup(
    name="powerbeatsvr",
    version=version,
    description="Convert beats saber levels to PowerBeatsVR",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/guysoft/PowerBeatsVR_song_writer",
    author="Guy Sheffer",
    author_email="gusyoft@gmail.com",
    license="GPLv3",
    py_modules=["powerbeatsvr"],
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
    ],
    packages=setuptools.find_packages(where="src"),
    package_dir={
        "": "src",
    },
    data_files=[],
    include_package_data=True,
    install_requires=install_requires,
    entry_points={"console_scripts": ["powerbeatsvr=powerbeatsvr.writer:run"]}
)
