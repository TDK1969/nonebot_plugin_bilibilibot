from nonebot import get_driver, on_command, on_message, require, permission, get_bot
from nonebot.rule import to_me
from nonebot.log import logger
from nonebot.rule import to_me, regex

from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, MessageSegment, MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND, GROUP_MEMBER
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg


from .config import Config

from .biliStream import *
from .biliVideo import *
from .biliTelegram import *
from .basicFunc import *
from .rule import groupMessageRule, privateMessageRule

import os
import json
import sys
import re
from typing import Union

global_config = get_driver().config
config = Config.parse_obj(global_config)

__PLUGIN_NAME = "[B站整合]"
__PLUGIN_NAME_STREAM = "[B站整合~直播]"
__PLUGIN_NAME_VIDEO = "[B站整合~视频]"
__PLUGIN_NAME_TELE = "[B站整合~影视]"

followStreamerCommand = on_command("关注主播", permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND)
@followStreamerCommand.handle()
async def followStreamerCommandHandler(event: Union[PrivateMessageEvent, GroupMessageEvent], args: Message = CommandArg()):
    uidList = args.extract_plain_text().split()
    if isinstance(event, PrivateMessageEvent):
        successList, failList = await FollowStreamers(event, event.sender.user_id, uidList, 0)
    if isinstance(event, GroupMessageEvent):
        successList, failList = await FollowStreamers(event, event.group_id, uidList, 1)
    await followStreamerCommand.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

"""
userFollowStreamer = on_message(rule=privateMessageRule & regex("^关注主播([ ]+[\d]+)+"), permission=PRIVATE_FRIEND)
@userFollowStreamer.handle()
async def userFollowStreamerHandler(event: PrivateMessageEvent):
    '''响应个人关注主播信息, 将主播加入用户的关注主播列表（如果无文件则建立），将用户加入主播的列表
    可同时关注多个主播

    Args:
        event (GroupMessageEvent): 消息事件     
        args (Message, optional): 命令参数. Defaults to CommandArg().
    '''
    
    uidList = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList =  await FollowStreamers(event, event.sender.user_id, uidList, 0)
    await userFollowStreamer.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

groupFollowStreamer = on_message(rule=groupMessageRule & regex("^关注主播([ ]+[\d]+)+"), permission=GROUP_ADMIN | GROUP_OWNER)
@groupFollowStreamer.handle()
async def groupFollowStreamerHandler(event: GroupMessageEvent):
    '''响应群关注主播信息, 将主播加入群的关注主播列表（如果无文件则建立），将群加入主播的列表
    可同时关注多个主播

    Args:
        event (GroupMessageEvent): 消息事件     
        args (Message, optional): 命令参数. Defaults to CommandArg().
    '''
    logger.debug(f'{__PLUGIN_NAME}收到消息{event.get_message}')
    
    uidList = event.get_message().extract_plain_text().split(' ')[1:]
    logger.debug(f'{__PLUGIN_NAME}uidList = {uidList}')
    
    #uidList = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await FollowStreamers(event, event.group_id, uidList, 1)
    await groupFollowStreamer.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")
"""

userUnfollowStreamer = on_message(rule=privateMessageRule & regex("^取关主播([ ]+[\d]+)+"), permission=PRIVATE_FRIEND)
@userUnfollowStreamer.handle()
async def userUnfollowStreamerHandler(event: PrivateMessageEvent):
    '''响应个人取关主播命令，从用户的关注主播列表中移除取关主播，同时主播的关注列表中去除用户
    可以同时取关多个主播

    Args:
        matcher (Matcher): _description_
        event (Union[PrivateMessageEvent, GroupMessageEvent]): 消息事件
        args (Message, optional): 命令参数. Defaults to CommandArg().
    '''
    
    uidList = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await UnfollowStreamers(event, event.sender.user_id, uidList, 0)
    await userUnfollowStreamer.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

