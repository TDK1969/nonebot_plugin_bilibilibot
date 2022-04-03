import requests
import json
from typing import Tuple, List, Union
import sys
import os
import traceback
import nonebot
from nonebot.log import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from .basicFunc import *
__PLUGIN_NAME = "B站整合~视频"
baseUrl = 'https://api.bilibili.com/x/space/arc/search?mid={}&ps=30&tid=0&pn=1&keyword=&order=pubdate&jsonp=jsonp'
biliUserInfoUrl = 'https://api.bilibili.com/x/space/acc/info?mid={}&jsonp=jsonp'
header = {
    'User-Agent':'Mozilla/5.0 (Windows NT 6.1; rv2.0.1) Gecko/20100101 Firefox/4.0.1'
}
videoDir = f"{PackagePath}/file/up/"

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
    #assert len(response['data']['list']['vlist']) != 0, '用户{}无发布视频'.format(uid)
    latestVideo = response['data']['list']['vlist'][0] if len(response['data']['list']['vlist']) != 0 else 0
    postTime = int(latestVideo['created']) if len(response['data']['list']['vlist']) else 0
    
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
            # upInfo = [upName, latestVideoTimeStamp, [userfollowers], [groupfollowers]]
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
                    logger.info(f'{__PLUGIN_NAME}检测到up主{info[0]}更新了视频')
                    textMsg = "【B站动态】\n <{}> 更新了视频\n标题: {}\n链接: https://www.bilibili.com/video/{}".format(info[0], res[2], res[1])
                    
                    for follower in info[2]:
                        logger.debug(f'{__PLUGIN_NAME}向用户{follower}发送更新通知')
                        await schedBot.send_msg(message=textMsg + MessageSegment.image(res[4]), user_id=follower)
                    
                    for group in info[3]:
                        await schedBot.send_msg(message=textMsg + MessageSegment.image(res[4]), group_id=group)
                    
                    info[1] = res[3]
                    f.seek(0)
                    f.truncate()
                    json.dump(info, f, ensure_ascii=False)

            except Exception as e:
                ex_type, ex_val, _ = sys.exc_info()
                exceptionMsg = '【错误报告】\n检测用户{}B站视频时发生错误\n错误类型: {}\n错误值: {}\n'.format(info[0], ex_type, ex_val)
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

async def FollowModifyUpFile(uid: str, userID: int, type: int) -> Tuple[bool, str]:
    '''根据用户或群关注up，修改up文件

    Args:
        uid (str): up的uid
        userID (int): 用户的qq或群号
        type (int): 0-个人用户，1-群

    Returns:
        Tuple[bool, str]: [是否成功，信息]
    '''
    
    if uid.isdigit():
        upFile = f"{PackagePath}/file/up/{uid}.json"
        if os.path.exists(upFile):
            logger.debug(f"{__PLUGIN_NAME}up主文件{upFile}已经存在")

            with open(upFile, "r+") as f:
                upInfo: List = json.load(f)
                # upInfo = [upName, latestVideoTimeStamp, [userFollowers], [groupFollowers]]
                logger.debug(f"{__PLUGIN_NAME}正在读取up主{upInfo[0]}文件")
                if userID not in upInfo[2 + type]:
                    upInfo[2 + type].append(userID)
                    logger.debug(f"{__PLUGIN_NAME}用户/群{userID}关注up主{upInfo[0]}成功")
                    f.seek(0)
                    f.truncate()
                    json.dump(upInfo, f, ensure_ascii=False)
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
                    upInfo = [userName, latestTimeStamp, [], []]
                    upInfo[2 + type].append(userID)

                    with open(upFile, "w+") as f:
                        json.dump(upInfo, f, ensure_ascii=False)
                    
                    logger.debug(f"{__PLUGIN_NAME}已创建up主{userName}的文件")
                    logger.debug(f"{__PLUGIN_NAME}用户{userID}关注up{upInfo[0]}成功")
                    return (True, upInfo[0] + f"(uid: {uid})")
                else:
                    logger.debug(f'{__PLUGIN_NAME}up{uid}不存在，请检查uid')
                    return (False, uid + "(uid错误)")
    else:
        return (False, uid + "(错误参数)")

