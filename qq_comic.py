# -*-coding:utf-8 -*-
#
# Created on 2016-10-14
#      __      __
#  -  /__) _  /__) __/
#  / / (  (/ / (    /
#                  /

import time
import json
import signal

import requests
from bs4 import BeautifulSoup
from selenium import webdriver

import gevent.monkey
gevent.monkey.patch_socket()
from gevent.queue import Queue

tasks = Queue()
results = Queue()

QQ_COMIC_URL = 'http://ac.qq.com'


def get_url(q):
    # 海贼王漫画
    url = 'http://ac.qq.com/Comic/comicInfo/id/505430'
    res = requests.get(url)
    soup = BeautifulSoup(res.content, 'lxml')
    span = soup.find_all('span', {'class': 'works-chapter-item'})
    for i, s in enumerate(span[:-1]):
        a = s.find('a')
        q.put_nowait({
            'order': i,
            'title': a.attrs.get('title').split(u'：')[-1],
            'url': '{}{}'.format(QQ_COMIC_URL, a.attrs.get('href'))
        })


def worker(name, driver):
    print 'Worker `{}` starting .....'.format(name)
    while not tasks.empty():
        t = tasks.get()
        driver.get(t.get('url'))
        t['pic'] = []
        try:
            for p in driver.execute_script("return window.PICTURE"):
                t['pic'].append(p.get('url'))
        except TypeError:
            print 'GET Pic Error -----------> `{}`'

        results.put(t)
        print 'Worker `{}` done a url --> `{}` --> `{}`'.format(name, t.get('url'), t.get('pic'))
    else:
        # 关闭driver
        try:
            driver.service.process.send_signal(signal.SIGTERM)
        except AttributeError:
            pass
        driver.quit()
        print 'Worker `{}` work is done'.format(name)


if __name__ == '__main__':
    start = time.time()
    print 'Start Time: {}'.format(start)

    # 生成所有的任务
    gevent.spawn(get_url, tasks).join()
    print 'Get All Task Done: {}'.format(time.time() - start)

    drivers = [webdriver.PhantomJS() for i in range(3)]

    # 生成worker, 完成任务
    gevent.joinall([gevent.spawn(worker, 'worker-{}'.format(i), drivers[i]) for i in range(3)])

    # 处理数据
    data = []
    while not results.empty():
        data.append(results.get())
    data.sort(key=lambda d: d.get('order'))

    # 写入文本
    with open('onepiece.txt', 'w+') as f:
        for d in data:
            f.write(json.dumps(d, ensure_ascii=False).encode('utf8') + '\n')

    # 获取时间
    print 'End Time: {}'.format(time.time())
    print 'Cost Time: {}(s)'.format(time.time() - start)