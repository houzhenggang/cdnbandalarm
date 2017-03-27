# -*- coding: utf-8 -*-
"""
@version: 0.1
@author: Pei5
@license: Apache Licence
@contact: demingan@gmail.com
@site: http://www.tvmining.com
@software: PyCharm
@file: monitorcdnband.py
@create_time: 2016/08/23 上午10:09
@description:定时获取cdn后台带宽情况，根据设定值发送报警邮件
"""

import urllib
import urllib2
import json
import time
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE,formatdate
from email import encoders
from email.header import Header

import os

import sys
reload(sys)
sys.setdefaultencoding('utf8')


class httphelper():
    def __init__(self):
        self.add_header = {"User-Agent" : "tvm-monitor"}

    def geturl(self, _url, _timeout):
        try:
            request = urllib2.Request(url=_url, headers=self.add_header)
            response = urllib2.urlopen(request, timeout=_timeout)
            return response.read()
        except urllib2.HTTPError, e:
            print e.code
        except urllib2.URLError, e:
            print "Error Reason:", e.reason
        return None


user = "xxxxx"
password = "yyyyy"
tokenurl = "http://www.a.com/open/getAccessToken?username=%s&password=%s"
bandurl = "http://www.b.com/openapi/open2/bandWidth/all?access_token=%s&startTime=%s&endTime=%s&group=d"
maxstay = 2*60*60
maxband = 5*1024
mail_info = {'name':'smtp.163.com','user':'xxxxxx','passwd':'xxxxxx'}
mail_sender = ("%s<xxxxxx@163.com>") % (Header('CDN带宽邮件中心','utf-8'),)
mail_to = ["xxxxx@tvmining.com"]
mail_title = "带宽警报"
mail_text = "CDN带宽超过预设警报值:%s mbps.持续时间:%s 分钟.共超过:%s 次."

def getband():
    totalbands = {}
    f_currtime = time.time()
    f_starttime = f_currtime - maxstay
    starttime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(f_starttime))
    endtime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(f_currtime))
    c_tokennul = tokenurl % (user, password)

    httph = httphelper()
    result = httph.geturl(c_tokennul, 10)
    if result is not None:
        token = json.loads(result)['access_token']
        c_bandurl = bandurl % (token, urllib.quote(starttime), urllib.quote(endtime))
        bands = httph.geturl(c_bandurl, 10)
        if bands is not None:
            j_bands = json.loads(bands)['data']
            for domain in j_bands:
                domain_bands = domain[u'\u670d\u52a1\u5e26\u5bbd']
                for band in domain_bands:
                    if totalbands.has_key(band['time']):
                        totalbands[band['time']] += float(band['value'])
                    else:
                        totalbands[band['time']] = float(band['value'])
            return totalbands
    return None


def checkband(_bands, _maxband):
    #连续超过警戒带宽次数
    i = 0
    #超过警戒带宽总次数
    j = 0
    times = list(_bands)
    times.sort()
    for t in times:
        if _bands[t] >= _maxband:
            i += 1
            j += 1
        else:
            i = 0
    return (i,j)


def ismail(_times, _maxstay):
    totaltimes = _maxstay/300 - 4 - 5
    alarmtimes = 2*5
    if _times[0] >= alarmtimes or _times[1] >= totaltimes:
        #发送邮件
        return 1
    else:
        return 0

def send_mail(server, fro, to, subject, text, files=[], format='plain'):
    assert type(server) == dict
    assert type(to) == list
    assert type(files) == list
    if isinstance(text,unicode):
        text = str(text)

    msg = MIMEText(text,format,'utf-8')
    msg['From'] = fro
    if not isinstance(subject,unicode):
        subject = unicode(subject)
    msg['Subject'] = subject
    msg['To'] = COMMASPACE.join(to) #COMMASPACE==', '
    msg['Date'] = formatdate(localtime=True)
    msg["Accept-Language"]="zh-CN"
    msg["Accept-Charset"]="ISO-8859-1,utf-8"

    for file in files:
        part = MIMEBase('application', 'octet-stream') #'octet-stream': binary data
        part.set_payload(open(file, 'rb'.read()))
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(file))
        msg.attach(part)

    try:
        import smtplib
        smtp = smtplib.SMTP(server['name'])
        print smtp.login(server['user'], server['passwd'])
        print smtp.sendmail(fro, to, msg.as_string())
        smtp.close()
        return "ok"
    except Exception, e:
        return e.message



if __name__ == "__main__":
    #程序每2小时检测一次.
    bands = getband()
    print bands
    if bands is not None:
        times = checkband(bands, maxband)
        print times
        if ismail(times, maxstay) > 0:
            send_mail(mail_info, mail_sender, mail_to, mail_title, mail_text % (str(maxband), str(times[0]*5), str(times[1])), files=[])