groupUnfollowStreamer = on_message(rule=groupMessageRule & regex("^取关主播([ ]+[\d]+)+"), permission=GROUP_ADMIN | GROUP_OWNER)
@groupUnfollowStreamer.handle()
async def groupUnfollowStreamerHandler(event: GroupMessageEvent):
    '''响应取关群主播消息，从群的关注主播列表中移除取关主播，同时主播的关注列表中去除群
    可以同时取关多个主播

    Args:
        matcher (Matcher): _description_
        event (Union[PrivateMessageEvent, GroupMessageEvent]): 消息事件
        args (Message, optional): 命令参数. Defaults to CommandArg().
    '''
    
    uidList = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await UnfollowStreamers(event, event.group_id, uidList, 1)
    await groupUnfollowStreamer.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")


listUserFollowing = on_command("listFollowing", rule=privateMessageRule, aliases={"查询关注", "查询成分"}, permission=PRIVATE_FRIEND)
@listUserFollowing.handle()
async def listUserFollowingHandler(event: PrivateMessageEvent):
    '''响应个人用户查询关注命令，根据参数返回查询的内容

    Args:
        event (MessageEvent): 消息事件
        args (Message, optional): 合法的参数有：主播、up主、番剧，可以同时带有多项参数. Defaults to CommandArg().
    '''
    
    inputArgs = event.get_message().extract_plain_text().split(' ')[1:]
    logger.debug(f'{__PLUGIN_NAME}查询成分命令输入的参数为{inputArgs}')
    
    userID = event.sender.user_id # 命令发出者的QQ
    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
    defaultArgs = ['直播', 'up主', '番剧']

    exceptArgs = set(inputArgs) - set(defaultArgs)
    if len(exceptArgs) != 0:
        logger.debug(f'{__PLUGIN_NAME}查询失败，存在错误参数{exceptArgs}')
        await listUserFollowing.finish(f"查询失败，存在错误参数:{exceptArgs}\n请正确输入命令,例如: '查询成分 直播' 或 '查询成分 直播 up主 番剧'")
    
    if os.path.exists(userFile):
        with open(userFile, "r+") as f:
            logger.debug(f'{__PLUGIN_NAME}打开用户文件{userFile}')
            userInfo = json.load(f)

        if not inputArgs:
            inputArgs = defaultArgs
        if '直播' in inputArgs:
            if userInfo[1]:
                textMsg = '关注的主播:\n'
                for info in userInfo[1]:
                    textMsg += '> ' + info + '\n'
            else:
                textMsg = '无关注的主播'
            await listUserFollowing.send(textMsg)
        if 'up主' in inputArgs:
            if userInfo[2]:
                textMsg = '关注的up主\n'
                for info in userInfo[2]:
                    textMsg += '> ' + info + '\n'
            else:
                textMsg = '无关注的up主'
            await listUserFollowing.send(textMsg)
        if '番剧' in inputArgs:
            if userInfo[3]:
                textMsg = '关注的番剧\n'
                for info in userInfo[3]:
                    textMsg += '> '+ info + '\n'
            else:
                textMsg = '无关注的番剧'
            await listUserFollowing.send(textMsg)
        await listUserFollowing.finish()
    else:
        logger.debug(f'{__PLUGIN_NAME}用户文件不存在，准备创建')
        await createUserFile(userFile, nickName=event.sender.nickname)
        await listUserFollowing.finish("关注列表为空")

