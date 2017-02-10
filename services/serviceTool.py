#!/usr/bin/python
# -*- coding: utf-8 -*-

# Deployment cleanup script

import argparse
import re
import requests
import sys
import json
import logging
from requests.auth import HTTPBasicAuth

# requests.packages.urllib3.disable_warnings()

parser = argparse.ArgumentParser()
parser.add_argument("username", help="Your API username. Not the same as your UI Login."
                                     " See your CloudCenter admin for help.")
parser.add_argument("apiKey", help="Your API key.")
parser.add_argument("ccm", help="CCM hostname or IP.")
parser.add_argument("-d", "--debug", help="Set debug logging", action='store_const', const=logging.DEBUG)
parser.add_argument("-o", "--overwrite", action='store_true',
                    help="When importing, overwrite existing service in CloudCenter. When exporting,"
                         " overwrite existing file.")
parser.add_argument("-l", "--logo", type=argparse.FileType('rb'),
                    help="Filename of the NEW or UPDATED logo to attach to this service."
                         " Can be ommitted to leave logo unchanged.")

group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-e", "--export", dest="e", metavar='servicename', help="(text, not int) Service ID of the service that you want to export.")
group.add_argument("-i", "--import", dest="i", metavar='filename', help="Filename of the service that you want to import.", type=argparse.FileType('r'))

args = parser.parse_args()
parser.parse_args()

username = args.username
apiKey = args.apiKey
ccm = args.ccm
baseUrl = "https://"+args.ccm

s = requests.Session()


def getTenantId():
    url = baseUrl+"/v1/users"

    querystring = {}

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    response = s.request("GET", url, headers=headers, params=querystring, verify=False, auth=HTTPBasicAuth(username, apiKey))

    j = response.json()
    tenantId = None
    for user in j['users']:
        if user['username'] == username:
            tenantId = user['tenantId']
            break
    if not tenantId:
        logging.error("Couldn't find tenantId")
        sys.exit(1)
    return tenantId

def getServiceId(tenantId, serviceName):
    url = baseUrl+"/v1/tenants/"+tenantId+"/services/"

    querystring = {
        "size" : 0
    }

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    response = s.request("GET", url, headers=headers, params=querystring, verify=False, auth=HTTPBasicAuth(username, apiKey))

    j = response.json()
    serviceId = None
    for service in j['services']:
        #print(json.dumps(user['username'], indent=2))
        if service['name'] == serviceName:
            serviceId = service['id']

    return serviceId

def getImageId(tenantId, imageName):
    url = baseUrl+"/v1/tenants/"+tenantId+"/images/"

    querystring = {
        "size" : 0
    }

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    response = s.request("GET", url, headers=headers, params=querystring, verify=False, auth=HTTPBasicAuth(username, apiKey))

    j = response.json()
    imageId = None
    for image in j['images']:
        #print(json.dumps(user['username'], indent=2))
        if image['name'] == imageName:
            imageId = image['id']

    return imageId

def getRepoId(repoName):
    url = baseUrl+"/repositories/"

    querystring = {
        "size" : 0
    }

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    response = s.request("GET", url, headers=headers, params=querystring, verify=False, auth=HTTPBasicAuth(username, apiKey))

    j = response.json()
    repoId = None
    for repo in j['repositories']:
        if repo['displayName'] == repoName:
            repoId = repo['id']

    return repoId

def getImageName(tenantId, imageId):
    url = baseUrl+"/v1/tenants/"+tenantId+"/images/"

    querystring = {
        "size" : 0
    }

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    response = s.request("GET", url, headers=headers, params=querystring, verify=False, auth=HTTPBasicAuth(username, apiKey))

    j = response.json()
    imageName = None
    for image in j['images']:
        #print(json.dumps(user['username'], indent=2))
        if int(image['id']) == imageId:
            imageName = image['name']

    return imageName

