from setuptools import setup, find_packages

setup(
    name="aec",
    version="0.1",
    description="AWS Easy CLI",
    entry_points={"console_scripts": ["ec2 = tools.ec2:main", "sqs = tools.sqs:main"]},
    packages=find_packages(),
    install_requires=[
        "boto3==1.10.40",
        "pytoml==0.1.21",
        "argh==0.26.2",
        "pyjq==2.4.0",
    ],
)
