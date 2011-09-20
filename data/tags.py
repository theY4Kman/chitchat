import redis

class Tagging(object):
    __slots__ = ['db']
    
    def __init__(self, db=None, port=9201):
        if db is None:
          db = redis.Redis(port=port)
        self.db = db
    
    def addtags(self, key, tags):
        for tag in tags:
            self.db.sadd('tag_group:' + tag, key)
            self.db.sadd('tags:' + key, tag)
    
    def addtag(self, key, tag):
        self.db.sadd('tag_group:' + tag, key)
        self.db.sadd('tags:' + key, tag)
    
    def removetags(self, key, tags):
        for tag in tags:
            self.db.srem('tag_group:' + tag, key)
            self.db.srem('tags:' + key, tag)
    
    def removetag(self, key, tag):
        self.db.srem('tag_group:' + tag, key)
        self.db.srem('tags:' + key, tag)
    
    def gettags(self, key):
        if not self.db.exists('tags:' + key):
            return None
        return self.db.smembers('tags:' + key)
    
    def getkeys(self, tag):
        if not self.db.exists('tag_group:' + tag):
            return None
        return self.db.smembers('tag_group:' + tag)
    
    def gettagnames(self):
        return [key.split(':')[1] for key in self.db.keys('tag_group:*')][::-1]
    
    def hastag(self, key, tag):
        if not self.db.exists('tags:' + key):
            return False
        return self.db.sismember('tags:' + key, tag)