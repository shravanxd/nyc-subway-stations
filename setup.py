from setuptools import setup, find_packages

setup(
    name="nyc_transit",
    version="0.1.0",
    description="NYC Subway Routing and Real-Time Data Library",
    author="NYC Buddy",
    url="https://github.com/shravanxd/nyc_transit",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "fastapi",
        "uvicorn",
        "pandas",
        "networkx",
        "requests",
        "gtfs-realtime-bindings",
        "protobuf",
        "python-dotenv",
        "geopy"
    ],
    python_requires=">=3.8",
)
