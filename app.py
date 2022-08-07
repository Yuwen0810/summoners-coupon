import sys

from flask import Flask, request, abort
from flask_apscheduler import APScheduler

from linebot import (
	LineBotApi, WebhookHandler
)
from linebot.exceptions import (
	InvalidSignatureError
)
from linebot.models import *

from utils import Recorder
from coupon import update_coupon, init_coupon

# ======python的函數庫==========
import os


# ======python的函數庫==========

class Config(object):
	# JOBS 可以在配置裡面配置
	JOBS = [{
		'id': 'refresh_coupon',
		'func': 'app:refresh_coupon',
		'trigger': 'interval',
		'seconds': 300
	}]
	SCHEDULER_TIMEZONE = 'Asia/Taipei'  # 配置時區
	SCHEDULER_API_ENABLED = True  # 新增API


app = Flask(__name__)
app.config.from_object(Config())

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')

# Channel Secret
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)

# Channel Access Token
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)

if channel_secret is None:
	print('Specify LINE_CHANNEL_SECRET as environment variable.')
	sys.exit(1)
if channel_access_token is None:
	print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
	sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

record = Recorder()

# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
	# get X-Line-Signature header value
	signature = request.headers['X-Line-Signature']
	# get request body as text
	body = request.get_data(as_text=True)
	app.logger.info("Request body: " + body)
	# handle webhook body
	try:
		handler.handle(body, signature)

	except InvalidSignatureError:
		abort(400)
	return 'OK'


# 處理訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
	msg = event.message.text
	user_id = event.source.user_id
	timestamp = event.timestamp

	if msg == "Turn on notifications":
		if record.add_user(user_id):
			line_bot_api.reply_message(event.reply_token, TextSendMessage(text="[Success] Notifications are on"))
		else:
			line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Already on"))

	elif msg == "Turn off notifications":
		if record.remove_user(user_id):
			line_bot_api.reply_message(event.reply_token, TextSendMessage(text="[Success] Notifications are off"))
		else:
			line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Already off"))

	elif msg.lower() == "setting":
		line_bot_api.reply_message(  # 回復傳入的訊息文字
			event.reply_token,
			TemplateSendMessage(
				alt_text='Buttons template',
				template=ButtonsTemplate(
					title='Setting',
					text='Select notifications status',
					actions=[
						MessageTemplateAction(
							label='Turn on',
							text='Turn on notifications'
						),
						MessageTemplateAction(
							label='Turn off',
							text='Turn off notifications'
						)
					]
				)
			)
		)


def refresh_coupon():
	print("Refresh coupon")
	new_data = update_coupon()
	user_ids = record.get_all_user()
	if new_data and user_ids:
		for d in new_data:
			line_bot_api.multicast(user_ids, TextSendMessage(
				text=f"[New Coupon]\nlabel: {d['label']}\ncreate_time: {d['create_time']}\nlink: {d['link']}"))


import os

if __name__ == "__main__":
	init_coupon()

	scheduler = APScheduler()
	scheduler.init_app(app)
	scheduler.start()

	# port = int(os.environ.get('PORT', 80))
	app.run(port=80)

# app.run()
