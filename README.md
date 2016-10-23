# free_proxy

Small programm that builds list of worked free proxies.

Two versions in repo - old one, build on threads basis and new, build in asynchronous maner.

Free proxy used from:
* https://best-proxy.com
* http://hideme.ru
* http://www.prime-speed.ru

To start building proxy list:
```python
fproxy = Proxy()
fproxy.start()
```
Result's would be saved in proxylist.txt.

Proxy arguments:
```python
class Proxy(validate=True, http_only=False, limit_concurrent=20, timeout=10, retry=10, sleep=0)
```
* validate if set to True - trying to check if every received proxy server is working (try to get google homepage via proxy)
* http_only is set to False - parse all proxies; if true - only those wich have open 80 and 8080 port's
* limit_concurent - limits simultaniously running corutines
* timeout - limits time (sec) trying to connect to remote proxy server
* retry - limits attempts to reconnect to remote server
* sleep - not implemented
