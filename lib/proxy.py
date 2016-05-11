#-*- coding: utf-8 -*
import urllib
import urllib2
import re
import time
import sys
import socket
import cPickle
import os

class proxy_info:
    def __init__(self, anonymous = None, type = None, ip = None, port = None, speed = None, conn_time = None):
        self.anonymous = anonymous
        self.type = type
        self.ip = ip
        self.port = port
        self.speed = speed
        self.conn_time = conn_time

def visit_url(url, retry_times = 3, timeout = 5):
    proxy_ua = {'User-Agent':'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36','Accept-Language':'zh-CN,zh;q=0.8'}
    proxy_url = urllib2.Request(url = url, headers = proxy_ua)
    times = 0
    error = None
    while True:
        try:
            response = urllib2.urlopen(proxy_url, timeout = timeout)
            html = response.read()
            print 'visit [DONE]'
            return html
        except socket.timeout, err:
            error = err
        except urllib2.HTTPError, err:
            error = err
        except urllib2.URLError, err:
            error = err
        except Exception, err:
            print 'error: %s' % repr(err)
            break

        if hasattr(error, 'reason'):
            print 'error: %s' % error.reason
        else:
            print 'error: %s' % repr(error)
        times += 1
        if times > retry_times:
            break

        time.sleep(1)
        print 'retry: %s' % times

    return None

def load_proxy(fname = 'proxy.info', force = False):
    if not os.path.exists(fname):
        return None

    # interval time must small than 10 min
    if not force and (time.time() - os.stat(fname).st_mtime) > 10 * 60:
        return None

    proxy_info = None

    with open(fname, 'r') as f:
        try:
            proxy_info = cPickle.load(f)
        except Exception, err:
            print err

    return proxy_info

def get_page_num(url):
    num = 0

    html = visit_url(url)
    if html != None:
        ret = re.search('>(\d+?)</a>\s*?<a class="next_page"', html)
        if ret != None:
            num = int(ret.group(1))

    return num

# just only for this url
def get_proxy(url = 'http://www.xici.net.co', fname = 'proxy.info', limit = 500):
    #fname = 'valid_proxy.info'
    retry_times = 5

    proxy_list = load_proxy(fname)
    if proxy_list != None:
        print 'load proxy from: %s' % fname
        return proxy_list

    proxy_list = []

    # just only for this url
    #zone_type = ['nn', 'nt', 'wn', 'wt', 'qq']
    #zone_type = ['nn', 'wn']
    zone_type = ['wn']

    # (IP, PORT, [HTTP | HTTPS | socket3/4])
    pattern = re.compile('''<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>.*?<td>(\d+?)</td> # ip, port
                            .*?<td>.*?</td>.*?<td>.*?</td>.*?<td>(.*?)</td> # type
                            .*?style="width:(\d+?)%".*?style="width:(\d+?)%" # speed, connection time
                        ''', re.S | re.X)

    for sec in zone_type:
        print 'get proxy from: %s/%s' % (url, sec)
        page_num = get_page_num('%s/%s' % (url, sec))
        print 'find %s pages' % page_num

        anonymous = sec.endswith('n')

        page_index = 0
        while page_index < page_num and len(proxy_list) < limit:
            page_index += 1
            html = visit_url('%s/%s/%s' % (url, sec, page_index))
            if html is None:
                continue
   
            ret = pattern.findall(html)
            for ip, port, type, speed, conn_time in ret:
                proxy_list.append(proxy_info(anonymous, type.lower(), ip, port, speed, conn_time))

        if len(proxy_list) > limit:
            break

    if proxy_list != []:
        with open(fname, 'w') as f:
            try:
                cPickle.dump(proxy_list, f)
            except Exception, err:
                print err

    if proxy_list == []:
        proxy_list = load_proxy(fname, force = True)

    return proxy_list if proxy_list != [] else None

def inst_proxy(proxy):
    if not isinstance(proxy, proxy_info) and proxy != None:
        return False

    if proxy is None:
        proxy_handler = urllib2.ProxyHandler({})
    else:
        proxy_handler = urllib2.ProxyHandler({proxy.type :'%s:%s' % (proxy.ip, proxy.port)})

    opener = urllib2.build_opener(proxy_handler)
    urllib2.install_opener(opener)

def uninst_proxy():
    inst_proxy(proxy = None)

def proxy_available(proxy):
    if not isinstance(proxy, proxy_info):
        return False

    inst_proxy(proxy)
        
    #visit_url('http://www.ip.cn/') # <code>*.*.*.*</code>
    html = visit_url('http://1111.ip138.com/ic.asp', retry_times = 2, timeout = 3)

    uninst_proxy()

    if html is None:
        return False

    if proxy.anonymous:
        pattern = re.compile('(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
        ip = pattern.search(html).group() 
        if ip != proxy.ip:
            print 'proxy ip %s should equal to %s' % (ip, proxy_ip)
            return False

    return True

def filter_proxy(proxy_list, anonymous = False, type = 'http', limit = 100, saveable = False):
    if anonymous:
        dest_proxy = [proxy for proxy in proxy_list if proxy.type == type and proxy.anonymous]
    else:
        dest_proxy = [proxy for proxy in proxy_list if proxy.type == type]

    dest_proxy.sort(key = lambda proxy: int(proxy.speed), reverse = True)

    available_proxy = []
    count = 0
    while count < len(dest_proxy) and len(available_proxy) < limit:
        count += 1
        if proxy_available(proxy):
            available_proxy.append(proxy)

    if saveable:
        with open('valid_proxy.info', 'w') as f:
            try:
                cPickle.dump(available_proxy, f)
            except Exception, err:
                print err

    return available_proxy

def show_proxy(proxy):
    print '-'*35
    print 'use proxy:'
    print 'anonymouse: %s' % proxy.anonymous
    print 'ip: %s, port: %s' % (proxy.ip, proxy.port)
    print 'speed: %s, connection_time: %s' % (proxy.speed, proxy.conn_time)
    print '-'*35

def main():
    #proxy_info = get_proxy('http://www.kuaidaili.com/proxylist/')
    #proxy_info = get_proxy('http://www.youdaili.net/Daili/http/3568.html')
    #proxy_info = get_proxy('http://ip.shifengsoft.com/get.php?tqsl=500&submit=%CC%E1++%C8%A1')
    proxy_list = get_proxy(limit = 100)
    if proxy_list == None:
        return

    print 'get proxy num: %s' % len(proxy_list)

    http_proxy_a = [proxy for proxy in proxy_list if proxy.type == 'http' and proxy.anonymous]
    http_proxy_a.sort(key = lambda proxy: int(proxy.speed), reverse = True)

    print 'get http anonymous proxy num: %s' % len(http_proxy_a)

    success = []
    times = 0
    limit = 1
    while times < len(http_proxy_a) and len(success) < limit:
        times += 1
        print 'visit: %s' % len(success)
    
        proxy = http_proxy_a[times]
        show_proxy(proxy)
        inst_proxy(proxy)

        if None != visit_url('http://www.facebook.com'):
            success.append(proxy)

        time.sleep(1)

    print len(success)

if __name__ == '__main__':
    main()
