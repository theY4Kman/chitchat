import redis

class Tagging(object):
    __slots__ = ['db']
    
    def __init__(self, db=None, port=9201):
        if db is None:
          db = redis.Redis(port=port)
        self.db = db
    
    def addtags(self, key, tags, prefix=''):
        for tag in tags:
            self.db.sadd('tag_group:%s:%s' % (prefix, tag), key)
            self.db.sadd('tags:%s:%s' % (prefix, key), tag)
    
    def addtag(self, key, tag, prefix=''):
        self.db.sadd('tag_group:%s:%s' % (prefix, tag), key)
        self.db.sadd('tags:%s:%s' % (prefix, key), tag)
    
    def updatetags(self, key, tags, prefix=''):
        '''Given a list of `tags`, automatically adds or removes tags'''
        current = set([])
        if self.db.exists('tags:%s:%s' % (prefix, key)):
            current = self.db.smembers('tags:%s:%s' % (prefix, key))
        
        tags = set(tags)
        self.addtags(key, (tags - current), prefix)
        self.removetags(key, (current - tags), prefix)
    
    def removetags(self, key, tags, prefix=''):
        for tag in tags:
            self.db.srem('tag_group:%s:%s' % (prefix, tag), key)
            self.db.srem('tags:%s:%s' % (prefix, key), tag)
    
    def removetag(self, key, tag, prefix=''):
        self.db.srem('tag_group:%s:%s' % (prefix, tag), key)
        self.db.srem('tags:%s:%s' % (prefix, key), tag)
    
    def gettags(self, key, prefix=''):
        if not self.db.exists('tags:%s:%s' % (prefix, key)):
            return None
        return self.db.smembers('tags:%s:%s' % (prefix, key))
    
    def getkeys(self, tag, prefix=''):
        if not self.db.exists('tag_group:%s:%s' % (prefix, tag)):
            return None
        return self.db.smembers('tag_group:%s:%s' % (prefix, tag))
    
    def gettagnames(self, prefix=''):
        return [key.split(':', 2)[-1] for key in self.db.keys('tag_group:' + prefix + ':*')][::-1]
    
    def hastag(self, key, tag, prefix=''):
        if not self.db.exists('tags:%s:%s' % (prefix, key)):
            return False
        return self.db.sismember('tags:%s:%s' % (prefix, key), tag)
    
    def _erase_all_tags(self, prefix='*'):
        num = self.db.delete(*self.db.keys('tags:%s:*' % prefix))
        num += self.db.delete(*self.db.keys('tag_group:%s:*' % prefix))
        return num