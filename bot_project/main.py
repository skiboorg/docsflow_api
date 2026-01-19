from flask import Flask
from flask_api.routes import bp
from bot.app import start_bot

# Запускаем бота
start_bot()

# Запускаем Flask API
app = Flask(__name__)
app.register_blueprint(bp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
