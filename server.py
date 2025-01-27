# <Trading Game>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import os
import os.path
import urlparse
from binascii import crc32
from time import time
import sys
import argparse
import flask
from gevent.wsgi import WSGIServer
import gevent
import redis
from werkzeug import SharedDataMiddleware

from data.tags import Tagging
from data.util import Util

from gevent import monkey
monkey.patch_all()

import game
reload(game)

app = None
db = None
tags = None
util = None
base = os.path.dirname(__file__)

ADMIN_KEY = 'adminueqytMXDDS'


def all_events():
    ids = db.smembers('used_url_ids')
    events = dict([(id, db.lrange('%s:log' % id, 0, -1)) for id in ids])
    return events


def startapp(args):
    global app, db
    global get_next_url, add_next_url, add_urls, gen_url_csv, clear_urls
    
    app = flask.Flask(__name__, static_url_path='/')

    # Turn Debug on
    app.debug = True
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/': os.path.join(base, 'static')})

    db = redis.Redis(port=args.redis_port)
    game.setup_redis(args.redis_port)
    
    tags = Tagging(db)
    util = Util(db)

    @app.route('/')
    def index(**kwargs):
        if args.debug:
            with open(os.path.join(base, 'static', 'game.htm'), 'r') as fp:
                return fp.read()
        else:
            return "Error message. Only access this page with a session"

    # Main page for a session
    @app.route('/<userkey>/')
    def default(userkey=None, **kwargs):
        if userkey == ADMIN_KEY:
            return "Wow! You are an admin"

        # Return an error if they are not a valid user
        if not db.sismember('invited_userkeys', userkey):
            return 'This user key is not invited', 403

        # Render the main page
        with open(os.path.join(base, 'static', 'game.htm'), 'r') as fp:
            return fp.read()

    @app.route('/post/<userkey>/', methods=['POST'])
    def post(userkey, **kwargs):
        status = game.user_status(userkey)
        if status['status'] == 'uninvited':
            flask.abort(403)

        # Check if we should be considering the form
        events = json.loads(flask.request.form['events'])
        for event in events:
            # Deal with the event
            game.process_user_event(userkey, event)
        return 'OK'

    @app.route('/events/<userkey>/', methods=['POST'])
    def events(userkey):
        def response(events):
            rv = flask.make_response()
            rv.mimetype = 'text/json'
            rv.data = json.dumps(events)
            return rv
            
        status = game.user_status(userkey)
        if status['status'] == 'uninvited':
            return response([status])

        if status['status'] == 'queued':
            # try to avoid a race condition here
            with db.pipeline() as pipe:
                pipe.watch('user_status:%s' % userkey)
                status = json.loads(pipe.get('user_status:%s' % userkey))
                pipe.multi()
                assert status['status'] == 'queued'
                status['lastseen'] = repr(time())
                pipe['user_status:%s' % userkey] = json.dumps(status)
                pipe.execute()
                print 'refreshed!'

        for i in range(30):
            since = None
            if 'since' in flask.request.form:
                since = flask.request.form['since']
            events = game.events_for_user(userkey, since)

            # Return if there are some events
            if events:
                # Add a time event to help sync the alarms
                events.append({'name': 'time',
                               'time': repr(time()), 'data': {}})
                return response(events)

            # Otherwise wait and poll
            gevent.sleep(1)

        return response([])
    
    @app.route('/quest/<userkey>/', methods=['GET'])
    def quest(userkey):
        if userkey == ADMIN_KEY:
            return "Wow! You are an admin"

        # Return an error if they are not a valid user
        if not db.sismember('invited_userkeys', userkey):
            return 'This user key is not invited', 403

        # Go immediately to questover if we already have their survey 
        if db.exists('survey_user:%s' % userkey):
            return flask.redirect('/questover/%s/' % userkey)

        # Render the main page
        status = game.user_status(userkey)
        with open(os.path.join(base, 'static', 'quest.htm'), 'r') as fp:
            return fp.read().replace('{{userkey}}', userkey)\
                   .replace('{{role}}', status['role'])

    @app.route('/overqueued/<userkey>/', methods=['GET'])
    def overqueued(userkey):

        # Return an error if they are not a valid user
        if not db.sismember('invited_userkeys', userkey):
            return 'This user key is not invited', 403

        # Render the main page
        with open(os.path.join(base, 'static', 'overqueued.htm'), 'r') as fp:
            return fp.read()
    
    @app.route('/questover/<userkey>/', methods=['GET', 'POST'])
    def questover(userkey):
        if userkey == ADMIN_KEY:
            return "Wow! You are an admin"
        
        if flask.request.method == 'POST':
            db['survey_user:%s' % userkey] = json.dumps({
                'situation_fair': flask.request.form['situation_fair'],
                'seller_truth': flask.request.form['seller_truth'],
                'buyer_truth': flask.request.form['buyer_truth'],
                'insurer_truth': flask.request.form['insurer_truth'],
                'comments': flask.request.form['comments'],
                'interest': flask.request.form['interest'],
            });

        # Return an error if they are not a valid user
        if not db.sismember('invited_userkeys', userkey):
            return 'This user key is not invited', 403

        # Render the main page
        with open(os.path.join(base, 'static', 'questover.htm'), 'r') as fp:
            return fp.read()
    
    @app.route('/queueover/')
    def queueover():
        with open(os.path.join(base, 'static', 'queueover.htm'), 'r') as fp:
            return fp.read()

    @app.route('/adminueqytMXDDS/newuser')
    def admin_newuser():
        # Create a new random string
        userkey = game.add_invite()
        return flask.redirect('/' + userkey)

    seller_sends = {
        'send_money_insurer_seller': ('insurer', 'seller'),
        'send_money_seller_insurer': ('seller', 'insurer'),
    }
    buyer_sends = {
        'send_money_insurer_buyer': ('insurer', 'buyer'),
        'send_money_buyer_insurer': ('buyer', 'insurer'),
    }
    both_sends = {
        'send_money_buyer_seller': ('buyer', 'seller'),
        'send_token': ('seller', 'buyer')
    }
    
    @app.route('/adminueqytMXDDS/')
    def admin():
        mturk_users = db.hgetall('notified_workers').values()
        
        games = []
        for key in db.keys('game:*'):
            events = db.zrange('events_' + key, 0, -1)
            
            game = {
                'key': key,
                'buyer_log': [],
                'seller_log': [],
                'has_chat': False
            }
            
            state = json.loads(db[key])
            for role in ('buyer', 'seller', 'insurer'):
                game[role] = {}
                
                userkey = state[role]['userkey']
                game[role]['key'] = userkey
                if db.exists('survey_user:%s' % userkey):
                    game[role]['answers'] = json.loads(db['survey_user:%s' % userkey])
                else:
                    game[role]['answers'] = {'none': True}
                game[role]['is_mturk'] = userkey in mturk_users
            
            for event in events:
                event = json.loads(event)
                event['data']['name'] = event['name']
                event['data']['time'] = event['time']
                
                if event['name'] == 'chat':
                    game['has_chat'] = True
                    if event['data']['chatbox'] == 'buyer':
                        game['buyer_log'].append(event['data'])
                    elif event['data']['chatbox'] == 'seller':
                        game['seller_log'].append(event['data'])
                
                elif event['name'] in seller_sends:
                    send = seller_sends[event['name']]
                    event['data']['from'] = send[0]
                    event['data']['to'] = send[1]
                    game['seller_log'].append(event['data'])
                
                elif event['name'] in buyer_sends:
                    send = buyer_sends[event['name']]
                    event['data']['from'] = send[0]
                    event['data']['to'] = send[1]
                    game['buyer_log'].append(event['data'])
                
                elif event['name'] in both_sends:
                    send = both_sends[event['name']]
                    event['data']['from'] = send[0]
                    event['data']['to'] = send[1]
                    
                    game['buyer_log'].append(event['data'])
                    game['seller_log'].append(event['data'])
            
            games.append(game)
        
        queue = []
        for user,queuetime in db.zrange('queue', 0, -1, withscores=True):
            waited = time() - queuetime
            lastseen = time() - float(json.loads(db['user_status:' +
                                                    user])['lastseen'])
            queue.append({'waited': waited,
                          'userkey': user, 'lastseen': lastseen})
        
        return flask.render_template('admin.htm', games=games, queue=queue)
    
    @app.route('/adminueqytMXDDS/tags/add/', methods=['POST'])
    def admin_tags_add():
        tags.addtag(flask.request.form['key'], flask.request.form['tag'],
            flask.request.form['prefix'])
        return 'OK'
    
    @app.route('/adminueqytMXDDS/tags/update/', methods=['POST'])
    def admin_tags_update():
        tags.updatetags(flask.request.form['key'],
            json.loads(flask.request.form['tags']), flask.request.form['prefix'])
        return 'OK'
    
    @app.route('/adminueqytMXDDS/tags/remove/', methods=['POST'])
    def admin_tags_remove():
        tags.removetag(flask.request.form['key'], flask.request.form['tag'],
            flask.request.form['prefix'])
        return 'OK'
    
    @app.route('/adminueqytMXDDS/tags/get/', methods=['POST'])
    def admin_tags_get():
        t = tags.gettags(flask.request.form['key'], flask.request.form['prefix'])
        if t is None:
            return '[]'
        
        return json.dumps(list(t))

    @app.route('/adminueqytMXDDS/tags/')
    def admin_tags():
        mturk_users = db.hgetall('notified_workers').values()
        
        games = []
        for key in db.keys('game:*'):
            events = db.zrange('events_' + key, 0, -1)
            
            state = json.loads(db[key])
            game = {
                'key': key,
                'buyer_log': [],
                'seller_log': [],
                'has_chat': False,
                'cond': state['condition'],
                'starttime': float(state['starttime'])
            }
            
            for role in ('buyer', 'seller', 'insurer'):
                game[role] = {}
                
                userkey = state[role]['userkey']
                game[role]['key'] = userkey
                if db.exists('survey_user:%s' % userkey):
                    game[role]['answers'] = json.loads(db['survey_user:%s' % userkey])
                else:
                    game[role]['answers'] = {'none': True}
                game[role]['is_mturk'] = userkey in mturk_users
            
            for event in events:
                event = json.loads(event)
                event['data']['name'] = event['name']
                event['data']['time'] = event['time']
                
                if event['name'] == 'chat':
                    game['has_chat'] = True
                    if event['data']['chatbox'] == 'buyer':
                        game['buyer_log'].append(event['data'])
                    elif event['data']['chatbox'] == 'seller':
                        game['seller_log'].append(event['data'])
                
                elif event['name'] in seller_sends:
                    send = seller_sends[event['name']]
                    event['data']['from'] = send[0]
                    event['data']['to'] = send[1]
                    game['seller_log'].append(event['data'])
                
                elif event['name'] in buyer_sends:
                    send = buyer_sends[event['name']]
                    event['data']['from'] = send[0]
                    event['data']['to'] = send[1]
                    game['buyer_log'].append(event['data'])
                
                elif event['name'] in both_sends:
                    send = both_sends[event['name']]
                    event['data']['from'] = send[0]
                    event['data']['to'] = send[1]
                    
                    game['buyer_log'].append(event['data'])
                    game['seller_log'].append(event['data'])
            
            games.append(game)
        
        return flask.render_template('tags.htm', games=games, util=util, tags=tags)
    
    @app.route('/adminueqytMXDDS/table')
    def admin_table():
        if not app.debug:
            return '', 404
        
        html = '<link rel="stylesheet" href="/css/other-screen.css" />'
        ids = db.smembers('used_url_ids')
        for id in ids:
            events = db.lrange('%s:log' % id, 0, -1)
            html += '''\
<div style="margin-bottom: 3em;">
  <h2>%s</h2>
  <ul>
    <li>%s</li>
  </ul>
</div>
''' % (id, '    </li>\n    <li>'.join(events) or 'No events')
        
        return html


def main():
    global args
    parser = argparse.ArgumentParser('<Trading Game>')
    parser.add_argument('--port', type=int, default=9202)
    parser.add_argument('--redis-port', type=int, default=9201)
    parser.add_argument('--debug', type=bool, default=False)
    args = parser.parse_args()
    
    startapp(args)

    print 'Serving on port', args.port
    if app.debug and 0:  # Use gevent?
        app.run('0.0.0.0', args.port)
    else:
        http_server = WSGIServer(('', args.port), app)
        http_server.serve_forever()
        
if __name__ == '__main__':
    main()
