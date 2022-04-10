#!/usr/bin/env python
# -*- coding:utf-8 -*-
import os
import json
import random
import logging
import time
from hashlib import md5
from datetime import datetime
from typing import List, Dict
from multiprocessing.pool import ThreadPool

import click
import py7zr
import aiohttp
import asyncio
import requests
from pyquery import PyQuery as pq

logging.basicConfig(
    level=logging.INFO,
    filename='./record/log.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s: %(message)s'
)

FORCE_UPDATE = False

HOME_URL = "http://malware.cnsrc.org.cn/"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "malware.cnsrc.org.cn",
    "Upgrade-Insecure-Requests": "1",
}
UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.83 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.46",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) MicroMessenger/6.8.0(0x16080000) MacWechat/3.3.1(0x13030111) Safari/605.1.15 NetType/WIFI",
]

DOWNLOAD_PATH = "./download"
DECOMPRESSION_PATH = "./extract"
DECOMPRESSION_PWD = "infected"
DECOMPRESSION_NOW = False

catalog = []
samples = []
downloaded = []
decompress_errors = []


def refresh_downloaded(downloaded_path=DOWNLOAD_PATH):
    """
    read ./download and write ./record/downloaded.json
    :param downloaded_path:
    :return:
    """
    table = get_all_dir_re(downloaded_path)
    if downloaded:
        with open("./record/downloaded.json", "w") as f:
            f.write(json.dumps(table, indent=2))


def get_all_dir_re(path):
    global downloaded
    files_list = os.listdir(path)
    for file_name in files_list:
        abs_path = os.path.join(path, file_name)
        file_path = abs_path.replace(f"{DOWNLOAD_PATH}/", "", 1)
        if os.path.isdir(abs_path):
            get_all_dir_re(abs_path)
        else:
            row = {"title": file_name, "category": file_path.rstrip(f"/{file_name}")}
            row.update({"md5": sum_md5(json.dumps(row))})
            downloaded.append(row)
    return downloaded


def decompress(category, root_path=DOWNLOAD_PATH, decompress_path=DECOMPRESSION_PATH):
    root_path = "/Volumes/DockerDuck/download"
    decompress_path = "/Volumes/DockerDuck/decompress"
    path = os.path.join(root_path, category)
    folder = os.path.join(decompress_path, category)
    if not folder:
        os.makedirs(folder)
    for item in os.listdir(path):
        if not is_file_directory(item) and item[-3:] == ".7z":
            file_path = os.path.join(path, item)

            if os.path.exists(os.path.join(folder, item[:-3])):
                continue
            try:
                with py7zr.SevenZipFile(file_path, mode='r', password=DECOMPRESSION_PWD) as z:
                    z.extractall(folder)
            except py7zr.exceptions.Bad7zFile as e:
                decompress_errors.append("[error:py7zr.exceptions.Bad7zFile]: %s" % f"{category}/{item}")
                logging.info(
                    "[decompression][error:py7zr.exceptions.Bad7zFile]decompression[%s]: %s" % (category, item))
            except OSError as e:
                decompress_errors.append("[error:OSError]: %s" % f"{category}/{item}")
                logging.error("[decompression][error:OSError]decompression[%s]: %s" % (category, item))
            logging.info("decompression[%s]: %s" % (category, item))

    if decompress_errors:
        with open("./record/decompress_error.json", "w") as f:
            f.write(json.dumps(decompress_errors, indent=2))


def decompress_all():
    with open("./record/downloaded.json", "r") as f:
        catalog = [item['category'] for item in json.loads(f.read())]
    pool = ThreadPool(10)
    pool.map(decompress, catalog)
    pool.close()
    pool.join()


def get_home_page():
    table = []
    resps = []
    for i in range(len(UAS)):
        headers = HEADERS
        headers.update({
            "User-Agent": UAS[i]
        })
        r = requests.get(HOME_URL, headers=headers)
        resps.append(r)

    resp = resps[0]
    doc = pq(resp.text)
    trs = pq(doc("#table tbody tr")[1:])
    for tr in trs:
        column_one = pq(pq(tr)("td")[0])("a")
        url = column_one.attr("href")
        title = column_one.attr("title")
        column_two, column_three = pq(tr)("td")[1:]
        size, date = column_two.text, column_three.text
        row = {
            "title": title,
            "url": url,
            "size": size,
            "date": date,
        }
        row.update({"md5": sum_md5(json.dumps(row))})
        table.append(row)
    return table, resps


