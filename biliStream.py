import requests
import json
from typing import Tuple, List
import sys
import traceback
import nonebot
import os
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Message, MessageSegment

__PLUGIN_NAME = "B站整合~直播"
baseUrl = 'https://api.bilibili.com/x/space/arc/search?mid={}&ps=30&tid=0&pn=1&keyword=&order=pubdate&jsonp=jsonp'
biliUserInfoUrl = 'https://api.bilibili.com/x/space/acc/info?mid={}&jsonp=jsonp'
biliLiveInfoUrl = 'https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={}&protocol=0,1&format=0,1,2&codec=0,1&qn=0&platform=web&ptype=8'
header = {
    'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv2.0.1) Gecko/20100101 Firefox/4.0.1'
}

streamDir = './src/plugins/nonebot_plugin_bilibilibot/file/stream/'

def GetBiliStream(uid: str) -> Tuple[bool, str, str]:
    """
    @description  :
    获取bilibili直播间信息
    ---------
    @param  :
    uid: 主播的uid，不是直播间号码
    -------
    @Returns  :
    返回一个元组
    [是否正在直播，直播间标题，直播间封面链接]
    -------
    """
    
    response = requests.get(url=biliUserInfoUrl.format(uid), headers=header)
    assert response.status_code == 200, '获取直播间信息时连接错误, status_code = {}'.format(response.status_code)

    response = json.loads(response.text)
    if response['code'] == 0:
        liveRoom = response['data']['live_room']
        liveStatus = liveRoom['liveStatus']
        title = liveRoom['title']
        coverURL = liveRoom['cover']

        if liveStatus == 1:
            return (True, title, coverURL)
    return (False, '', '')

