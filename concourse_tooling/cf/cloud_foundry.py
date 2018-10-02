import subprocess
from string import Template
import json
import logging

class CloudFoundry:
    '''Cloud Foundry client'''

    logger = logging.getLogger(__name__)

    @staticmethod
    def login(cf_api, cf_org, cf_space, cf_user, cf_pwd):
        subprocess.run(["cf login -a " + cf_api + " -u " + cf_user + " -o " + cf_org + " -s " + cf_space + " -p " + cf_pwd + " --skip-ssl-validation"], shell=True)
     
    @staticmethod
    def apps():
        subprocess.run(["cf apps"], shell=True)   

    @staticmethod
    def routes():
        subprocess.run(["cf routes"], shell=True)   

    @staticmethod
    def logout(): 
        subprocess.run(["cf logout"], shell=True)

    @staticmethod
    def stop(cf_app):
        subprocess.run(["cf stop {}".format(cf_app)], shell=True)

    @staticmethod
    def domains():
        domains = subprocess.run(["cf domains | tail -n +3 | awk '{print $1}'"], stdout=subprocess.PIPE, shell=True, encoding='utf-8').stdout.split('\n')
        # there's an empty line at the end of the bash command's stdout, we remove that here
        if domains[len(domains)-1] == '':
            domains.pop()
        return domains

    @staticmethod
    def exists(cf_app):
        app_results = subprocess.run('cf a | grep "{}"'.format(cf_app), stdout=subprocess.PIPE, shell=True, encoding='utf-8').stdout
        return bool(app_results)

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

            cf_call(cf_app, hostname, domain, path)

    @staticmethod
    def get_hostname_param(hostname):
        hostname_param = ""
        if hostname:
            hostname_param = "--hostname " + hostname
        return hostname_param

    @staticmethod
    def get_path_param(path):
        path_param = ""
        if path:
            path_param = "--path " + path
        return path_param

    @staticmethod
    def call_cf_map(cf_app, hostname, domain, path):
        hostname_param = CloudFoundry.get_hostname_param(hostname)
        path_param = CloudFoundry.get_path_param(path)
        cmd = 'cf map-route {} {} {} {}'.format(cf_app, domain, hostname_param, path_param)
        subprocess.run(cmd, shell=True)


    @staticmethod
    def call_cf_unmap(cf_app, hostname, domain, path):
        hostname_param = CloudFoundry.get_hostname_param(hostname)
        path_param = CloudFoundry.get_path_param(path)
        cmd = 'cf unmap-route {} {} {} {}'.format(cf_app, domain, hostname_param, path_param)
        subprocess.run(cmd, shell=True)

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
        '''If not exists create a user provided service from config with ups_name
        '''
        services = CloudFoundry.get_all_services()
        cjson = json.dumps(config)
        if ups_name in services:
            ## update
            xary=["cf", "uups", ups_name,  "-p", cjson]
            CloudFoundry.logger.debug(xary)
            CloudFoundry.__run(xary)
        else:
            ## create
            xary=["cf", "cups", ups_name,  "-p", cjson]
            CloudFoundry.logger.debug(xary)
            CloudFoundry.__run(xary)

    @staticmethod
    def __run(cmd):
        ret=subprocess.run([cmd], shell=True, check=True, stdout=subprocess.PIPE, encoding='utf-8')
        return ret