def getServiceManifest(serviceName):
    tenantId = getTenantId()
    serviceId = getServiceId(tenantId, serviceName)

    if not serviceId:
        logging.error("Couldn't find serviceId for service {} in tenant Id {}".format(serviceName, tenantId))
        sys.exit(1)

    url = baseUrl+"/v1/tenants/"+tenantId+"/services/"+serviceId

    querystring = {}

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    response = s.request("GET", url, headers=headers, params=querystring, verify=False, auth=HTTPBasicAuth(username, apiKey))
    logging.debug(json.dumps(response.json(), indent=2))
    j = response.json()

    # Add a custom attribute to persist the name of the default image which makes this portal. The
    # default image Id won't be. Remove the default image Id for safety.
    j['defaultImageName'] = getImageName(tenantId, j['defaultImageId'])
    j.pop("defaultImageId", None)

    # Get rid of these instance/user/tenant-specific parameters to make it importable.
    j.pop("id", None)
    #j.pop("logoPath", None)
    j.pop("ownerUserId", None)
    j.pop("resource", None)
    for  port in j['servicePorts']:
        port.pop("id", None)
        port.pop("resource", None)

    return j

# Get the name of the service from the JSON
def getServiceName(serviceJson):
    serviceName = serviceJson['name']
    return(serviceName)

# Return a list of images used in the service
def getImagesFromService(serviceJson):
    images = []
    for image in serviceJson['images']:
        images.append(image['name'])

    return images

def getImages():
    tenantId = getTenantId()
    url = baseUrl+"/v1/tenants/"+tenantId+"/images"

    querystring = {}

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    response = s.request("GET", url, headers=headers, params=querystring, verify=False, auth=HTTPBasicAuth(username, apiKey))

    j = response.json()

    images = []
    for image in j['images']:
        images.append(image['name'])
    return images

def createImage(image):
    url = baseUrl+"/v1/tenants/"+tenantId+"/images"

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    image.pop('id', None)
    image.pop('resource', None)
    image.pop('systemImage', None)

    response = s.request("POST", url, headers=headers, data=json.dumps(image), verify=False, auth=HTTPBasicAuth(username, apiKey))
    newImage = response.json()
    logging.info("Image {} created with ID {}".format(newImage['name'], int(newImage['id'])))
    return int(newImage['id'])

def createRepo(repo):
    url = baseUrl+"/repositories/"

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    repo.pop('id', None)
    repo.pop('resource', None)

    response = s.request("POST", url, headers=headers, data=json.dumps(repo), verify=False, auth=HTTPBasicAuth(username, apiKey))
    newRepo = response.json()
    logging.info("Repo {} created with ID {}".format(newRepo['displayName'], int(newRepo['id'])))
    return int(newRepo['id'])


