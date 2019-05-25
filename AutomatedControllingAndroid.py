import uiautomator2 as u2
import time
import glob
import os
import re
import sqlite3
from aip import AipOcr


class OCR_detect:
    # construct funtion of the ocr
    def __init__(self, imgpath, sample_size):
        '''
        :param imgpath: the folder path of screenshots
        :param sample_size: the number of screenshots
        '''
        self.imgpath = imgpath
        self.sample_size = sample_size
        self.config = {
                'appId': '',# Your id
                'apiKey': '',# Your api key
                'secretKey': ''# Your secret key
        }
        self.client = AipOcr(**self.config)

    def get_file_content(self, img):
        with open(img, 'rb') as f:
            return f.read()

    def img_to_str(self, imgpath):
        '''
        :param imgpath: picture path
        :return: the result of scan a picture
        '''
        img = self.get_file_content(imgpath)
        res = self.client.basicGeneral(img)
        if 'words_result' in res:
            words = '\n'.join(w['words'] for w in res['words_result'])
            # print(words)
            return words

    def traverse_file(self, rootdir):
        '''
        :param rootdir: traverse a folder and get files
        :return: None
        '''
        ls = os.listdir(rootdir)
        for i in range(0, len(ls)):
            path = os.path.join(rootdir, ls[i])
            if os.path.isfile(path) and (path.endswith('.jpg') or path.endswith('.png')):
                os.remove(path)

    def getname_title_region(self, string):
        '''
        This funtion a used to process the screen's first block and get the
        users' name, title and their region
        :param string:
        :return:
        '''
        try:
            name = ''
            tmpstr = string.strip('\n')
            # print(type(tmpstr))
            # block = tmpstr.partition('猜您认识')[2].partition('忽略')[0]
            if tmpstr.find('<猜您认识') >=0:
                block = tmpstr.partition('<猜您认识')[2].partition('忽略')[0]
            elif tmpstr.find('猜您认识') >=0:
                block = tmpstr.partition('猜您认识')[2].partition('忽略')[0]
            res = block.split('\n')
            title = ''
            # print(res)
            name = res[1]
            region = ''
            for item in res[2:]:
                if item.find('·') >= 0:
                    region = item.partition('·')[0]
                else:
                    # if title == 'Not fill':
                    #     title = ''
                    title = title + item.strip('\n')
            if region.find('…') >= 0:
                region = region[:region.find('…')]
            if title.find('…') >= 0:
                title = title[:title.find('…')]
            return name, title, region
        except Exception as e:
            print(e)

    def get_experiece(self, string):
        ans = string.strip('\n')
        exper = ans.partition('最新经历')[2].partition('教育经历')[0]
        try:
            workpattern = r'其他\d+个职位'
            t = re.search(workpattern, exper)
            exper = ans.partition('最新经历')[2].partition(t.group())[0]
        except AttributeError as e:
            print('')
        res = exper.split('\n')
        res = [x.strip() for x in res if x.strip() != '']
        ls = []
        for i in range(len(res)):
            if res[i].find('查看完整档案') >= 0 or (res[i].find('且') >= 0 and res[i].split('且')[1] == ''):
                continue
            elif res[i].find('且') >= 0 and res[i].split('且')[1] != '':
                ls.append(res[i].split('且')[1].strip(' '))
            else:
                ls.append(res[i].strip(' '))
        return ls

    def get_edu(self, string):
        ans = string.strip('\n')
        edu = ans.partition('教育经历')[2].partition('查看完整档案')[0]
        try:
            schpattern = r'其他\d+个学校'
            s = re.search(schpattern, edu)
            edu = ans.partition('教育经历')[2].partition(s.group())[0]
        except AttributeError as e:
            print('')
        res = edu.split('\n')
        res = [x.strip() for x in res if x.strip() != '']
        ls = []
        for i in range(len(res)):
            if res[i].find('查看完整档案') >= 0 or (res[i].find('且') >= 0 and res[i].split('且')[1] == '') or (
                    res[i].find('回') >= 0 and res[i].split('回')[1] == ''):
                continue
            elif res[i].find('且') >= 0 and res[i].split('且')[1] != '':
                ls.append(res[i].split('且')[1].split("\'")[0])
            elif res[i].find('回') >= 0 and res[i].split('回')[1] != '':
                ls.append(res[i].split('回')[1].split("\'")[0])
            else:
                ls.append(res[i].split("\'")[0])
        return ls

    def run(self):
        conn = sqlite3.connect('persons.db')
        # create table
        try:
            cursor = conn.cursor()

            cursor.execute('create table if not exists person (id varchar(5) primary key, '
                           'name varchar(20), headline varchar(50), region varchar(10))')

            cursor.execute('create table if not exists experience (id varchar(5) primary key, '
                           'title varchar(50), org varchar(50), p_id varchar(5),foreign key (p_id) '
                           'references person(id))')

            cursor.execute('create table if not exists education (id varchar(5) primary key, school varchar(50), '
                           'major varchar(50), p_id varchar(5),foreign key (p_id) references person(id))')

        except Exception as e:
            print(e)
        finally:
            try:
                cursor.execute('delete from person')
                cursor.execute('delete from experience')
                cursor.execute('delete from education')
            except Exception as e:
                print(e)
            finally:
                cursor.close()
            conn.commit()
            conn.close()

        # insert records
        eduid = 0
        experid = 0
        for i in range(self.sample_size):
            try:
                tmp = self.img_to_str(self.imgpath+'\\%s.jpg'%i)
                conn = sqlite3.connect('persons.db')
                edu = self.get_edu(tmp)
                exper = self.get_experiece(tmp)
                name, title, region = self.getname_title_region(tmp)
                print(name + ',' + title + ',' + region)
                print(exper)
                print(edu)
                ID = str(i)
                person_query = 'insert into person values (\'%s\',\'%s\',\'%s\',\'%s\')' % (ID, name, title, region)

                try:
                    cursor = conn.cursor()
                    cursor.execute(person_query)
                    print('insert name, title, region, ok')
                    major = ''
                    school = ''
                    exper_title = ''
                    org = ''
                    if len(edu) == 0:
                        edu_query = 'insert into education values(\'%s\',\'%s\',\'%s\',\'%s\')' % (
                        str(eduid), '', '', ID)
                        cursor.execute(edu_query)
                        eduid += 1
                    elif len(edu) == 1:
                        edu_query = 'insert into education values (\'%s\',\'%s\',\'%s\',\'%s\')' % (
                        str(eduid), edu[0], '', ID)
                        cursor.execute(edu_query)
                        eduid += 1
                    elif len(edu) % 2 == 0 and len(edu) != 0:
                        cnt = 0
                        for idx in range(len(edu)):
                            if idx % 2 == 0:
                                school = edu[idx]
                                cnt += 1
                            else:
                                major = edu[idx]
                                cnt +=1
                            if cnt == 2:
                                edu_query = 'insert into education values (\'%s\',\'%s\',\'%s\',\'%s\')' % (
                                    str(eduid), school, major, ID)
                                cursor.execute(edu_query)
                                eduid += 1
                                cnt = 0
                    elif len(edu) % 2 == 1 and len(edu) != 0:
                        cnt = 0
                        for idx in range(len(edu)):
                            if idx % 2 == 0:
                                school = edu[idx]
                                cnt += 1
                            else:
                                major = edu[idx]
                                cnt += 1
                            if cnt == 2:
                                edu_query = 'insert into education values (\'%s\',\'%s\',\'%s\',\'%s\')' % (
                                    str(eduid), school, major, ID)
                                cursor.execute(edu_query)
                                eduid += 1
                                break
                    print('insert edu ok')
                    if len(exper) == 0:
                        exper_query = 'insert into experience values (\'%s\',\'%s\',\'%s\',\'%s\')' % (
                        str(experid), '', '', ID)
                        cursor.execute(exper_query)
                        experid += 1
                    elif len(exper) == 1:
                        exper_query = 'insert into experience values (\'%s\',\'%s\',\'%s\',\'%s\')' % (str(experid),
                                                                    exper[0], '', ID)
                        cursor.execute(exper_query)
                        experid += 1
                    elif len(exper)>6:
                        cnt = 0
                        for idx in range(6):
                            if idx % 2 ==0:
                                exper_title = exper[idx]
                                cnt += 1
                            else:
                                org = exper[idx]
                                cnt += 1
                            if cnt == 2:
                                exper_query = 'insert into experience values (\'%s\',\'%s\',\'%s\',\'%s\')' % (
                                    str(experid), exper_title, org, ID)
                                cursor.execute(exper_query)
                                experid += 1
                                cnt = 0
                    elif len(exper) % 2 == 0 and len(exper) != 0 and len(exper)<=6:
                        cnt = 0
                        for idx in range(len(exper)):
                            if idx % 2 == 0:
                                exper_title = exper[idx]
                                cnt += 1
                            else:
                                org = exper[idx]
                                cnt += 1
                            if cnt == 2:
                                exper_query = 'insert into experience values (\'%s\',\'%s\',\'%s\',\'%s\')' % (
                                    str(experid), exper_title, org, ID)
                                cursor.execute(exper_query)
                                experid += 1
                                cnt = 0
                    elif len(exper) % 2 == 1 and len(exper) != 0 and len(exper)<=6:
                        cnt = 0
                        for idx in range(len(exper)):
                            if idx % 2 == 0:
                                exper_title = exper[idx]
                                cnt += 1
                            else:
                                org = exper[idx]
                                cnt += 1
                            if cnt == 2:
                                exper_query = 'insert into experience values (\'%s\',\'%s\',\'%s\',\'%s\')' % (
                                    str(experid), exper_title, org, ID)
                                cursor.execute(exper_query)
                                experid += 1
                                break
                    print('insert exper ok')
                except Exception as e:
                    eduid += 1
                    experid += 1
                    print(e)
                finally:
                    cursor.close()
                    conn.commit()
                    conn.close()
            except Exception as e:
                print(e)
        self.traverse_file(self.imgpath)

