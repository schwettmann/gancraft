
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
URL = "https://api.harvardartmuseums.org/object"


#parameters
PARAMS = {'apikey': "10142270-04b8-11ea-b4a0-a94e03732016", "keyword": "landscape", "size": 100, "hasimage": 1}

#open a JSON file to save image data
# f = open("/root/UROP/harvard_data.json", "w")
f = open("/Users/anisha/UROP/harvard_data.json", "w")

def getSpecificData(objectNum):
    """
    Saves specifically queried data for each image to a complete json file
    """
    image_url = URL + "/" + str(objectNum) + "?apikey=10142270-04b8-11ea-b4a0-a94e03732016"
    r = requests.get(url = image_url)
    try:
        data = r.json()
        json.dump(data, f)
    except:
        print("getSpecificData: ", objectNum)


def putDirectlyInBucket(data):
    
    # working_dir = "/mnt/harvard-art-museum"
    working_dir = "rijksmuseum"
    base_url = "https://ids.lib.harvard.edu/ids/iiif/"
    image_addon = "/full/full/0/default.jpg"

    for imageDict in data['records']:
        # I want to download and upload the image, but
        # also query each object number for specific info
        object_id = str(imageDict['objectid'])
        #getSpecificData(object_id)
        try:
            url = base_url + object_id + image_addon
            print(url)
            file_name = object_id
            download_file_from_url(url, file_name, save_directory=working_dir)                
        except:
            print("putDirectlyInBucket: ", object_id)


def addType100():
    """
    Helper function to iterate through the number of pages, requesting the images matching that data
    calls downloadUpload
    """
    r = requests.get(url = URL + "?", params = PARAMS)
    data = r.json()
    while "next" in data["info"].keys():
        putDirectlyInBucket(data)
        r = requests.get(url = data["info"]["next"])



addType100()

f.close()




