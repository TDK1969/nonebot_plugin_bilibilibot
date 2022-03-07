import requests
import json
from typing import Tuple, List
import sys
import os
import traceback
import nonebot
from nonebot.log import logger
from nonebot import require
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import Arg, CommandArg, ArgPlainText
from nonebot import permission

__PLUGIN_NAME = "B站整合~视频"
baseUrl = 'https://api.bilibili.com/x/space/arc/search?mid={}&ps=30&tid=0&pn=1&keyword=&order=pubdate&jsonp=jsonp'
biliUserInfoUrl = 'https://api.bilibili.com/x/space/acc/info?mid={}&jsonp=jsonp'
header = {
    'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv2.0.1) Gecko/20100101 Firefox/4.0.1'
}
videoDir = "./src/plugins/nonebot_plugin_bilibilibot/file/up/"

# 视频
def GetLatestVideo(uid: str, lastPostTime: int) -> Tuple[bool, str, str, int, str]:
    """
    @description  :
    根据uid和时间戳, 返回元组，表示存在新视频或无新视频
    ---------
    @param  :
    uid: 查询新视频用户的uid
    lastPostTime: 文件中记录的最新视频的时间戳
    -------
    @Returns  :
    返回一个元组[是否更新，bv号，标题，发布时间戳，封面的链接]
    -------
    """
    
    response = requests.get(url = baseUrl.format(uid), headers=header)
    assert response.status_code == 200, '获取视频列表时连接出错, status_code = {}'.format(response.status_code)

    response = json.loads(response.text)
    assert len(response['data']['list']['vlist']) != 0, '用户{}无发布视频'.format(uid)
    latestVideo = response['data']['list']['vlist'][0] if len(response['data']['list']['vlist']) != 0 else 0
    postTime = int(latestVideo['created'])
    
    if postTime > lastPostTime:
        # 发现新视频
        title = latestVideo['title']
        bvID = latestVideo['bvid']
        picUrl = latestVideo['pic']
        return (True, bvID, title, postTime, picUrl)
    return (False, '', '', 0, '')

async def CheckUpUpdate():
    """
    @description  :
    检查关注UP主是否更新新视频，如果更新则通知用户并写入文件
    ---------
    @param  :
    -------
    @Returns  :
    -------
    """
    upFiles = os.listdir(videoDir)
    for filename in upFiles:
        with open(videoDir + '/' + filename, 'r+') as f:
            info = json.load(f)
            # upInfo = [upName, latestVideoTimeStamp, [followers]]
            shouldUpdated = False
            schedBot = nonebot.get_bot()

            try:
                res = GetLatestVideo(filename.split('.')[0], info[1])
                """
                res[0]: 是否更新
                res[1]: bv号
                res[2]: 视频标题
                res[3]: 发布时间(时间戳)
                res[4]: 封面链接
                """
                if res[0]:
                    logger.debug(f'{__PLUGIN_NAME}检测到up主{info[0]}更新了视频')
                    textMsg = "【B站动态】\n <{}> 更新了视频\n标题: {}\n链接: https://www.bilibili.com/video/{}".format(info[0], res[2], res[1])
                    for follower in info[2]:
                        logger.debug(f'{__PLUGIN_NAME}向用户{follower}发送更新通知')
                        await schedBot.send_msg(message=textMsg + MessageSegment.image(res[4]), user_id=follower)
                    info[1] = res[3]
                    f.seek(0)
                    f.truncate()
                    json.dump(info, f)

            except Exception as e:
                ex_type, ex_val, _ = sys.exc_info()
                exceptionMsg = '【错误报告】\n检测用户{}B站视频时发生错误\n错误类型: {}\n错误值: {}\n'.format(info[0], ex_type, ex_val)
                await schedBot.send_msg(message=exceptionMsg, user_id="793065367")
                logger.error(f"{__PLUGIN_NAME}" + exceptionMsg + traceback.format_exc())


"""
bilibili视频更新关注命令
"""

def InitUpInfo(uid: str) -> Tuple[str, int]:
    """
    @description  :
    根据uid查询up主信息
    ---------
    @param  :
    uid：用户的uid
    -------
    @Returns  :
    返回一个元组
    [up主名字，最新视频的时间戳]
    -------
    """
    
    
    response = requests.get(url=biliUserInfoUrl.format(uid), headers=header)
    response = json.loads(response.text)
    if response['code'] == 0:
        userName = response['data']['name']
        res = GetLatestVideo(uid, 0)
        return (userName, res[3])
    else:
        return ('', '')

