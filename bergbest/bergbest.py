#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# h2m@access.uzh.ch

from lxml import etree
from os import sep, sys
from re import sub
from sys import stdout

# Filename prefix
FILENAME_PREFIX = "SAC-Jahrbuch_"

# XML suffix
XML_SUFFIX = '.xml'

# Language of words wanted
DE_LANG = 'de'
FR_LANG = 'fr'

# Lemmata with candidate verbs for DE and FR
CANDID_LEMMATA_DE = [
                     'besteigen',
                     'erreichen',
                     'gelingen',
                     'ersteigen', 
                     'bezwingen',
                     'gelangen',
                     'erklettern',
                     'erklimmen',
                     'aufsteigen',
                     'gelangen|gelingen',
                     'bewältigen',
                     'hinaufsteigen'
                     ]
CANDID_LEMMATA_FR = [
                     'réussir',
                     'atteindre',
                     'gravir',
                     'traverser',
                     'escalader',
                     'monter',
                     #'obtenir',
                     'conquérir',
                     #'arriver'
                     ]

# NER filename substring, which indicates NER contents of an XML file.
NER_SUBSTR = '-ner'

# SAC XML folder path
SAC_XML_DIR = 'Text+Berg_Release_147_v03' + sep + 'XML' + sep \
            + 'SAC' + sep

# Range of documents to check
YEAR_RANGE = range(1957, 2012) # 1957-2011

# Name for an empty title
EMPTY_TITLE = "NONE"

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

class ArticleTranslated:
    """Class to hold a (single) article pair; used for analysis of 
       candidate facts."""
    
    def __init__(self, article_pair, yearbook, book_ne, pair_id):
        
        # Meta data
        self.yearbook = yearbook
        self.article_title_de = ''
        self.article_title_fr = ''
        self.sentences_de_number = 0
        self.sentences_fr_number = 0
        self.candidate_sentences_de_number = 0
        self.candidate_sentences_fr_number = 0
        self.pair_id = pair_id
        
        # Effective data
        self.book_ne = book_ne
        self.sentences_de = []
        self.sentences_fr = []
        self.candidate_sentences_de = []
        self.candidate_sentences_fr = []
        self.mountain_dict_de = {}
        self.mountain_dict_fr = {}

        # XXX: Todo if time given
        self.candidate_supersentences_de = []
        self.candidate_supersentences_fr = []
        
        self._read_title(article_pair)
        self._read_sentences(article_pair)
        self._create_candidate_sentences(DE_LANG)
        self._create_candidate_sentences(FR_LANG)
    
    def _create_candidate_sentences(self, lang):
        """Find sentences which contain NEs."""
        sentences = []
        ne_tag = ''
        mountains = None
        persons = None
        word_positions = []
        mountain_positions = []
        person_positions = []
        
        if lang == DE_LANG:
            sentences = self.sentences_de
            mountains = self.book_ne.mountains_de
            persons = self.book_ne.persons_de
        elif lang == FR_LANG:
            sentences = self.sentences_fr
            mountains = self.book_ne.mountains_fr
            persons = self.book_ne.persons_fr
            
        for sentence in sentences:
            # Get all words' positions
            for word in sentence.xpath('./w'):
                word_positions.append(word.attrib['n'])
        
        mountain_positions = self.book_ne.mountain_positions(lang)
        person_positions = self.book_ne.person_positions(lang)

        mountains_present = set(mountain_positions).\
                            intersection(set(word_positions))
        persons_present = set(person_positions).\
                          intersection(set(word_positions))

        mountain_sentences = [position.split('-')[1] for position in \
                              mountains_present]
        person_sentences = [position.split('-')[1] for position in \
                            persons_present]
        mountain_and_person_sentences = set(mountain_sentences).\
                                        intersection(set(person_sentences))
       
        print('Sentences with mountains (' + lang + '):', 
               mountain_sentences)
        print('Sentences with persons (' + lang + '):', 
               person_sentences)
        print('Sentences with both (' + lang + '):', 
               mountain_and_person_sentences)
        
        for sentence in sentences:
            if sentence.attrib['n'].split('-')[1] in \
            mountain_and_person_sentences:
                for word in sentence.xpath('w'):
                    try:
                        if lang == DE_LANG:
                            if word.attrib['lemma'] \
                             in CANDID_LEMMATA_DE:
                                print("* * * * * CHECK " \
                                      + str(self.yearbook) + "#" \
                                      + str(self.pair_id) + " (de)")
                                self._print_sentence(sentence, lang)
                        elif lang == FR_LANG:
                            if word.attrib['lemma'] \
                             in CANDID_LEMMATA_FR:
                                print("* * * * * CHECK " \
                                      + str(self.yearbook) + "#" \
                                      + str(self.pair_id) + " (fr)")
                                self._print_sentence(sentence, lang)
                    except:
                        pass
                    try:
                        if lang == DE_LANG:
                            if word.attrib['pos'].startswith('VV'):
                                #print('VERB (' + lang + '): ' + \
                                # word.text)
                                print('VERB (' + lang + '): ' + \
                                      word.attrib['lemma'])

                        elif lang == FR_LANG:
                            if word.attrib['pos'].startswith('V'):
                                #print('VERB: (' + lang + '): ' + \
                                # word.text)
                                print('VERB (' + lang + '): ' + \
                                       word.attrib['lemma'])

                    except:
                        pass
    
    def _print_sentence(self, sentence, lang):
        """Prints sentence as a whole."""
        stdout.write('* * * SENTENCE (' + lang + '): ')
        for word in sentence.xpath('w'):
            stdout.write(word.text + " ")
        print('\n')
                                    
    def _read_title(self, article_pair):
        """Read title (in German and French) of article pair given."""
        article_de = article_pair[0]
        article_fr = article_pair[1]
        
        # It may be that a title is not given.
        try:
            self.article_title_de = article_de.xpath('./tocEntry')[0].\
                                    attrib['title']
            self.article_title_fr = article_fr.xpath('./tocEntry')[0].\
                                    attrib['title']
        except:
            self.article_title_de = EMPTY_TITLE
            self.article = EMPTY_TITLE
        
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
                  '\nArticle number: ' + str(self.pair_id) + \
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

