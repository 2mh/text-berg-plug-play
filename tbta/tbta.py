#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# h2m@access.uzh.ch

from gensim.corpora import Dictionary, MmCorpus
from gensim.models import TfidfModel
from gensim.models.ldamodel import LdaModel
from lxml import etree
from os import sep, sys, makedirs
from os.path import exists
from re import match

# Parameters

# No words with an occurrence below this number are allowed
NO_BELOW = 4 

# Fraction of most common words to drop away 
NO_ABOVE = 0.1 

 # Number of LDA iterations to fullfil
PASSES = 1

# Set to -1 to default to k = number of documents
NUM_TOPICS = 42

# Number of (random) topics to display
TOPICS_DISPLAY = 7 

# Number of top probable words of topic shown to display
WORDS_DISPLAY = 7 

# Filename prefix
SAC_FILENAME_PREFIX = 'SAC-Jahrbuch_'

# XML suffix
XML_SUFFIX = '.xml'

# Languages to be used
DE_LANG = 'de'
FR_LANG = 'fr'

# Only use German words from these categories
DE_POS_FILTER = ['NN']
#DE_POS_FILTER = ['NN', 'ADJA', 'ADJD', 'VVPP', 'VVINF']

# Only use French words from these categories
FR_POS_FILTER = ['N_P', 'N_C', 'V']

# Years available in SAC corpus
YEARS_ALLOWED = range(1864, 2012) # 1864 to 2011

# SAC XML folder path
SAC_XML_DIR = 'Text+Berg_Release_147_v03' + sep + 'XML' + sep \
            + 'SAC' + sep

# Folder to hold word ids for each document's words
WORDSIDS_DIR = 'wordid_files' + sep

# Folder where matrix representations of bag-of-words corpora is held
BOWMM_DIR = 'bowmm_files' + sep

# Folder to hold TF*IDF matrices for each document
TFIDF_DIR = 'tfidf_files' + sep

def sac_filepath(year, lang=DE_LANG):
    """Return SAC book filepath based on year and (optional) language 
       information."""
       
    year = int(year)
    base_prefix = SAC_FILENAME_PREFIX + str(year)
    
    # Naming scheme for SAC year books before 1957 differ
    if year < 1957:
        return(base_prefix + '_' + 'mul' + XML_SUFFIX)
    
    return(base_prefix + '_' + lang + XML_SUFFIX)

class ArticlesCollection:
    """Class which holds all articles (perhaps over several years)
       -- with ability to perform LDA on it."""
    
    def __init__(self, year_range, lang=DE_LANG):
        self.year_range = year_range
        self.lang = lang
        self.articles = []
        self.bow_corpus = None
        self.identifier = ''
        self.wordsids_filepath = ''
        self.bowmm_filepath = ''
        self.tfidf_filepath = ''
        
        # gensim data structures
        self.dictionary = None
        
        # Read in collection & clean it & start LDA process
        self._read_collection()
        self._collection_identifier()
        self._set_filepaths()
        self._create_dictionary()
        self._create_bow_representation()
        self._create_tfidf_matrix()
    
    def show_lda(self):
        """Show latent topics found."""
        
        # Find out and print ten most promising LDA topics
        tfidf = MmCorpus(self.tfidf_filepath)
        # print(tfidf)
        # dictionary = Dictionary.load_from_text(wordsids_filepath)
        
        # k = number of documents = number of topics (for now)
        num_topics = tfidf.num_docs
        if NUM_TOPICS != -1:
            num_topics = NUM_TOPICS
        print(num_topics)
            
        lda = LdaModel(corpus=tfidf,
                       id2word=self.dictionary,
                       num_topics=num_topics,
                       passes=PASSES,
                       distributed=True)
        topic_number = 0
        for topic in lda.show_topics(topics=TOPICS_DISPLAY, 
                                     topn=WORDS_DISPLAY):
            topic_number += 1
            print('Topic#' + str(topic_number) + ': ', topic)
                            
    def _set_filepaths(self):
        """Sets filepaths for intermediate data."""

        # Filepaths necessary for topic modeling
        self.wordsids_filepath = WORDSIDS_DIR + self.identifier + \
                                 '_' + 'wordsids.txt'
        self.bowmm_filepath = BOWMM_DIR + self.identifier + '_' + \
                              'bow.mm'
        self.tfidf_filepath = TFIDF_DIR + self.identifier + '_' + \
                              'tfidf.mm'

    def _create_dictionary(self):
        """Create a mapping of ids and surface froms (=words)."""
        
        print('Create dictionary of collection.')
        self.dictionary = Dictionary(self.articles)
        self.dictionary.filter_extremes(no_below=NO_BELOW, 
                                        no_above=NO_ABOVE)
        self.dictionary.save_as_text(self.wordsids_filepath)
        print(self.dictionary)
    
    def _create_bow_representation(self):
        """Create bag-of-words representation of collection, and save it 
           in Matrix Matrix format to disk."""
        
        print('Create bag-of-words matrix representation.')
        self.bow_corpus = [self.dictionary.doc2bow(article) 
                           for article in self.articles]
        MmCorpus.serialize(self.bowmm_filepath, self.bow_corpus)

    def _create_tfidf_matrix(self):
        """Create TF-IDF matrix and save it in Matrix Matrix format to 
           disk"""
        
        print('Create TF-IDF matrix of collection.')
        tfidf = TfidfModel(self.bow_corpus, 
                           id2word=self.dictionary, 
                           normalize=True)
        MmCorpus.serialize(self.tfidf_filepath, 
                           tfidf[self.bow_corpus])
        print('Number of documents:', tfidf.num_docs)

    def _collection_identifier(self):
        """Collection id is important for the caching files and the
           file naming of the corresponding files."""
           
        start_year = self.year_range[0]
        end_year = self.year_range[-1]
        
        if start_year == end_year:
            self.identifier = str(start_year) + '_' + self.lang
        else:
            self.identifier = str(start_year) + '-' + str(end_year) + \
                              '_' + self.lang 
        
    def _read_collection(self):
        """Iterate through all years in order to get all articles read
           in."""
        for year in self.year_range:
            # Not every single yearbook is available.
            try:
                self._read_book(year)
            except:
                print('Skip (inexistent) yearbook ' + str(year) + '.')
        
    def _read_book(self, year):
        """Read in a a single book and save its articles."""
        filepath = sac_filepath(year, lang=self.lang)
        
        print('Read in yearbook ' + str(year) + '.')
        sac_xml = etree.parse(SAC_XML_DIR + filepath)
        sac_xml_articles_list = sac_xml.xpath('.//article')
        
        # For each article
        for sac_xml_article in sac_xml_articles_list:
            article_word_list = []
            sac_xml_sentences_list = \
                sac_xml_article.xpath('.//s[@lang=\'' + \
                                      self.lang + '\']')
            # For each sentence (in the article)
            for sac_xml_sentence in sac_xml_sentences_list:
                sac_xml_words_list = \
                    sac_xml_words_list = sac_xml_sentence.xpath('.//w')
                # For each word (in the sentence of the article)
                for sac_xml_word in sac_xml_words_list:
                    try:
                        # Look for POS tags of FR_LANG
                        if self.lang is not DE_LANG:
                            if sac_xml_word.attrib['pos'] \
                            in FR_POS_FILTER:
                                article_word_list.append(sac_xml_word.\
                                attrib['lemma'].lower())
                        # Assume DE_LANG (default lang)
                        else:
                            if sac_xml_word.attrib['pos'] \
                            in DE_POS_FILTER:
                                article_word_list.append(sac_xml_word.\
                                attrib['lemma'].lower())
                    except: # PoS attribute may not be given
                        pass
            # Save article as bag-of-words (of the sentences)
            self.articles.append(article_word_list)
                
    def __str__(self):
        """ Return a string which shows document number, number of
            words and number of types.
        """
        ret_string = ''
        art_number = 0
        
        for article in self.articles:
            art_number += 1
            ret_string += 'Doc#' + str(art_number) + ': '
            ret_string += str(len(article)) + ' [' + \
                          str(len(set((article)))) + ']'
            ret_string += '\n'
            
        return ret_string