async def FollowModifyUpFile(uid: str, userID: str) -> Tuple[bool, str]:
    """
    @description  :
    根据用户关注up，修改up文件
    ---------
    @param  :
    uid: up的uid
    userID: 用户的qq号
    -------
    @Returns  :
    返回一个元组
    [isSuccessful, userName(uid) | uid(reason)]
    -------
    """
    if uid.isdigit():
        upFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/up/{uid}.json"
        if os.path.exists(upFile):
            logger.debug(f"{__PLUGIN_NAME}up主文件{upFile}已经存在")
            with open(upFile, "r+") as f:
                upInfo: List = json.load(f)
                # upInfo = [upName, latestVideoTimeStamp, [followers]]
                logger.debug(f"{__PLUGIN_NAME}正在读取up主{upInfo[0]}文件")
                if userID not in upInfo[2]:
                    upInfo[2].append(userID)
                    logger.debug(f"{__PLUGIN_NAME}用户{userID}关注up主{upInfo[0]}成功")
                    f.seek(0)
                    f.truncate()
                    json.dump(upInfo, f)
                    return (True, upInfo[0] + f"(uid: {uid})")
                else:
                    logger.debug(f"{__PLUGIN_NAME}用户{userID}已经关注了up{upInfo[0]}")
                    return (False, upInfo[0] + "(已关注)")
        else:
            logger.debug(f"{__PLUGIN_NAME}up主{uid}文件不存在")
            
            try:
                userName, latestTimeStamp = InitUpInfo(uid)
            except Exception:
                ex_type, ex_val, _ = sys.exc_info()
                logger.error(f'{__PLUGIN_NAME}获取up主{uid}信息时发生错误')
                logger.error(f'{__PLUGIN_NAME}错误类型: {ex_type},错误值: {ex_val}')
                return (False, uid + "(网络连接错误)")
            else:
                if userName:
                    upInfo = [userName, latestTimeStamp, [userID]]
                    with open(upFile, "w+") as f:
                        json.dump(upInfo, f)
                    logger.debug(f"{__PLUGIN_NAME}已创建up主{userName}的文件")
                    logger.debug(f"{__PLUGIN_NAME}用户{userID}关注up{upInfo[0]}成功")
                    return (True, upInfo[0] + f"(uid: {uid})")
                else:
                    logger.debug(f'{__PLUGIN_NAME}up{uid}不存在，请检查uid')
                    return (False, uid + "(uid错误)")
    else:
        return (False, uid + "(错误参数)")

async def UnfollowModifyUpFile(uid: str, userID: str) -> Tuple[bool, str]:
    """
    @description  :
    根据用户取关up，修改up主文件
    ---------
    @param  :
    uid: up的uid
    userID: 用户的qq号
    -------
    @Returns  :
    返回一个元组
    [isSuccessful, userName | uid(reason)]
    -------
    """
    if uid.isdigit():
        upFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/up/{uid}.json"
        if os.path.exists(upFile):
            with open(upFile, "r+") as f:
                upInfo: List = json.load(f)
                # upInfo = [upName, latestVideoTimeStamp, [followers]]
                logger.debug(f"{__PLUGIN_NAME}正在读取用户{upInfo[0]}文件")
                if userID not in upInfo[2]:
                    logger.debug(f'{__PLUGIN_NAME}用户{userID}未关注up主{uid}')
                    return (False, uid + "(未关注)")
                else:
                    upInfo[2].remove(userID)
                    if upInfo[2]:
                        f.seek(0)
                        f.truncate()
                        json.dump(upInfo, f)
                    else:
                        logger.debug(f'{__PLUGIN_NAME}up主{upInfo[0]}已无人关注，将文件删除')
                        os.remove(upFile)
                        
                    logger.debug(f'{__PLUGIN_NAME}用户{userID}成功取关up主{upInfo[0]}')
                    return (True, upInfo[0]  + f"(uid: {uid})")
        else:
            logger.debug(f'{__PLUGIN_NAME}用户{userID}未关注up主{uid}')
            return (False, uid + "(未关注)")
    else:
        return (False, uid + "(错误参数)")