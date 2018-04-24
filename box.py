import os
import argparse
import glob
import json
import sys
import requests
from requests.auth import HTTPBasicAuth

class upload_in_chunks(object):
	def __init__(self, filename, chunksize=1 << 13):
		self.filename = filename
		self.chunksize = chunksize
		self.totalsize = os.path.getsize(self.filename)
		self.readsofar = 0

	def __iter__(self):
		with open(self.filename, 'rb') as file:
			while True:
				data = file.read(self.chunksize)
				if not data:
					sys.stderr.write("\n")
					break
				self.readsofar += len(data)
				percent = self.readsofar * 1e2 / self.totalsize
				sys.stderr.write("\r"+self.filename+": {percent:3.0f}%".format(percent=percent))
				yield data

	def __len__(self):
		return self.totalsize

class IterableToFileAdapter(object):
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.length = len(iterable)

    def read(self, size=-1): # TBD: add buffer for `len(data) > size` case
        return next(self.iterator, b'')

    def __len__(self):
        return self.length

parser = argparse.ArgumentParser(description='Upload files to Box.com')
parser.add_argument('files', metavar='<.idl file>', type=str, nargs='+',
					help='list of files to be converted')
parser.add_argument('-c', "--config", help="Config file")
args = parser.parse_args()

conf_file = os.path.expanduser("~")+"/.boxpy_conf"
if args.config != None:
	conf_file = args.config

user_config = None
with open(conf_file) as configjson:
	user_config = json.loads(configjson.read())

for fil in args.files:
	reg_match_files = glob.glob(fil)
	for match_file in reg_match_files:
		if user_config != None:
			uname = user_config['users'][user_config['default']]['username']
			passwd = user_config['users'][user_config['default']]['password']
			url = "https://dav.box.com/dav/"+os.path.basename(match_file)
			it = upload_in_chunks(match_file, 10)
			r = requests.put(url, data=IterableToFileAdapter(it), auth=HTTPBasicAuth(uname, passwd))
				
