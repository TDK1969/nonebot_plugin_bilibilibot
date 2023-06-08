import sys
from functools import reduce
from hashlib import md5
import urllib.parse
import time
import requests

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    '对 imgKey 和 subKey 进行字符顺序打乱编码'
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    '为请求参数进行 wbi 签名'
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time                                   # 添加 wts 字段
    params = dict(sorted(params.items()))                       # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k : ''.join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v
        in params.items()
    }
    query = urllib.parse.urlencode(params)                      # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()    # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params

def getWbiKeys() :
    '获取最新的 img_key 和 sub_key'
    resp = requests.get('https://api.bilibili.com/x/web-interface/nav')
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key


def get_query(**parameters: dict):
    """
    获取签名后的查询参数
    """
    img_key, sub_key = getWbiKeys()
    signed_params = encWbi(
        params=parameters,
        img_key=img_key,
        sub_key=sub_key
    )
    query = urllib.parse.urlencode(signed_params)
    return query


if __name__ == "__main__":
    session = requests.session()
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36"
    }
    session.get("https://www.bilibili.com", verify=False)
    API = {
        # 用于获取临时cookie
        "get_bili_cookie": "https://www.bilibili.com",
        "get_user_info_by_uid": "https://api.bilibili.com/x/space/wbi/acc/info?",  # 需要修改
        "get_latest_video_by_uid": "https://api.bilibili.com/x/space/wbi/arc/search?",  # 需要修改
        "get_live_info_by_room_id": "https://api.live.bilibili.com/room/v1/Room/get_info?room_id=",
        "get_liver_info_by_uid": "https://api.live.bilibili.com/live_user/v1/Master/info?uid=",
        "get_telegram_info_by_media_id": "https://api.bilibili.com/pgc/review/user?media_id=",
        "get_telegram_info_by_ep_id": "https://api.bilibili.com/pgc/view/web/season?ep_id=",
        "get_telegram_info_by_season_id": "https://api.bilibili.com/pgc/view/web/season?season_id=",
        "get_telegram_latest_episode": "https://api.bilibili.com/pgc/view/web/season?season_id=",
        "get_dynamic_list_by_uid": "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?", # buvid3 需要认证，post请求到https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi
        "get_detail_dynamic_by_id": "https://t.bilibili.com/",
        "validate_buvid3": "https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi"
    }
    uid = "2487065"
    # session.post("https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi", verify=False, json={
	#     "payload": '{"39c8":"333.999.fp.risk","3c43":{"adca":"Win","80c9":[]}}'
    # })
    import httpx
    # res = session.get(f'{API["get_dynamic_list_by_uid"]}host_mid={uid}', verify=False)
    # print(res.json())
    import asyncio

    async def run():
        async with httpx.AsyncClient(headers=session.headers, verify=False) as client:
            await client.get(url=API["get_bili_cookie"])
            await client.post(API["validate_buvid3"], json={
                "payload": '{"39c8":"333.999.fp.risk","3c43":{"adca":"Win","80c9":[]}}'
            })
            await client.get(f'{API["get_dynamic_list_by_uid"]}host_mid={uid}')

    asyncio.run(run())
