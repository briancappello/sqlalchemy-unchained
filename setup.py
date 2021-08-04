from setuptools import setup, find_packages


with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='SQLAlchemy-Unchained',
    version='0.12.2',
    description='Improved declarative SQLAlchemy models',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/briancappello/sqlalchemy-unchained',
    author='Brian Cappello',
    license='MIT',

    packages=find_packages(exclude=['docs', 'tests']),
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.6',
    install_requires=[
        'alembic>=1.0.9',
        'py-meta-utils>=0.7.6',
        'sqlalchemy>=1.2.12,<2',
    ],
    extras_require={
        'dev': [
            'coverage',
            'pytest>=5.0',
            'tox',
        ],
        'docs': [
            'm2rr',
            'sphinx',
            'sphinx-material',
        ],
    },

    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    entry_points={
        'console_scripts': ['alembic = sqlalchemy_unchained.cli:main'],
    }
)
