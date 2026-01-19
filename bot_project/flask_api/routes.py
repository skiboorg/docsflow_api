from flask import Blueprint, request, jsonify
from bot_project.bot.app import telegram_app

bp = Blueprint('api', __name__)

@bp.route('/send_message', methods=['POST'])
def send_message():
    content = request.json
    chat_id = content['chat_id']
    message = content['message']
    telegram_app.bot.send_message(chat_id=chat_id, text=message)
    return jsonify({'status': 'ok'})
