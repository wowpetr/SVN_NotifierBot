#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# SVN Notifier Bot monitors Apache Subversion (SVN) repositories
# and sends messages when new commits are made.
#
# Copyright (c) 2017 Petr Losev
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import svn.remote
from telegram.ext import Updater, CommandHandler


# Global constants
THIS_BOT_TOKEN = ''
SVN_CHECK_INTERVAL = 900  # in seconds
SVN_MSG_LIMIT = 10
N_LAST_COMMITS_AT_START = 1  # how many old log messages are shown when /start


def check_svn_job(bot, job):
    if job.context not in bot.reg_data:
        return

    chat_id = job.context
    repos_list = bot.reg_data[chat_id]

    for rep_addr in repos_list:

        last_timestamp = repos_list[rep_addr]

        # Receive the log data from the SVN repository
        r = svn.remote.RemoteClient(rep_addr)
        t = r.log_default(timestamp_from_dt=last_timestamp,
                          timestamp_to_dt=None,
                          limit=SVN_MSG_LIMIT)

        new_timestamp = None
        i = 0
        for m in t:
            if last_timestamp is None or m.date > last_timestamp:
                i += 1

                if i == 1:
                    new_timestamp = m.date

                # Defining the right adjective for noun "commit"
                if last_timestamp is None:
                    adj_commit = 'Last'
                else:
                    adj_commit = 'New'

                chat_msg = '<strong>' + adj_commit + ' commit</strong> (' + str(m.revision) + ')   ' + \
                    m.date.strftime("%c") + '   <b>' + m.author + '</b>' + '\n\n' + \
                    '<i>' + str(m.msg) + '</i>' + '\n\n' + \
                    'Repository: ' + rep_addr

                bot.send_message(job.context, text=chat_msg, parse_mode='HTML')

                if last_timestamp is None and i == N_LAST_COMMITS_AT_START:
                    break

        if new_timestamp is not None:
            repos_list[rep_addr] = new_timestamp


def start(bot, update, job_queue):

    # update.message.reply_text('SVN_NotifierBot has started.')

    # Creating jobs for current chat room
    chat_id = update.message.chat_id
    if chat_id in bot.reg_data:

        # show last log messages at once
        if N_LAST_COMMITS_AT_START > 0:
            job_queue.run_once(check_svn_job, 3, context=chat_id)

        # regular check for new commits
        job_queue.run_repeating(check_svn_job, SVN_CHECK_INTERVAL, context=chat_id)


def add(bot, update, args):
    if args:
        repos = args[0]
    else:
        update.message.reply_text('Usage: /add <repository>')
        return

    chat_id = update.message.chat_id
    chats = bot.reg_data
    if chat_id in chats:
        chats[chat_id][repos] = None
    else:
        chats[chat_id] = {repos: None}

    update.message.reply_text('Repository <' + repos + '> has successfully added.')


def list_(bot, update):
    chat_id = update.message.chat_id
    repos_list = ''

    # if chat_id in bot.reg_data:
    for i, val in enumerate(bot.reg_data.get(chat_id, []), start=1):
        repos_list += str(i) + '. ' + val + '\n'

    if repos_list == '':
        update.message.reply_text('There are not any repositories registered.')
    else:
        update.message.reply_text(repos_list)


def main():
    updater = Updater(THIS_BOT_TOKEN)
    updater.bot.reg_data = dict()

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start, pass_job_queue=True))
    dp.add_handler(CommandHandler("add", add, pass_args=True))
    dp.add_handler(CommandHandler("list", list_))

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()