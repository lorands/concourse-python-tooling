#!/usr/bin/env python3

import logging
import re
import subprocess
# from collections import namedtuple
import xml.etree.ElementTree as ET
import random
import string
import os

import requests

logger = logging.getLogger(__name__)

def bx_login(endpoint, user, pwd, account, resource_group = 'Default'):
  '''Blumix login. If resource group is not defined it defaults to 'Default'.
  '''
  # login
  completed = __run("bx login -a {} -u {} -p {} -c {} -g {}".format(
                    endpoint, user, pwd, account, resource_group))
  return completed.returncode ## we might not need this at all, it will raise an exception if failed

def get_bx_iam_token() :
  '''Get bluemix IAM Token. Cloud only be obtained after call to bx_login().
  '''
  completed = __run('bx iam oauth-tokens')
  return completed.stdout.split('\n', 1)[0].split(':')[1].strip()

def get_bx_resource_service_instance(instance_name):
  '''Get bluemix resource service instance details.
  '''
  shout = __run("bx resource service-instance {}".format(instance_name))
  return __process_bx_output_to_dict(shout.stdout)

def deploy_docker_as_cf_app(name, docker_image, domain, hostname=None, instances="1", disk_limit='2G', mem_limit='1G'):
  '''Deploy docker to CF as app. 
  Will do it with no-route!!
  '''
  tokenDict = __get_cr_token()
  token = tokenDict['Token']
  logger.debug("Token is: {}".format(token))

  my_env = os.environ.copy()
  my_env["CF_DOCKER_PASSWORD"] = token
  logger.debug("Prepared env to run is: {}".format(my_env))
  host = hostname
  if hostname == None:
    host = name
  cmd = "cf push -i {} -m {} -k {} -d {} -n {} {} --docker-image {} --docker-username token".format(instances, mem_limit, disk_limit, domain, host, name, docker_image)
  __run(cmd, env=my_env)
  # cmdAry = ["cf", "push", "-i", instances, "-m", mem_limit, "-k", disk_limit, "-d", domain, "-n", host, name, "--docker-image", docker_image, "--docker-username", "token"]  
  # logging.debug("About to call: {}".format(cmdAry))
  # completed = subprocess.run(cmdAry, check=True, stdout=subprocess.PIPE, encoding='utf-8', env=my_env)
  # logger.debug('Call returned with: {}'.format(completed))


def __get_cr_token():
  # bx cr token-add
  shout = __run("bx cr token-add")
  ##tokenDict = __process_bx_output_to_dict(shout.stdout)
  lines = shout.stdout.split('\n')
  tokenDict = {}
  for line_no, line in enumerate(lines) :
    # print("l{} : {}".format(line_no, line))
    if line_no == 2:
      # print(re.split(r"\s{2,3}", line))
      tokenDict['Identifier'] = re.split(r"\s{2,3}", line)[1].strip()
    if line_no == 3:
      tokenDict['Token'] = re.split(r"\s+", line)[1].strip()
  return tokenDict


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


def __run(cmd, check=True, env=None):
  logging.debug("About to call: {}".format(cmd))
  completed = subprocess.run([cmd], shell=True, check=check, stdout=subprocess.PIPE, encoding='utf-8', env=env)
  logger.debug('Call returned with: {}'.format(completed))
  return completed


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
