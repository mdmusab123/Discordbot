import discord
import os
import json
import logging
from discord.ui import Button, View
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio

# Load environment variables from .env file
load_dotenv()

# Grab the API token from the .env file
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Define the intents the bot will use
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

# Gets the client object from discord.py with the specified intents
bot = discord.Client(intents=intents)

# Load order data from the external orders.json file
def load_orders():
    with open('orders.json', 'r') as file:
        return json.load(file)

# Load updated IP information from the updated_isp.json file
def load_updated_ips():
    with open('updated_isp.json', 'r') as file:
        return json.load(file)

# Load proxy status from the external proxy_status.json file
def load_proxy_status():
    with open('proxy_status.json', 'r') as file:
        return json.load(file)

# Load order IDs from the id.json file
def load_order_ids():
    with open('id.json', 'r') as file:
        return json.load(file)

# This will store the order data loaded from the file
orders = load_orders()

# This will store the updated IP information loaded from the file
updated_ips = load_updated_ips()

# This will store the user and the state of awaiting order ID
awaiting_order_id = {}

# This will store the active tickets (user ID: private channel)
active_tickets = {}

# This will store the proxy statuses loaded from the file
proxy_status = load_proxy_status()

# This will store the order IDs loaded from the file
order_ids = load_order_ids()

# Setup logging to log interactions to a file
logging.basicConfig(filename='bot_interactions.log',
                    level=logging.INFO,
                    format='%(asctime)s - %(message)s')

def log_interaction(user, query, response):
    # Format the log message for clarity
    log_message = f"**User:** {user} | **Query:** `{query}` | **Response:** ```{response}```"
    logging.info(log_message)

# Function to create or get the transcript channel
async def get_transcript_channel(guild):
    channel = discord.utils.get(guild.text_channels,
                                name="𝖲𝖴𝖯𝖯𝖮𝖱𝖳-𝖳𝖱𝖠𝖭𝖲𝖢𝖨𝖯𝖳-AI")
    if not channel:
        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)  # Allow the bot to read
        }
        channel = await guild.create_text_channel("𝖲𝖴𝖯𝖯𝖮𝖱𝖳-𝖳𝖱𝖠𝖭𝖲𝖢𝖨𝖯𝖳-AI",
                                                  overwrites=overwrites)
    return channel

# Event listener for when the bot is ready
@bot.event
async def on_ready():
    guild_count = 0
    for guild in bot.guilds:
        print(f"- {guild.id} (name: {guild.name})")
        guild_count += 1

    print(f"SampleDiscordBot is in {guild_count} guilds.")

    # Automatically greet the user in the first channel of the first guild
    if guild_count > 0:
        channel = bot.guilds[0].text_channels[0]  # Get the first text channel of the first guild
        await greet_user(channel)

    # Start background task to sync orders every 5 minutes
    bot.loop.create_task(sync_orders())

