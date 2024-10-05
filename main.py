import discord
import os
import json
import logging
from discord.ui import Button, View
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

# This will store the order data loaded from the file
orders = load_orders()

# Updated IP information based on packages
updated_ips = {
    "1 Month - 100Mbps": {
        "ip": "49.0.41.6",
        "user": "REXFTP",
        "port": "14852",
        "password": "REXFTP86325"
    },
    "1 Month - 50Mbps": {
        "ip": "103.35.109.22",
        "user": "REXFTP",
        "port": "4040",
        "password": "REXFTP563258"
    },
}

# This will store the user and the state of awaiting order ID
awaiting_order_id = {}

# Setup logging to log interactions to a file
logging.basicConfig(
    filename='bot_interactions.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

def log_interaction(user, query, response):
    log_message = f"User: {user} | Query: {query} | Response: {response}"
    logging.info(log_message)

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

# Function to greet the user and present Yes/No buttons
async def greet_user(channel):
    # Create Yes and No buttons
    yes_button = Button(label="Yes", style=discord.ButtonStyle.success)
    no_button = Button(label="No", style=discord.ButtonStyle.danger)

    # Define what happens when the Yes button is clicked
    async def yes_callback(interaction):
        # Create buttons for help topics
        proxy_button = Button(label="If your proxy not working click here to Check proxy update", style=discord.ButtonStyle.primary)
        normal_button = Button(label="Ask question", style=discord.ButtonStyle.secondary)

        # Define what happens when the Check for proxy updates button is clicked
        async def proxy_callback(interaction):
            # Check if an update is available (this is where you can implement your own logic)
            update_available = True  # Change this according to your update logic

            if update_available:
                # Ask the user if they want to update their proxy
                update_button_view = View()
                yes_update_button = Button(label="Yes", style=discord.ButtonStyle.success)
                no_update_button = Button(label="No", style=discord.ButtonStyle.danger)

                async def yes_update_callback(interaction):
                    # Set the state that this user is awaiting an order ID
                    awaiting_order_id[interaction.user.id] = True
                    await interaction.response.send_message("Please provide your Order ID by sending it in the chat.")

                async def no_update_callback(interaction):
                    await interaction.response.send_message("Okay! If you need further assistance, let me know.")

                yes_update_button.callback = yes_update_callback
                no_update_button.callback = no_update_callback

                update_button_view.add_item(yes_update_button)
                update_button_view.add_item(no_update_button)

                await interaction.response.send_message("Update is available! Do you want to update your proxy?", view=update_button_view)
            else:
                await interaction.response.send_message("No updates are available at this time.")

        # Define what happens when the Normal Help button is clicked
        async def normal_callback(interaction):
            await interaction.response.send_message("Ask your question here, and we'll assist you.")

        # Assign the callbacks to the buttons
        proxy_button.callback = proxy_callback
        normal_button.callback = normal_callback

        # Create a new view to hold the help topic buttons
        help_view = View()
        help_view.add_item(proxy_button)
        help_view.add_item(normal_button)

        # Respond to the interaction with the help topic buttons
        await interaction.response.send_message("Please choose a topic for help:", view=help_view)

    # Define what happens when the No button is clicked
    async def no_callback(interaction):
        await interaction.response.send_message("Okay! If you need help later, just let me know.")

    # Assign the callbacks to the Yes and No buttons
    yes_button.callback = yes_callback
    no_button.callback = no_callback

    # Create a view to hold the Yes and No buttons
    view = View()
    view.add_item(yes_button)
    view.add_item(no_button)

    # Send the updated greeting message with the buttons
    await channel.send("This is Amexcess Automated Bot for Customer Support. If your proxy not working or if you need help click Yes", view=view)

# Listen for messages to handle the order ID after the "Yes" button is clicked for updates
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if the user is awaiting an Order ID
    if message.author.id in awaiting_order_id and awaiting_order_id[message.author.id]:
        order_id = message.content.strip()

        # Check if the order ID exists in the orders dictionary
        if order_id in orders:
            order_details = orders[order_id]
            order_date_str = order_details.get('order_date', None)  # Get the order date
            
            if order_date_str:
                # Parse the order_date from string to datetime object
                order_date = datetime.strptime(order_date_str, '%d-%m-%Y')
                current_date = datetime.now()

                # Calculate the expiration date (30 days after order date)
                valid_until = order_date + timedelta(days=30)

                # Calculate days left until expiration
                days_left = (valid_until - current_date).days

                # Check if the order was placed 25 days ago or more
                if (current_date - order_date).days >= 25:
                    validation_status = "Expired⛔"
                    ip_info = ""  # Don't provide new IP information
                elif current_date <= valid_until:
                    validation_status = "Valid👌"
                    package = order_details.get('package', None)
                    new_ip_info = updated_ips.get(package, None)

                    if new_ip_info:
                        ip_info = (f"🆕New Updated IP Details🆕:\n"
                                   f"IP: {new_ip_info['ip']}\n"
                                   f"User: {new_ip_info['user']}\n"
                                   f"Port: {new_ip_info['port']}\n"
                                   f"Password: {new_ip_info['password']}\n")
                    else:
                        ip_info = "No updated IP information available for your package."
                else:
                    validation_status = "Expired⛔"
                    ip_info = ""

                # Suggest renewal if there are 5 or fewer days left
                renewal_suggestion = ""
                if days_left <= 5:
                    renewal_suggestion = "\n⚠️You have to renew to get updated Proxy, Because your validation 5 or fewer days left or Expired Please Renew."

                response = (f"Order Details:\n"
                            f"Name: {order_details['name']}\n"
                            f"Email: {order_details['email']}\n"
                            f"Phone Number: {order_details['phone']}\n"
                            f"IP Given: {order_details['ip']}\n"
                            f"Order Date: {order_date_str}\n"
                            f"Total Amount: {order_details['total_amount']}\n"
                            f"Package: {order_details['package']}\n"
                            f"Validation Status: {validation_status}\n"
                            f"Days Left: {days_left}{renewal_suggestion}\n"
                            f"{ip_info}")
            else:
                response = "Order date not available"
        else:
            response = "Sorry, I couldn't find that Order ID. Please check and try again."

        # Log the interaction to the file
        log_interaction(message.author.name, order_id, response)

        # Send the response to the user
        await message.channel.send(response)

        # Show "Close Chat" and "Problem Not Solved" buttons after providing IP details
        close_button = Button(label="Close Chat", style=discord.ButtonStyle.success)
        problem_button = Button(label="Problem Not Solved", style=discord.ButtonStyle.danger)

        # Define what happens when the "Close Chat" button is clicked
        async def close_callback(interaction):
            await interaction.response.send_message("Thank you! The chat is now closed.")

        # Define what happens when the "Problem Not Solved" button is clicked
        async def problem_callback(interaction):
            await interaction.response.send_message("We apologize for the inconvenience. Please contact support for further assistance.")

        close_button.callback = close_callback
        problem_button.callback = problem_callback

        # Create a view to hold the buttons
        close_view = View()
        close_view.add_item(close_button)
        close_view.add_item(problem_button)

        # Send the message with the buttons
        await message.channel.send("Is your problem solved? If yes, please close the chat. If no, let us know.", view=close_view)

        # Reset the state
        awaiting_order_id[message.author.id] = False

# Start the bot with the specified token
bot.run(DISCORD_TOKEN)
