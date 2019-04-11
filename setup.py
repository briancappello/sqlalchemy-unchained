from setuptools import setup, find_packages


with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='SQLAlchemy-Unchained',
    version='0.7.3',
    description='Improved declarative SQLAlchemy models',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/briancappello/sqlalchemy-unchained',
    author='Brian Cappello',
    license='MIT',

    packages=find_packages(exclude=['docs', 'tests']),
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.5',
    install_requires=[
        'alembic @ git+https://github.com/sqlalchemy/alembic.git@d46de05b8b3281a85e6b107ef3f3407e232eb9e9#egg=alembic',
        'py-meta-utils>=0.7.6',
        'sqlalchemy>=1.2.12',
    ],
    extras_require={
        'dev': [
            'coverage',
            'pytest',
            'tox',
        ],
        'docs': [
            'm2r',
            'sphinx',
            'sphinx-autobuild',
            'sphinx-rtd-theme',
        ],
    },

    # https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points={
        'console_scripts': ['alembic = sqlalchemy_unchained.cli:main'],
    }
)
