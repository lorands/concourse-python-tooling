from setuptools import setup

setup(name='concourse_tooling',
      version='0.1',
      description='Concourse Python Tooling',
      url='http://plensys.com',
      author='Plensys',
      author_email='lorand.somogyi@plensys.com',
      license='MAT',
      packages=['concourse_tooling'],
      install_requires=[
            "requests",
      ],
      zip_safe=False)
      