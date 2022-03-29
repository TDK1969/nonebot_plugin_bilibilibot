from nonebot import get_driver, on_command, on_message, require, permission
from nonebot.rule import to_me
from nonebot.log import logger
from nonebot.rule import to_me, regex
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.params import  CommandArg

from .config import Config

from .biliStream import CheckBiliStream, FollowModifyStreamerFile, UnfollowModifyStreamerFile, GetUidByRoomNumber
from .biliVideo import CheckUpUpdate, FollowModifyUpFile, UnfollowModifyUpFile
from .biliTelegram import FollowModifyTelegramFile, UnfollowModifyTelegramFile, CheckTeleUpdate
from .basicFunc import GetAllUser, createUserFile, FollowModifyUserFile, UnfollowModifyUserFile, parseB23Url, SendMsgToUsers, CheckDir
import os
import json
import sys
import re
global_config = get_driver().config
config = Config.parse_obj(global_config)

__PLUGIN_NAME = "[B站整合]"
__PLUGIN_NAME_STREAM = "[B站整合~直播]"
__PLUGIN_NAME_VIDEO = "[B站整合~视频]"
__PLUGIN_NAME_TELE = "[B站整合~影视]"
# Export something for other plugin
# export = nonebot.export()
# export.foo = "bar"

# @export.xxx
# def some_function():
#     pass

followStreamer = on_command("followStreamer", rule=to_me, aliases={"关注主播"}, block=True)
@followStreamer.handle()
async def followStream(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """
    @description  :
    响应关注主播命令, 将主播加入用户的关注主播列表（如果无文件则建立），将用户加入主播的列表
    可同时关注多个主播
    ---------
    @param  :
    
    -------
    @Returns  :
    
    -------
    """
    
    uidList = args.extract_plain_text().split()
    userID = event.get_user_id() # 命令发出者的QQ
    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
    successList = []
    failList = []

    for uid in uidList:
        isSuccess, s = await FollowModifyStreamerFile(uid, userID)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)

    if os.path.exists(userFile):
        await FollowModifyUserFile(userFile, successList, 1)
    else:
        logger.debug(f'{__PLUGIN_NAME_STREAM}用户文件{userFile}不存在, 准备创建')
        await createUserFile(userFile, event.sender.nickname, streamers=successList)

    await followStreamer.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

unfollowStreamer = on_command("unfollowStreamer", rule=to_me, aliases={"切割主播"}, block=True)
@unfollowStreamer.handle()
async def unfollowStream(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """
    @description  :
    响应取关主播命令，从用户的关注主播列表中去除取关主播，同时主播的关注列表中去除用户
    可以同时取关多个主播
    ---------
    @param  :
    
    -------
    @Returns  :
    
    -------
    """
    
    uidList = args.extract_plain_text().split()
    userID = event.get_user_id() # 命令发出者的QQ
    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
    successList = []
    failList = []

    for uid in uidList:
        isSuccess, s = await UnfollowModifyStreamerFile(uid, userID)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)
    
    if os.path.exists(userFile):
        await UnfollowModifyUserFile(userFile, successList, 1)
    else:
        logger.debug(f'{__PLUGIN_NAME_STREAM}用户文件{userFile}不存在, 准备创建')
        await createUserFile(userFile, event.sender.nickname)

    await unfollowStreamer.finish(f"取关成功: \n{successList}\n取关失败:\n{failList}")

listUserFollowing = on_command("listFollowing", rule=to_me, aliases={"查询关注", "查询成分"}, block=True)
@listUserFollowing.handle()
async def listFollowing(event: MessageEvent, args: Message = CommandArg()):
    """
    @description  :
    响应查询成分命令，根据参数返回查询的内容
    ---------
    @param  :
    合法的参数有：主播、up主、节目，可以同时带有多项参数
    -------
    @Returns  :
    返回查询结果
    -------
    """
    
    inputArgs = args.extract_plain_text().split()
    logger.debug(f'{__PLUGIN_NAME}查询成分命令输入的参数为{inputArgs}')
    
    userID = event.get_user_id() # 命令发出者的QQ
    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
    defaultArgs = ['直播', 'up主', '节目']

    exceptArgs = set(inputArgs) - set(defaultArgs)
    if len(exceptArgs) != 0:
        logger.debug(f'{__PLUGIN_NAME}查询失败，存在错误参数{exceptArgs}')
        await listUserFollowing.finish(f"查询失败，存在错误参数:{exceptArgs}\n请正确输入命令,例如: '查询成分 直播' 或 '查询成分 直播 up主 节目'")
    
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
        if '节目' in inputArgs:
            if userInfo[3]:
                textMsg = '关注的节目\n'
                for info in userInfo[3]:
                    textMsg += '> '+ info + '\n'
            else:
                textMsg = '无关注的节目'
            await listUserFollowing.send(textMsg)
        await listUserFollowing.finish()
    else:
        logger.debug(f'{__PLUGIN_NAME}用户文件不存在，准备创建')
        await createUserFile(userFile, nickName=event.sender.nickname)
        await listUserFollowing.finish("关注列表为空")
    

