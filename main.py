import discord
import os
import json
import logging
from discord.ui import Button, View
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio

import time  # Import time module for file modification times

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
    try:
        with open('orders.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("orders.json file not found.")
        return {}


# Load updated ISP information from the updated_isp.json file
def load_updated_isp():
    try:
        with open('updated_isp.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("updated_isp.json file not found.")
        return {}


# Load IP status data from the ip_status.json file
def load_ip_status():
    try:
        with open('ip_status.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("ip_status.json file not found.")
        return {}

# This will store the order data loaded from the file
orders = load_orders()

# This will store the updated ISP information loaded from the file
updated_isp = load_updated_isp()

# This will store the IP status data loaded from the file
ip_status_data = load_ip_status()

# Store the last modification time of ip_status.json
ip_status_mtime = os.path.getmtime('ip_status.json') if os.path.exists('ip_status.json') else 0

# This will store the user and the state of awaiting input
awaiting_input = {}

# This will store the active tickets (user ID: private channel)
active_tickets = {}

# Setup logging to log interactions to a file
logging.basicConfig(
    filename=os.path.join(os.getcwd(), 'bot_interactions.log'),
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)


def log_interaction(user, query, response):
    # Format the log message for clarity
    log_message = f"User: {user} | Query: {query} | Response: {response}"
    logging.info(log_message)


# Function to create or get the transcript channel
async def get_transcript_channel(guild):
    channel = discord.utils.get(guild.text_channels, name="support-transcript-ai")
    if not channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)  # Allow the bot to read
        }
        channel = await guild.create_text_channel("support-transcript-ai", overwrites=overwrites)
    return channel


# Store the views to prevent them from being garbage collected
persistent_views = []

# Event listener for when the bot is ready
@bot.event
async def on_ready():
    guild_count = 0
    for guild in bot.guilds:
        print(f"- {guild.id} (name: {guild.name})")
        guild_count += 1

        # Find the channel named '𝗦𝗨𝗣𝗣𝗢𝗥𝗧-𝗔𝗜' in this guild
        channel = discord.utils.get(guild.text_channels, name='𝗦𝗨𝗣𝗣𝗢𝗥𝗧-𝗔𝗜')
        if channel:
            await greet_user(channel)
        else:
            print(f"Channel '𝗦𝗨𝗣𝗣𝗢𝗥𝗧-𝗔𝗜' not found in guild {guild.name}")

    print(f"SampleDiscordBot is in {guild_count} guilds.")

    # Start background tasks
    asyncio.create_task(sync_data())  # Task to sync orders and updated ISP every 5 minutes
    asyncio.create_task(watch_ip_status())  # Task to watch ip_status.json for changes


# Function to greet the user and present Yes/No buttons
async def greet_user(channel):
    yes_button = Button(
        label="Yes",
        style=discord.ButtonStyle.success,
        custom_id="greet_yes_button"
    )
    no_button = Button(
        label="No",
        style=discord.ButtonStyle.danger,
        custom_id="greet_no_button"
    )

    async def yes_callback(interaction):
        user = interaction.user

        # Check if the user already has an active ticket
        if user.id in active_tickets:
            await interaction.response.send_message(
                "You already have an open support ticket. Please close it before opening a new one.",
                ephemeral=True
            )
            return

        # Create a private channel for the user
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True)
        }
        private_channel = await guild.create_text_channel(
            f"{user.name}-support", overwrites=overwrites
        )

        # Track the active ticket
        active_tickets[user.id] = private_channel

        await interaction.response.send_message(
            f"Support ticket created: {private_channel.mention}",
            ephemeral=True
        )

        # Send a message to the user in the private channel
        await private_channel.send(
            "This is Amexcess Automated Bot for Customer Support. Please choose an option below."
        )

        # Create buttons for help topics
        proxy_button = Button(
            label="Check proxy update",
            style=discord.ButtonStyle.primary,
            custom_id="help_proxy_button"
        )
        ip_status_button = Button(
            label="IP Status",
            style=discord.ButtonStyle.success,  # Changed style to success (green color)
            custom_id="ip_status_button"
        )
        close_ticket_button = Button(
            label="Close Ticket",
            style=discord.ButtonStyle.danger,
            custom_id="help_close_ticket_button"
        )

        async def proxy_callback(interaction):
            user = interaction.user

            # Read from function.txt to check for updates
            try:
                with open('function.txt', 'r') as f:
                    update_available = f.read().strip().lower() == 'true'
            except FileNotFoundError:
                update_available = False  # If the file doesn't exist, assume no updates

            if update_available:
                update_button_view = View(timeout=None)  # Set timeout to None
                yes_update_button = Button(
                    label="Yes",
                    style=discord.ButtonStyle.success,
                    custom_id="update_yes_button"
                )
                no_update_button = Button(
                    label="No",
                    style=discord.ButtonStyle.danger,
                    custom_id="update_no_button"
                )

                async def yes_update_callback(interaction):
                    awaiting_input[user.id] = 'order_id'
                    await interaction.response.send_message(
                        "Please provide your Order ID by sending it in the chat."
                    )

                async def no_update_callback(interaction):
                    await interaction.response.send_message(
                        "Okay! Closing your support ticket."
                    )

                    # Retrieve the private channel
                    private_channel = active_tickets.get(interaction.user.id)

                    if private_channel:
                        try:
                            await private_channel.send("Thank you! The chat is now closed.")
                            await private_channel.delete()
                        except discord.errors.NotFound:
                            pass  # Channel already deleted

                    # Remove the user from active tickets
                    if interaction.user.id in active_tickets:
                        del active_tickets[interaction.user.id]

                yes_update_button.callback = yes_update_callback
                no_update_button.callback = no_update_callback

                update_button_view.add_item(yes_update_button)
                update_button_view.add_item(no_update_button)

                # Register the view to keep it persistent
                bot.add_view(update_button_view)
                persistent_views.append(update_button_view)

                await interaction.response.send_message(
                    "Proxy Update 2024.11.1.3 is available! Do you want to update your proxy?",
                    view=update_button_view
                )
            else:
                await interaction.response.send_message("Sorry! No updates available.")

                # Close the ticket with an appropriate message
                close_button = Button(
                    label="Close Ticket",
                    style=discord.ButtonStyle.success,
                    custom_id="close_ticket_button"
                )

                async def close_callback(interaction):
                    await interaction.response.send_message(
                        "Thank you! The ticket is now closed."
                    )

                    # Retrieve the private channel
                    private_channel = active_tickets.get(interaction.user.id)

                    if private_channel:
                        try:
                            await private_channel.delete()
                        except discord.errors.NotFound:
                            pass  # Channel already deleted

                    # Remove the user from active tickets
                    if interaction.user.id in active_tickets:
                        del active_tickets[interaction.user.id]

                close_button.callback = close_callback

                close_view = View(timeout=None)
                close_view.add_item(close_button)

                # Register the view
                bot.add_view(close_view)
                persistent_views.append(close_view)

                await interaction.followup.send("Please close the ticket below:", view=close_view)

        # **IP Status Callback**
        async def ip_status_callback(interaction):
            user = interaction.user
            awaiting_input[user.id] = 'ip_status'
            await interaction.response.send_message(
                "Please enter the IP address you want to check."
            )

        # **Close Ticket Callback**
        async def close_ticket_callback(interaction):
            await interaction.response.send_message("Thank you! The ticket is now closed.")

            # Retrieve the private channel
            private_channel = active_tickets.get(interaction.user.id)

            if private_channel:
                try:
                    await private_channel.delete()
                except discord.errors.NotFound:
                    pass  # Channel already deleted

            # Remove the user from active tickets
            if interaction.user.id in active_tickets:
                del active_tickets[interaction.user.id]

            # Log the closure in the transcript channel
            transcript_channel = await get_transcript_channel(guild)
            await transcript_channel.send(
                f"**User:** {interaction.user.name} has closed the ticket."
            )

        # Assign Callbacks
        proxy_button.callback = proxy_callback
        ip_status_button.callback = ip_status_callback
        close_ticket_button.callback = close_ticket_callback

        help_view = View(timeout=None)
        help_view.add_item(proxy_button)
        help_view.add_item(ip_status_button)
        help_view.add_item(close_ticket_button)

        # Register the view
        bot.add_view(help_view)
        persistent_views.append(help_view)

        await private_channel.send("Please choose a topic for help:", view=help_view)

    async def no_callback(interaction):
        await interaction.response.send_message(
            "Okay! If you need help later, just let me know.",
            ephemeral=True
        )

    yes_button.callback = yes_callback
    no_button.callback = no_callback

    view = View(timeout=None)
    view.add_item(yes_button)
    view.add_item(no_button)

    # Register the view
    bot.add_view(view)
    persistent_views.append(view)

    await channel.send(
        content="This is Amexcess Automated Bot for Customer Support. If your proxy is not working or if you need help, click Yes.",
        view=view
    )


