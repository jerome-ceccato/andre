import socket
import json
import time
import aiohttp
import zlib
import bbcode

import utils

class vndbException(Exception):
    pass

class VNDB(object):
    protocol = 1
    clientname = 'andre'
    clientver = '0.1'

    def __init__(self, username=None, password=None, debug=False):
        self.sock = socket.socket()

        if debug: print('Connecting to api.vndb.org')
        self.sock.connect(('api.vndb.org', 19534))
        if debug: print('Connected')

        if debug: print('Authenticating')
        if (username == None) or (password == None):
            self.sendCommand('login', {'protocol': self.protocol, 'client': self.clientname,
                                       'clientver': float(self.clientver)})
        else:
            self.sendCommand('login', {'protocol': self.protocol, 'client': self.clientname,
                                       'clientver': float(self.clientver), 'username': username, 'password': password})
        res = self.getRawResponse()
        if res.find('error ') == 0:
            raise vndbException(json.loads(' '.join(res.split(' ')[1:]))['msg'])
        if debug: print('Authenticated')

        self.cache = {'get': []}
        self.cachetime = 3600 * 12  # cache stuff for 12 hours

    def close(self):
        self.sock.close()

    def get(self, type, flags, filters, options):
        args = '{0} {1} {2} {3}'.format(type, flags, filters, options)
        for item in self.cache['get']:
            if (item['query'] == args) and (time.time() < (item['time'] + self.cachetime)):
                return item['results']

        self.sendCommand('get', args)
        res = self.getResponse()[1]
        self.cache['get'].append({'time': time.time(), 'query': args, 'results': res})
        return res

    def sendCommand(self, command, args=None):
        whole = ''
        whole += command.lower()
        if isinstance(args, str):
            whole += ' ' + args
        elif isinstance(args, dict):
            whole += ' ' + json.dumps(args)

        self.sock.send('{0}\x04'.format(whole).encode())

    def getResponse(self):
        args = {}
        res = self.getRawResponse()
        cmdname = res.split(' ')[0]
        if len(res.split(' ')) > 1:
            args = json.loads(' '.join(res.split(' ')[1:]))

        if cmdname == 'error':
            if args['id'] == 'throttled':
                raise vndbException('Throttled, limit of 100 commands per 10 minutes')
            else:
                raise vndbException(args['msg'])
        return (cmdname, args)

    def getRawResponse(self):
        finished = False
        whole = ''
        while not finished:
            whole += self.sock.recv(4096).decode('utf-8')
            if '\x04' in whole: finished = True
        return whole.replace('\x04', '').strip()


class VNDBStatic(object):

    def __init__(self):
        self.cache = {'tags': None, 'traits': None}
        self.cache_last = {}
        self.cache_last['tags'] = utils.utils.read_property('vndb_cache_tags')
        self.cache_last['traits'] = utils.utils.read_property('vndb_cache_traits')

        self.load_from_cache('tags')
        self.load_from_cache('traits')

        self.bbcode_parser = self.build_bbcode_parser()
        self.bbcode_parser_spoil = self.build_bbcode_parser(spoiler=True)

        self.aliases = utils.utils.read_property('vndb_aliases', {})

    def load_from_cache(self, identifier):
        cache_limit = 3600 * 24
        if self.cache_last[identifier] and time.time() - self.cache_last[identifier] < cache_limit:
            if not self.cache[identifier]:
                with open(f'data/cache/vndb_{identifier}.json') as f:
                    self.cache[identifier] = json.load(f)
            return self.cache[identifier]
        else:
            self.cache[identifier] = None
            self.cache_last[identifier] = None
            return None

    def cache_new_data(self, identifier, data):
        now = time.time()
        self.cache[identifier] = data
        self.cache_last[identifier] = now

        utils.utils.write_property(f'vndb_cache_{identifier}', now)
        with open(f'data/cache/vndb_{identifier}.json', 'w') as f:
            json.dump(data, f)

    def extract_data(self, identifier, raw):
        if identifier == 'tags':
            data = {}
            for item in raw:
                parents_string = list(map(lambda x: str(x), item['parents']))
                data[str(item['id'])] = {'name': item['name'], 'parents': parents_string, 'cat': item['cat']}
            return data
        elif identifier == 'traits':
            data = {}
            for item in raw:
                parents_string = list(map(lambda x: str(x), item['parents']))
                data[str(item['id'])] = {'name': item['name'], 'parents': parents_string}
            return data
        return raw

    async def require_data(self, identifier):
        data = self.load_from_cache(identifier)
        if data:
            return data

        print(f'Will load {identifier}')
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://vndb.org/api/{identifier}.json.gz') as response:
                try:
                    raw_json = zlib.decompress(await response.read(), 16+zlib.MAX_WBITS)
                    data = json.loads(raw_json)
                    data = self.extract_data(identifier, data)
                    self.cache_new_data(identifier, data)
                    return data
                except Exception as e:
                    print(e)
                    return None

    def game_length(self, id):
        lengths = {1: 'Very short (< 2 hours)',
                   2: 'Short (2 - 10 hours)',
                   3: 'Medium (10 - 30 hours)',
                   4: 'Long (30 - 50 hours)',
                   5: 'Very long (> 50 hours)'}
        return lengths[id] if id in lengths else 'Unknown'

    def gender_display_char(self, gender):
        genders = {'f': '♀',
                   'm': '♂',
                   'b': '⚤'}
        return genders[gender] if gender in genders else '?'

    def birthday_display_string(self, birthday):
        def month_string(value):
            months = ["Unknown",
                      "January",
                      "Febuary",
                      "March",
                      "April",
                      "May",
                      "June",
                      "July",
                      "August",
                      "September",
                      "October",
                      "November",
                      "December"]
            return months[value] if value > 0 and value <= 12 else '?'

        if len(birthday) == 2:
            return '{} {}'.format(birthday[0] or '', month_string(birthday[1] or 0))
        return 'Unknown'

    def measurements_display_string(self, chara):
        items = []
        if chara.get('height', None):
            items.append(f'Height: {chara["height"]}cm')
        if chara.get('weight', None):
            items.append(f'Weight: {chara["weight"]}kg')
        if chara.get('bust', None) and chara.get('waist', None) and chara.get('hip', None):
            items.append('Bust-Waist-Hips: {}-{}-{}cm'.format(chara['bust'], chara['waist'], chara['hip']))
        return '\n'.join(items) if items else None


    def build_bbcode_parser(self, spoiler=False):
        parser = bbcode.Parser(newline='\n',
                               install_defaults=False,
                               escape_html=False,
                               replace_links=False,
                               replace_cosmetic=False,
                               drop_unrecognized=True)

        def true_formatter(tag, value, options, parent, context):
            if tag == 'url':
                return f'**{value}**'
            elif tag == 'spoiler':
                if spoiler:
                    return f'*{value}*'
                return '~~spoiler~~'
            elif tag == 'raw':
                return f'`{value}`'
            elif tag in ['quote', 'code']:
                return f'```{value}```'
            return ''

        for tag in ['url', 'spoiler', 'quote', 'raw', 'code']:
            parser.add_formatter(tag, true_formatter, escape_html=False, replace_links=False, replace_cosmetic=False)

        return parser

    def purge_bbcode(self, input, spoiler=False):
        if spoiler:
            return self.bbcode_parser_spoil.format(input)
        else:
            return self.bbcode_parser.format(input)

    def synchronize_aliases(self):
        utils.utils.write_property('vndb_aliases', self.aliases)
