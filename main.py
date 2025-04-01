# -*- coding: utf-8 -*-
import json
from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
import pkg.platform.types as platform_types


# 注册插件
@register(name="Hello", description="hello world", version="0.1", author="RockChinQ")
class MyPlugin(BasePlugin):

    # 插件加载时触发
    def __init__(self, host: APIHost):
        super().__init__(host)
        self.adapter = None

    # 异步初始化
    async def initialize(self):
        for plt in self.host.get_platform_adapters():
            print('active platform:', plt.config)
            if plt.config.get('bot_name', 'None') == '小美':
                msg = platform_types.MessageChain([
                    platform_types.Plain('飞书小美已就位，随时为您提供帮助！')
                ])
                self.adapter = plt
                await self.host.send_active_message(adapter=plt,
                                                    target_type="person",
                                                    target_id='ou_63053bc6508a9fc06be536d937b50e4e',
                                                    message=msg)

    async def get_local_search_url(self, query, sender, num_results=10, searx_host="http://124.223.45.165:22109"):
        url = f"{searx_host}/search"
        params = {
            "q": query,
            "categories": "images",
            "num": num_results,
            "format": "json"
        }
        import os
        import shutil
        import aiohttp  # 引入 aiohttp 库用于异步请求

        # 创建img_download目录
        download_dir = os.path.join(os.path.dirname(__file__), 'img_download')
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        try:
            print('start query keyword:', query, 'sender:', sender)
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()  # 检查是否有 HTTP 错误
                    results = await response.json()  # 异步解析 JSON
                    for it in results['results']:
                        print('search result:', it)
                        if 'img_src' in it:
                            img_url = it['img_src']
                            try:
                                # 异步下载图片
                                async with session.get(img_url) as img_response:
                                    img_response.raise_for_status()
                                    img_bytes = await img_response.read()
                                    # import datetime
                                    # # 获取当前时间戳，精确到秒
                                    # timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                                    # base_name = os.path.basename(img_url)
                                    # # 构建新的文件名，包含时间戳
                                    # img_filename = os.path.join(download_dir, f"{timestamp}_{base_name}")
                                    # with open(img_filename, 'wb') as out_file:
                                    #     out_file.write(await img_response.read())  # 异步读取图片内容
                                    # img = {'url': img_url, 'local_path': img_filename}
                                    return {'url': img_url, 'bytes': img_bytes}
                            except aiohttp.ClientError as e:
                                print(f"下载图片 {img_url} 失败: {e}")
                                continue
                        else:
                            print(f"未找到与查询 '{query}' 相关的图片结果。")
                            continue
        except aiohttp.ClientError as e:
            print(f"搜索查询 '{query}' 失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"解析 JSON 响应失败: {e}, 响应内容：{await response.text()}")
            return None
        except KeyError as e:
            print(f"KeyError: 缺少预期的键: {e}, 响应内容：{await response.text()}")
            return None

    # 当收到个人消息时触发
    @handler(PersonNormalMessageReceived)
    async def person_normal_message_received(self, ctx: EventContext):
        msg = ctx.event.text_message  # 这里的 event 即为 PersonNormalMessageReceived 的对象
        print('plugin handle:', msg)
        if msg == "hello":  # 如果消息为hello

            # 输出调试信息
            self.ap.logger.debug("hello, {}".format(ctx.event.sender_id))

            # 回复消息 "hello, <发送者id>!"
            ctx.add_return("reply", ["hello, {}!".format(ctx.event.sender_id)])
            ctx.prevent_default()
        elif msg.startswith(("search", "搜", "搜索", "查询")):
            keyword = msg
            # 截取关键字
            for keyword_prefix in ("search", "搜", "搜索", "查询"):
                if msg.startswith(keyword_prefix):
                    keyword = msg[len(keyword_prefix):].strip()
                    break
            import asyncio
            search_task = asyncio.create_task(self.get_local_search_url(keyword, ctx.event.sender_id))
            # 你可以在后续代码中使用 await 等待任务完成
            img = await search_task
            if img:
                ctx.add_return("reply", [f"我找到一个链接{img['url']}:，等我下载后回复你!"])
                # ctx.add_return("reply", [platform_types.Image(path=img["local_path"])])
                LarkClient(self.adapter.api_client).send_image(ctx.event.sender_id, img["bytes"])
            # 阻止该事件默认行为（向接口获取回复）
            ctx.prevent_default()

    # 当收到群消息时触发
    @handler(GroupNormalMessageReceived)
    async def group_normal_message_received(self, ctx: EventContext):
        msg = ctx.event.text_message  # 这里的 event 即为 GroupNormalMessageReceived 的对象
        if msg == "hello":  # 如果消息为hello

            # 输出调试信息
            self.ap.logger.debug("hello, {}".format(ctx.event.sender_id))

            # 回复消息 "hello, everyone!"
            ctx.add_return("reply", ["hello, everyone!"])

            # 阻止该事件默认行为（向接口获取回复）
            ctx.prevent_default()

    # 插件卸载时触发
    def __del__(self):
        pass


"""
发送图片消息，使用到两个OpenAPI：
1. [上传图片](https://open.feishu.cn/document/server-docs/im-v1/image/create)
2. [发送消息](https://open.feishu.cn/document/server-docs/im-v1/message/create)
"""

import lark_oapi as lark
from lark_oapi.api.im.v1 import *
import uuid


class SendImageRequest(object):

    def __init__(self) -> None:
        self.image: Optional[IO[Any]] = None  # 图片，必填
        self.receive_id_type: Optional[str] = None  # 消息接收者ID类型，必填
        self.receive_id: Optional[str] = None  # 消息接收者的ID，必填
        self.uuid: Optional[str] = None  # 消息uuid，选填


class SendImageResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__()
        self.create_image_response: Optional[CreateImageResponseBody] = None
        self.create_message_response: Optional[CreateMessageResponseBody] = None


class LarkClient:
    def __init__(self, adapter_client: lark.Client):
        self.client = adapter_client

    def send_image(self, target_id: str, image_bytes: IO[Any]) -> BaseResponse:
        # 上传图片
        create_image_req = CreateImageRequest.builder() \
            .request_body(CreateImageRequestBody.builder()
                          .image_type("message")
                          .image(image_bytes)
                          .build()) \
            .build()

        create_image_resp = self.client.im.v1.image.create(create_image_req)

        if not create_image_resp.success():
            lark.logger.error(
                f"client.im.v1.image.create failed, "
                f"code: {create_image_resp.code}, "
                f"msg: {create_image_resp.msg}, "
                f"log_id: {create_image_resp.get_log_id()}")
            return create_image_resp

        # 发送消息
        option = lark.RequestOption.builder().headers({"X-Tt-Logid": create_image_resp.get_log_id()}).build()
        create_message_req = CreateMessageRequest.builder() \
            .receive_id_type('open_id') \
            .request_body(CreateMessageRequestBody.builder()
                          .receive_id(target_id)
                          .msg_type("image")
                          .content(lark.JSON.marshal(create_image_resp.data))
                          .uuid(str(uuid.uuid4()))
                          .build()) \
            .build()

        create_message_resp: CreateMessageResponse = self.client.im.v1.message.create(create_message_req, option)

        if not create_message_resp.success():
            lark.logger.error(
                f"client.im.v1.message.create failed, "
                f"code: {create_message_resp.code}, "
                f"msg: {create_message_resp.msg}, "
                f"log_id: {create_message_resp.get_log_id()}")
            return create_message_resp

        # 返回结果
        response = SendImageResponse()
        response.code = 0
        response.msg = "success"
        response.create_image_response = create_image_resp.data
        response.create_message_response = create_message_resp.data

        return response