async def UnfollowModifyUpFile(uid: str, userID: int, type: int) -> Tuple[bool, str]:
    '''根据个人用户或群取关up主，修改up文件

    Args:
        uid (str): up的uid
        userID (int): 用户的qq号/群号
        type (int): 0-个人用户，1-群

    Returns:
        Tuple[bool, str]: [是否成功，信息]
    '''
    
    if uid.isdigit():
        upFile = f"{PackagePath}/file/up/{uid}.json"
        if os.path.exists(upFile):
            with open(upFile, "r+") as f:
                upInfo: List = json.load(f)
                # upInfo = [upName, latestVideoTimeStamp, [userFollowers], [groupFollowers]]
                logger.debug(f"{__PLUGIN_NAME}正在读取用户{upInfo[0]}文件")
                if userID not in upInfo[2 + type]:
                    logger.debug(f'{__PLUGIN_NAME}用户{userID}未关注up主{uid}')
                    return (False, uid + "(未关注)")
                else:
                    upInfo[2 + type].remove(userID)
                    if upInfo[2] or upInfo[3]:
                        f.seek(0)
                        f.truncate()
                        json.dump(upInfo, f, ensure_ascii=False)
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

async def FollowUp(
    event: Union[PrivateMessageEvent, GroupMessageEvent], 
    id: int, 
    uidList: List[str],
    type: int
    ) -> List[List[str]]:
    '''个人用户/群关注up主

    Args:
        event (Union[PrivateMessageEvent, GroupMessageEvent]): 消息事件
        id (int): qq号/群号
        uidList (List[str]): up主的uid
        type (int): 0-个人用户，1-群        

    Returns:
        List[List[str]]: [是否成功，信息]
    '''
    userFile = f"{PackagePath}/file/{'user' if type == 0 else 'group'}/{id}.json"
    successList = []
    failList = []

    for uid in uidList:
        isSuccess, s = await FollowModifyUpFile(uid, id, type)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)

    if os.path.exists(userFile):
        await FollowModifyUserFile(userFile, successList, 2)
    else:
        logger.debug(f'{__PLUGIN_NAME}用户文件{userFile}不存在, 准备创建')
        name = event.sender.nickname

        if type == 1:
            bot = get_bot()
            groupInfo = await bot.get_group_info(group_id=id)
            name = groupInfo["group_name"]

        await createUserFile(userFile, name, ups=successList)
    
    return [successList, failList]

async def UnfollowUp(
    event: Union[PrivateMessageEvent, GroupMessageEvent], 
    id: int, 
    uidList: List[str],
    type: int
    ) -> List[List[str]]:
    '''个人用户/群取关up主

    Args:
        event (Union[PrivateMessageEvent, GroupMessageEvent]): 消息事件
        id (int): qq号/群号
        uidList (List[str]): 取关的up主
        type (int): 0-个人用户，1-群

    Returns:
        List[List[str]]: [是否成功，信息]
    '''
    userFile = f"{PackagePath}/file/{'user' if type == 0 else 'group'}/{id}.json"
    successList = []
    failList = []

    for uid in uidList:
        isSuccess, s = await UnfollowModifyUpFile(uid, id, type)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)
    
    if os.path.exists(userFile):
        await UnfollowModifyUserFile(userFile, successList, 2)
    else:
        logger.debug(f'{__PLUGIN_NAME}用户文件{userFile}不存在, 准备创建')
        name = event.sender.nickname

        if type == 1:
            bot = get_bot()
            groupInfo = await bot.get_group_info(group_id=id)
            name = groupInfo["group_name"]
        
        await createUserFile(userFile, name)

    return [successList, failList]