import subprocess
from string import Template
import json
import logging

class CloudFoundry:
    '''Cloud Foundry client'''

    logger = logging.getLogger(__name__)

    @staticmethod
    def login(cf_api, cf_org, cf_space, cf_user, cf_pwd):
        CloudFoundry.__run("cf login -a " + cf_api + " -u " + cf_user + " -o " + cf_org + " -s " + cf_space + " -p " + cf_pwd + " --skip-ssl-validation")
     
    @staticmethod
    def apps():
        CloudFoundry.__run("cf apps")

    @staticmethod
    def routes():
        CloudFoundry.__run("cf routes")

    @staticmethod
    def logout(): 
        CloudFoundry.__run("cf logout")

    @staticmethod
    def start(cf_app):
        CloudFoundry.__run("cf start {}".format(cf_app))

    @staticmethod
    def stop(cf_app):
        CloudFoundry.__run("cf stop {}".format(cf_app))

    @staticmethod
    def domains():
        domains = CloudFoundry.__run("cf domains | tail -n +3 | awk '{print $1}'").stdout.split('\n')
        # there's an empty line at the end of the bash command's stdout, we remove that here
        if domains[len(domains)-1] == '':
            domains.pop()
        return domains

    @staticmethod
    def exists(cf_app):
        exit_code = subprocess.run(['cf a | grep "{}"'.format(cf_app)], shell=True, stdout=subprocess.PIPE, encoding='utf-8').returncode
        if exit_code == 0:
            return True
        elif exit_code == 1:
            return False
        else:
            raise Exception("An error occured while checking if app [{}] exists in CF".format(cf_app))

    @staticmethod
    def map_routes(cf_app, cf_approutes):
        CloudFoundry.change_routes(cf_app, cf_approutes, CloudFoundry.call_cf_map)
        
    @staticmethod
    def unmap_routes(cf_app, cf_approutes):
        CloudFoundry.change_routes(cf_app, cf_approutes, CloudFoundry.call_cf_unmap)

    @staticmethod
    def change_routes(cf_app, cf_approutes, cf_call):
        domains = CloudFoundry.domains()

        for route in cf_approutes:

            # check if the route as a whole is a domain
            domain_found = False
            for domain in domains:
                if route == domains: 
                    domain_found = True
                    break

            # cut the path from the end of the route
            split_route = route.split('/', 1)
            hostname_domain = split_route[0]
            path = ""
            if len(split_route) > 1:
                path = split_route[1]

            
            hostname = ""
            domain = ""
            # if the route is a domain, use it as is, don't cut off the first segment as a hostname
            if domain_found == True: 
                domain = hostname_domain
            else:
            # else dissect the route into hostname and domain
                split_hostname_domain = hostname_domain.split('.', 1)
                hostname = split_hostname_domain[0]
                domain = split_hostname_domain[1]

            CloudFoundry.logger.debug("hostname: {} | domain: {} | path: {}".format(hostname, domain, path))
            cf_call(cf_app, hostname, domain, path)

    @staticmethod
    def get_hostname_param(hostname):
        hostname_param = ""
        if hostname:
            hostname_param = "--hostname " + hostname
        CloudFoundry.logger.debug("hostname_param: {}".format(hostname_param))
        return hostname_param

    @staticmethod
    def get_path_param(path):
        path_param = ""
        if path:
            path_param = "--path " + path
        CloudFoundry.logger.debug("path_param: {}".format(path_param))
        return path_param

    @staticmethod
    def call_cf_map(cf_app, hostname, domain, path):
        hostname_param = CloudFoundry.get_hostname_param(hostname)
        path_param = CloudFoundry.get_path_param(path)
        cmd = 'cf map-route {} {} {} {}'.format(cf_app, domain, hostname_param, path_param)
        CloudFoundry.logger.debug("Assembled cf map-route command: {}".format(cmd))
        CloudFoundry.__run(cmd)


    @staticmethod
    def call_cf_unmap(cf_app, hostname, domain, path):
        hostname_param = CloudFoundry.get_hostname_param(hostname)
        path_param = CloudFoundry.get_path_param(path)
        cmd = 'cf unmap-route {} {} {} {}'.format(cf_app, domain, hostname_param, path_param)
        CloudFoundry.logger.debug("Assembled cf unmap-route command: {}".format(cmd))
        CloudFoundry.__run(cmd)

    @staticmethod
    def get_all_services():
        proc = CloudFoundry.__run("cf s")
        ret = list()
        if proc.returncode == 0:
            for line in proc.stdout.split('\n')[3:]:
                # print("L:  " + line.split())
                splits = line.split()
                if( len(splits) > 1 ):
                    item=splits[0].strip()
                    ret.append(item)
        else:
            return None
        return ret

    # @staticmethod
    # def get_service_details(service_name):
    #     proc = CloudFoundry.__run(["cf service {}".format(service_name)])
    #     if proc.returncode == 0:
    #         ## TODO
    #         return None
    #     else: 
    #         return None    

    @staticmethod
    def create_user_provided_service(ups_name, config):
        '''If not exists create a user provided service from config with ups_name. 
        If exists it will be updated!

        Parameters
        ----------
        ups_name : name of the user provided service
        config : expecting a dict with key/value pair to be converted to json
        '''
        services = CloudFoundry.get_all_services()
        cjson = json.dumps(config)
        if ups_name in services:
            ## update
            xary=["cf", "uups", ups_name,  "-p", cjson]
            CloudFoundry.logger.debug(xary)
            ret=subprocess.run(xary, stdout=subprocess.PIPE, encoding='utf-8')
            if ret.returncode != 0 :
                raise Exception("Fail to update CF UPS. Output {}".format(ret.stdout))
        else:
            ## create
            xary=["cf", "cups", ups_name,  "-p", cjson]
            CloudFoundry.logger.debug(xary)
            ret=subprocess.run(xary, stdout=subprocess.PIPE, encoding='utf-8')
            if ret.returncode != 0 :
                raise Exception("Fail to create CF UPS. Output {}".format(ret.stdout))

    @staticmethod
    def __run(cmd):
        ret=subprocess.run([cmd], shell=True, check=True, stdout=subprocess.PIPE, encoding='utf-8')
        return ret

