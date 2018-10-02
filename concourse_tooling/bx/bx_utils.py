#!/usr/bin/env python3

import logging
import re
import subprocess
# from collections import namedtuple
import xml.etree.ElementTree as ET
import random
import string

import requests

logger = logging.getLogger(__name__)

def bx_login(endpoint, user, pwd, account, resource_group = 'Default'):
  '''Blumix login. If resource group is not defined it defaults to 'Default'.
  '''
  try:
    subprocess.run(["bx", "config", "--check-version=false"]) ## should go to docker

    # login
    completed = subprocess.run(["bx login -a {} -u {} -p {} -c {} -g {}".format(
      endpoint, user, pwd, account, resource_group)
    ], shell=True)
    logger.info('bx login returncode: {}'.format(completed.returncode))
    return completed.returncode
  except subprocess.CalledProcessError as err:
    logging.error('ERROR: {}'.format(err))
    return 1

def get_bx_iam_token() :
  '''Get bluemix IAM Token. Cloud only be obtained after call to bx_login().
  '''
  completed = __run('bx iam oauth-tokens')
  retcode = completed.returncode
  #print(completed)
  if retcode == 0 :
    return completed.stdout.split('\n', 1)[0].split(':')[1].strip()
  else:
    raise Exception

def get_bx_resource_service_instance(instance_name):
  '''Get bluemix resource service instance details.
  '''
  #COS_RID=$(bx resource service-instance $COS_NAME | grep '^ID:' | awk '{print $2}')
  shout = __run("bx resource service-instance {}".format(instance_name))
  if shout.returncode == 0 :
    return __process_bx_output_to_dict(shout.stdout)
  else :
    raise Exception("Process failed.")


def bx_create_bucket(desired_name, cos_url, cos_rid, bucket_location):
  '''Creats a bucket and returns it real name
  '''
  iam_token = get_bx_iam_token()
  if __find_bucket(desired_name, cos_url, cos_rid, iam_token):
    ## found
    return desired_name
  else:
    ## not found so try to create it
    logging.info("Bucket {} not found.".format(desired_name))
    if not __create_bucket(desired_name, cos_url, cos_rid, iam_token, bucket_location):
      ## try 5 times with rnd
      for i in list(range(1, 5)):
        rnd=random.sample(list(string.ascii_lowercase+string.digits), 4)
        forged_bucket_name = desired_name + '-' + ''.join(rnd)
        logging.info("Trying to create bucket with forged name: {}".format(forged_bucket_name))
        if __create_bucket(forged_bucket_name, cos_url, cos_rid, iam_token, bucket_location):
          logging.info("Successfully created a bucket in {}".format(i))
          return forged_bucket_name
      raise Exception("Fail to create bucket after 6 tries. Bailing out.")
  return desired_name

def __create_bucket(bucket_name, cos_url, cos_rid, iam_token, bucket_location):
  headers= {'Content-Type': 'text/plain; charset=utf-8', \
            'Authorization': iam_token, \
            'ibm-service-instance-id' : cos_rid }
  logging.debug("Bucket Create Headers: {}".format(headers))
  data="<CreateBucketConfiguration><LocationConstraint>{}</LocationConstraint></CreateBucketConfiguration>".format(bucket_location)
  logging.debug("Data: {}".format(data))
  url='{}/{}'.format(cos_url, bucket_name)
  logging.debug("Bucket create url {}".format(url))
  resp = requests.put(url, headers=headers, data=data)
  logging.debug(resp)
  if resp.status_code == 200:
    print('cucccess')
    return True
  elif resp.status_code == 409:
    tree = ET.ElementTree(ET.fromstring(resp.content))
    root = tree.getroot()
    error_code = root.find('.//Code')
    print(error_code.text)
    if error_code.text == 'BucketAlreadyExists' :
      logging.warn('Bucket {} already exists somewhere in the wild. Got message: {}'.format(bucket_name, resp.content))
    else:
      logging.warn('Unknown problem occured: {}'.format(resp.content))
    return False
  else:
    logging.warn('Unknown problem occured: {}'.format(resp.content))
    return False

def __find_bucket(desired_name, cos_url, cos_rid, iam_token):
  headers= {'Accept': 'application/json', \
            'Content-Type': 'application/json', \
            'Authorization': iam_token, \
            'ibm-service-instance-id' : cos_rid }
  logging.debug(headers)
  ## check if exists
  resp = requests.get(cos_url, headers=headers)

  if resp.status_code == 200:
    content = resp.content.decode('utf-8')
    logging.debug(content)
    tree = ET.ElementTree(ET.fromstring(content))
    root = tree.getroot()
    ns = {'s3' : 'http://s3.amazonaws.com/doc/2006-03-01/'}
    for bucket in root.findall('.//s3:Bucket', ns):
      name = bucket.find('s3:Name', ns)
      logging.debug("Found bucket with name: {}".format(name.text))
      p = re.compile( '^'+desired_name + r'(-\w{4})?$' )

      if p.match(name.text):
        ## found
        logging.info("Bucket found with name {}".format(name.text))
        return True
    return False
  else:
    raise Exception

  ## try to create, iterate while not done
  return 0


def __run(cmd):
  return subprocess.run([cmd], shell=True, check=True, stdout=subprocess.PIPE, encoding='utf-8')


def __process_bx_output_to_dict(output):
  '''Process IBM Cloud classical output of key-value pair to dict.
  '''
  p = re.compile(r'((\w+\s?)+)\:\s+(.+)')
  ret = {}
  lines = output.split('\n')
  for line in lines :
    m = p.match(line)
    if m :
      g = m.groups()
      # print("K: -{}- V: -{}-".format(g[0], g[2].strip()))
      ret[g[0]]=g[2].strip()
  return ret
