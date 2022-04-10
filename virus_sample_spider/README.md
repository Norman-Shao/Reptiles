# READEME

## 1 | 环境说明

Python 版本 `3.8.10`

可使用 `poetry` 创建虚拟环境，相关命令如下：
```
# pip3 install poetry

# 进入项目根目录（包含pyproject.toml），执行
poetry install

# 激活虚拟环境
poetry shell
```

## 2 | 脚本说明

目标网站：http://malware.cnsrc.org.cn/

该网站带宽较小，为防止将网站请求挂掉，需要根据下载的文件大小设置不同的并发数及超时时间。

- `python virus_crawl.py -f crawl`       执行爬虫任务
- `python virus_crawl.py -f refresh`     更新 record/downloaded.json 文件，记录 ./download 已下载样本
- `python virus_crawl.py -f decompress`  根据 record/downloaded.json 解压已下载样本文件


`./record/log.log` 脚本日志文件

`./record/catalog.json` 目标网站目录记录存储

`./record/samples.json` 目标网站全部样本记录存储

`./record/downloaded.json` 已下载样本文件记录存储

`./record/version.text` 判断目标网站是否更新的记录

`./record/decompress_error.json` 解压错误的样本文件记录

```
// virus_crawl.py

FORCE_UPDATE                # 强制更新开关，建议关闭，需要时再开启，会检查全站样本，对未下载的样本进行下载

start_crawl()               # 爬虫任务

refresh_downloaded()        # 根据 ./download 目录更新 record/downloaded.json 文件

decompress_all()            # 根据 record/downloaded.json 文件解压已下载样本到 ./extract

```


## 3 | 20220330 已下载样本数量 54568