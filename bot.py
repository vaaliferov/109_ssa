import math
import subprocess
import numpy as np
import telegram.ext
import matplotlib.pyplot as plt
from secret import *

SR = 16000
source, shadow = {}, {}

def load_voice(context, file_id):
    context.bot.getFile(file_id).download('a.ogg')
    args = ['opusdec', '--quiet', '--rate', str(SR), 'a.ogg', '-']
    return np.frombuffer(subprocess.check_output(args), dtype=np.int16)

def send_voice(context, chat_id, audio, caption=''):
    args = ['opusenc', '--quiet', '--raw-chan', '1', 
            '--raw-rate', str(SR), '-', 'a.ogg']
    subprocess.check_output(args, input=audio.tobytes())
    with open('a.ogg', 'rb') as fd:
        context.bot.send_voice(chat_id, fd, caption=caption)

def split_audio(audio, n_secs=2):
    n_pieces = math.ceil(len(audio) / (n_secs * SR))
    return np.array_split(audio, n_pieces)

def send_plot(context, chat_id, audio, caption=''):
    fig, ax = plt.subplots(); fig.set_size_inches(6,3)
    ax.plot(audio); fig.savefig('p.jpg'); plt.close(fig)
    with open('p.jpg', 'rb') as fd:
        context.bot.send_photo(chat_id, fd, caption=caption)

def send_spec(context, chat_id, audio, caption=''):
    fig, ax = plt.subplots(); fig.set_size_inches(6,3)
    ax.specgram(audio, Fs=SR, NFFT=512)
    fig.savefig('p.jpg'); plt.close(fig)
    with open('p.jpg', 'rb') as fd:
        context.bot.send_photo(chat_id, fd, caption=caption)

def handle_voice(update, context):
    user = update.message.from_user
    file_id = update.message.voice['file_id']
    audio = load_voice(context, file_id)
    
    if user['id'] != TG_BOT_OWNER_ID:
        msg = f"@{user['username']} {user['id']}"
        context.bot.send_message(TG_BOT_OWNER_ID, msg)
        context.bot.send_voice(TG_BOT_OWNER_ID, file_id)
    
    if user['id'] not in source:
        source[user['id']] = split_audio(audio[::-1])
        send_plot(context, user['id'], audio)
        send_spec(context, user['id'], audio)
        send_voice(context, user['id'], audio[::-1], 'reversed')
        shadow[user['id']] = []
        
    else:
        shadow[user['id']].append(audio)
    
    if len(shadow[user['id']]) < len(source[user['id']]):
        part = f"part #{len(shadow[user['id']]) + 1}"
        audio = source[user['id']][len(shadow[user['id']])]
        send_voice(context, user['id'], audio, part)
        
    else:
        audio = np.concatenate(shadow[user['id']])[::-1]
        send_voice(context, user['id'], audio, 'done!')
        del source[user['id']], shadow[user['id']]

h = telegram.ext.MessageHandler
vf = telegram.ext.Filters.voice 
u = telegram.ext.Updater(TG_BOT_TOKEN)
u.dispatcher.add_handler(h(vf, handle_voice))
u.start_polling(); u.idle()