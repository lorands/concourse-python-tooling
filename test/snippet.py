#!/usr/bin/env python3

# from cloudfoundry_client.client import CloudFoundryClient
# from concourse_python_tooling.concourse_tooling.bx import bx_utils
from concoursetooling.cf.cloud_foundry import CloudFoundry

ss = CloudFoundry.get_all_services()

# CloudFoundryClient.

print(ss)

CloudFoundry.create_user_provided_service('test-me', {'foo' : 'bar'})