import matplotlib
import numpy as np
import matplotlib.pyplot as plt
import math, argparse, subprocess
from telegram.ext import Updater, MessageHandler, Filters


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('id', type=int, help='bot owner id')
    parser.add_argument('token', type=str, help='bot token')
    return parser.parse_args()

def load_voice(context, file_id):
    context.bot.getFile(file_id).download('a.ogg')
    args = ['opusdec', '--quiet', '--rate', str(16000), 'a.ogg', '-']
    return np.frombuffer(subprocess.check_output(args), dtype=np.int16)

def send_voice(context, chat_id, audio, caption=''):
    args = ['opusenc', '--quiet', '--raw-chan', '1', 
            '--raw-rate', str(16000), '-', 'a.ogg']
    subprocess.check_output(args, input=audio.tobytes())
    with open('a.ogg', 'rb') as fd:
        context.bot.send_voice(chat_id, fd, caption=caption)

def split_audio(audio, n_secs=2):
    n_pieces = math.ceil(len(audio) / (n_secs * 16000))
    return np.array_split(audio, n_pieces)

def send_plot(context, chat_id, audio, caption=''):
    fig, ax = plt.subplots(); fig.set_size_inches(6,3)
    ax.plot(audio); fig.savefig('p.jpg'); plt.close(fig)
    with open('p.jpg', 'rb') as fd:
        context.bot.send_photo(chat_id, fd, caption=caption)

def send_spec(context, chat_id, audio, caption=''):
    fig, ax = plt.subplots(); fig.set_size_inches(6,3)
    ax.specgram(audio, Fs=16000, NFFT=512)
    fig.savefig('p.jpg'); plt.close(fig)
    with open('p.jpg', 'rb') as fd:
        context.bot.send_photo(chat_id, fd, caption=caption)


args = parse_args()
matplotlib.use('Agg')
source, shadow = {}, {}


def handle_voice(update, context):

    user = update.message.from_user
    file_id = update.message.voice['file_id']
    audio = load_voice(context, file_id)

    if user['id'] != args.id:
        msg = f"@{user['username']} {user['id']}"
        context.bot.send_message(args.id, msg)
        context.bot.send_voice(args.id, file_id)
    
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


updater = Updater(args.token)
voice_handler = MessageHandler(Filters.voice, handle_voice)
updater.dispatcher.add_handler(voice_handler)
updater.start_polling()
updater.idle()