import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)).replace("/bot_project", ""))

from flask import Flask
from bot_project.flask_api.routes import bp
from bot_project.bot.app import start_bot

# Запускаем бота
start_bot()

# Запускаем Flask API
app = Flask(__name__)
app.register_blueprint(bp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