class Mountain:
    """Information about a mountain."""
    
    def __init__(self):
        self.stid = '' # Collection-wide id (unique)
        self.name_parts = []
        self.name = '' # Name in full length
        self.location = [] # One location can span several 
        
    def __str__(self):
        """Print mountain."""
        return self.name
        
class Person:
    """Information about a person."""
    
    def __init__(self):
        self.pid = '' # Document-wide id (not collection unique)
        self.firstname = ''
        self.lastname = ''
        self.locations = [] # Contains othter lists with spanned locs
        # More information can be gathered, but is of no use now.

    def __str__(self):
        """Print person."""
        return self.firstname + ' ' + self.lastname
        
class BookNE:
    """Class which holds a book's Named Entities."""
    
    def __init__(self, year):
        self.year = year
        self.mountains_de = []
        self.mountains_fr = []
        self.persons_de = []
        self.persons_fr = []
        self.filepath_de = self._filepath(DE_LANG)
        self.filepath_fr = self._filepath(FR_LANG)
        
        # XML XPath of NEs we need
        self.XML_PATH_MOUNTAINS = '/ner/geo'
        self.XML_PATH_PERSONS = '/ner/persons'
        
        # Collect NEs
        self._source_mountains(DE_LANG)
        self._source_mountains(FR_LANG)
        self._source_persons(DE_LANG)
        self._source_persons(FR_LANG)
    
    def _source_mountains(self, lang):
        """Collect mountains in NER file."""
        sac_geo_elem = None
        
        if lang == DE_LANG:
            sac_geo_elem = self._etree_parse(self.filepath_de,
                                             self.XML_PATH_MOUNTAINS)[0]
        elif lang == FR_LANG:
            sac_geo_elem = self._etree_parse(self.filepath_fr,
                                            self.XML_PATH_MOUNTAINS)[0]
        
        # Get all <g> elements, where types is a mountain
        sac_g_elem_list = sac_geo_elem.xpath('.//g[@type=\'' + \
                                             'mountain' + '\']')
     
        # Go through all <g> elements found
        for sac_g_elem in sac_g_elem_list:
            mountain = Mountain()
            mountain.stid = sac_g_elem.attrib['stid']
            mountain.location = sac_g_elem.attrib['span'].split(',')
            
            if lang == DE_LANG:
                self.mountains_de.append(mountain)
            elif lang == FR_LANG:
                self.mountains_fr.append(mountain)
            
    def _etree_parse(self, filepath, xmlpath):
        """Return etree parse of an XML file."""
        return etree.parse(filepath).xpath(xmlpath)
        
    def _source_persons(self, lang):
        """Collect presons in NER file."""
        sac_per_elem = None
        
        if lang == DE_LANG:
            sac_per_elem = self._etree_parse(self.filepath_de,
                                             self.XML_PATH_PERSONS)[0]
        elif lang == FR_LANG:
            sac_per_elem = self._etree_parse(self.filepath_fr,
                                            self.XML_PATH_PERSONS)[0]
        
        # Get all <person> elements
        sac_person_elem_list = sac_per_elem.xpath('person')
        
        # Go through all <person> elements
        for sac_person in sac_person_elem_list:
            person = Person()
            person.pid = sac_person.attrib['id']
            person.firstname = sac_person.xpath('./firstname')[0].text
            person.lastname = sac_person.xpath('./lastname')[0].text
            sac_per_positions = sac_person.xpath('.//positions')
            
            for sac_per_position in sac_per_positions:
                sac_position_parts = sac_per_position.\
                                      xpath('./position')
                position = []
                for sac_position_part in sac_position_parts:
                    position.append(sac_position_part.text)
                    
                person.locations.append(position)
                
            if lang == DE_LANG:
                self.persons_de.append(person)
            elif lang == FR_LANG:
                self.persons_fr.append(person)
    
    def _filepath(self, lang):
        """Return filepath to NE file dependent on the language."""
        return(SAC_XML_DIR + FILENAME_PREFIX + \
               str(self.year) + '_' + lang + NER_SUBSTR + \
               XML_SUFFIX)
    
    def mountain_positions(self, lang):
        """Return all mountain positions -- flat way."""
        mountains = None
        positions = []
        
        if lang == DE_LANG:
            mountains = self.mountains_de
        elif lang == FR_LANG:
            mountains = self.mountains_fr
            
        for mountain in mountains:
            for position in mountain.location:
                positions.append(position)
                
        return positions
    
    def person_positions(self, lang):
        """Return positions of persons -- flat way."""
        persons = None
        positions = []
        
        if lang == DE_LANG:
            persons = self.persons_de
        elif lang == FR_LANG:
            persons = self.persons_fr
            
        for person in persons:
            for location in person.locations:
                for location_part in location:
                    positions.append(location_part)
                
        return positions
    
    def __str__(self):
        """Return information about the the Named Entities found."""
        return 'Mountains: ' + str(len(self.mountains_de)) + ' |  ' + \
               str(len(self.mountains_fr)) +\
               '\nPersons: ' + str(len(self.persons_de)) + ' | ' + \
               str(len(self.persons_fr))

    '''
                                                
    for sac_g_elem in sac_g_elem_list:
        locations = sac_g_elem.attrib['span'].split(',')
        for loc in locations:
            geo_ne_dict[loc] = geo_ne_type
            
    return geo_ne_dict
    '''

def explore_bergsteiger(book_translated, year, book_ne):
    
    # Get article pair of yearbook given
    articles_pairs = book_translated.articles_pairs
    
    # Go through each article pair
    pair_id = 1
    for article_pair in articles_pairs:
        article_translated = ArticleTranslated(article_pair, year, 
                                               book_ne, pair_id)
        pair_id += 1
        print(article_translated)

def process_xml():
    
    global YEAR_RANGE
    
    # If there's an argument assume it to be a year number
    if len(sys.argv) > 1:
        YEAR_RANGE = [sys.argv[1]]
    
    # Iterate through all german documents, 1957-2011 (by default)
    for year in YEAR_RANGE:
        filepath_base = SAC_XML_DIR + FILENAME_PREFIX + \
                        str(year) + '_' + DE_LANG 
        filepath = filepath_base + XML_SUFFIX
        book_translated = BookTranslated(filepath)
        
        # Search for people who climbed (supposedely) mountains
        book_ne = BookNE(year)
        print('%')
        print(book_ne.mountain_positions('de'))
        explore_bergsteiger(book_translated, year, book_ne)
    
def main():
    process_xml()
                
    return(0)

if __name__ == '__main__':
	main()