listGroupFollowing = on_command("listFollowing", rule=groupMessageRule, aliases={"查询关注", "查询成分"}, permission=GROUP_OWNER | GROUP_ADMIN)
@listGroupFollowing.handle()
async def listGroupFollowingHandler(event: GroupMessageEvent):
    '''响应群查询关注命令，根据参数返回查询的内容

    Args:
        event (GroupMessageEvent): 消息事件
        args (Message, optional): 合法的参数有：主播、up主、番剧，可以同时带有多项参数. Defaults to CommandArg().
    '''
    
    inputArgs = event.get_message().extract_plain_text().split(' ')[1:]
    logger.debug(f'{__PLUGIN_NAME}查询成分命令输入的参数为{inputArgs}')
    
    groupID = event.group_id # 命令发出者的QQ
    groupFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/group/{groupID}.json"
    defaultArgs = ['直播', 'up主', '番剧']

    exceptArgs = set(inputArgs) - set(defaultArgs)
    if len(exceptArgs) != 0:
        logger.debug(f'{__PLUGIN_NAME}查询失败，存在错误参数{exceptArgs}')
        await listGroupFollowing.finish(f"查询失败，存在错误参数:{exceptArgs}\n请正确输入命令,例如: '查询成分 直播' 或 '查询成分 直播 up主 番剧'")
    
    if os.path.exists(groupFile):
        with open(groupFile, "r+") as f:
            logger.debug(f'{__PLUGIN_NAME}打开群文件{groupFile}')
            userInfo = json.load(f)

        if not inputArgs:
            inputArgs = defaultArgs
        if '直播' in inputArgs:
            if userInfo[1]:
                textMsg = '关注的主播:\n'
                for info in userInfo[1]:
                    textMsg += '> ' + info + '\n'
            else:
                textMsg = '无关注的主播'
            await listGroupFollowing.send(textMsg)
        if 'up主' in inputArgs:
            if userInfo[2]:
                textMsg = '关注的up主\n'
                for info in userInfo[2]:
                    textMsg += '> ' + info + '\n'
            else:
                textMsg = '无关注的up主'
            await listGroupFollowing.send(textMsg)
        if '番剧' in inputArgs:
            if userInfo[3]:
                textMsg = '关注的番剧\n'
                for info in userInfo[3]:
                    textMsg += '> '+ info + '\n'
            else:
                textMsg = '无关注的番剧'
            await listGroupFollowing.send(textMsg)
        await listGroupFollowing.finish()
    else:
        logger.debug(f'{__PLUGIN_NAME}群文件不存在，准备创建')
        bot = get_bot()
        groupInfo = bot.get_group_info(groupID)
        name = groupInfo["group_name"]
        await createUserFile(groupFile, name)
        await listGroupFollowing.finish("关注列表为空")

userFollowUp = on_message(rule=privateMessageRule & regex("^关注up([ ]+[\d]+)+"), permission=PRIVATE_FRIEND)
@userFollowUp.handle()
async def userFollowUpHandler(event: PrivateMessageEvent):
    '''响应个人关注up主信息，关注up主，修改文件

    Args:
        event (PrivateMessageEvent): 消息事件
        args (Message, optional): 关注的up主的uid. Defaults to CommandArg().
    '''
    
    uidList = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await FollowUp(event, event.sender.user_id, uidList, 0)
    await userFollowUp.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

groupFollowUp = on_message(rule=groupMessageRule & regex("^关注up([ ]+[\d]+)+"), permission=GROUP_ADMIN | GROUP_OWNER)
@groupFollowUp.handle()
async def groupFollowUpHandler(event: GroupMessageEvent):
    '''响应群关注up主信息，关注up主，修改文件

    Args:
        event (PrivateMessageEvent): 消息事件
        args (Message, optional): 关注的up主的uid. Defaults to CommandArg().
    '''
    
    uidList = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await FollowUp(event, event.group_id, uidList, 1)
    await groupFollowUp.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

userUnfollowUp = on_message(rule=privateMessageRule & regex("^取关up([ ]+[\d]+)+"), permission=PRIVATE_FRIEND)
@userUnfollowUp.handle()
async def userUnfollowUpHandler(event: PrivateMessageEvent):
    '''响应个人用户取关up主信息，取关up主

    Args:
        event (PrivateMessageEvent): 消息事件
        args (Message, optional): 取关的up主uid. Defaults to CommandArg().
    '''

    uidList = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await UnfollowUp(event, event.sender.user_id, uidList, 0)
    await userUnfollowUp.finish(f"取关成功: \n{successList}\n取关失败:\n{failList}")

groupUnfollowUp = on_message(rule=groupMessageRule & regex("^取关up([ ]+[\d]+)+"), permission=GROUP_ADMIN | GROUP_OWNER)
@groupUnfollowUp.handle()
async def groupUnfollowUpHandler(event: GroupMessageEvent):
    '''响应个人用户取关up主信息，取关up主

    Args:
        event (PrivateMessageEvent): 消息事件
        args (Message, optional): 取关的up主uid. Defaults to CommandArg().
    '''

    uidList = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await UnfollowUp(event, event.group_id, uidList, 1)
    await groupUnfollowUp.finish(f"取关成功: \n{successList}\n取关失败:\n{failList}")

