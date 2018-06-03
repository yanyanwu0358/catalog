"""
Uses a line separated file listing bad words as it's source
to check if a user submitted something inappropriate

f = Filter('slut', clean_word='unicorn')
word = f.clean()
print word
>>slut
"""
import re

current_file_path = __file__
current_file_dir = os.path.dirname(__file__)
bw_file_path = os.path.join(current_file_dir, "static/bad_words.txt")

class Filter(object):
    """
    Replaces a bad word in a string with something more PG friendly
    
    Filter('you annoying prick', 'unicorn')
    
    """
    def __init__(self, original_string, clean_word='****'):
        
        bad_words_file = open(bw_file_path, 'r')
        
        self.bad_words = set(line.strip('\n') for line in open(bw_file_path))
        self.original_string = original_string
        self.clean_word = clean_word
        
    def clean(self):
        exp = '(%s)' %'|'.join(self.bad_words)
        r = re.compile(exp, re.IGNORECASE)
        return r.sub(self.clean_word, self.original_string)