# Function to greet the user and present Yes/No buttons
async def greet_user(channel):
    yes_button = Button(label="Yes", style=discord.ButtonStyle.success)
    no_button = Button(label="No", style=discord.ButtonStyle.danger)

    async def yes_callback(interaction):
        await interaction.response.defer()  # Defer the response
        user = interaction.user

        # Check if the user already has an active ticket
        if user.id in active_tickets:
            await interaction.followup.send(
                "You already have an open support ticket. Please close it before opening a new one."
            )
            return

        # Create a private channel for the user
        guild = interaction.guild
        overwrites = {
            guild.default_role:
            discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True)
        }
        private_channel = await guild.create_text_channel(
            f"{user.name}-support", overwrites=overwrites)

        # Track the active ticket
        active_tickets[user.id] = private_channel

        # Send a message to the user in the private channel
        await private_channel.send(
            "This is the Amexcess Automated Support Bot. You can use it to update your proxy and check your Proxy status. If your proxy isn’t working, please check for available updates and check the proxy IP status If you find that your proxy is down, click “Yes” for assistance."
        )

        # Create buttons for help topics
        proxy_button = Button(
            label="If your proxy is not working, click here to Check proxy update",
            style=discord.ButtonStyle.primary)
        normal_button = Button(label="Ask a question", style=discord.ButtonStyle.secondary)
        proxy_checker_button = Button(label="Proxy Down Checker", style=discord.ButtonStyle.primary)

        async def proxy_checker_callback(interaction):
            await interaction.response.defer()
            response = "Proxy Status:\n"
            for proxy, status in proxy_status.items():
                status_text = "✅ Up" if status else "❌ Down"
                response += f"{proxy}: {status_text}\n"
            await private_channel.send(response)

        async def proxy_down_checker_callback(interaction):
            await interaction.response.defer()
            await private_channel.send("Please provide your Order ID to check the proxy status.")

            def check(msg):
                return msg.author == user and msg.channel == private_channel

            try:
                message = await bot.wait_for('message', check=check, timeout=60.0)
                order_id = message.content.strip()

                if order_id in order_ids:
                    # Order ID exists; check the proxy status
                    await private_channel.send("Please provide the Proxy IP to check its status.")

                    try:
                        proxy_message = await bot.wait_for('message', check=check, timeout=60.0)
                        proxy_ip = proxy_message.content.strip()

                        if proxy_ip in proxy_status:
                            status_text = "✅ Up" if proxy_status[proxy_ip] else "❌ Down"
                            await private_channel.send(f"Proxy IP `{proxy_ip}` status: {status_text}")
                        else:
                            await private_channel.send("Proxy IP not found in the records. Please check and try again.")
                    except asyncio.TimeoutError:
                        await private_channel.send("You took too long to respond! Please try again.")
                else:
                    await private_channel.send("Order ID not found. Please check and try again.")
            except asyncio.TimeoutError:
                await private_channel.send("You took too long to respond! Please try again.")

        proxy_checker_button.callback = proxy_checker_callback
        proxy_checker_button.callback = proxy_down_checker_callback

        async def proxy_callback(interaction):
            await interaction.response.defer()  # Defer this response
            user = interaction.user

            # Read from function.txt to check for updates
            try:
                with open('function.txt', 'r') as f:
                    update_available = f.read().strip().lower() == 'true'
            except FileNotFoundError:
                update_available = False  # If the file doesn't exist, assume no updates

            if update_available:
                update_button_view = View()
                yes_update_button = Button(label="Yes", style=discord.ButtonStyle.success)
                no_update_button = Button(label="No", style=discord.ButtonStyle.danger)

                async def yes_update_callback(interaction):
                    await interaction.response.defer()  # Defer this response
                    awaiting_order_id[user.id] = True
                    await private_channel.send(
                        "Please provide your Order ID by sending it in the chat."
                    )

                async def no_update_callback(interaction):
                    await interaction.response.defer()  # Defer this response
                    await private_channel.send(
                        "Okay! Closing your support ticket.")
                    await private_channel.send(
                        "Thank you! The chat is now closed.")
                    await private_channel.delete()

                    # Remove the user from active tickets
                    del active_tickets[user.id]

                yes_update_button.callback = yes_update_callback
                no_update_button.callback = no_update_callback

                update_button_view.add_item(yes_update_button)
                update_button_view.add_item(no_update_button)

                await private_channel.send(
                    "Update is available! Do you want to update your proxy?",
                    view=update_button_view)
            else:
                await private_channel.send("Sorry! No updates available.")

                # Close the ticket with an appropriate message
                close_button = Button(label="Close Ticket", style=discord.ButtonStyle.success)

                async def close_callback(interaction):
                    await interaction.response.defer()  # Defer this response
                    await private_channel.send(
                        "Thank you! The ticket is now closed.")
                    await private_channel.delete()

                    # Remove the user from active tickets
                    del active_tickets[user.id]

                close_button.callback = close_callback

                close_view = View()
                close_view.add_item(close_button)

                await private_channel.send("Please close the ticket below:", view=close_view)

        async def normal_callback(interaction):
            await interaction.response.defer()  # Defer this response
            await private_channel.send(
                "Ask your question here, and we'll assist you.")

            # Wait for a response for 15 seconds
            await asyncio.sleep(15)

            # Prompt to close the ticket if no response received
            close_button = Button(label="Close Ticket", style=discord.ButtonStyle.success)

            async def close_callback(interaction):
                await interaction.response.defer()  # Defer this response
                await private_channel.send(
                    "Thank you! The ticket is now closed.")
                await private_channel.delete()

                # Remove the user from active tickets
                del active_tickets[user.id]

                # Log the closure in the transcript channel
                transcript_channel = await get_transcript_channel(guild)
                await transcript_channel.send(
                    f"**User:** {user.name} has closed the ticket.")

            close_button.callback = close_callback

            close_view = View()
            close_view.add_item(close_button)

            await private_channel.send(
                "If you have not received a response, you can close the ticket below:",
                view=close_view)

        proxy_button.callback = proxy_callback
        normal_button.callback = normal_callback

        help_view = View()
        help_view.add_item(proxy_button)
        help_view.add_item(normal_button)
        help_view.add_item(proxy_checker_button)

        await private_channel.send("Please choose a topic for help:", view=help_view)

    async def no_callback(interaction):
        await interaction.response.defer()  # Defer this response
        await interaction.user.send(
            "Okay! If you need help later, just let me know.")

    yes_button.callback = yes_callback
    no_button.callback = no_callback

    view = View()
    view.add_item(yes_button)
    view.add_item(no_button)

    await channel.send(
        content=( 
            "This is the Amexcess Automated Support Bot. You can use it to update your proxy and check your Proxy status. If your proxy isn’t working, please check for available updates and check the proxy IP status If you find that your proxy is down, click “Yes” for assistance."
        ),
        view=view)

# Function to sync orders every 5 minutes
async def sync_orders():
    while True:
        await asyncio.sleep(300)  # Wait for 5 minutes (300 seconds)
        global orders
        orders = load_orders()  # Reload the order data