async def CheckBiliStream():
    """
    @description  :
    检查streamDir中所有主播的开播状态
    如果关注的主播开播，则通知所有关注的用户
    如果主播下播了，则写入文件
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    #logger.info(f'[{__PLUGIN_NAME}]开始检测开播状态')
    streamerFiles = os.listdir(streamDir)
    for filename in streamerFiles:
        with open(streamDir + '/' + filename, 'r+') as f:
            #logger.info(f'[{__PLUGIN_NAME}]打开文件{filename}！')
            info = json.load(f)
            # [username, isStreaming, roomURL, [followers]]
            shouldUpdated = False
            schedBot = nonebot.get_bot()
            
            try:
                isStreaming, title, coverURL = GetBiliStream(filename.split('.')[0])
                if isStreaming and not info[1]:
                    logger.info(f'[{__PLUGIN_NAME}]检测到主播{info[0]}已开播！')
                    shouldUpdated = True
                    info[1] = True
                    textMsg = '【直播动态】\n<{}>正在直播!\n标题: {}\n链接: {}'.format(info[0], title, info[2])
                    
                    reportedMsg = Message([
                        MessageSegment(type='text', data={'text':textMsg}),
                        MessageSegment(type='image', data={'file':coverURL})
                    ])
                    
                    logger.info(f'[{__PLUGIN_NAME}]向粉丝发送开播通知')
                    for follower in info[3]:
                        await schedBot.send_msg(message=reportedMsg, user_id=follower)
                elif not isStreaming and info[1]:
                    logger.info(f"检测到主播{info[0]}已下播！")
                    shouldUpdated = True
                    info[1] = False
            except Exception as e:
                ex_type, ex_val, _ = sys.exc_info()
                exceptionMsg = '【错误报告】\n检测用户{}B站直播时发生错误\n错误类型: {}\n错误值: {}\n'.format(info[0], ex_type, ex_val)
                logger.error(f"{__PLUGIN_NAME}\n" + exceptionMsg + traceback.format_exc())
            
            if shouldUpdated:
                f.seek(0)
                f.truncate()
                json.dump(info, f) 

def InitStreamerInfo(uid: str) -> Tuple[str, str]:
    """
    @description  :
    根据uid，返回直播间信息
    ---------
    @param  :
    uid： 用户的uid
    -------
    @Returns  :
    返回一个元组
    [用户名，直播间链接]
    -------
    """
    
    response = requests.get(url=biliUserInfoUrl.format(uid), headers=header)
    response = json.loads(response.text)
    if response['code'] == 0:
        userName = response['data']['name']
        roomURL = response['data']['live_room']['url']
        logger.info(f"获取到uid为{uid}的用户名为{userName}, 直播间链接为{roomURL}")
        return (userName, roomURL)
    else:
        return ('', '')

def GetUidByRoomNumber(roomNumber: str) -> Tuple[bool, str]:
    """
    @description  :
    根据直播间号获得uid
    ---------
    @param  :
    roomNumber: 房间号
    -------
    @Returns  :
    返回一个元组
    [isSuccess, uid | '']
    -------
    """
    
    res = requests.get(url=biliLiveInfoUrl.format(roomNumber), headers=header)
    assert res.status_code == 200, "获取直播间信息时出现连接错误"
    res = json.loads(res.text)
    if res['code'] == 0:
        uid = res['data']['uid']
        logger.debug(f'{__PLUGIN_NAME}获取主播的uid为{uid}')
        return (True, str(uid))
    else:
        return (False, '')
    




async def FollowModifyStreamerFile(uid: str, userID: str) -> Tuple[bool, str]:
    """
    @description  :
    根据用户关注主播，修改主播文件
    ---------
    @param  :
    uid: 主播的uid
    userID: 用户的qq号
    -------
    @Returns  :
    返回一个元组
    [isSuccessful, userNam(uid) | uid(reason)]
    -------
    """
    
    if not uid.isdigit():
        logger.debug(f'{__PLUGIN_NAME}存在错误参数{uid}')
        return (False, uid + "(错误参数)")
    streamerFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/stream/{uid}.json"
    if os.path.exists(streamerFile):
        logger.debug(f"{__PLUGIN_NAME}主播{uid}文件已经存在")
        with open(streamerFile, "r+") as f:
            streamerInfo: List = json.load(f)
            # streamerInfo = [streamerName, isStreaming, roomURL, [followers]]
            logger.debug(f"{__PLUGIN_NAME}正在读取用户{streamerInfo[0]}文件")
            if userID not in streamerInfo[3]:
                streamerInfo[3].append(userID)
                logger.debug(f"{__PLUGIN_NAME}用户{userID}关注主播{streamerInfo[0]}成功")
                f.seek(0)
                f.truncate()
                json.dump(streamerInfo, f)
                return (True, streamerInfo[0] + f"(uid: {uid})")
            else:
                logger.debug(f"{__PLUGIN_NAME}用户{userID}已经关注了主播{streamerInfo[0]}")
                return (False, streamerInfo[0] + "(已关注)")
                
    else:
        logger.debug(f"{__PLUGIN_NAME}用户{uid}文件不存在")
        try:
            userName, roomURL = InitStreamerInfo(uid)
        except Exception:
            ex_type, ex_val, _ = sys.exc_info()
            logger.error(f'{__PLUGIN_NAME}获取主播{uid}信息时发生错误')
            logger.error(f'{__PLUGIN_NAME}错误类型: {ex_type},错误值: {ex_val}')
            return (False, uid + "(网络连接错误)")
        else:
            if userName and roomURL:
                streamerInfo = [userName, False, roomURL, [userID]]
                with open(streamerFile, "w+") as f:
                    json.dump(streamerInfo, f)
                logger.debug(f"{__PLUGIN_NAME}已创建主播{userName}的文件")
                logger.debug(f"{__PLUGIN_NAME}用户{userID}关注主播{streamerInfo[0]}成功")
                return (True, streamerInfo[0] + f"(uid: {uid})")
            elif userName:
                logger.debug(f'{__PLUGIN_NAME}用户{uid}无直播间')
                return (False, uid + "(该用户无直播间)")
            else:
                logger.debug(f'{__PLUGIN_NAME}用户{uid}不存在')
                return (False, uid + "(非法uid)")
                

async def UnfollowModifyStreamerFile(uid: str, userID: str) -> Tuple[bool, str]:
    """
    @description  :
    根据用户取关主播，修改主播文件
    ---------
    @param  :
    uid: 主播的uid
    userID: 用户的qq号
    -------
    @Returns  :
    返回一个元组
    [isSuccessful, userName | uid(reason)]
    -------
    """
    if uid.isdigit():
        streamerFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/stream/{uid}.json"
        if os.path.exists(streamerFile):
            with open(streamerFile, "r+") as f:
                streamerInfo: List = json.load(f)
                # streamerInfo = [streamerName, isStreaming, roomURL, [followers]]
                logger.debug(f"{__PLUGIN_NAME}正在读取用户{streamerInfo[0]}文件")
                if userID not in streamerInfo[3]:
                    logger.debug(f'{__PLUGIN_NAME}用户{userID}未关注主播{uid}')
                    return (False, uid + "(未关注)")
                else:
                    streamerInfo[3].remove(userID)
                    if streamerInfo[3]:
                        f.seek(0)
                        f.truncate()
                        json.dump(streamerInfo, f)
                    else:
                        logger.debug(f'{__PLUGIN_NAME}主播{streamerInfo[0]}已无人关注，将文件删除')
                        os.remove(streamerFile)
                        
                    logger.debug(f'{__PLUGIN_NAME}用户{userID}成功取关主播{streamerInfo[0]}')
                    return (True, streamerInfo[0] + f"(uid: {uid})")
        else:
            logger.debug(f'{__PLUGIN_NAME}用户{userID}未关注主播{uid}')
            return (False, uid + "(未关注)")
    else:
        return (False, uid + "(错误参数)")