# Import the service into a CloudCenter instance
def import_service(service):
    tenantId = getTenantId()
    serviceName = getServiceName(serviceJson = service)
    serviceId = getServiceId(tenantId = tenantId, serviceName = serviceName)
    service.pop("id", None)
    service.pop("ownerUserId", None)
    service.pop("resource", None)
    for  port in service['servicePorts']:
        port.pop("id", None)
        port.pop("resource", None)

    # Update all the imageIds in the service to match the ones in the instance that you're importing into.
    if len(service.get('images', [])) > 0:
        for image in service['images']:
            imageId = getImageId(tenantId, image['name'])
            if imageId:
                image['id'] = imageId
            else:
                logging.warn("Image {} not found. I will create it so that the service will import, but it will be UNMAPPED."
                      "You will have to create the worker if necessary and map it yourself.".format(image['name']))
                image['id'] = createImage(image)
        # Assume that key defaultImageName was properly inserted into the exported JSON, then use that to get correct
        # Image Id for the default Image.
        service['defaultImageId'] = getImageId(tenantId, service['defaultImageName'])

    # Create any respositories that are referenced by the service but not yet in the instance.
    if len(service.get('repositories', [])) > 0:
        repomap = {}
        for repo in service['repositories']:
            oldRepoId = repo['id']
            repoId = getRepoId(repo['displayName'])
            if repoId:
                repo['id'] = repoId
            else:
                print("Repo {} not found. I will create it so that the service will import, but can't promise it will be accessible or not.".format(repo['displayName']))
                repo['id'] = createRepo(repo)
            # Create a map of old repo IDs to new ones.
            repomap[str(oldRepoId)] = str(repo['id'])

        service_json = json.dumps(service)

        pattern = re.compile('|'.join(repomap.keys()))
        result = pattern.sub(lambda x: repomap[x.group()], service_json)

        service = json.loads(result)

    # Assume that key defaultImageName was properly inserted into the exported JSON, then use that to get correct
    # Image Id for the default Image.
    if 'defaultImageName' in service:
        service['defaultImageId'] = getImageId(tenantId, service['defaultImageName'])
    else:
        logging.warn("Your manifest file didn't have a defaultImageName key, as it would if exported from the instance "
              "using this tool. Therefore I'm not able to update the image ID to the one that matches your instance"
              ", which may be different than the one it came from. Funny image related things may happen.")

    # Upload Logo
    if args.logo:
        logofile = args.logo
        headers = {
            'accept': "*/*"
        }
        params = {
            "type": "logo"
        }
        url = baseUrl+"/v1/file"
        files = {'file': logofile}
        response = s.request("POST", url, files=files, params=params, headers=headers, verify=False, auth=HTTPBasicAuth(username, apiKey))
        # After uploading the image the response contains a temporary location for the logo which has to be placed into
        # the logoPath for the service. This gets change behind the scenes automatically to what it should be.
        j = response.json()
        logoPath = j['params'][0]['value']
        service['logoPath'] = logoPath

    logging.debug(json.dumps(service, indent=2))

    headers = {
        'x-cliqr-api-key-auth': "true",
        'accept': "application/json",
        'content-type': "application/json",
        'cache-control': "no-cache"
    }
    if serviceId:
        logging.info("Service ID: {} for service {} found in the CloudCenter instance.".format(serviceId, serviceName))
        if not args.overwrite:
            print("--overwrite not specified. Exiting")
            sys.exit()
        else:
            logging.info("--overwrite specified. Updating existing service.")
            url = baseUrl+"/v1/tenants/"+tenantId+"/services/"+serviceId
            service['id'] = serviceId
            response = s.request("PUT", url, headers=headers, data=json.dumps(service), verify=False, auth=HTTPBasicAuth(username, apiKey))
            logging.debug(json.dumps(response.json(), indent=2))

    else:
        if not args.logo:
            logging.critical("You must specify a logo file for new services. Use the -l switch.")
            exit(1)
        logging.info("Service ID for service {} not found. Creating".format(serviceName))
        url = baseUrl+"/v1/tenants/"+tenantId+"/services/"
        response = s.request("POST", url, headers=headers, data=json.dumps(service), verify=False, auth=HTTPBasicAuth(username, apiKey))
        logging.debug(json.dumps(response.json(), indent=2))
        logging.info("Service {} created with Id {}".format(serviceName, response.json()['id']))

# TODO: Check for existing file and properly use the overwrite flag.
if args.debug:
    logging.basicConfig(level=args.debug)

if args.e:
    serviceName = args.e
    logoPath = "{}/assets/img/appTiers/{}/logo.png".format(baseUrl, serviceName)
    logoFile = "{}.png".format(serviceName)
    filename = "{serviceName}.servicemanifest".format(serviceName=serviceName)

    logging.info("Exporting service: {}".format(serviceName))
    j = getServiceManifest(serviceName)
    with open(filename, 'w') as f:
        json.dump(j, f, indent=4)
    logging.info("Service {} exported to {}".format(serviceName, filename))

    # Download logo too
    try:
        response = s.request("GET", logoPath)
        with open(logoFile, 'wb') as out_file:
            out_file.write(response.content)
        logging.info("Logo downloaded to {}".format(logoFile))

    except Exception as err:
        logging.error("Unable to download logo from {}: {}".format(logoPath, err))

if args.i:
    serviceJson = json.load(args.i)

    import_service(serviceJson)