# Function to sync orders and updated ISP every 5 minutes
async def sync_data():
    while True:
        await asyncio.sleep(300)  # Wait for 5 minutes (300 seconds)
        global orders, updated_isp
        orders = load_orders()         # Reload the order data
        updated_isp = load_updated_isp()  # Reload the updated ISP data
        print("Orders and updated ISP reloaded.")


# Function to watch ip_status.json for changes
async def watch_ip_status():
    global ip_status_data, ip_status_mtime
    while True:
        await asyncio.sleep(5)  # Check every 5 seconds
        try:
            current_mtime = os.path.getmtime('ip_status.json')
            if current_mtime != ip_status_mtime:
                ip_status_data = load_ip_status()
                ip_status_mtime = current_mtime
                print("ip_status.json has changed. Data reloaded.")
        except FileNotFoundError:
            print("ip_status.json file not found.")
            ip_status_data = {}
            ip_status_mtime = 0


# Listen for messages to handle the user input after buttons are clicked
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Define the allowed channel names
    ALLOWED_CHANNELS = ['𝗦𝗨𝗣𝗣𝗢𝗥𝗧-𝗔𝗜', 'support-transcript-ai']

    if message.guild is not None:
        # If the message is in a guild channel
        if message.channel.name in ALLOWED_CHANNELS or message.channel in active_tickets.values():
            pass  # Proceed to handle the message
        else:
            return  # Ignore messages in other channels

        # Check for the clear command
        if message.content.startswith("/clear all"):
            if message.author.guild_permissions.manage_messages:  # Check if the user has permission
                await message.channel.purge()  # Clear all messages in the channel
                confirmation = await message.channel.send("All messages have been cleared.")
                await asyncio.sleep(5)
                await confirmation.delete()  # Delete the confirmation message
            else:
                await message.channel.send(
                    "You don't have permission to clear messages.", delete_after=5
                )
            return

    user_id = message.author.id

    if user_id in awaiting_input:
        input_type = awaiting_input[user_id]
        if input_type == 'order_id':
            order_id = message.content.strip()

            if order_id in orders:
                order_details = orders[order_id]
                order_date_str = order_details.get('order_date', None)

                if order_date_str:
                    order_date = datetime.strptime(order_date_str, '%d-%m-%Y')
                    current_date = datetime.now()
                    valid_until = order_date + timedelta(days=30)
                    days_left = (valid_until - current_date).days

                    if (current_date - order_date).days >= 25:
                        validation_status = "Expired⛔"
                        ip_info = ""
                    elif current_date <= valid_until:
                        validation_status = "Valid👌"
                        package = order_details.get('package', None)
                        new_isp_info = updated_isp.get(package, None)

                        if new_isp_info:
                            ip_info = (
                                f"🆕 New Updated IP Details 🆕:\n"
                                f"IP: `{new_isp_info['ip']}`\n"
                                f"User: `{new_isp_info['user']}`\n"
                                f"Port: `{new_isp_info['port']}`\n"
                                f"Password: `{new_isp_info['password']}`\n"
                            )
                        else:
                            ip_info = "No updated ISP information available for your package."
                    else:
                        validation_status = "Expired⛔"
                        ip_info = ""

                    renewal_suggestion = ""
                    if days_left <= 5:
                        renewal_suggestion = "\n⚠️ You need to renew to get updated Proxy, as your validation has 5 days or fewer left or expired. Please renew."

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
                        f"{ip_info}"
                    )
                else:
                    response = "Order date not available."
            else:
                response = "Sorry, I couldn't find that Order ID. Please check and try again."

            log_interaction(message.author.name, order_id, response)

            # Send the response in the private channel
            await message.channel.send(response)

            # Log the interaction in the transcript channel with highlighting
            if message.guild is not None:
                transcript_channel = await get_transcript_channel(message.guild)
                await transcript_channel.send(
                    f"**User:** {message.author.name}\n"
                    f"**Query:** `{order_id}`\n"
                    f"**Response:** ```{response}```"
                )

            close_button = Button(
                label="Close Chat",
                style=discord.ButtonStyle.success,
                custom_id="close_chat_button"
            )
            problem_button = Button(
                label="Problem Not Solved",
                style=discord.ButtonStyle.danger,
                custom_id="problem_not_solved_button"
            )

            async def close_callback(interaction):
                await interaction.response.send_message("Thank you! The chat is now closed.")
                try:
                    await message.channel.delete()
                except discord.errors.NotFound:
                    pass  # Channel already deleted

                # Remove the user from active tickets
                if interaction.user.id in active_tickets:
                    del active_tickets[interaction.user.id]

            async def problem_callback(interaction):
                # Find the SUPPORT-TICKET channel
                if message.guild is not None:
                    support_channel = discord.utils.get(
                        message.guild.text_channels, name="support-ticket"
                    )
                    if support_channel:
                        await support_channel.send(
                            f"User {interaction.user.name} indicated their problem is not solved."
                        )

                await interaction.response.send_message(
                    "We apologize for the inconvenience. Please contact support for further assistance."
                )

                # Show the button to close the ticket instead of closing it automatically
                close_button_inner = Button(
                    label="Close Ticket",
                    style=discord.ButtonStyle.success,
                    custom_id="close_ticket_inner_button"
                )

                async def close_inner_callback(interaction):
                    await interaction.response.send_message("Thank you! The ticket is now closed.")
                    try:
                        await message.channel.delete()
                    except discord.errors.NotFound:
                        pass  # Channel already deleted

                    # Remove the user from active tickets
                    if interaction.user.id in active_tickets:
                        del active_tickets[interaction.user.id]

                close_button_inner.callback = close_inner_callback
                close_view_inner = View(timeout=None)
                close_view_inner.add_item(close_button_inner)

                # Register the view
                bot.add_view(close_view_inner)
                persistent_views.append(close_view_inner)

                await message.channel.send(
                    "If you want to close the ticket, please click below:",
                    view=close_view_inner
                )

            close_button.callback = close_callback
            problem_button.callback = problem_callback

            close_view = View(timeout=None)
            close_view.add_item(close_button)
            close_view.add_item(problem_button)

            # Register the view
            bot.add_view(close_view)
            persistent_views.append(close_view)

            await message.channel.send(
                "Is your problem solved? If yes, please close the chat. If no, let us know.",
                view=close_view
            )

            # Remove the awaiting input state
            del awaiting_input[user_id]

        elif input_type == 'ip_status':
            ip_address = message.content.strip()

            status = ip_status_data.get(ip_address)

            if status:
                if status.lower() == 'active':
                    emoji = '✅'
                elif status.lower() == 'inactive':
                    emoji = '❌'
                else:
                    emoji = ''
                response = f"The status of IP `{ip_address}` is {emoji} **{status.upper()}**."
            else:
                response = f"IP address `{ip_address}` not found in our records."

            log_interaction(message.author.name, ip_address, response)

            # Send the response in the private channel
            await message.channel.send(response)

            # Log the interaction in the transcript channel
            if message.guild is not None:
                transcript_channel = await get_transcript_channel(message.guild)
                await transcript_channel.send(
                    f"**User:** {message.author.name}\n"
                    f"**IP Address Checked:** `{ip_address}`\n"
                    f"**Status:** {response}"
                )

            # Provide an option to close the ticket
            close_button = Button(
                label="Close Ticket",
                style=discord.ButtonStyle.success,
                custom_id="close_ticket_after_ip_status"
            )

            async def close_callback(interaction):
                await interaction.response.send_message("Thank you! The ticket is now closed.")
                try:
                    await message.channel.delete()
                except discord.errors.NotFound:
                    pass  # Channel already deleted

                # Remove the user from active tickets
                if interaction.user.id in active_tickets:
                    del active_tickets[interaction.user.id]

            close_button.callback = close_callback

            close_view = View(timeout=None)
            close_view.add_item(close_button)

            # Register the view
            bot.add_view(close_view)
            persistent_views.append(close_view)

            await message.channel.send(
                "If you have no further questions, you can close the ticket below:",
                view=close_view
            )

            # Remove the awaiting input state
            del awaiting_input[user_id]

    else:
        # Handle other messages if necessary
        pass


# Run the bot
bot.run(DISCORD_TOKEN)