# Listen for messages to handle the order ID after the "Yes" button is clicked for updates
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check for the clear command
    if message.content.startswith("/clear all"):
        if message.author.guild_permissions.manage_messages:  # Check if the user has permission
            await message.channel.purge()  # Clear all messages in the channel
            await message.channel.send("All messages have been cleared.", delete_after=5)  # Optional confirmation message
        else:
            await message.channel.send("You don't have permission to clear messages.", delete_after=5)
        return

    if message.author.id in awaiting_order_id and awaiting_order_id[message.author.id]:
        order_id = message.content.strip()

        if order_id in orders:
            order_details = orders[order_id]
            order_date_str = order_details.get('order_date', None)

            if order_date_str:
                order_date = datetime.strptime(order_date_str, '%d-%m-%Y')
                current_date = datetime.now()
                valid_until = order_date + timedelta(days=30)
                days_left = (valid_until - current_date).days

                if (current_date - order_date).days >= 24:
                    validation_status = "Expired⛔"
                    ip_info = ""
                elif current_date <= valid_until:
                    validation_status = "Valid👌"
                    package = order_details.get('package', None)
                    new_ip_info = updated_ips.get(package, None)

                    if new_ip_info:
                        ip_info = (f"🆕 New Updated IP Details 🆕:\n"
                                   f"IP: `{new_ip_info['ip']}`\n"
                                   f"User: `{new_ip_info['user']}`\n"
                                   f"Port: `{new_ip_info['port']}`\n"
                                   f"Password: `{new_ip_info['password']}`\n")
                    else:
                        ip_info = "No updated IP information available for your package."
                else:
                    validation_status = "Expired⛔"
                    ip_info = ""

                renewal_suggestion = ""
                if days_left <= 5:
                    renewal_suggestion = "\n⚠️ You need to renew to get updated Proxy, as your validation is 5 days or fewer left or expired. Please renew."

                response = (
                    f"**Order Details:**\n"
                    f"**Name:** {order_details['name']}\n"
                    f"**Email:** {order_details['email']}\n"
                    f"**Phone Number:** {order_details['phone']}\n"
                    f"**IP Given:** {order_details['ip']}\n"
                    f"**Order Date:** {order_date_str}\n"
                    f"**Total Amount:** {order_details['total_amount']}\n"
                    f"**Package:** {order_details['package']}\n"
                    f"**Validation Status:** {validation_status}\n"
                    f"**Days Left:** {days_left}{renewal_suggestion}\n"
                    f"{ip_info}")
            else:
                response = "Order date not available"
        else:
            response = "Sorry, I couldn't find that Order ID. Please check and try again."

        log_interaction(message.author.name, order_id, response)

        # Send the response in the private channel
        await message.channel.send(response)

        # Log the interaction in the transcript channel with highlighting
        transcript_channel = await get_transcript_channel(message.guild)
        await transcript_channel.send(f"**User:** {message.author.name}\n"
                                      f"**Query:** `{order_id}`\n"
                                      f"**Response:** ```{response}```")

        close_button = Button(label="Close Chat", style=discord.ButtonStyle.success)
        problem_button = Button(label="Problem Not Solved", style=discord.ButtonStyle.danger)

        async def close_callback(interaction):
            await interaction.response.defer()  # Defer this response
            await interaction.channel.send("Thank you! The chat is now closed.")
            await interaction.channel.delete()

            # Remove the user from active tickets
            if message.author.id in active_tickets:
                del active_tickets[message.author.id]

        async def problem_callback(interaction):
            await interaction.response.defer()  # Defer this response

            # Find the SUPPORT-TICKET channel
            support_channel = discord.utils.get(message.guild.text_channels, name="𝖲𝖴𝖯𝖯𝖮𝖱𝖳-𝖳𝖨𝖢𝖤𝖳")
            if support_channel:
                await support_channel.send(
                    f"User {message.author.name} indicated their problem is not solved."
                )

            await message.channel.send(
                "We apologize for the inconvenience. Please contact support for further assistance."
            )

            # Show the button to close the ticket instead of closing it automatically
            close_button = Button(label="Close Ticket", style=discord.ButtonStyle.success)

            async def close_callback(interaction):
                await interaction.response.defer()  # Defer this response
                await message.channel.send("Thank you! The ticket is now closed.")
                await message.channel.delete()

                # Remove the user from active tickets
                if message.author.id in active_tickets:
                    del active_tickets[message.author.id]

            close_button.callback = close_callback
            close_view = View()
            close_view.add_item(close_button)

            await message.channel.send(
                "If you want to close the ticket, please click below:",
                view=close_view)

        close_button.callback = close_callback
        problem_button.callback = problem_callback

        close_view = View()
        close_view.add_item(close_button)
        close_view.add_item(problem_button)

        await message.channel.send(
            "Is your problem solved? If yes, please close the chat. If no, let us know.",
            view=close_view)

        awaiting_order_id[message.author.id] = False

# Ensure the token is loaded correctly
if DISCORD_TOKEN is None:
    raise ValueError("No DISCORD_TOKEN found. Please set it in your .env file.")

# Run the bot
bot.run(DISCORD_TOKEN)