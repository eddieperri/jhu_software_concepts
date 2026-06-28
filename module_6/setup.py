"""
Setup packaging definition for Module 5 code validation routines.
"""
from setuptools import setup, find_packages

setup(
    name="grad_cafe_app",
    version="0.1.0",
    description="Flask and PostgreSQL web application.",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
)
