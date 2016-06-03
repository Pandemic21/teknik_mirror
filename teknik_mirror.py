import praw
import requests
import json
import time
from mimetypes import MimeTypes


def download_reddit_image(url):
	try:
		response = requests.get(url.replace('http:','https:'), stream=True)
		f = open("image." + url.split('.')[3], 'wb')
		f.write(response.content)
		f.close()
		return True
	except Exception as e:
		gen_log("Error downloading image. URL: " + url + ", exception: " + str(e))
		return False


def upload_to_teknik(image_path):
	try:
		url = 'https://api.teknik.io/v1/Upload'
		files = {"file": open(image_path, 'rb')}
		params = {"saveKey": "true", "encrypt": "true", "contentType": mime.guess_type(image_path)}
		resp = requests.post(url, params=params, files=files)
		return json.loads(resp.text)['result']['url']
	except Exception as e:
		gen_log("Error uploading image. Exception: " + str(e))
		return None

def is_already_done(post_id):
	for done in already_done:
		if done == post_id:
			return True
	return False


def gen_log(data):
	f = open(LOGFILE, 'a')
	datetime =  str(time.strftime("%Y/%m/%d")) + " " + str(time.strftime("%H:%M:%S"))
	f.write(datetime + ": " + str(data) + "\n")
	f.close()
	print datetime + ": " + str(data)



### MAIN ##############################################################
# bot username
USERNAME = ''
# bot password
PASSWORD = ''
# file to which events are logged
LOGFILE = 'upload_mirror.log'
# multireddit name of whitelisted subreddits
MULTI_NAME = ''
# text with which bot replies to submissions after mirroring on teknik
REPLY_TEXT = "Here is a Teknik mirror, in case i.redd.it isn't working for mobile users:\n\n"
# time (in seconds) bot waits before searching for new submissions
SLEEP_TIME = 10

r = praw.Reddit("Teknik mirror by /u/Pandemic21")
r.login(USERNAME,PASSWORD,disable_warning=True)
mime = MimeTypes()
multi = r.get_multireddit(r.get_redditor(USERNAME), MULTI_NAME)
already_done = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
done_index = 0

while 1:
	#search whitelisted subreddits
	for post in multi.get_new(limit=20):
		#if it's not i.redd.it, skip it
		if not post.domain == 'i.redd.it':
			continue
		
		#check if we already mirrored it
		if is_already_done(post.id):
			gen_log("Found " + post.permalink + ", but it's already mirrored")
			continue

		#add post to already_done
		already_done[done_index] = post.id
		if done_index > len(already_done): done_index = 0
		else: done_index = done_index + 1

		#attempt to download and upload image
		complete = download_reddit_image(post.url)
		teknik_url = None

		if complete:
			gen_log("Found " + post.permalink + ", download successful, uploading to Teknik...")
			teknik_url = upload_to_teknik("image." + post.url.split('.')[3])
		else: 
			gen_log("Found " + post.permalink + ", download unsuccessful")
			continue
		if teknik_url is None:
			gen_log("Error uploading to tekik, URL is None") 
			continue
		
		#you can mess with this, teknik_url is the URL to the teknik mirror
		post.add_comment(REPLY_TEXT + teknik_url)

	#search mail for mentions
	unread = r.get_unread()
	for mail in unread:
		if not mail.subject == "username mention":
			mail.mark_as_read()
			continue
		post = r.get_submission(submission_id=mail.context.split('/')[4])
		if not post.domain == 'i.redd.it':
			gen_log("Request for mirror of " + post.permalink + ", but domain is " + post.domain)
			mail.mark_as_read()
			continue
		gen_log("Request for mirror of " + post.permalink + " by " + str(mail.author))

		complete = download_reddit_image(post.url)
		teknik_url = None

		if complete:
			gen_log(post.permalink + " download successful, uploading to Teknik...")
			teknik_url = upload_to_teknik("image." + post.url.split('.')[3])
		else: 
			gen_log(post.permalink + " mirror request download unsuccessful")
			mail.mark_as_read()
			continue
		if teknik_url is None:
			gen_log("Error uploading to tekik, URL is None") 
			mail.mark_as_read()
			continue

		mail.reply(REPLY_TEXT + teknik_url)
		gen_log("Mirror request completed successfully")
		mail.mark_as_read()

	gen_log("Cycle complete, sleeping")
	time.sleep(SLEEP_TIME)