if __name__ == '__main__':

    d = u2.connect('c8db0f7f')  # alias for u2.connect_usb('123456789F')
    print(d.info)
    while True:
        if d.toast.get_message(5.0):
            times = int(d.toast.get_message(5.0).split(' ')[1])
            break
    time.sleep(2)
    d.app_start("com.linkedin.android")
    time.sleep(4)
    d(text='人脉', className='android.widget.TextView').click()
    time.sleep(2)
    d(resourceId='com.linkedin.android:id/mynetwork_pymk_name', className='android.widget.TextView').click()
    for i in range(times):
        time.sleep(1)
        d(scrollable=True).scroll.toEnd()
        time.sleep(0.5)
        d.screenshot('screenshot/' + str(i) + '.jpg')
        d(scrollable=True).scroll.horiz.forward()
    time.sleep(1)
    d.app_start("uk.ac.lancs.myapplication")
    time.sleep(1)
    d.toast.show("Profiles collected successfully!", 2.0)
    time.sleep(2)
    d.toast.show("Now start scanning screenshots!", 2.0)

    files = glob.glob(os.getcwd() + '\\screenshot\\*.jpg')
    ocr = OCR_detect(os.getcwd() + '\\screenshot', times)
    ocr.run()

    d.push("persons.db", "/sdcard/Download/")
    d.press("back")
    d.toast.show("Now you can query information collected from LinkedIn!", 3.0)


