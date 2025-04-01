import lark_oapi as lark
from lark_oapi.api.im.v1 import *
import uuid


class SendImageResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__()
        self.create_image_response: Optional[CreateImageResponseBody] = None
        self.create_message_response: Optional[CreateMessageResponseBody] = None


class Lark_Image_Sender():
    def __init__(self, adapter_client: lark.Client):
        self.client = adapter_client

    def send_image(self, target_id: str, image_path: str) -> BaseResponse:
        print(f"正在发送图片到 {target_id}，图片路径: {image_path}")
        with open(image_path, 'rb') as file_io:
            # 上传图片
            create_image_req = CreateImageRequest.builder().request_body(CreateImageRequestBody.builder()
                                                                         .image_type("message")
                                                                         .image(file_io)
                                                                         .build()).build()
            create_image_resp = self.client.im.v1.image.create(create_image_req)

            if not create_image_resp.success():
                lark.logger.error(
                    f"client.im.v1.image.create failed, "
                    f"code: {create_image_resp.code}, "
                    f"msg: {create_image_resp.msg}, "
                    f"log_id: {create_image_resp.get_log_id()}")
                return create_image_resp
            return self.__send_img_req(target_id, create_image_resp)

    def __send_img_req(self, target_id: str, create_image_resp: CreateImageResponse) -> BaseResponse:
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


if __name__ == "__main__":
    client = lark.Client.builder().app_id('cli_a76f4745d37b100b').app_secret('NHcIysot1LVGJskZHyRVVeVVqL0FXcZp').build()
    # 异步读取图片内容
    Lark_Image_Sender(client).send_image('ou_63053bc6508a9fc06be536d937b50e4e',
                                  'D:\\dev_code\\AI-Application\\aigc-workflow\\flask_server\\static\\downloaded_images\\ComfyUI_00025_.png')
