import asyncio
#from .db import bili_database
#from .exception import BiliConnectionError, BiliDatebaseError
import httpx
import json
from typing import Dict, Tuple, List
import sys
import traceback
import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
#import basicFunc
#from .basicFunc import *

__PLUGIN_NAME = "B站整合~动态"
GET_NEWS_BY_UID_API = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={}&timezone_offset=-480"
DYNAMIC_DETAIL_URL = "https://t.bilibili.com/{}"
header = {
    'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv2.0.1) Gecko/20100101 Firefox/4.0.1'
}

async def get_latest_news(uid: str, pin_news_id: str, record_timestamp: int) -> Tuple[str, List[Dict]]:
    '''根据uid获取最新的动态

    Args:
        uid (str): 查询的uid
        pin_news_id (str): 数据库中记录置顶动态的id,无则返为""
        record_timestamp (int): 数据库中记录最新动态的时间戳

    Returns:
        Tuple[str, Dict]: 
        str - 置顶动态id
        List[Dict] - 更新的动态内容
    ''' 
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url=GET_NEWS_BY_UID_API.format(uid), headers=header)
    except Exception as e:
        pass
        raise BiliConnectionError(f"获取用户 <{uid}> 的动态时发生网络错误:{e.args[0]}")
    if response.status_code != 200:
        pass
        raise BiliConnectionError(f"获取用户 <{uid}> 的动态时连接出错:状态码={response.status_code}")
    response: Dict = response.json()
    if response["code"] != 0:
        raise BiliConnectionError(f"获取用户 <{uid}> 的动态时发生错误:{response['message']}")
    
    news_list: List = response["data"]["items"]

    # 如果动态列表长度为0则直接返回
    if len(news_list) == 0:
        return ("", [])
    
    update_news_list = []
    has_pin_news = 0
    top_news_id = ""

    # 处理置顶动态
    top_news = news_list[0]
    if "module_tag" in top_news["modules"] and top_news["modules"]["module_tag"]["text"] == "置顶":
        # 如果存在置顶动态,判断与数据库中记录的是否相同
        has_pin_news = 1
        top_news_id: str = top_news["id_str"]
        if top_news_id == pin_news_id:
            # 如果相同,则跳过该动态
            pass
        else:
            # 如果置顶动态发生更换
            # 处理置顶旧动态的情况,如果置顶旧动态,则不需要更新通知;
            logger.debug(f'{__PLUGIN_NAME} <{uid}> 的置顶动态发生变化,由{pin_news_id}变为{top_news_id}')
            major_module: Dict = top_news["modules"]["module_dynamic"]["major"]
            additional_module: Dict = top_news["modules"]["module_dynamic"]["additional"]
            desc_module: Dict  = top_news["modules"]["module_dynamic"]["desc"]
            top_news_timestamp: int = top_news["modules"]["module_author"]["pub_ts"]
            top_news_major_type = major_module["type"] if major_module else "MAJOR_TYPE_NONE"
            top_news_add_type = additional_module["type"] if additional_module else "ADDITIONAL_TYPE_NONE"

            if top_news_timestamp > record_timestamp:
                # 置顶动态是新动态,需要通知
                temp_news = {}
                temp_news["tag"] = "NORMAL"
                temp_news["news_id"] = top_news_id
                temp_news["text"] = desc_module["text"] if desc_module else ""
                temp_news["image"] = []
                temp_news["timestamp"] = top_news_timestamp

                if top_news_major_type == "MAJOR_TYPE_DRAW":
                    for image_item in major_module["draw"]["items"]:
                        temp_news["image"].append(image_item["src"])
                elif top_news_major_type == "MAJOR_TYPE_ARTICLE":
                    temp_news["tag"] = "MAJOR_ARTICLE"
                    temp_news["article"] = {
                        "title": major_module["article"]["title"],
                        "cover": major_module["article"]["covers"][0],
                        "jump_url": major_module["article"]["jump_url"]
                    }
                if top_news_add_type == "ADDITIONAL_TYPE_VOTE":
                    temp_news["tag"] = "ADD_VOTE"
                    temp_news["vote"] = {
                        "desc": additional_module["vote"]["desc"],
                        "vote_id": additional_module["vote"]["vote_id"]
                    }
                elif top_news_add_type == "ADDITIONAL_TYPE_UGC":
                    temp_news["tag"] = "ADD_UGC"
                    temp_news["tgc"] = {
                        "title" : additional_module["ugc"]["title"],
                        "jump_url": additional_module["ugc"]["jump_url"],
                        "cover": additional_module["ugc"]["cover"]
                    }
                elif top_news_add_type == "ADDITIONAL_TYPE_RESERVE":
                    temp_news["tag"] = "ADD_RESERVE",
                    temp_news["reserve"] = {
                        "title": additional_module["reserve"]["title"],
                        "desc": additional_module["reserve"]["desc1"]["text"]
                    }
                    
                if top_news_major_type in ("MAJOR_TYPE_DRAW", "MAJOR_TYPE_NONE", "MAJOR_TYPE_ARTICLE"):
                    update_news_list.append(temp_news)
                    print(json.dumps(temp_news, ensure_ascii=False, indent=4))
    
    # 处理置顶动态外的动态
    for news_item in news_list[has_pin_news:]:
        news_id = news_item["id_str"]
        major_module: Dict = news_item["modules"]["module_dynamic"]["major"]
        additional_module: Dict = news_item["modules"]["module_dynamic"]["additional"]
        desc_module: Dict  = news_item["modules"]["module_dynamic"]["desc"]
        news_item_major_type = major_module["type"] if major_module else "MAJOR_TYPE_NONE"
        news_item_add_type = additional_module["type"] if additional_module else "ADDITIONAL_TYPE_NONE"
        news_timestamp = news_item["modules"]["module_author"]["pub_ts"]
        
        if news_timestamp <= record_timestamp:
            break
        # 发现新动态
        logger.debug(f'{__PLUGIN_NAME} <{uid}> 更新了动态 {news_id}')
        temp_news = {}
        temp_news["tag"] = "NORMAL"
        temp_news["news_id"] = news_id
        temp_news["text"] = desc_module["text"] if desc_module else ""
        temp_news["image"] = []
        temp_news["timestamp"] = news_timestamp

        if news_item_major_type == "MAJOR_TYPE_DRAW":
            for image_item in major_module["draw"]["items"]:
                temp_news["image"].append(image_item["src"])
        elif news_item_major_type == "MAJOR_TYPE_ARTICLE":
            temp_news["tag"] = "MAJOR_ARTICLE"
            temp_news["article"] = {
                "title": major_module["article"]["title"],
                "cover": major_module["article"]["covers"][0],
                "jump_url": major_module["article"]["jump_url"]
            }
        if news_item_add_type == "ADDITIONAL_TYPE_VOTE":
            temp_news["tag"] = "ADD_VOTE"
            temp_news["vote"] = {
                "desc": additional_module["vote"]["desc"],
                "vote_id": additional_module["vote"]["vote_id"]
            }
        elif news_item_add_type == "ADDITIONAL_TYPE_UGC":
            temp_news["tag"] = "ADD_UGC"
            temp_news["tgc"] = {
                "title" : additional_module["ugc"]["title"],
                "jump_url": additional_module["ugc"]["jump_url"],
                "cover": additional_module["ugc"]["cover"]
            }
        elif news_item_add_type == "ADDITIONAL_TYPE_RESERVE":
            temp_news["tag"] = "ADD_RESERVE",
            temp_news["reserve"] = {
                "title": additional_module["reserve"]["title"],
                "desc": additional_module["reserve"]["desc1"]["text"]
            }
            
        if news_item_major_type in ("MAJOR_TYPE_DRAW", "MAJOR_TYPE_NONE", "MAJOR_TYPE_ARTICLE"):
            update_news_list.append(temp_news)
            print(json.dumps(temp_news, ensure_ascii=False, indent=4))
    
    return (top_news_id, update_news_list)

loop = asyncio.get_event_loop()
tasks = [get_latest_news("6700458", "", 0)]
loop.run_until_complete(asyncio.wait(tasks))

                


    










