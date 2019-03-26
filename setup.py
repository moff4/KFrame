import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='kframe',
    version='3.0',
    author='Komissarov Andrey',
    author_email='kak.to.tam@mail.ru',
    description='Framework for simple web service with it\'s own web-server Neon',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/moff4/kframe',
    install_requires=[
        'pygost',
        'mysql-connector',
    ],
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
)
