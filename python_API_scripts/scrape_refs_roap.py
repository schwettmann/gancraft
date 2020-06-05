import csv
import json
from bs4 import BeautifulSoup
import urllib.request 
import urllib.parse
import requests
import ibm_boto3
from ibm_botocore.client import Config
import boto3
import os
import random
import string
import time
from multiprocessing import Pool
import os.path
from os import path

success_count = 0

def get_credentials(credential_file):
    """
    Gets the cloud object storage credentials from a file that must be manually saved in the same directory.
    """
    with open(credential_file) as json_file:
        creds = json.load(json_file)
    
    return creds

#############1 of 3: Insert path to your locally saved copy of the cos credentials#################
# cos_credentials = get_credentials('cos_credentials.json')
cos_credentials = get_credentials('/root/UROP/cos_credentials.json')

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
    try:
        file_path, _ = urllib.request.urlretrieve(file_url, file_path)
    except Exception as inst:
        if str(inst) == "HTTP Error 403: Forbidden":
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            file_path, _ = urllib.request.urlretrieve(file_url, file_path)
        else:
            raise ValueError("This is broken")
    # stat_info = os.stat(file_path)
    # print('Downloaded', file_path, stat_info.st_size, 'bytes.')
    
# Remove files from the specified directory in the local environment
def remove_files_from_dir(dir):
    for f in os.listdir(dir):
        file_path = os.path.join(dir, f)
        if os.path.exists(file_path):
            os.remove(file_path)


#############################################################JUPYTER NOTEBOOK FUNCTIONS################################################################

def make_search_terms():
    """
    Helper function to parse csv file and get ref urls, painting names and museum names
    """
    paintings_to_parse = []
    with open('/root/UROP/merged_data.csv') as csv_file:
    ############## 2 of 3: CHANGE LOCATION TO THE NAME OF THE CSV WITH REF URLS AND ITEM INFO#########################
    # with open('/Users/anisha/UROP/merged_data.csv') as csv_file:

        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                print(f'Column names are {", ".join(row)}')
                line_count += 1
            elif line_count > 0:
                ########### EDIT indices based on how the new csv is structured!!!####################
                painting = [row[4], row[8], row[12]]
                line_count += 1
                paintings_to_parse.append(painting)
                # if "https://collections.gilcrease.org" in painting[0]:
                #     print (painting)

            else:
                line_count += 1
            

    print(f'Processed {line_count} lines.')
    return paintings_to_parse


def get_image_from_html(data):
    """
    Helper function to take the ref_url and get first image from html of a museum website
    params:
        data: [ref_url, painting name, museum_name]
    """
    image_name = data[1]
    museum = data[2]
    user_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.0.7) Gecko/2009021910 Firefox/3.0.7'
    url = data[0]
    headers = {'User-Agent': user_agent, }
    request = urllib.request.Request(url, None, headers)
    html = urllib.request.urlopen(request).read()
    try:
        soup = BeautifulSoup(html,'html.parser')
    except:
        print("Could not parse HTML response")

    try:
        # image_data = soup.find_all('li', {"data-idx": "1"})
        body = soup.find('body')
        images = (body.find_all('img'))
        # print(images)
        
        for i in range(len(images)):
            image_link = "uninitialized"
            try:
                if museum == "Museum of Modern Art":
                    image_link = "http://www.moma.org" + images[i]['src'] 
                elif museum == "Tate" and i in (0, 1):
                    continue
                elif museum == "Philadelphia Museum of Art" and i in (0, 1):
                    continue
                elif museum == "Cincinnati Art Museum" and i in (0,1):
                    continue
                elif museum == "Städel Museum":
                    image_link = "https://sammlung.staedelmuseum.de/" + images[i]['src']
                elif museum == "San Francisco Museum of Modern Art" and i == 0:
                    continue
                elif museum == 'National Galleries of Scotland' and i in range(0, 10):
                    continue
                
                elif museum == "National Gallery of Australia":
                    if i in (0,1):
                         continue
                    else:
                        image_link = "https://artsearch.nga.gov.au" + images[i]['src']
                
                elif "https://skd-online-collection.skd.museum/" in url:
                    image_link = "https://skd-online-collection.skd.museum/" + images[i]['src']

                elif "https://www.ngv.vic.gov.au/" in url:
                    image_link = "https:" + images[i]['src']
                    print(image_link)

                else:
                    image_link = images[i]['src']
                    if image_link[0:2] == "//":
                        image_link += "https:"
                
                success = download_image((image_link, image_name, museum))
                
                if success:
                    success_count += 1
                    return True

                else:
                    continue
            except:
                pass

    except:
        pass
    
    return False
        
    
def download_image(image_info):
    """
    Helper function to download the image into the desired directory
    """
    #################### 3 of 3:CHANGE TO CORRECT DIRECTORY!!!#################
    working_dir = "/mnt/restofallpaintings"
    # working_dir= "/Users/anisha/UROP/images"
    url = image_info[0]
    file_name = image_info[1] + ".jpg"
    try:
        file_path = working_dir + "/" + file_name
        if not path.exists(file_path):
            download_file_from_url(url, file_name, save_directory=working_dir)  
        # with open('/root/UROP/metadata.csv', 'a', newline='') as meta:
        #     writer = csv.writer(meta)
        #     writer.writerow([query, url])
        return True
    except:
        print("download_img failed: " + url)

        return False

def top_fn(url_name_museum):
    if success_count % 1000 == 0:
        print("##############################################################")
        print(success_count)
        print("##############################################################")
    try:
        ref_url = url_name_museum[0]
        name = url_name_museum[1]
        museum = url_name_museum[2]
        get_image_from_html((ref_url, name, museum))

    except:
        print("top fn failed: " + ref_url)



def run():
    pool = Pool()
    search_terms = make_search_terms()
    pool.map(top_fn, search_terms)

# print(len(terms))
# download_image(terms[0])
run()
# download_image("test")
# get_image_from_html(['https://collections.gilcrease.org/object/012247', "elk man", ""])
# make_search_terms()
# get_ref_from_wiki("http://www.wikidata.org/entity/Q66016628")