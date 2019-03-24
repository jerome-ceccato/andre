import json
import glob
import random
import discord

client = discord.Client()

def load_config():
    with open('config.json') as f:
        return json.load(f)

config = load_config()

@client.event
async def on_ready():
    print('is ready')
    files = glob.glob('avatar/*.*g')
    with open(random.choice(files), 'rb') as f:
        await client.edit_profile(password=config['user_password'], avatar=f.read())
    print('should have edited profile')
    await client.logout()

def main():
    client.run(config['user_token'], bot=False)

if __name__ == "__main__":
    main()
