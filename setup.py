from setuptools import setup

setup(name='concoursetooling',
      version='0.2',
      description='Concourse Python Tooling',
      url='http://plensys.com',
      author='Plensys',
      author_email='lorand.somogyi@plensys.com',
      license='MIT',
      packages=['concoursetooling', 'concoursetooling/bx', 'concoursetooling/cf'],
      install_requires=[
            "requests",
      ],
      zip_safe=False)