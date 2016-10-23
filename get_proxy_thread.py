import urllib3
import time
import lxml.html as ET
import threading
import queue
import re
from urllib.parse import urlparse

urllib3.disable_warnings()

PROXY_LIST_URLS = []
PROXY_LIST_URLS.extend(['https://best-proxy.com/english/index.php?p=%d' % p for p in range(1,10)])
PROXY_LIST_URLS.extend(['http://hideme.ru/proxy-list/?maxtime=1500&ports=%d' %
                            port for port in [80, 8080, 8888, 8898, 1080, 3128, 9150, 9750, 9000]])
PROXY_LIST_URLS.append('http://www.prime-speed.ru/proxy/free-proxy-list/all-working-proxies.php')

class Worker(threading.Thread):

    def __init__(self, tasks, result):
        super().__init__()
        self.tasks = tasks
        self.result = result
        self.daemon = True
        self.start()

    def run(self):
        while True:
            func, *args = self.tasks.get()
            try:
                self.result.put(func(*args))
            except Exception as e:
                print(e)
            finally:
                self.tasks.task_done()

class ThreadPool:

    def __init__(self, maxThreads):
        self.tasks = queue.Queue(maxThreads)
        self.result = queue.Queue()
        for w in range(maxThreads): Worker(self.tasks, self.result)

    def add_task(self, task):
        self.tasks.put(task)

    def wait_completion(self):
        self.tasks.join()

    def get_result(self):
        return self.result

def get_page_content(url):
    http = urllib3.PoolManager()

    header = {
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Encoding':'gzip, deflate, lzma, sdch',
        'Accept-Language':'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
        'Cache-Control':'max-age=0',
        'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.93 Safari/537.36 OPR/32.0.1948.69'
    }
    req = http.request('GET', url, headers=header)
    url_full = urlparse(url)
    domain_name = '{uri.scheme}://{uri.netloc}/'.format(uri=url_full)
    query = '{uri.query}'.format(uri=url_full)

    return {(domain_name, query):req.data.decode('utf-8', errors='ignore')}

def parser_bestproxy(data):
    proxy_list = []
    doc = ET.fromstring(data)
    for element in doc.xpath('//div[@class="table"]/ul/li[@class="proxy"]/text()'):
        proxy_list.append(element)
    return proxy_list

def parser_hideme(data, query):
    patter = re.compile('ports=(\d+)', re.IGNORECASE)
    port = re.search(patter, query).group(1)
    proxy_list = []
    doc = ET.fromstring(data)
    for element in doc.xpath('//td[@class="tdl"]/text()'):
        proxy_list.append(element + ':%s' % str(port))
    return proxy_list

def parser_primespeed(data):
    pattern = re.compile('\d+.\d+.\d+.\d+:\d+', re.IGNORECASE)
    proxy_list = []
    doc = ET.fromstring(data)
    for element in doc.xpath('//pre/text()'):
        for address in re.findall(pattern, element):
            proxy_list.append(address)
    return proxy_list

def proxy_validate(url, ctimeout=1.0, rtimeout=2.0):
    try:
        proxy = urllib3.ProxyManager('http://' + url, timeout=urllib3.Timeout(connect=ctimeout))
        header = {
        'Accept':'text/html',
        'Accept-Encoding':'gzip, deflate, lzma, sdch',
        'Accept-Language':'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
        'Cache-Control':'max-age=0',
        'Referer':'https://www.youtube.com/',
        'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.93 Safari/537.36 OPR/32.0.1948.69'
        }

        conn = proxy.request('GET', 'https://www.google.com', headers=header,
                             timeout=urllib3.Timeout(connect=ctimeout, read=rtimeout))
        data = ET.fromstring(conn.data)
        print('Working IP: ' + url)
        return url
    except Exception as e:
        print(e)
        return None

def make_proxy_list(threadsNumber=2, validate=True):
    download_pool = ThreadPool(threadsNumber)
    for i in PROXY_LIST_URLS:
        download_pool.add_task((get_page_content, i))
    download_pool.wait_completion()
    result = download_pool.get_result()

    data_pool = ThreadPool(threadsNumber)
    while True:
        if result.empty():
            break
        data = result.get()
        url = [k[0] for k in data].pop()
        query = [k[1] for k in data].pop()

        if 'https://best-proxy.com/' in url:
            data_pool.add_task((parser_bestproxy, data[('https://best-proxy.com/', query)]))
        elif 'http://hideme.ru/' in url:
            data_pool.add_task((parser_hideme, data[('http://hideme.ru/', query)],query))
        elif 'http://www.prime-speed.ru/' in url:
            data_pool.add_task((parser_primespeed, data[('http://www.prime-speed.ru/', query)]))
    data_pool.wait_completion()

    PROXY_LIST = []
    while True:
        if data_pool.result.empty():
            break
        lst = data_pool.result.get()
        if len(lst) > 0:
            PROXY_LIST.extend(lst)

    # raw proxy ip's
    print(len(PROXY_LIST))

    if validate:
        valid_pool = ThreadPool(threadsNumber*90)
        PROXY_LIST_VALID = []
        for proxy in PROXY_LIST:
            valid_pool.add_task((proxy_validate, proxy))
        valid_pool.wait_completion()

        while True:
            if valid_pool.result.empty():
                break
            valid_proxy = valid_pool.result.get()
            if valid_proxy is not None:
                PROXY_LIST_VALID.append(valid_proxy)
        return PROXY_LIST_VALID
    return PROXY_LIST

if __name__ == '__main__':
    print('Starting work at: %s' % time.strftime("%H:%M:%S"))
    start_time = time.time()
    proxy_list = make_proxy_list(4, True)
    end_time = time.time()
    print('Finish at: %s' % time.strftime("%H:%M:%S"))
    print('Total time spend: %s sec' % str(end_time-start_time))
    with open('proxylist.txt', 'w') as fh:
        for server in proxy_list:
            fh.write(server+'\n')