userFollowTelegram = on_message(rule=privateMessageRule & regex("^关注番剧([ ]+ep[\d]+)+"), permission=PRIVATE_FRIEND)
@userFollowTelegram.handle()
async def userFollowTelegramHandler(event: PrivateMessageEvent):
    '''响应个人用户关注番剧消息，修改文件

    Args:
        event (MessageEvent): 消息事件
        args (Message, optional): 关注的番剧的epid. Defaults to CommandArg().
    '''

    epIDs = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await FollowTelegram(event, event.sender.user_id, epIDs, 0)
    await userFollowTelegram.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

groupFollowTelegram = on_message(rule=groupMessageRule & regex("^关注番剧([ ]+ep[\d]+)+"), permission=GROUP_ADMIN | GROUP_OWNER)
@groupFollowTelegram.handle()
async def groupFollowTelegramHandler(event: GroupMessageEvent):
    '''响应群关注番剧消息，修改文件

    Args:
        event (MessageEvent): 消息事件
        args (Message, optional): 关注的番剧的epid. Defaults to CommandArg().
    '''

    epIDs = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await FollowTelegram(event, event.group_id, epIDs, 0)
    await groupFollowTelegram.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

userUnfollowTelegram = on_message(rule=privateMessageRule & regex("^取关番剧([ ]+[\d]+)+"), permission=PRIVATE_FRIEND)
@userUnfollowTelegram.handle()
async def userUnfollowTelegramHandler(event: PrivateMessageEvent):
    '''响应个人用户取关番剧消息，修改文件

    Args:
        event (MessageEvent): 消息事件
        args (Message, optional): _description_. Defaults to CommandArg().
    '''
    
    seasonIDs = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await UnfollowTelegram(event, event.sender.user_id, seasonIDs, 0)
    await userUnfollowTelegram.finish(f"取关成功: \n{successList}\n取关失败:\n{failList}")

groupUnfollowTelegram = on_message(rule=groupMessageRule & regex("^取关番剧([ ]+[\d]+)+"), permission=GROUP_ADMIN | GROUP_OWNER)
@groupUnfollowTelegram.handle()
async def groupUnfollowTelegramHandler(event: PrivateMessageEvent):
    '''响应群取关番剧消息，修改文件

    Args:
        event (MessageEvent): 消息事件
        args (Message, optional): _description_. Defaults to CommandArg().
    '''
    
    seasonIDs = event.get_message().extract_plain_text().split(' ')[1:]
    successList, failList = await UnfollowTelegram(event, event.sender.user_id, seasonIDs, 1)
    await groupUnfollowTelegram.finish(f"取关成功: \n{successList}\n取关失败:\n{failList}")
    
followUpByShare = on_message(
    rule=regex('\[CQ:json,[\w\W]*"appid":100951776[\w\W]*space.bilibili.com[\w\W]*[\w\W]*\]'), 
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND
    )
@followUpByShare.handle()
async def upShareHandler(event: Union[PrivateMessageEvent, GroupMessageEvent]):
    '''响应用户或群分享up主空间连接
    WARN: 有可能导致误关注

    Args:
        event (Union[PrivateMessageEvent, GroupMessageEvent]): 消息事件
    '''

    sJson = event.get_message()[-1].get('data')
    logger.debug(f'{__PLUGIN_NAME_VIDEO}收到B站空间分享的Json为: {sJson}')
    data = json.loads(sJson['data'])
    uid = data['meta']['news']['jumpUrl'].split('?')[0].split('/')[-1]
    logger.debug(f"{__PLUGIN_NAME_VIDEO}up主的uid为:{uid}")

    if isinstance(event, PrivateMessageEvent):
        successList, failList = await FollowUp(event, event.sender.user_id, [int(uid)], 0)
    if isinstance(event, GroupMessageEvent):
        successList, failList = await FollowUp(event, event.sender.user_id, [int(uid)], 1)

    if successList:
        await followUpByShare.finish(f"关注up成功: <{successList[0]}>")
    elif failList:
        await followUpByShare.finish(f"关注up失败: <{failList[0]}> ")

followStreamerByShare = on_message(
    rule=regex('^\[CQ:json,[\w\W]*"appid":100951776[\w\W]*live.bilibili.com[\w\W]*'),
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND
    )
