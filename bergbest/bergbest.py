#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# h2m@access.uzh.ch

from lxml import etree
from os import sep
from re import sub

# Filename prefix
FILENAME_PREFIX = "SAC-Jahrbuch_"

# XML suffix
XML_SUFFIX = '.xml'

# Language of words wanted
DE_LANG = 'de'
FR_LANG = 'fr'

# NER filename substring, which indicates NER contents of an XML file.
NER_SUBSTR = '-ner'

# SAC XML folder path
SAC_XML_DIR = 'Text+Berg_Release_147_v03' + sep + 'XML' + sep \
            + 'SAC' + sep
            
# Geo types we are looking for
GEO_NE_TYPE = 'mountain'

# Range of documents to check
YEAR_RANGE = range(1957, 2012) # 1957-2011

class ArticlesHashed(dict):
    """Class to hold and get articles directly by id (hashed = faster).
    """
    
    def __init__(self, xml_articles):
        dict.__init__(self)
        self._hash_articles(xml_articles)
        
    def _hash_articles(self, xml_articles):
        """Hash articles by article id."""
        for xml_article in xml_articles:
            self[xml_article.attrib['n']] = xml_article
            
# XXX: Todo if time given
class SuperSentence:
    """Class which unites several sentences to one, where evidence
       *seems* given that no real sentence boundary is given by the
       Text+Berg XML annotation."""
       
    def __init__(self):
        pass

class ArticleTranslated:
    """Class to hold a (single) article pair; used for analysis of 
       candidate facts."""
    
    def __init__(self, article_pair, yearbook):
        
        # Meta data
        self.yearbook = yearbook
        self.article_title_de = ''
        self.article_title_fr = ''
        self.sentences_de_number = 0
        self.sentences_fr_number = 0
        self.candidate_sentences_de_number = 0
        self.candidate_sentences_fr_number = 0
        
        # Effective data
        self.sentences_de = []
        self.sentences_fr = []
        self.candidate_sentences_de = []
        self.candidate_sentences_fr = []

        # XXX: Todo if time given
        self.candidate_supersentences_de = []
        self.candidate_supersentences_fr = []
        
        self._read_title(article_pair)
        self._read_sentences(article_pair)
        
    def _read_title(self, article_pair):
        """Read title (in German and French) of article pair given."""
        article_de = article_pair[0]
        article_fr = article_pair[1]
        
        self.article_title_de = article_de.xpath('./tocEntry')[0].\
                                attrib['title']
        self.article_title_fr = article_fr.xpath('./tocEntry')[0].\
                                attrib['title']
        
    def _read_sentences(self, article_pair):
        """Method to read in the sentences of the article 
           -- in both languages."""
        article_de = article_pair[0]
        article_fr = article_pair[1]
        
        self.sentences_de = article_de.xpath('.//s')
        self.sentences_fr = article_fr.xpath('.//s')
        self.sentences_de_number = len(self.sentences_de)
        self.sentences_fr_number = len(self.sentences_fr)
        
    def __str__(self):
        ret_str = ''
        
        ret_str = 72 * '=' + \
                  '\nArticle year: ' + str(self.yearbook) + \
                  '\nArticle name: ' + self.article_title_de + \
                  '\nNumber of sentences (German): ' + \
                  str(self.sentences_de_number) + \
                  '\n' + 24 * ' - ' + \
                  '\nArticle name: ' + self.article_title_fr + \
                  '\nNumber of sentences (French): ' + \
                  str(self.sentences_fr_number)
                  
        return ret_str

