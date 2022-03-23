import os
import shutil
from datetime import datetime

from setuptools import find_packages, setup

import versioneer
# read the contents of your README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

package_name = "nvflops"

setup(
    name=package_name,
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description="New Version of Free-style machine-Learning Open Platform System",
    url="https://github.com/IsaacYangSLA/nvflops",
    package_dir={"nvflops": "nvflops"},
    packages=find_packages(
        where=".",
        include=[
            "*",
        ],
        exclude=[
            "test",
        ],
    ),
    package_data={"": ["*.yml", "*.html"]},
    zip_safe=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    install_requires=['boto3==1.21.24', "botocore==1.24.24; python_version >= '3.6'", 'certifi==2021.10.8', "charset-normalizer==2.0.12; python_version >= '3'", "click==8.0.4; python_version >= '3.6'", 'flask==2.0.3', 'flask-sqlalchemy==2.5.1', "greenlet==1.1.2; python_version >= '3' and platform_machine == 'aarch64' or (platform_machine == 'ppc64le' or (platform_machine == 'x86_64' or (platform_machine == 'amd64' or (platform_machine == 'AMD64' or (platform_machine == 'win32' or platform_machine == 'WIN32')))))", "idna==3.3; python_version >= '3'", "itsdangerous==2.1.1; python_version >= '3.7'", "jinja2==3.0.3; python_version >= '3.6'", "jmespath==1.0.0; python_version >= '3.7'", "markupsafe==2.1.1; python_version >= '3.7'", 'minio==7.1.5', "python-dateutil==2.8.2; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'", 'requests==2.27.1', "s3transfer==0.5.2; python_version >= '3.6'", "six==1.16.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'", "sqlalchemy==1.4.32; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4, 3.5'", "urllib3==1.26.9; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4' and python_version < '4'", "werkzeug==2.0.3; python_version >= '3.6'"],
)