@followStreamerByShare.handle()
async def streamerShareHandler(event: Union[PrivateMessageEvent, GroupMessageEvent]):
    '''响应个人用户/群的直播间分享

    Args:
        event (Union[PrivateMessageEvent, GroupMessageEvent]): 消息事件
    '''
    sJson = event.get_message()[-1].get('data')
    logger.debug(f'{__PLUGIN_NAME_VIDEO}收到B站直播间分享的Json为: {sJson}')
    data = json.loads(sJson['data'])
    roomNumber = data['meta']['news']['jumpUrl'].split('?')[0].split('/')[-1]
    logger.debug(f'{__PLUGIN_NAME_STREAM}主播的房间号为{roomNumber}')

    try:
        isUidSuccess, uid = GetUidByRoomNumber(roomNumber)
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        logger.error(f'{__PLUGIN_NAME_STREAM}获取主播 <{uid}> 信息时发生错误')
        logger.error(f'{__PLUGIN_NAME_STREAM}错误类型: {ex_type},错误值: {ex_val}')
        await followStreamerByShare.finish('关注失败: 连接错误')
    else:
        if isUidSuccess:
            if isinstance(event, PrivateMessageEvent):
                successList, failList = await FollowStreamers(event, event.sender.user_id, [uid], 0)
            if isinstance(event, GroupMessageEvent):
                successList, failList = await FollowStreamers(event, event.group_id, [uid], 1)
            
            if successList:
                await followUpByShare.finish(f"关注主播成功: <{successList[0]}>")
            elif failList:
                await followUpByShare.finish(f"关注主播失败: <{failList[0]}> ")

        else:
            await followStreamerByShare.finish(f'关注失败: 非法uid')

followTelegramByShare = on_message(
    rule = regex('^\[CQ:json[\w\W]*"appid":100951776[\w\W]*www.bilibili.com\/bangumi\/play\/[\w\W]*'),
    permission=GROUP_ADMIN | GROUP_OWNER | PRIVATE_FRIEND
)
@followTelegramByShare.handle()
async def telegramShareHandler(event: Union[PrivateMessageEvent, GroupMessageEvent]):
    '''响应用户/群分享番剧页面

    Args:
        event (Union[PrivateMessageEvent, GroupMessageEvent]): 消息事件
    '''
    sJson = event.get_message()[-1].get('data')
    data = json.loads(sJson['data'])
    epID = data['meta']['detail_1']['qqdocurl'].split('?')[0].split('/')[-1]
    epID = epID[2:]
    logger.debug(f"{__PLUGIN_NAME_TELE}番剧的epID为:{epID}")

    if isinstance(event, PrivateMessageEvent):
        successList, failList = await FollowTelegram(event, event.sender.user_id, [epID], 0)
    if isinstance(event, GroupMessageEvent):
        successList, failList = await FollowTelegram(event, event.group_id, [epID], 1)
    
    if successList:
        await followUpByShare.finish(f"关注番剧成功: <{successList[0]}>")
    elif failList:
        await followUpByShare.finish(f"关注番剧失败: <{failList[0]}> ")