class BookTranslated:
    """Class which holds translated articles of an SAC year book."""
    
    def __init__(self, filepath):
        self.filepath = filepath
        self.yearbook = ''
        self.articles_pairs = []
        self.articles_number = 0
        self.articles_mapping = {} # Mapping of articles numbers de->fr
        
        self._read_article_pairs()
        self._print_text("Article pair read. Article pair count: " +\
                         str(self.articles_number))

    def _print_text(self, text):
        """Print text with yearbook year info in prefix."""
        print('Yearbook ' + self.yearbook + ":", text)
   
    def _fr_filepath(self, filepath):
        """Return filepath of French SAC yearbook file."""
        return filepath.replace(DE_LANG, FR_LANG)
        
    def _read_articles(self, filepath):
        """Method to generically return articles from a SAC year book.
        """
        sac_book_elem = etree.parse(filepath).xpath('/book')[0]
        self.yearbook = sac_book_elem.attrib['id'].split('_')[0]
        sac_book_articles = sac_book_elem.xpath('article')
        
        """
        for sac_book_article in sac_book_articles:
            try:
                print sac_book_article.xpath('./tocEntry')[0].attrib['title']
            except:
                pass
        """
        
        return sac_book_articles
        
    def _fr_article_id(self, article):
        """Return (based on the German article) the French article id,
           which represents its basis or translation.
        """
        article_id_fr = None
        
        # Not all articles have a translation / correspondence.
        try:
            article_id_fr = article.\
                            attrib['translation-of'].split(':')[1]
        except:
            pass
            
        return article_id_fr
    
    def _read_article_pairs(self):
        """Method to find out translated pairs between articles in
           German and French language in SAC.
        """
        filepath_fr = self._fr_filepath(self.filepath)
        articles_de = self._read_articles(self.filepath)
        articles_fr = self._read_articles(filepath_fr)
        
        # Find German-French corresponding articles
        for article in articles_de:
            article_id_de = article.attrib['n']
            article_id_fr = self._fr_article_id(article)
            if article_id_fr is not None:
                self.articles_mapping[article_id_de] = article_id_fr
        
        # Hash articles to get them by id
        articles_de_hashed = ArticlesHashed(articles_de)
        articles_fr_hashed = ArticlesHashed(articles_fr)
        
        # Add article pairs to object
        for de_id, fr_id in self.articles_mapping.items():
            article_pair = [articles_de_hashed[de_id], 
                            articles_fr_hashed[fr_id]
                           ]
            self.articles_pairs.append(article_pair)
            self.articles_number += 1

def read_geo_ne(filepath, geo_ne_type=GEO_NE_TYPE):
    """Returns a dict with position of geo entity and type as value."""
    geo_ne_dict = dict()
    sac_geo_elem = etree.parse(filepath).xpath('/ner/geo')[0]
    
    # Get all <g> elements, where type equals GEO_NE_TYPE
    sac_g_elem_list = sac_geo_elem.xpath('.//g[@type=\'' + \
                                                GEO_NE_TYPE + '\']')
                                                
    for sac_g_elem in sac_g_elem_list:
        locations = sac_g_elem.attrib['span'].split(',')
        for loc in locations:
            geo_ne_dict[loc] = geo_ne_type
            
    return geo_ne_dict

def explore_bergsteiger(book_translated, year):
    
    # Get article pair of yearbook given
    articles_pairs = book_translated.articles_pairs
    
    # Go through each article pair
    for article_pair in articles_pairs:
        #print article_pair[0].xpath('./tocEntry')[0].attrib['title']
        article_translated = ArticleTranslated(article_pair, year)
        print(article_translated)
    
    """
    for year in YEAR_RANGE:
        filepath_base = SAC_XML_DIR + FILENAME_PREFIX + \
                        str(year) + '_' + DE_LANG 
        filepath_content =  filepath_base + XML_SUFFIX
        filepath_ner = filepath_base + '-ner' + XML_SUFFIX
        geo_ne_dict = read_geo_ne(filepath_ner)
                
        sac_book_elem = etree.parse(filepath_content).xpath('/book')[0]
        # Get all <s> (=sentence) elements in given language
        sac_sentences_elem_list = sac_book_elem.xpath('.//s[@lang=\'' + \
                                                lang + '\']')
        for sac_sentence_elem in sac_sentences_elem_list:
            print '###'
            sac_word_elem_list = sac_sentence_elem.xpath('.//w')
            '''
            print filepath_content, "| Satz", \
                  sac_sentence_elem.attrib['n']
            '''
            for sac_word_elem in sac_word_elem_list:
                try: 
                    if sac_word_elem.attrib['pos'] == 'NE' \
                       and geo_ne_dict[sac_word_elem.attrib['n']] == \
                           'mountain' :
                        print sac_word_elem.text
                    '''
                    if sac_word_elem.attrib['lemma'] == 'besteigen':
                        print sac_word_elem.text
                    '''
                except:
                    pass
    """

def process_xml():
    
    # Iterate through all german documents, 1957-2011
    for year in YEAR_RANGE:
        filepath_base = SAC_XML_DIR + FILENAME_PREFIX + \
                        str(year) + '_' + DE_LANG 
        filepath = filepath_base + XML_SUFFIX
        book_translated = BookTranslated(filepath)
        
        # Search for people who climbed (supposedely) mountains
        explore_bergsteiger(book_translated, year)
    
def main():
    process_xml()
                
    return 0

if __name__ == '__main__':
	main()
