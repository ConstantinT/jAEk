# jÄk - jet Änother krawler.

jÄk (or jAEk) is a web application crawler and scanner which uses dynamic JavaScript code analysis. jÄk installs hooks in JavaScript APIs in order to detect the registration of event handlers, the use of network communication APIs, and dynamically-generated URLs or user forms. It then builds and mantains a navigation graph to crawl and test web applications. For more details on the internals please have a look at [my thesis and our paper](#papers-and-further-readings)

## Requirements

jÄk is written in python (version 3) and it is based on [PyQT5](https://riverbankcomputing.com/software/pyqt/intro) (version 5.3 - 5.4). To store data, jÄk uses mongodb via the [pymongo](https://api.mongodb.org/python/current/) 3.x.x bindings. Please, install the required packaged using pip, the packages manager of your distribution, or follow the documentation.

## Running jÄk

The current version of jÄk does not offer a command-line interface. To run jÄk, you will have to write some python code and get familiar with jÄk classes and libraries. The entry point to start using jÄk is [crawler/example.py](https://github.com/ConstantinT/jAEk/blob/master/crawler/example.py). 

### 1. Configuration Objects

#### 1.1 Users
jÄk can use user credential and perform user login. The URL of the login page and the credential can be configured via the object `utils.user.User`. For example:

```
user = User("Wordpress", 0, "http://localhost:8080/wp-login.php", login_data = {"log": "admin", "pwd": "admin"}, session="ABC")
```

TODO: describe the meaning of each parameter

#### 1.2 Crawler and Attacker Configuration

```
url = "http://localhost/
[...]
crawler_config = CrawlConfig("jÄk", url, max_depth=3, max_click_depth=3, crawl_speed=CrawlSpeed.Fast)
attack_config = AttackConfig(url)
```

where:
* `max_depth` is the maximum depth of the web application link tree;
* `max_click_depth` is the maximum depth of click event that are fired;
* `crawl_speed` is XXX. Please see `CrawlSpeed` in `crawler/models/utils.py`.

#### 1.3 Database

```
database_manager = DatabaseManager(user, dropping=True)
```

`user` is also an instance of the `User` class.

### 2 Setting up the Crawler

To run the crawler use:

```
crawler = Crawler(crawl_config=crawler_config, database_manager=database_manager)
crawler.crawl(user)
```

You can also setup an HTTP proxy between the crawler and the web application (e.g., localhost:8082):

```
crawler = Crawler(crawl_config=crawler_config, database_manager=database_manager, proxy="localhost", port=8082)
crawler.crawl(user)
```

## Papers and further readings

* C. Tschürtz. *Improving Crawling with JavaScript Function Hooking* [DE: Verbesserung von Webcrawling durch JavaScript Funktion Hooking].
* G. Pellegrino, C. Tschürtz, E. Bodden, and C. Rossow. *jÄk: Using Dynamic Analysis to Crawl and Test Modern Web Applications*. Proceedings of Research in Attacks, Intrusions and Defenses (RAID) Symposium (RAID 2015). [PDF](http://trouge.net/gp/papers/jAEk_raid2015.pdf)

## Contacts

* C. Tschürtz *[constantin dot tschuertz (at) gmail dot com]*
* G. Pellegrino *[gpellegrino (at) cispa dot saarland]*

## License

jÄk is released as General Public License version 3 or later.
