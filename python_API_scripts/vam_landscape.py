# goals: 
# 1) delete all objects currently in rijksmuseum
# 2) put all images from rijks in bucket
# 3) all images should have the correct object name
# 4) query all their data and save it into a json

import requests
import json
import pprint
import ibm_boto3
from ibm_botocore.client import Config
import boto3
import os
import random
import string
import urllib

cos_credentials = {
  "apikey": "gF_7Gjvqflf4TPju7t5lbgR4NB9dDAQ8EVwf1DmwKGDo",
  "cos_hmac_keys": {
    "access_key_id": "2b946807fa48404bb2cf98fb1987b97b",
    "secret_access_key": "c5a0f3b7a406621dd66847800dfb32eb98aecf35773528fe"
  },
  "endpoints": "https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints",
  "iam_apikey_description": "Auto-generated for key 2b946807-fa48-404b-b2cf-98fb1987b97b",
  "iam_apikey_name": "credentials",
  "iam_role_crn": "crn:v1:bluemix:public:iam::::serviceRole:Manager",
  "iam_serviceid_crn": "crn:v1:bluemix:public:iam-identity::a/f8a68e33cf3f4b72bf16e2d2827a16c5::serviceid:ServiceId-dc98af04-3ddb-4f94-9c22-7b2744342cd1",
  "resource_instance_id": "crn:v1:bluemix:public:cloud-object-storage:global:a/f8a68e33cf3f4b72bf16e2d2827a16c5:cbb6b174-e693-43b3-ba00-eff5c448394d::"
}

service_endpoint = 'https://s3.private.us-east.cloud-object-storage.appdomain.cloud'

cos_client = boto3.client('s3', 
                          endpoint_url = service_endpoint, 
                          aws_access_key_id=cos_credentials["cos_hmac_keys"]["access_key_id"], 
                          aws_secret_access_key=cos_credentials["cos_hmac_keys"]["secret_access_key"])

# Return all buckets in your COS instance
def get_all_buckets(cos_client):
    response = cos_client.list_buckets()
    allbuckets = []
    for bucket in response['Buckets']:
        allbuckets.append(bucket['Name'])
    return allbuckets

# Return all the objects in a COS bucket
def get_objects_in_bucket(cos_client,bucket_name):
    return cos_client.list_objects(Bucket=bucket_name)

# Create a unique COS bucket
def create_unique_bucket(cos_client, bucket_prefix):
    # Create a random 10 digit string
    # this random string increases the likelihood of the bucket name to be unique
    lst = [random.choice(string.ascii_letters + string.digits) for n in range(10)]
    random_string = "".join(lst).lower()
    bucket = "%s-%s" % (bucket_prefix, random_string)
    
    #print("creating bucket: ", bucket)
    cos_client.create_bucket(Bucket=bucket)
    print("Bucket %s created" % bucket)

# Upload objects to COS bucket
def upload_file_to_bucket(cos_client,f,bucket):
    file_name = os.path.basename(f)
    # print("Uploading %s to bucket: %s" % (file_name,bucket))
    cos_client.upload_file(Filename = f, Bucket = bucket, Key = file_name)

# Download objects from a URL 
def download_file_from_url(file_url, file_name, save_directory=None):
    # If save directory provided then don't delete local downloads
    working_directory = "temp_cos_files"
    if save_directory is not None:
        working_directory = save_directory
    os.makedirs(working_directory, exist_ok=True)

    # file_name = os.path.basename(file_url)
    # Delete file if present as perhaps download failed and file corrupted
    file_path = os.path.join(working_directory, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)

    file_path, _ = urllib.request.urlretrieve(file_url, file_path)
    # stat_info = os.stat(file_path)
    # print('Downloaded', file_path, stat_info.st_size, 'bytes.')
    
# Remove files from the specified directory in the local environment
def remove_files_from_dir(dir):
    for f in os.listdir(dir):
        file_path = os.path.join(dir, f)
        if os.path.exists(file_path):
            os.remove(file_path)


#############################################################JUPYTER NOTEBOOK FUNCTIONS################################################################

# initialize URL
URL = "http://www.vam.ac.uk/api/json/museumobject/search?"

#style of art we're looking for:

#parameters
PARAMS = {'q': "landscape", 'limit': 45, "offset": 0}

#open a JSON file to save image data
f = open("/root/UROP/vam_data.json", "w")
# f = open("/Users/anisha/UROP/vam_data.json", "w")

def getSpecificData(data):
    """
    Saves specifically queried data for each image to a complete json file
    """
    for imageDict in data['records']:
        objectNum = imageDict['fields']["object_number"]
        image_url = "http://www.vam.ac.uk/api/json/museumobject/" + objectNum
        r = requests.get(url = image_url)
        try:
            data = r.json()
            json.dump(data, f)
        except:
            print(objectNum)

def downloadUploadFromURL(data):
    """
    Helper function to take a dictionary and download/upload the images from
    the URLs that are in the dictionary  (one dict within the dict for each image)
    Downloads them then uploads them to the specified bucket
    """
    working_dir = "vam"
    # list of dictionaries
    for imageDict in data['records']:
        # I want to download and upload the image, but
        # also query each object number for specific info
        url_id = imageDict['fields']["primary_image_id"]
        objectNum = imageDict['fields']["object_number"]
        getSpecificData(objectNum)
        if url_id is not None:
            try:
                url = "http://media.vam.ac.uk/media/thira/collection_images/" + url_id[:6] + "/" + url_id + ".jpg"

                download_file_from_url(url, url_id, save_directory=working_dir)
                file_path = os.path.join(working_dir, url_id)
                
                upload_file_to_bucket(cos_client, file_path, "rijksmuseum")
            except:
                print("Something went wrong")

    remove_files_from_dir(working_dir) 

def putDirectlyInBucket(data):
    
    working_dir = "/mnt/victoria-and-albert"

    for imageDict in data['records']:
        # I want to download and upload the image, but
        # also query each object number for specific info
        # getSpecificData(imageDict['objectNumber'])
        try:
            url_id = imageDict['fields']["primary_image_id"]
            url = "http://media.vam.ac.uk/media/thira/collection_images/" + url_id[0:6] + "/" + url_id + ".jpg"
            file_name = url_id
            download_file_from_url(url, file_name, save_directory=working_dir)                
        except:
            print("Something went wrong")


def addType100():
    """
    Helper function to iterate through the number of pages, requesting the images matching that data
    calls downloadUpload
    """

    while PARAMS['offset'] < 25111:
        r = requests.get(url = URL, params = PARAMS)
        data = r.json()
        # putDirectlyInBucket(data)
        getSpecificData(data)
        # deleteObjects(data)
        PARAMS['offset'] += 45
        print(PARAMS['offset'])

def deleteObjects(data):
    # add landscape back in as a param
    delete_request = {"Objects": []}
    for imageDict in data['artObjects']:
        # I want to download and upload the image, but
        # also query each object number for specific info
        if imageDict['hasImage']:
            try:
                url = imageDict['webImage']['url']
                to_delete_filename = os.path.basename(url)
                delete_request["Objects"].append({"Key": to_delete_filename})
            except:
                print(imageDict)
    try:
        cos_client.delete_objects(Bucket='rijksmuseum', Delete=delete_request)
    except:
        print("eh")


addType100()

f.close()




