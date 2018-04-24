import os
import argparse
import glob
import json
import sys
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET


WEBDAV_STATUS_CODE = { 
  'OK'                  : 200,
  'CREATED'             : 201,
  'NO_CONTENT'          : 204,
  'MULTI_STATUS'        : 207,
  'NOT_FOUND'           : 404,
  'METHOD_NOT_ALLOWED'  : 405,
  'PRECONDITION_FAILED' : 412,
  'REQUEST_URI_TOO_LONG': 414,
  'UNPROCESSABLE_ENTITY': 422,
  'LOCKED'              : 423,
  'FAILED_DEPENDENCY'   : 424,
  'INSUFFICIENT_STORAGE': 507,
}

class upload_in_chunks(object):
	def __init__(self, filename, chunksize=1 << 13):
		self.filename = filename
		self.basename = os.path.basename(filename)
		self.chunksize = chunksize
		self.totalsize = os.path.getsize(filename)
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
				sys.stderr.write("\r"+self.basename+": {percent:3.0f}%".format(percent=percent))
				yield data

	def __len__(self):
		return self.totalsize

class IterableToFileAdapter(object):
    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.length = len(iterable)

    def read(self, size=-1):
        return next(self.iterator, b'')

    def __len__(self):
        return self.length

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

parser = argparse.ArgumentParser(description='Box.com python client',add_help=True)

group = parser.add_mutually_exclusive_group(required=False)

group.add_argument('--upload', action='store_true')
group.add_argument('--list', action='store_true')

parser.add_argument('--files', metavar='<file>', type=str, nargs='+',
					help='files to be uploaded')
parser.add_argument('-c', "--config", metavar='<config_file>', help="Config file")
args = parser.parse_args()

conf_file = os.path.expanduser("~")+"/.boxpy_conf"
if args.config != None:
	conf_file = args.config

user_config = None
with open(conf_file) as configjson:
	user_config = json.loads(configjson.read())

if args.upload == True:
	if args.files == None:
		print "Error: No files to be uploaded"
		sys.exit(1)

	for fil in args.files:
		reg_match_files = glob.glob(fil)
		for match_file in reg_match_files:
			if user_config != None:
				uname = user_config['users'][user_config['default']]['username']
				passwd = user_config['users'][user_config['default']]['password']
				url = "https://dav.box.com/dav/"+os.path.basename(match_file)
				it = upload_in_chunks(match_file, 10)
				r = requests.put(url, data=IterableToFileAdapter(it), auth=HTTPBasicAuth(uname, passwd))
			else:
				print "Error: User config not found"
				sys.exit(1)

elif args.list == True:
	if user_config == None:
		print "Error: User config not found"
		sys.exit(1)

	_session = requests.Session()
	uname = user_config['users'][user_config['default']]['username']
	passwd = user_config['users'][user_config['default']]['password']
	_session.auth = (uname, passwd)

	_response = _session.request('PROPFIND', "https://dav.box.com/dav/")
	if _response.status_code == WEBDAV_STATUS_CODE['MULTI_STATUS']:
		resp_root = ET.fromstring(_response.text)
		for resp in resp_root.iter('{DAV:}response'): 
			print resp.find('{DAV:}href').text + " (" + sizeof_fmt(int(resp.find('{DAV:}propstat').find('{DAV:}prop').find('{DAV:}getcontentlength').text)) + ")"
	else:
		print "Error: Unable to process request"
		sys.exit(1)
else:
	parser.print_help(sys.stderr)
	sys.exit(1)