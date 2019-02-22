import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='kframe',
    version='2.4.3',
    author='Komissarov Andrey',
    author_email='kak.to.tam@mail.ru',
    description='Framework with it\'s own web-server Neon',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/moff4/kframe',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