def print_help(program_name):
    
    print("TBTA: Text+Berg Topic Analysis tool\n")
    print(program_name + ' <from_year[-to_year]> [lang code]')
    print('Example: ' + program_name + ' 1960\n' + \
          'Example: ' + program_name + ' 1972 de\n' + \
          'Example: ' + program_name + ' 1957 de\n' + \
          'Example: ' + program_name + ' 1984 fr\n' + \
          'Example: ' + program_name + ' 1970-1980 de\n\n' + \
          'Years allowed: 1864 to 2011\n' + \
          'Langs allowed:', DE_LANG, FR_LANG
         )
    sys.exit(0)
    
def print_year_not_allowed():
    """Simply print out which ranges are feasible."""
    
    print("Not allowed year (range).")
    print_help(sys.argv[0])    

def create_caching_folders():
    """Creates folders used for caching pre-processing results."""
    
    if not exists(WORDSIDS_DIR):
        makedirs(WORDSIDS_DIR)
    if not exists(TFIDF_DIR):
        makedirs(TFIDF_DIR)
    if not exists(BOWMM_DIR):
        makedirs(BOWMM_DIR)

def get_arguments(argv):
    """Check if valid input is provided and return arguments"""
    
    # At least a year must be provided
    if len(argv) < 2:
        print_help(sys.argv[0])
        
    # Perhaps the language of the document is given
    # (That's important because of POS tags.)
    lang=DE_LANG
    if len(sys.argv) > 2:
        if sys.argv[2] == FR_LANG:
            lang = FR_LANG
        elif sys.argv[2] == DE_LANG:
            pass # Already set
        else:
            print("Only languages supported:", DE_LANG, FR_LANG)
            sys.exit(2) # Error code 2: Second argument bogus

    allowed_years_re = "[12][089][0-9]{2}"
    year_range = None
    
    res = match(allowed_years_re + "(-" + allowed_years_re + ")?",
                 sys.argv[1])
    if res:
        # Check if first argument is fine
        try:
            # Works out if only one year provided
            year = int(sys.argv[1])
            year_range = range(year, year+1)
            if year not in YEARS_ALLOWED:
                print_year_not_allowed()
        except:
            # Two years with dash must have been provided
            years_extracted = [int(year) for year 
                               in sys.argv[1].split('-')]
            year_range = range(years_extracted[0],
                               years_extracted[1] + 1)
    else:
        print_year_not_allowed()

    return(year_range, lang)

def main():
    
    lang = ''
    year_range = None
    
    # Create folders used to save pre-processing results
    create_caching_folders()
    
    # Check and get arguments   
    year_range, lang = get_arguments(sys.argv)
        
    articles_collection = ArticlesCollection(year_range, lang)
    articles_collection.show_lda()
    
if __name__ == '__main__':
	main()