def sum_md5(string: str) -> str:
    return md5(string.encode("utf-8")).hexdigest()


def is_update(home_table: List) -> bool:
    current_md5 = sum_md5(json.dumps(home_table))
    with open("./record/version.txt", "rb+") as f:
        lines = f.readlines()
        date, old_md5 = lines[-1].split(b' ') if lines else [b"", b""]
        if current_md5 != old_md5.decode("utf-8"):
            now = datetime.strftime(datetime.now(), '%Y-%m-%d')
            holder = b'\n' if lines else b''
            tmp = b"%s%s %s" % (holder, now.encode('utf8'), current_md5.encode('utf8'))
            f.write(tmp)
            f.flush()
            return True
    return False


def diff_samples(current_samples):
    old_samples = read_record("./record/samples.json")
    old_samples_set = {sample['md5']: sample for sample in old_samples}
    current_samples_set = {sample['md5']: sample for sample in current_samples}
    downloaded_samples = read_record("./record/downloaded.json")
    downloaded_samples_set = {sample['md5']: sample for sample in downloaded_samples}
    diff_sample = current_samples_set.keys() - old_samples_set.keys() - downloaded_samples_set.keys()
    if diff_sample:
        return [current_samples_set[item] for item in diff_sample]
    return []


def is_file_directory(title):
    if title[-3:] not in (".7z", "pdf"):
        if len(title) == 64:
            return False
        return True
    return False


def crawl_catalog(catalog_url, client=None):
    dir_table = []
    headers = HEADERS
    headers.update({
        "User-Agent": UAS[0]
    })
    if client:
        cookie = client.headers.get("Set-Cookie")
        headers.update({
            "Cookie": cookie,
        })
    resp = requests.get(catalog_url, headers=headers)
    if resp.status_code == 200:
        doc = pq(resp.text)
        trs = pq(doc("#table tbody tr")[1:])
        for tr in trs:
            column_one = pq(pq(tr)("td")[0])("a")
            url = column_one.attr("href")
            title = column_one.attr("title")
            column_two, column_three = pq(tr)("td")[1:]
            size_str, date = column_two.text, column_three.text
            size, size_type = size_str.split(" ")

            if is_file_directory(title):
                path = url.split("/")[-1]
                title = (title if not path else path.replace("%2F", "/")).lstrip("/")

                row = {
                    "title": title,
                    "url": url,
                    "size": size,
                    "size_type": size_type,
                    "date": date,
                }
                row.update({"md5": sum_md5(json.dumps(row))})
                dir_table.append(row)
                dir_table_, resp_ = crawl_catalog(url, resp)
                if dir_table_:
                    dir_table.extend(dir_table_)
            else:
                category = url[len(HOME_URL):-len(title)].replace("%2F", "/").strip("/")
                row = {
                    "title": title,
                    "url": url,
                    "size": size,
                    "size_type": size_type,
                    "date": date,
                    "category": category,
                }
                row.update({"md5": sum_md5(json.dumps({"title": title, "category": category}))})
                samples.append(row)

            logging.info(f"[parse page][succeed]: {url}")
        return dir_table, resp
    else:
        logging.info(f"[parse page][failed]: {catalog_url}")


def download_samples(urls, clients, sem, timeout=600):
    sem = asyncio.Semaphore(sem)
    tasks = [asyncio.ensure_future(download(item, clients[idx % len(UAS)], sem, timeout)) for idx, item in
             enumerate(urls)]
    loop = asyncio.get_event_loop()
    tasks = asyncio.gather(*tasks)
    loop.run_until_complete(tasks)


