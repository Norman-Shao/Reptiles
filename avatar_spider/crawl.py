#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
目标网站 http://www.imeitou.com/
爬取 5000 个左右头像图片
"""
import requests
import logging
import aiofiles
import glob
from PIL import Image
import os
from hashlib import md5
from pyquery import PyQuery as pq
import asyncio
from aiohttp_requests import requests as aio_requests


HEADERS = {
    "Host": "www.imeitou.com",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Content-Type": "html/text;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
IMG_HEADERS = {
    "Host": "m.imeitou.com",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "http://www.imeitou.com/gexing/",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

IMG_DIRNAME = "images"


def save_image(dirname, url, img_content):
    title = md5(url.split("/")[-1].encode("utf-8")).hexdigest() + ".jpg"
    path = f"./{IMG_DIRNAME}/{dirname}/{title}"
    with open(path, "wb") as f:
        f.write(img_content)
        logging.info(f"{dirname}: {title} 保存成功 1 张")


def get_classify():
    url = "http://www.imeitou.com/"
    r = requests.get(url, headers=HEADERS)
    a_link = pq(r.text)(".g-class-top a")
    titles = {
        str(pq(a).attr("href"))
        .replace("/", ""): pq(a)
        .text()
        .encode("latin-1")
        .decode("gbk")
        for a in a_link
    }

    return titles


def mkdir(path):
    folder = os.path.exists(path)
    # 判断是否存在文件夹如果不存在则创建为文件夹
    if not folder:
        # makedirs 创建文件时如果路径不存在会创建这个路径
        os.makedirs(path)
        logging.info("---  new folder create ok  ---")
    else:
        logging.info("---  There is this folder!  ---")


def get_img_url(title):
    url_list = []
    url = f"http://www.imeitou.com/{title}/"
    r = requests.get(url, headers=HEADERS)
    ul = pq(r.text)(".g-gxlist-imgbox ")
    li = pq(ul)("li")
    urls = [pq(l)("img").attr("src") for l in li]
    url_list.extend(urls)
    for i in range(2, 12):
        url = f"http://www.imeitou.com/{title}/index_{str(i)}.html"
        r = requests.get(url, headers=HEADERS)
        ul = pq(r.text)(".g-gxlist-imgbox ")
        li = pq(ul)("li")
        urls = [pq(l)("img").attr("src") for l in li]
        url_list.extend(urls)
    return url_list


async def down_load_img(url, dirname):
    resp = await aio_requests.session.get(url, headers=IMG_HEADERS)
    if resp.status == 200:
        logging.info(f"下载成功: {url}")
        body = await resp.read()
        return save_image(dirname, url, body)
    else:
        logging.info(f"下载失败: {url}")


def convert_jpg(jpg_path, width=400, height=400):
    img = Image.open(jpg_path)
    try:
        new_img = img.resize((width, height), Image.BILINEAR)
        new_img.save(jpg_path)
    except Exception as e:
        print(jpg_path)
        print(e)


if __name__ == "__main__":

    titles = get_classify()
    # for k, v in titles.items():
    #     path = f"./{IMG_DIRNAME}/{v}"
    #     mkdir(path)
    for k, v in titles.items():
        tasks = []
        url_list = get_img_url(k)
        for url in url_list:
            task = asyncio.ensure_future(down_load_img(url, v))
            tasks.append(task)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.wait(tasks))
    # base_dir = os.path.dirname(os.path.abspath(__file__))
    # for dirname in os.listdir(f"{base_dir}/{IMG_DIRNAME}"):
    #     for jpg in glob.glob(f"{base_dir}/{IMG_DIRNAME}/{dirname}/*.jpg"):
    #         convert_jpg(jpg)
