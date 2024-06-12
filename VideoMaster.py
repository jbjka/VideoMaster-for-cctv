import concurrent.futures
import math
import os
import queue
import re
import string
import random
import requests
from lxml import html


class VideoMaster:
    __HEADER = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        "referer": "https://tv.cctv.com/"
    }
    BaseUrl = "https://hlswx.cntv.kcdnvip.com/asp/hls/1200/0303000a/3/default/"
    download_url = []
    frequncy = 0
    directory_name = ''
    file_name=''

    def __init__(self, url, thread):
        self.url = url
        self.thread = thread

    def getResponse(self, url):
        resp = requests.get(url, headers=self.__HEADER)
        return resp
    # 得到视频的名称
    def get_title(self):
        resp = self.getResponse(self.url)
        resp.encoding = "utf-8"
        tree = html.fromstring(resp.text)
        data = tree.xpath('//div[@class="ph_title_l"]/text()')[0]
        return data
    # 得到这个视频的guid
    def __getGuid(self):
        resp = self.getResponse(self.url)
        guid_pattern = r'var guid = "([0-9a-fA-F]{32})";'  # 这个正则表达式可能需要根据实际页面内容调整
        match = re.search(guid_pattern, resp.text)
        if match:
            # 提取GUID（或任意长度的十六进制字符串）
            guid = match.group(1)
            return guid
        else:
            print("No GUID found in the text.")
    # 得到这个视频的时长及下载ts的次数
    def getTimeFrequency(self):
        info_url = "https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid="
        guid = self.__getGuid()
        getInfoUrl = info_url + guid
        content = requests.get(getInfoUrl, headers=self.__HEADER)
        content_text = content.json()
        time = content_text["video"]["totalLength"]
        if (int(float(time)) % 10 != 0):
            frequency = int(float(time)) / 10
            frequency = math.floor(frequency) + 1
            self.frequncy = frequency
        return frequency
    # 创建随机的文件目录名称，防止冲突
    def random_file_name(self):
        letters = string.ascii_letters  # string.ascii_letters 包含所有大小写英文字母
        file_name = ''
        for i in range(10):
            file_name += random.choice(letters)

        return file_name
    # 得到ts视频片段的下载地址
    def create_download_url(self):
        guid = self.__getGuid()
        frequency = self.getTimeFrequency()
        self.download_url = [f'{self.BaseUrl}{guid}/{i}.ts' for i in range(frequency)]
        print(self.download_url)

    # 下载ts文件
    def download_file(self, url, session, directory_name):
        try:
            response = session.get(url, headers=self.__HEADER)
            response.raise_for_status()  # 如果请求失败，抛出异常
            file_name = url.split("/")[-1]

            with open(f"{directory_name}{file_name}", mode="wb") as f:
                f.write(response.content)
        except Exception as e:
            # 如果下载失败，将异常信息放入队列
            print(e)

    # 主下载程序
    def start_download(self):
        result_queue = queue.Queue()
        random_name = self.random_file_name();
        directory_name = f'./{random_name}/video/'
        self.directory_name = directory_name
        directory_path = os.path.dirname(directory_name)
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        # 创建一个requests.Session来复用TCP连接
        with requests.Session() as session:
            # 创建一个线程池
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread) as executor:
                # 提交任务到线程池

                futures = []
                for url in self.download_url:
                    future = executor.submit(self.download_file, url, session, directory_name)
                    futures.append(future)
                    # 等待所有任务完成
                concurrent.futures.wait(futures)
        result_queue.join()
        # 但我们可以轮询结果队列直到它为空
        for _ in range(5):  # 因为有5个工作线程
            result_queue.put(None)

    def __rename_file(self,file_path,old_name,new_name):
        if os.path.exists(file_path):
            os.rename(old_name,new_name)
        else:print("此文件不存在")

    def get_file_path(self):
        return f'{self.directory_name}{self.file_name}'

    # 合并文件
    def merge(self):
        # 列表生成器生成文件名列表
        movie_list = [f"{i}.ts" for i in range(self.frequncy)]
        # 进入文件夹内
        os.chdir(self.directory_name)
        # 分段合并
        n = self.frequncy
        temp = []
        for i in range(len(movie_list)):
            file_name = movie_list[i]
            temp.append(file_name)
            if i != 0 and i % 20 == 0:
                # 可以合并一次了
                cmd = f"copy /b {'+'.join(temp)} {n}.ts"
                r = os.popen(cmd)
                print(r.read())
                temp = []  # 新列表
                n = n + 1
        # 需要把剩余的ts进行合并
        cmd = f"copy /b {'+'.join(temp)} {n}.ts"
        r = os.popen(cmd)
        print(r.read())
        n = n + 1
        # 第二次大合并
        last_temp = []
        for i in range(self.frequncy, n):
            last_temp.append(f"{i}.ts")
        # 最后一次合并
        title = self.get_title()
        old_name = 'cachedog.mp4'
        cmd = f"copy /b {'+'.join(last_temp)} {old_name}"
        r = os.popen(cmd)
        print(r.read())
        new_name = f'{title}.mp4'
        self.file_name = new_name
        self.__rename_file(os.path.dirname(f'./{old_name}'),old_name,new_name)
        # 回来
        os.chdir("../../../")