async def download(item: Dict, client, sem, timeout):
    async with sem:
        url = item.get("url")
        cookie = client.headers.get("Set-Cookie")
        ua = client.request.headers.get("user-agent")
        category = item.get("category")
        title = item.get("title")
        category_path = os.path.join(DOWNLOAD_PATH, category)
        file_path = os.path.join(category_path, title)
        folder = os.path.exists(category_path)
        if not folder:
            os.makedirs(category_path)
        if not os.path.exists(file_path):
            headers = HEADERS
            headers.update({
                "Referer": HOME_URL + "%2F" + item.get("category"),
                "Cookie": cookie,
                "User-Agent": ua,
            })
            timeout = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(headers=headers) as session:
                content = b""
                status = "success"
                try:
                    response = await session.get(url, timeout=timeout)
                    if response.status == 200:
                        try:
                            with open(file_path, 'wb') as f:
                                while True:
                                    chunk = await response.content.read(1024)
                                    if not chunk:
                                        break
                                    f.write(chunk)

                        except Exception as e:
                            status = "failed"
                            logging.info(f"[download][failed]: {file_path}")
                except Exception as e:
                    status = "failed"
                    logging.info(f"[download][{status}]crawl [%s] is error: %s" % (url, e))
                    return

                logging.info(f"[download][{status}][%s]: %s" % (category, title))

                # if DECOMPRESSION_NOW:
                #     decompression__path = os.path.join(DECOMPRESSION_PATH, item.get("category"))
                #     with py7zr.SevenZipFile(file_path, mode='r', password=DECOMPRESSION_PWD) as z:
                #         z.extractall(decompression__path)
                #     logging.info("decompression[%s]: %s" % (category, title))


def read_record(record_file):
    with open(record_file, "r") as f:
        samples = f.read()
    samples = json.loads(samples) if samples else []
    return samples


def save_samples(current_samples):
    ret = True
    try:
        with open("./record/samples.json", "w") as f:
            f.write(json.dumps(current_samples, indent=2))
    except Exception:
        ret = False
        logging.info("[save][error]: save samples is failed.")
    return ret


def save_catalog(current_catalog):
    with open("./record/catalog.json", "w") as f:
        f.write(json.dumps(current_catalog, indent=2))


def filter_and_split_samples(download_urls):
    fast = []
    middle = []
    slow = []
    for item in download_urls[:]:
        file_path = f"{DOWNLOAD_PATH}/{item['category']}/{item['title']}"
        if os.path.exists(file_path) or item['title'][-3:] != ".7z":
            download_urls.remove(item)
        elif item["size_type"] == "MB" and float(item['size']) > 30:
            slow.append(item)
        elif item["size_type"] == "MB" and float(item['size']) > 10:
            middle.append(item)
        else:
            fast.append(item)
    return fast, middle, slow


def start_crawl():
    start_time = time.time()
    home_table, clients = get_home_page()
    if is_update(home_table) or FORCE_UPDATE:
        logging.info("The virus database has been updated, ready to crawl ...")
        dir_table, _ = crawl_catalog(HOME_URL)
        catalog.extend(dir_table)
        save_catalog(catalog)

        download_urls = diff_samples(samples)
        if download_urls:
            save_samples(samples)
        fast, middle, slow = filter_and_split_samples(download_urls)
        if fast:
            download_samples(fast, clients, 100, 300)
        if middle:
            download_samples(middle, clients, 30, 1200)
        if slow:
            download_samples(slow, clients, 10, 1800)
    else:
        logging.info("The virus database is latest, don't need to crawl.")
    end_time = time.time()
    logging.info('[task][done]total time %s seconds', end_time - start_time)


@click.command()
@click.option("-f", "--func_name",
              type=click.Choice(['crawl', 'refresh', 'decompress']),
              help="select function in ('crawl', 'refresh', 'decompress')")
def main(func_name):
    if func_name == "crawl":
        start_crawl()
    elif func_name == "refresh":
        refresh_downloaded()
    elif func_name == "decompress":
        decompress_all()


if __name__ == '__main__':
    # main()
    # start_crawl()
    # refresh_downloaded()
    decompress_all()
    # decompress("HiveRansomware/v3/win", "/Volumes/DockerDuck/download", "/Volumes/DockerDuck/decompress")