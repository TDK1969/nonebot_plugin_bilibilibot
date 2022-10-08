import httpx
from random import choice
from lxml import etree
import asyncio
import json
from typing import List, Tuple
from .exception import BiliAPI404Error, BiliAPIRetCodeError, BiliConnectionError, BiliDatebaseError, BiliInvalidRoomId, BiliInvalidShortUrl, BiliNoLiveRoom, BiliStatusCodeError
from nonebot.log import logger

__PLUGIN_NAME__ = "[bilibilibot~Client]"
class BiliClient():
    def __init__(self) -> None:
        self.__proxy_pool__ = [None]
        self.__retry_times__ = 3
        self.__ua_list__ = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML like Gecko) Chrome/44.0.2403.155 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2226.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.4; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2224.3 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.93 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 4.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.67 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.67 Safari/537.36",
            "Mozilla/5.0 (X11; OpenBSD i386) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1944.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.3319.102 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.2309.372 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.2117.157 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1866.237 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.137 Safari/4E423F",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36 Mozilla/5.0 (iPad; U; CPU OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B334b Safari/531.21.10",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.517 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1664.3 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1664.3 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1623.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.17 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.62 Safari/537.36",
            "Mozilla/5.0 (X11; CrOS i686 4319.74.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.57 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.2 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1468.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1467.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1464.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1500.55 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36",
            "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.90 Safari/537.36",
            "Mozilla/5.0 (X11; NetBSD) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36",
            "Mozilla/5.0 (X11; CrOS i686 3912.101.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.60 Safari/537.17",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1309.0 Safari/537.17"
        ]
        self.__usable_ip_list__ = set()

        self.API = {
            # 用于获取临时cookie
            "get_bili_cookie": "https://www.bilibili.com",
            "get_user_info_by_uid": "https://api.bilibili.com/x/space/acc/info?mid={}&jsonp=jsonp",
            "get_latest_video_by_uid": "https://api.bilibili.com/x/space/arc/search?mid={}&ps=1&tid=0&pn=1&order=pubdate&jsonp=jsonp",
            "get_live_info_by_room_id": "https://api.live.bilibili.com/room/v1/Room/get_info?room_id={}",
            "get_liver_info_by_uid": "https://api.live.bilibili.com/live_user/v1/Master/info?uid={}",
            "get_telegram_info_by_media_id": "https://api.bilibili.com/pgc/review/user?media_id={}",
            "get_telegram_info_by_ep_id": "https://api.bilibili.com/pgc/view/web/season?ep_id={}",
            "get_telegram_info_by_season_id": "https://api.bilibili.com/pgc/view/web/season?season_id={}",
            "get_telegram_latest_episode": "https://api.bilibili.com/pgc/view/web/season?season_id={}"
        
        }

        self.__proxy_lock__ = asyncio.Lock()

    @classmethod
    async def async_client_init(cls) -> "BiliClient":
        self = cls()
        await self.update_proxy_pool()
        return self


    def __request_header__(self) -> httpx.Headers:
        '''返回随机UA的header

        Returns:
            httpx.Headers: 返回header
        '''
        headers = {
            'User-Agent': choice(self.__ua_list__),
        }
        return httpx.Headers(headers)

    async def __get_page__(self, page: int):
        print(f'正在抓取第{page}页……')
        try:
            async with httpx.AsyncClient(headers=self.__request_header__()) as client:
                response = await client.get(url=f'http://www.ip3366.net/free/?stype=1&page={page}', timeout=5)
        except Exception as e:
            return
        text = response.text
        https_proxy_list = []
        html = etree.HTML(text)
        tr_list = html.xpath('/html/body/div[2]/div/div[2]/table/tbody/tr')
        for td in tr_list:
            ip_ = td.xpath('./td[1]/text()')[0] #ip
            port_ = td.xpath('./td[2]/text()')[0]  #端口
            type_ = td.xpath('./td[4]/text()')[0].lower()
            proxy = f"http://{ip_ + ':' + port_}"
            if type_ == "https":
                https_proxy_list.append(proxy)
        
        await asyncio.gather(*[self.test_ip(i) for i in https_proxy_list])

    async def __test_ip__(self, proxy) -> None:
        try:
            async with httpx.AsyncClient(headers=self.__request_header__(), proxies=proxy) as client:
                response = await client.get(url='https://api.live.bilibili.com/room/v1/Room/get_info?room_id=42062')
            if response.status_code == 200:
                if response.json()["code"] == 0:
                    self.__usable_ip_list__.add(proxy)
                    print(proxy, '\033[31m可用\033[0m')
            else:
                print(proxy, '不可用')
            return
        except Exception as e:
            print(proxy,'请求异常')
            return

    async def update_proxy_pool(self) -> None:
        '''更新代理池
        '''
        self.__usable_ip_list__.clear()
        tasks_list = [self.__get_page__(i) for i in range(1, 6)]
        await asyncio.gather(*tasks_list)

        async with self.__proxy_lock__:
            self.__proxy_pool__ = list(self.__usable_ip_list__)
            self.__proxy_pool__.append(None)
        
        self.__usable_ip_list__.clear()
    
    async def get_latest_video(self, uid: str, last_udpate_time: int) -> Tuple[bool, str, str, int, str]:
        """
        @description  :
        根据uid和时间戳, 返回元组，表示存在新视频或无新视频
        ---------
        @param  :
        uid: 查询新视频用户的uid
        last_udpate_time: 数据库中记录的最新视频的时间戳
        -------
        @Returns  :
        返回一个元组[是否更新，bv号，标题，发布时间戳，封面的链接]
        -------
        """
        try:
            async with httpx.AsyncClient(headers=self.__request_header__()) as client:
                await client.get(url=self.API["get_bili_cookie"])
                response = await client.get(url=self.API["get_latest_video_by_uid"].format(uid))
        except Exception as e:
            raise BiliConnectionError(0, uid, e.args[0])

        if response.status_code != 200:
            raise BiliStatusCodeError(0, uid, response.status_code)

        response = response.json()
        if response["code"] != 0:
            raise BiliAPIRetCodeError(0, uid, response["code"], response["message"])
        
        #logger.debug(f'{__PLUGIN_NAME__}{json.dumps(response, ensure_ascii=False, indent=4)}')
        
        latest_video = response['data']['list']['vlist'][0] if len(response['data']['list']['vlist']) != 0 else {}
        post_time = latest_video.get("created", 0)

        if post_time > last_udpate_time:
            # 发现新视频
            title = latest_video['title']
            bvID = latest_video['bvid']
            cover_url = latest_video['pic']
            return (True, bvID, title, post_time, cover_url)

        return (False, '', '', 0, '')

    async def init_up_info(self, uid: str) -> Tuple[str, int]:
        """
        @description  :
        根据uid查询up主信息
        ---------
        @param  :
        uid: 用户的uid
        -------
        @Returns  :
        返回一个元组
        [up主名字，最新视频的时间戳]
        -------
        """
        
        async with httpx.AsyncClient(headers=self.__request_header__()) as client:
            try:
                await client.get(self.API["get_bili_cookie"])
                response1 = await client.get(url=self.API["get_user_info_by_uid"].format(uid))
            except Exception as e:
                raise BiliConnectionError(0, uid, e.args[0])

            if response1.status_code != 200:
                raise  BiliStatusCodeError(0, uid, response1.status_code)
    
            response1 = response1.json()
            if response1["code"] == -404:
                raise BiliAPI404Error()
            elif response1["code"] != 0:
                raise BiliAPIRetCodeError(0, uid, response1["code"], response1["message"])
            
            user_name = response1["data"]["name"]
            try:
                response2 = await client.get(url=self.API["get_latest_video_by_uid"].format(uid))
            except Exception as e:
                raise BiliConnectionError(0, uid, e.args[0])

            if response2.status_code != 200:
                raise  BiliStatusCodeError(0, uid, response2.status_code)
    
            response2 = response2.json()
            if response2["code"] != 0:
                raise BiliAPIRetCodeError(0, uid, response2["code"], response2["message"])
            
            latest_video = response2['data']['list']['vlist'][0] if len(response2['data']['list']['vlist']) != 0 else {}
            post_time = latest_video.get("created", 0)

            return (user_name, post_time)
           
    async def get_live_status(self, uid: str, room_id: str) -> Tuple[bool, str, str]:
        """
        @description  :
        根据房间号,获取直播间是否开播
        ---------
        @param  :
        uid: 主播的uid
        room_id: 直播间号
        -------
        @Returns  :
        返回一个元组
        [是否正在直播，直播间标题，直播间封面链接]
        -------
        """
        
        async with httpx.AsyncClient(headers=self.__request_header__()) as client:
            try:
                await client.get(self.API["get_bili_cookie"])
                response = await client.get(self.API["get_live_info_by_room_id"].format(room_id))
            except Exception as e:
                raise BiliConnectionError(1, uid, e.args[0])
            
            if response.status_code != 200:
                raise BiliStatusCodeError(1, uid, response.status_code)
            
            response = response.json()
            if response["code"] != 0:
                raise BiliAPIRetCodeError(1, uid, response["code"], response["message"])
            
            live_status = response["data"]["live_status"]
            title = response["data"]["title"]
            cover_url = response["data"]["user_cover"]
        
            if live_status == 1:
                return (True, title, cover_url)
            else:
                return (False, "", "")
    
    async def init_liver_info(self, uid: str) -> Tuple[str, str]:
        """
        @description  :
        根据uid，返回直播间信息
        ---------
        @param  :
        uid: 用户的uid
        -------
        @Returns  :
        返回一个元组
        [用户名，直播间房间号]
        -------
        """

        async with httpx.AsyncClient(headers=self.__request_header__()) as client:
            try:
                await client.get(self.API["get_bili_cookie"])
                response = await client.get(self.API["get_liver_info_by_uid"].format(uid))
            except Exception as e:
                raise BiliConnectionError(0, uid, e.args[0])
            
        if response.status_code != 200:
            raise BiliStatusCodeError(1, uid, response.status_code)
        
        response = response.json()
        if response["code"] != 0:
            raise BiliAPIRetCodeError(1, uid, response["code"], response["message"])
        
        liver_name = response["data"]["info"]["uname"]
        room_id = response["data"]["room_id"]

        if room_id == 0:
            raise BiliNoLiveRoom(liver_name)
        
        return (liver_name, room_id)
    
    async def init_liver_info_by_room_id(self, room_id: str) -> Tuple[str, str]:
        '''根据直播房间号获得主播uid和主播用户名

        Args:
            room_id (str): 直播房间号

        Returns:
            Tuple[str, str]: 
            返回一个元组
            [主播uid, 主播用户名]
        '''

        async with httpx.AsyncClient(headers=self.__request_header__()) as client:
            try:
                await client.get(url=self.API["get_bili_cookie"])
                response1 = await client.get(url=self.API["get_live_info_by_room_id"].format(room_id))
            except Exception as e:
                raise BiliConnectionError(1, f"房间号:{room_id}", e.args[0])
            
            if response1.status_code != 200:
                raise BiliStatusCodeError(1, f"房间号:{room_id}", response1.status_code)

            response1 = response1.json()
            if response1["code"] == 1:
                raise BiliInvalidRoomId(room_id)
            if response1["code"] != 0:
                raise BiliAPIRetCodeError(1, f"房间号:{room_id}", response1["code"], response1["message"])
            
            uid = str(response1["data"]["uid"])

            try:
                response2 = await client.get(self.API["get_liver_info_by_uid"].format(uid))
            except Exception as e:
                raise BiliConnectionError(0, uid, e.args[0])
            
            if response2.status_code != 200:
                raise  BiliStatusCodeError(1, uid, response2.status_code)
    
            response2 = response2.json()
            if response2["code"] != 0:
                raise BiliAPIRetCodeError(1, uid, response2["code"], response2["message"])
            
            liver_name = response2["data"]["info"]["uname"]

            return (uid, liver_name)
    
    async def init_telegram_info_by_ep_id(self, ep_id: int) -> Tuple[int, str, int, bool]:
        ''' 根据ep_id初始化番剧信息

        Args:
            ep_id (int): ep_id

        Returns:
            Tuple[int, str, int, bool]: 
            返回一个元组
            [season_id, 番剧名, 最新集, 是否完结]
        '''

        async with httpx.AsyncClient(headers=self.__request_header__()) as client:
            try:
                await client.get(url=self.API["get_bili_cookie"])
                response = await client.get(url=self.API["get_telegram_info_by_ep_id"].format(ep_id))
            except Exception as e:
                raise BiliConnectionError(2, f"ep_id:{ep_id}", e.args[0])
            
            if response.status_code != 200:
                raise BiliStatusCodeError(2, f"ep_id:{ep_id}", response.status_code)
    
            response = response.json()
            if response["code"] == -404:
                raise BiliAPI404Error()
            elif response["code"] != 0:
                raise BiliAPIRetCodeError(2, f"ep_id:{ep_id}", response["code"], response["message"])

            season_id = response["result"]["season_id"]
            season_title = response["result"]["season_title"]
            is_finish = bool(response["result"]["publish"]["is_finish"])
            latest_episode = len(response["result"]["episodes"])
    


            return (season_id, season_title, latest_episode, is_finish)

    async def init_telegram_info_by_season_id(self, season_id: int) -> Tuple[int, str, int, bool]:
        ''' 根据season_id初始化番剧信息

        Args:
            season_id (int): season_id

        Returns:
            Tuple[int, str, int, bool]: 
            返回一个元组
            [season_id, 番剧名, 最新集, 是否完结]
        '''

        async with httpx.AsyncClient(headers=self.__request_header__()) as client:
            try:
                await client.get(url=self.API["get_bili_cookie"])
                response = await client.get(url=self.API["get_telegram_info_by_season_id"].format(season_id))
            except Exception as e:
                raise BiliConnectionError(2, f"season_id:{season_id}", e.args[0])
            
            if response.status_code != 200:
                raise BiliStatusCodeError(2, f"season_id:{season_id}", response.status_code)
    
            response = response.json()
            if response["code"] == -404:
                raise BiliAPI404Error()
            elif response["code"] != 0:
                raise BiliAPIRetCodeError(2, f"season_id:{season_id}", response["code"], response["message"])

            season_title = response["result"]["title"]
            is_finish = bool(response["result"]["publish"]["is_finish"])
            latest_episode = len(response["result"]["episodes"])

            return (season_id, season_title, latest_episode, is_finish)

    async def init_telegram_info_by_media_id(self, media_id: int) -> Tuple[int, str, int, bool]:
        ''' 根据media_id初始化番剧信息

        Args:
            media_id (int): media_id

        Returns:
            Tuple[int, str, int, bool]: 
            返回一个元组
            [season_id, 番剧名, 最新集, 是否完结]
        '''

        async with httpx.AsyncClient(headers=self.__request_header__()) as client:
            try:
                await client.get(url=self.API["get_bili_cookie"])
                response = await client.get(url=self.API["get_telegram_info_by_media_id"].format(media_id))
            except Exception as e:
                raise BiliConnectionError(2, f"media_id:{media_id}", e.args[0])
            
            if response.status_code != 200:
                raise BiliStatusCodeError(2, f"media_id:{media_id}", response.status_code)
    
            response = response.json()
            if response["code"] == -404:
                raise BiliAPI404Error()
            elif response["code"] != 0:
                raise BiliAPIRetCodeError(2, f"media_id:{media_id}", response["code"], response["message"])

            season_id = response["result"]["media"]["season_id"]
            season_title = response["result"]["media"]["title"]
            is_finish = False
            latest_episode = int(response["result"]["media"]["new_ep"]["index"])

            return (season_id, season_title, latest_episode, is_finish)
    
    async def get_telegram_latest_episode(self, season_id: int, index: int) -> Tuple[bool, int, str, str, str, bool]:
        '''根据season_id获取番剧的最新集信息

        Args:
            season_id (int): season_id
            index (int): 记录的最新集数

        Returns:
            Tuple[bool, int, str, str, str, bool]: 
            返回一个元组
            [是否更新, 最新集数, 最新集标题, 最新集链接, 封面链接, 是否完结]
        '''

        async with httpx.AsyncClient(headers=self.__request_header__()) as client:
            try:
                await client.get(url=self.API["get_bili_cookie"])
                response = await client.get(url=self.API["get_telegram_latest_episode"].format(season_id))
            except Exception as e:
                raise BiliConnectionError(2, f"season_id:{season_id}", e.args[0])
            
            if response.status_code != 200:
                raise BiliStatusCodeError(2, f"season_id:{season_id}", response.status_code)
    
            response = response.json()
            if response["code"] != 0:
                raise BiliAPIRetCodeError(2, f"season_id:{season_id}", response["code"], response["message"])

            episodes = response['result']['episodes']
            is_finish = bool(response["result"]["publish"]["is_finish"])

            if len(episodes) > index:
                latest_episode = episodes[-1]
                cover_url = latest_episode['cover']
                title = latest_episode['long_title']
                play_url = latest_episode['share_url']
                
                return (True, len(episodes), title, play_url, cover_url, is_finish)
            else:
                return (False, 0, "", "", "", is_finish)
    
    async def parse_short_url(self, short_url: str) -> Tuple[int, str]:
        '''解析b23.tv的短链接,返回短链接类型以及目标id

        Args:
            short_url (str): 短链接

        Returns:
            Tuple[int, str]: 
            返回一个元组
            [类型:0-up的uid,1-主播的房间号,2-番剧的ep_id, 目标id]
        '''
        async with httpx.AsyncClient(headers=self.__request_header__()) as client:
            try:
                await client.get(url=self.API["get_bili_cookie"])
                response = await client.get(url=short_url)
            except Exception as e:
                raise BiliConnectionError(3, short_url, e.args[0])
            
            if response.status_code != 302:
                raise BiliStatusCodeError(3, short_url, response.status_code)
            
            origin_url = response.headers["Location"].split("?")[0]
            logger.debug(f"get origin url = {origin_url}")
            target_id = origin_url.split("/")[-1]
            if "space" in origin_url:
                return (0, target_id)
            elif "live" in origin_url:
                return (1, target_id)
            elif "bangumi" in origin_url:
                return (2, target_id)
            
            raise BiliInvalidShortUrl(short_url)
    
bili_client = BiliClient()