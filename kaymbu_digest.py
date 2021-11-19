#!/usr/bin/env python

##
# Kaymbu digest image downloader.
# Copyright 2018 Matthew F. Coates
# http://github.com/mattjackets
# See LICENSE.txt for license terms.
##
from dateutil import parser
import datetime
import imaplib
import email
import quopri
import re
from bs4 import BeautifulSoup
import requests
import config
import json
import pathlib
from mimetypes import guess_extension

def get_name_links_date(email_msg):
  email_message = email.message_from_string(email_msg)
  #matches=re.search(r'.*\s*([A-Z][a-z]+)\'s Digest from .* for (\d?\d\/\d?\d\/\d\d)',email_message['Subject'])
  #name=matches.group(1)
  #date=matches.group(2)
  name=email_message["From"].replace('<','').replace('>','').replace(' ','_')
  date=parser.parse(email_message["Date"])

  html_block=get_first_html_block(email_message)
  decoded_html_block=quopri.decodestring(html_block)
  fixed_html=""
  # Kaymbu emails contain invalid HTML, there is a closing html tag before the body, remove it and add it to the end
  try:
   fixed_html=decoded_html_block.decode('utf8').replace("</html>","",1)+"</html>\r\n"
  except:
   fixed_html=decoded_html_block
  soup=BeautifulSoup(fixed_html,'lxml')
  #soup=BeautifulSoup(decoded_html_block,'lxml')
  links=[]
  for moment_img_tag in soup.findAll('img',alt="Download this moment"):
    links.append(moment_img_tag.parent['href'])
  return (name,links,date)

def get_first_html_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_type() == 'text/html':
                return part.get_payload()
    elif email_message_instance.get_content_type() == 'text/html':
        return email_message_instance.get_payload()

###
# link should be a link to the image
# returns the file content
###
def get_photo(link):
  r=requests.get(link)
  if (r.status_code != 200):
    raise ValueError("Unsuccessful requesting photo(s). Code %d returned."%r.status_code)
  return r.content

def get_mail_connection(imap_server,mail_username,mail_password,mail_folder):
  mail = imaplib.IMAP4_SSL(imap_server)
  mail.login(mail_username,mail_password)
  mail.select(mail_folder,readonly=True)
  return mail

def get_new_digest_message_uids(mail):
  result,search_results=mail.uid('search',None,'(OR (FROM "cls5f7c712a3508b6012b598423@inbox.kaymbu.com") (FROM "cls5f7c71033edac901261e595f@inbox.kaymbu.com"))')
  message_uids=search_results[0].split()
  return message_uids

  
if __name__=="__main__":
  mail=get_mail_connection(config.imap_server,config.mail_username,config.mail_password,config.folder)
  message_uids=get_new_digest_message_uids(mail)
  print( "%d new kaymbu digest messages"%len(message_uids))
  pics = []
  for uid in message_uids:
    print("Starting work on message %s"%uid)
    #result,msg_data=mail.uid('fetch',uid,'(RFC822)')
    result,msg_data=mail.uid('fetch',uid,'(BODY.PEEK[])')
    if result != "OK":
      print( "Problem fetching message %s"%uid)
      continue
    #result,message=mail.uid('STORE', uid, '-FLAGS', '(\SEEN)')
    #if result != "OK":
    #  print "Problem setting message %s unseen"%uid
    anemail=msg_data[0][1].decode('utf-8')
    name,links,date=get_name_links_date(anemail)
    for link in links:
      pics.append([uid.decode('utf8'),name,str(date),link])
  now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
  pathlib.Path(f'pics/{now}').mkdir(parents=True, exist_ok=True)
  muids = []
  for m in message_uids:
    muids.append(m.decode('utf8'))
  with open(f'pics/{now}/uids.json','w') as f:
    json.dump(muids,f)
  with open(f'pics/{now}/urls.json','w') as f:
    json.dump(pics,f)
  for pic in pics:
    dt = pic[2].split(' ')[0].split('-')
    img_path = f'pics/{now}/{dt[0]}/{dt[1]}/{dt[2]}'
    pathlib.Path(img_path).mkdir(parents=True, exist_ok=True)
    r = requests.get(pic[3])
    img_name = r.url.split('?')[1].split('&')[0]
    ext = guess_extension(r.headers['content-type'])
    with open(f'{img_path}/{img_name}{ext}', 'wb') as f:
      f.write(r.content)
    print(r.url)
    print(f'{img_name}{ext}')
    print(r.status_code)
    print(r.headers['content-type'])
    print(r.encoding)
