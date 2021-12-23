#!/usr/bin/env python

from setuptools import setup, find_namespace_packages
from proton.constants import VERSION

setup(
    name="proton-core",
    version="0.0.0",
    description="Proton Technologies API wrapper",
    author="Proton Technologies",
    author_email="contact@protonmail.com",
    url="https://github.com/ProtonMail/python-proton-core",
    install_requires=["requests", "bcrypt", "python-gnupg", "pyopenssl", "importlib-metadata; python_version < '3.8'"],
    tests_requires=['pyotp'],
    entry_points={
        "proton_loader_keyring": [
            "json = proton.keyring.textfile:KeyringBackendJsonFiles"
        ]
    },
    packages=find_namespace_packages(include=['proton.*']),
    include_package_data=True,
    license="GPLv3",
    platforms="OS Independent",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python",
        "Topic :: Security",
    ]
)