followUp = on_command("followUp", rule=to_me, aliases={"关注up"}, block=True)
@followUp.handle()
async def followVideo(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """
    @description  :
    响应关注up主的命令，将作为参数的uid加入用户的关注列表，将用户的qq加入主播的关注列表
    ---------
    @param  :
    
    -------
    @Returns  :
    
    -------
    """
    
    uidList = args.extract_plain_text().split()
    userID = event.get_user_id() # 命令发出者的QQ
    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
    successList = []
    failList = []

    for uid in uidList:
        isSuccess, s = await FollowModifyUpFile(uid, userID)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)

    if os.path.exists(userFile):
        await FollowModifyUserFile(userFile, successList, 2)
    else:
        logger.debug(f'{__PLUGIN_NAME_VIDEO}用户文件{userFile}不存在, 准备创建')
        await createUserFile(userFile, event.sender.nickname, ups = successList)

    await followUp.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

unfollowUp = on_command("unfollowUp", rule=to_me, aliases={"取关up"}, block=True)
@unfollowUp.handle()
async def unfollowVideo(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """
    @description  :
    响应取关up命令，从用户的关注up主列表中去除取关up主，同时up主的关注列表中去除用户
    可以同时取关多个up主
    ---------
    @param  :
    
    -------
    @Returns  :
    
    -------
    """
    
    uidList = args.extract_plain_text().split()
    userID = event.get_user_id() # 命令发出者的QQ
    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
    successList = []
    failList = []

    for uid in uidList:
        isSuccess, s = await UnfollowModifyUpFile(uid, userID)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)
    
    if os.path.exists(userFile):
        await UnfollowModifyUserFile(userFile, successList, 2)
    else:
        logger.debug(f'{__PLUGIN_NAME_VIDEO}用户文件{userFile}不存在, 准备创建')
        await createUserFile(userFile, event.sender.nickname)

    await unfollowUp.finish(f"取关成功: \n{successList}\n取关失败:\n{failList}")