followByShareB23Url = on_message(
    rule = regex('^\[CQ:json[\w\W]*"appid":100951776[\w\W]*b23.tv[\w\W]*'),
    permission=GROUP_OWNER | GROUP_ADMIN | PRIVATE_FRIEND
)
@followByShareB23Url.handle()
async def b23UrlShareHandler(event: Union[PrivateMessageEvent, GroupMessageEvent]):
    sJson = event.get_message()[-1].get('data')
    shortLink = re.search("https:\/\/b23.tv\/\w+", sJson['data'])
    b23Url = shortLink.group()
    logger.debug(f'{__PLUGIN_NAME}提取出短链接为{b23Url}')
    
    if isinstance(event, PrivateMessageEvent):
        msgType = 0
        userID = event.sender.user_id
    if isinstance(event, GroupMessageEvent):
        msgType = 1
        userID = event.group_id

    try:
        isSuccess, idType, id = parseB23Url(b23Url)
    except Exception:
        ex_type, ex_val, _ = sys.exc_info()
        logger.error(f'{__PLUGIN_NAME_STREAM}解析短链接 <{b23Url}> 时发生错误')
        logger.error(f'{__PLUGIN_NAME_STREAM}错误类型: {ex_type},错误值: {ex_val}')
        await followByShareB23Url.finish('关注失败: 连接错误')
    else:
        if isSuccess:
            if idType == 1:
                try:
                    isUidSuccess, uid = GetUidByRoomNumber(id)
                except Exception:
                    ex_type, ex_val, _ = sys.exc_info()
                    logger.error(f'{__PLUGIN_NAME_STREAM}获取主播 <{uid}> 信息时发生错误')
                    logger.error(f'{__PLUGIN_NAME_STREAM}错误类型: {ex_type},错误值: {ex_val}')
                    await followByShareB23Url.finish('关注失败: 连接错误')
                else:
                    if isUidSuccess:
                        successList, failList = await FollowStreamers(event, userID, [uid], msgType)
                        if successList:
                            await followByShareB23Url.finish(f"关注成功: {successList[0]}")
                        elif failList:
                            await followByShareB23Url.finish(f"关注失败: {failList[0]}")
                    else:
                        await followByShareB23Url.finish(f'关注失败: 非法uid')

            elif idType == 2:
                successList, failList = await FollowUp(event, userID, [uid], msgType)
                if successList:
                    await followByShareB23Url.finish(f"关注成功: {successList[0]}")
                elif failList:
                    await followByShareB23Url.finish(f"关注失败: {failList[0]}")

            elif idType == 3:
                successList, failList = await FollowTelegram(event, userID, [uid], msgType)
                if successList:
                    await followByShareB23Url.finish(f"关注成功: {successList[0]}")
                elif failList:
                    await followByShareB23Url.finish(f"关注失败: {failList[0]}")
        else:
            await followByShareB23Url.finish(f"关注失败: 非法短链接{b23Url}")

helpCommand = on_command("help",permission=PRIVATE_FRIEND | GROUP_ADMIN | GROUP_OWNER, aliases={'帮助'})
@helpCommand.handle()
async def sendHelpMsg(event: MessageEvent):
    userID = event.sender.user_id
    logger.debug(f'用户{userID}正在获取帮助')
    helpMsg = ""
    with open('./src/plugins/nonebot_plugin_bilibilibot/file/source/help.txt', 'r') as f:
        helpMsg = f.read()
    await helpCommand.finish(helpMsg)

publicBroacast = on_command("broacast", aliases={'广播'}, permission=permission.SUPERUSER)
@publicBroacast.handle()
async def sendBroacast(event: MessageEvent):
    userID = event.sender.user_id
    logger.debug(f'超级用户{userID}正在发起广播')
    announcement = ""
    announcementPath = './src/plugins/nonebot_plugin_bilibilibot/file/source/announcement.txt'
    if os.path.exists(announcementPath):
        with open('./src/plugins/nonebot_plugin_bilibilibot/file/source/announcement.txt', 'r') as f:
            announcement = f.read()

        users = GetAllUser()
        await SendMsgToUsers(announcement, users)

        groups = GetAllGroup()
        await SendMsgToGroups(announcement, groups)

        await publicBroacast.finish("公告发送成功")
    else:
        logger.debug(f'{__PLUGIN_NAME}公告文件不存在')
        await publicBroacast.finish("公告发送失败: 公告文件不存在") 
"""
unknownMessage = on_message(rule=to_me, priority=30)
@unknownMessage.handle()
async def unknownMessageHandler(matcher: Matcher, event: MessageEvent):
    userID = event.sender.user_id
    logger.debug(f"用户{userID}发送了一条未知信息")
    msg = "❌未知指令，请检查输入或通过/help指令获取帮助"
    await unknownMessage.finish(msg)
"""
scheduler = require("nonebot_plugin_apscheduler").scheduler
scheduler.add_job(CheckBiliStream, "interval", seconds=10, id="biliStream", misfire_grace_time=90)
scheduler.add_job(CheckUpUpdate, "interval", minutes=5, id="biliUp", misfire_grace_time=90)
scheduler.add_job(CheckTeleUpdate, "interval", minutes=10, id="biliTele", misfire_grace_time=90)

CheckDir()