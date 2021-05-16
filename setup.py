import setuptools


def long_description():
    with open('README.md', 'r') as file:
        return file.read()


setuptools.setup(
    name='iterable-subprocess',
    version='0.0.4',
    author='Department for International Trade',
    author_email='sre@digital.trade.gov.uk',
    description='Communicate with a subprocess using iterables: for when data is too big to fit in memory and has to be streamed',
    long_description=long_description(),
    long_description_content_type='text/markdown',
    url='https://github.com/uktrade/iterable-subprocess',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
    ],
    python_requires='>=3.6.0',
    py_modules=[
        'iterable_subprocess',
    ],
)
