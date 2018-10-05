#!/usr/bin/env python3

import os
import logging
from concoursetooling.cf.cloud_foundry import CloudFoundry
from concoursetooling.bx import bx_utils

logging.getLogger().setLevel(logging.DEBUG)
lr = bx_utils.bx_login(
    os.environ['BX_API'], \
    os.environ['BX_USER'], \
    os.environ['BX_PASS'], \
    os.environ['BX_ACC'], \
    os.environ['BX_RESOURCE_GROUP'] )

ss = CloudFoundry.get_all_services()

# CloudFoundryClient.

print(ss)

CloudFoundry.create_user_provided_service('test-me', {'foo' : 'bar'})