followTelegram = on_command("followTelegram", rule=to_me, aliases={"关注影视"}, block=True)
@followTelegram.handle()
async def followTelegramHandler(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """
    @description  :
    响应关注影视命令，修改节目文件与用户文件
    ---------
    @param  :
    
    -------
    @Returns  :
    
    -------
    """
    epIDs = args.extract_plain_text().split()
    userID = event.get_user_id() # 命令发出者的QQ
    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
    successList = []
    failList = []

    for epID in epIDs:
        if epID[0:2] != 'ep':
            failList.append(epID + "(错误参数)")
        else:
            epID = epID[2:]
            isSuccess, s = await FollowModifyTelegramFile(epID, userID)
            if isSuccess:
                successList.append(s)
            else:
                failList.append(s)
    
    if os.path.exists(userFile):
        await FollowModifyUserFile(userFile, successList, 3)
    else:
        logger.debug(f'{__PLUGIN_NAME_TELE}用户文件{userFile}不存在, 准备创建')
        await createUserFile(userFile, event.sender.nickname, telegrams=successList)

    await followUp.finish(f"关注成功:\n{successList}\n关注失败:\n{failList}")

unfollowTelegram = on_command("unfollowTelegram", rule=to_me, aliases={"取关影视"}, block=True)
@unfollowTelegram.handle()
async def unfollowTelegramHandler(matcher: Matcher, event: MessageEvent, args: Message = CommandArg()):
    """
    @description  :
    响应取关影视命令，修改影视文件和用户文件
    ---------
    @param  :
    
    -------
    @Returns  :
    
    -------
    """
    seasonIDs = args.extract_plain_text().split()
    userID = event.get_user_id() # 命令发出者的QQ
    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
    successList = []
    failList = []

    for seasonID in seasonIDs:
        isSuccess, s = await UnfollowModifyTelegramFile(seasonID, userID)
        if isSuccess:
            successList.append(s)
        else:
            failList.append(s)
    
    if os.path.exists(userFile):
        await UnfollowModifyUserFile(userFile, successList, 3)
    else:
        logger.debug(f'{__PLUGIN_NAME_TELE}用户文件{userFile}不存在, 准备创建')
        await createUserFile(userFile, event.sender.nickname)

    await unfollowUp.finish(f"取关成功: \n{successList}\n取关失败:\n{failList}")
    

followUpByShare = on_message(rule=regex('\[CQ:json,[\w\W]*"appid":100951776[\w\W]*space.bilibili.com[\w\W]*[\w\W]*\]'))
@followUpByShare.handle()
async def upShareHandler(matcher: Matcher, event: MessageEvent):
    userID = event.get_user_id()
    logger.debug(f"{__PLUGIN_NAME_VIDEO}收到来自用户{userID}的B站空间分享")
    event.get_message().extract_plain_text()
    sJson = event.get_message()[-1].get('data')
    logger.debug(f'{__PLUGIN_NAME_VIDEO}收到B站空间分享的Json为: {sJson}')
    data = json.loads(sJson['data'])
    uid = data['meta']['news']['jumpUrl'].split('?')[0].split('/')[-1]
    logger.debug(f"{__PLUGIN_NAME_VIDEO}up主的uid为:{uid}")

    isSuccess, s = await FollowModifyUpFile(uid, userID)
    if isSuccess:
        userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
        if os.path.exists(userFile):
            await FollowModifyUserFile(userFile, [s], 2)
        else:
            logger.debug(f'{__PLUGIN_NAME_VIDEO}用户文件{userFile}不存在, 准备创建')
            await createUserFile(userFile, event.sender.nickname, ups = [s])
        await followUpByShare.finish(f"关注up <{s}> 成功")
    else:
        await followUpByShare.finish(f"关注失败: {s}")

followStreamerByShare = on_message(rule=regex('^\[CQ:json,[\w\W]*"appid":100951776[\w\W]*live.bilibili.com[\w\W]*'))
@followStreamerByShare.handle()
async def streamerShareHandler(matcher: Matcher, event: MessageEvent):
    userID = event.get_user_id()
    logger.debug(f'{__PLUGIN_NAME_STREAM}收到来自用户{userID}的直播间分享')
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
            isSuccess, s = await FollowModifyStreamerFile(uid, userID)
            if isSuccess:
                userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
                if os.path.exists(userFile):
                    await FollowModifyUserFile(userFile, [s], 1)
                else:
                    logger.debug(f'{__PLUGIN_NAME_STREAM}用户文件{userFile}不存在, 准备创建')
                    await createUserFile(userFile, event.sender.nickname, streamers = [s])
                await followStreamerByShare.finish(f'关注主播{s}成功')
            else:
                await followStreamerByShare.finish(f'关注失败: {s}')
        else:
            await followStreamerByShare.finish(f'关注失败: 非法uid')

followTelegramByShare = on_message(rule = regex('^\[CQ:json[\w\W]*"appid":100951776[\w\W]*www.bilibili.com\/bangumi\/play\/[\w\W]*'))
@followTelegramByShare.handle()
async def telegramShareHandler(matcher: Matcher, event: MessageEvent):
    userID = event.get_user_id()
    logger.debug(f'{__PLUGIN_NAME_TELE}收到来自用户{userID}的影视分享')
    sJson = event.get_message()[-1].get('data')
    data = json.loads(sJson['data'])
    epID = data['meta']['detail_1']['qqdocurl'].split('?')[0].split('/')[-1]
    epID = epID[2:]
    logger.debug(f"{__PLUGIN_NAME_TELE}影视的epID为:{epID}")

    isSuccess, s = await FollowModifyTelegramFile(epID, userID)
    if isSuccess:
        userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
        if os.path.exists(userFile):
            await FollowModifyUserFile(userFile, [s], 3)
        else:
            logger.debug(f'{__PLUGIN_NAME_TELE}用户文件{userFile}不存在, 准备创建')
            await createUserFile(userFile, event.sender.nickname, telegrams = [s])
        await followUpByShare.finish(f"关注影视 <{s}> 成功")
    else:
        await followUpByShare.finish(f"关注失败: {s}")

followByShareB23Url = on_message(rule = regex('^\[CQ:json[\w\W]*"appid":100951776[\w\W]*b23.tv[\w\W]*'))
@followByShareB23Url.handle()
async def b23UrlShareHandler(matcher: Matcher, event: MessageEvent):
    userID = event.get_user_id()
    logger.debug(f'{__PLUGIN_NAME_TELE}收到来自用户{userID}的短链接分享')
    sJson = event.get_message()[-1].get('data')
    shortLink = re.search("https:\/\/b23.tv\/\w+", sJson['data'])
    b23Url = shortLink.group()
    logger.debug(f'{__PLUGIN_NAME}提取出短链接为{b23Url}')

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
                        isModifySuccess, s = await FollowModifyStreamerFile(uid, userID)
                        if isModifySuccess:
                            userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
                            if os.path.exists(userFile):
                                await FollowModifyUserFile(userFile, [s], 1)
                            else:
                                logger.debug(f'{__PLUGIN_NAME_STREAM}用户文件{userFile}不存在, 准备创建')
                                await createUserFile(userFile, event.sender.nickname, streamers = [s])
                            await followByShareB23Url.finish(f'关注主播{s}成功')
                        else:
                            await followByShareB23Url.finish(f'关注失败: {s}')
                    else:
                        await followByShareB23Url.finish(f'关注失败: 非法uid')
            elif idType == 2:
                isModifySuccess, s = await FollowModifyUpFile(id, userID)
                if isModifySuccess:
                    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
                    if os.path.exists(userFile):
                        await FollowModifyUserFile(userFile, [s], 2)
                    else:
                        logger.debug(f'{__PLUGIN_NAME_VIDEO}用户文件{userFile}不存在, 准备创建')
                        await createUserFile(userFile, event.sender.nickname, ups = [s])
                    await followByShareB23Url.finish(f"关注up <{s}> 成功")
                else:
                    await followByShareB23Url.finish(f"关注失败: {s}")
            elif idType == 3:
                isModifySuccess, s = await FollowModifyTelegramFile(id, userID)
                if isModifySuccess:
                    userFile = f"./src/plugins/nonebot_plugin_bilibilibot/file/user/{userID}.json"
                    if os.path.exists(userFile):
                        await FollowModifyUserFile(userFile, [s], 3)
                    else:
                        logger.debug(f'{__PLUGIN_NAME_TELE}用户文件{userFile}不存在, 准备创建')
                        await createUserFile(userFile, event.sender.nickname, telegrams = [s])
                    await followByShareB23Url.finish(f"关注影视 <{s}> 成功")
                else:
                    await followByShareB23Url.finish(f"关注失败: {s}")
        else:
            await followByShareB23Url.finish(f"关注失败: 非法短链接{b23Url}")

helpCommand = on_command("help",rule=to_me, aliases={'帮助'}, block=True)
@helpCommand.handle()
async def sendHelpMsg(matcher: Matcher, event: MessageEvent):
    userID = event.get_user_id()
    logger.debug(f'用户{userID}正在获取帮助')
    helpMsg = ""
    with open('./src/plugins/nonebot_plugin_bilibilibot/file/source/help.txt', 'r') as f:
        helpMsg = f.read()
    await helpCommand.finish(helpMsg)

publicBroacast = on_command("broacast", rule=to_me, aliases={'广播'}, permission=permission.SUPERUSER, block=True)
@publicBroacast.handle()
async def sendBroacast(matcher: Matcher, event: MessageEvent):
    userID = event.get_user_id()
    logger.debug(f'超级用户{userID}正在发起广播')
    announcement = ""
    announcementPath = './src/plugins/nonebot_plugin_bilibilibot/file/source/announcement.txt'
    if os.path.exists(announcementPath):
        with open('./src/plugins/nonebot_plugin_bilibilibot/file/source/announcement.txt', 'r') as f:
            announcement = f.read()
        users = GetAllUser()
        await SendMsgToUsers(announcement, users)
        await publicBroacast.finish("公告发送成功")
    else:
        logger.debug(f'{__PLUGIN_NAME}公告文件不存在')
        await publicBroacast.finish("公告发送失败: 公告文件不存在") 

unknownMessage = on_message(rule=to_me, priority=30)
@unknownMessage.handle()
async def unknownMessageHandler(matcher: Matcher, event: MessageEvent):
    userID = event.get_user_id()
    logger.debug(f"用户{userID}发送了一条未知信息")
    msg = "❌未知指令，请检查输入或通过/help指令获取帮助"
    await unknownMessage.finish(msg)

scheduler = require("nonebot_plugin_apscheduler").scheduler
scheduler.add_job(CheckBiliStream, "interval", seconds=10, id="biliStream", misfire_grace_time=90)
scheduler.add_job(CheckUpUpdate, "interval", minutes=5, id="biliUp", misfire_grace_time=90)
scheduler.add_job(CheckTeleUpdate, "interval", minutes=10, id="biliTele", misfire_grace_time=90)

CheckDir()