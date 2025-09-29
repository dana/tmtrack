from setuptools import setup, find_packages

setup(
    name='tmtrack',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask',
        'pymongo',
        'python-dotenv',
        'uwsgi',
        'Flask-Cors',
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-flask',
            'tox',
        ],
    },
    entry_points={
        'console_scripts': [
            'tmtrack=app.__init__:create_app',
        ],
    },
    author='Your Name',
    author_email='your.email@example.com',
    description='A Flask-based REST API for tracking daily tasks.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/your-username/tmtrack',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: Flask',
    ],
    python_requires='>=3.10',
)
