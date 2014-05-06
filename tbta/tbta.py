#!/usr/bin/env python
# -*- coding: utf-8 -*-
# h2m@access.uzh.ch

from os import sep, sys, makedirs
from os.path import exists
from re import match
import itertools

from gensim.corpora import Dictionary, MmCorpus
from gensim.models import TfidfModel
from gensim.models.ldamodel import LdaModel
from gensim.models.ldamallet import LdaMallet
from lxml import etree

# Parameters

# Words with a global occurrence below this number are dropped
# Suggested value = 5
NO_BELOW = 3

# Only words are kept that appear almost by the indicated fraction
# in the whole corpus
# Suggested value = 0.5
NO_ABOVE = 0.5

# Set to -1 to default to k = number of documents
NUM_TOPICS = 100

# Number of (random) topics to display
TOPICS_DISPLAY = 100

# Number of top probable words of topic shown to display
WORDS_DISPLAY = 10

# Filename prefix
SAC_FILENAME_PREFIX = 'SAC-Jahrbuch_'

# XML suffix
XML_SUFFIX = '.xml'

# Languages to be used
DE_LANG = 'de'
FR_LANG = 'fr'

# Minimal word length
MIN_WORDLEN = 2

# Define if POS filter is to be used or not (see below)
WITH_POS_FILTER = False

# Define if lemmata should be used (if possible)
WITH_LEMMATA = True

# Use TF*IDF input instead of direct bow
USE_TFIDF = False

# Use mallet's (gibbs sampled) LDA system
USE_MALLET = True

# Number of iterations to fullfil
ITERATIONS = 200

POS_FILTER = { 
#                DE_LANG : ['NN', 'NE', 'VVINF', 'VVFIN', 'VVIMP', 
#                         'VVIZU', 'VAPP', 'VMPP', 'ADJA', 'ADJD'],
#                DE_LANG : ['NN', 'NE', 'VVFIN', 'VVINF', 'ADJA', 'ADJD'],
                 DE_LANG : ['NN', 'NE', 'ADJA', 'ADJD'],
                FR_LANG : ['N_C', 'N_C', 'A_qual', 'V']          
             }

# German stop words from NLTK
DE_STOPWORDS = open('de_stop_words.txt', 'r').read().split('\n')
DE_STOPWORDS.pop()

# Stop words from nltk
STOPWORDS = {
                DE_LANG : open('de_stop_words.txt', 'r').read().\
                                                         split('\n'),
                FR_LANG : []
            }
STOPWORDS[DE_LANG].pop() 

# If one of these signs are found in lemma, take surface form instead
DE_SURFACE_TRIGGERS = ['unk', '@ord@', '|', '@card@', '+', '#', '%']

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

# Folder name for plain text output of articles
TEXT_OUTPUT_DIR = 'text_output_dir'

PATH_TO_MALLET_BIN = '/home/hernani/uzh/master/modir/mallet-2.0.7/bin/mallet'

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
    
    def __init__(self, year_range, text_output_dirpath, lang=DE_LANG):
        self.year_range = year_range
        self.text_output_dirpath = text_output_dirpath
        self.lang = lang
        self.articles = []
        self.bow_corpus = None
        self.identifier = ''
        self.wordsids_filepath = ''
        self.bowmm_filepath = ''
        self.tfidf_filepath = ''
        self.number_of_docs = 0
        self.number_of_tokens = 0
        self.number_of_types = 0
        
        # gensim data structures
        self.dictionary = None
        
        # Read in collection & clean it & start LDA process
        self._read_collection()
        self._collection_identifier()
        self._set_filepaths()
        self._create_dictionary()
        self._create_bow_representation()
        self._set_number_of_docs()
        self._set_number_of_tokens()
        self._set_number_of_types()
        
        # Create tf*idf matrix if requested.
        if USE_TFIDF:
            self._create_tfidf_matrix()
    
    def show_lda(self):
        """Show latent topics found."""
        
        lda = None
        
        # Only use tf*idf input if requested.
        corpus = self.bow_corpus
        if USE_TFIDF:
            corpus = MmCorpus(self.tfidf_filepath)
        
        # k = number of documents = number of topics (for now)
        num_topics = self.number_of_docs
        if NUM_TOPICS != -1:
            num_topics = NUM_TOPICS
        
        print('Number of docs presented: ' + str(self.number_of_docs))
        print('Number of origin. tokens: ' + str(self.number_of_tokens))
        print('Number of original types: ' + str(self.number_of_types))
        print('Number of types at usage: ' + str(len(self.dictionary.\
                                                     keys())))
        print('Number of topics to find: ' + str(num_topics))
        print('Number of topics to show: ' + str(TOPICS_DISPLAY))
        
        if USE_MALLET:
            lda = LdaMallet(PATH_TO_MALLET_BIN,
                            corpus=corpus,
                            num_topics=num_topics,
                            id2word=self.dictionary,
                            iterations=ITERATIONS)
                            
        else:
            lda = LdaModel(corpus=corpus,
                           id2word=self.dictionary,
                           num_topics=num_topics,
                           chunksize=1,
                           update_every=1,
                           decay=0.5,
                           distributed=False)
                       
        topic_number = 0
        for topic in lda.show_topics(topics=TOPICS_DISPLAY, 
                                     topn=WORDS_DISPLAY,
                                     formatted=True):
            topic_number += 1
            print('Topic#' + str(topic_number) + ': ', topic)

    def _set_number_of_types(self):
        """Set number of types (from tokens)."""
        self.number_of_types = len(set(list(itertools.\
                                    chain(*self.articles))))
        
    def _set_number_of_tokens(self):
        """Set number of tokens gotten in all documents."""
        self.number_of_tokens = sum(len(article) \
                                    for article in self.articles)
        
    def _set_number_of_docs(self):
        """Set number of docs found in collection read in."""
        self.number_of_docs = len(self.articles)
        
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
        self.dictionary.compactify()
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
            
            # Prepare file to write out words
            sac_xml_article_no = sac_xml_article.attrib['n']
            out_filename = str(year) + '-' + str(self.lang) + '-' \
                           + sac_xml_article_no + '.txt'
            out_filepath = self.text_output_dirpath + sep + out_filename
            print(out_filepath)
            out_filehdl = open(out_filepath, 'w')
                               
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
                    word = None
                    try:
                        if WITH_POS_FILTER is False:
                            if WITH_LEMMATA:
                                word = sac_xml_word.attrib['lemma'].lower()
                                if self._is_lemma_bogus(word):
                                    word = sac_xml_word.text.lower()
                            if WITH_LEMMATA is False:
                                word = sac_xml_word.text.lower()
                        elif WITH_POS_FILTER:
                            word = self._get_pos_filtered_word(sac_xml_word)
                    except:
                        pass
                        
                    # Don't add stop words, in any case
                    if not word in STOPWORDS[self.lang] \
                    and word is not None and len(word) >= MIN_WORDLEN:
                        article_word_list.append(self._normalize_word(word))
            # Save article as bag-of-words (of the sentences)
            self.articles.append(article_word_list)
            out_filehdl.write(' '.join(article_word_list))
            out_filehdl.close()
    
    def _get_pos_filtered_word(self, sac_xml_word):
        """ Get word by PoS filter
        """
        # There are words without PoS tags, i. e. try
        try:
            if sac_xml_word.attrib['pos'] \
            in POS_FILTER[self.lang]:
                if WITH_LEMMATA:
                    word = sac_xml_word.attrib['lemma'].lower()
                    if self._is_lemma_bogus(word):
                        return sac_xml_word.text.lower()
                    else:
                        return sac_xml_word.attrib['lemma'].lower()
                else:
                    return sac_xml_word.text.lower()
            else:
                return None
        except:
            return None
    
    def _is_lemma_bogus(self, lemma):
        """ Return true if the lemma is not useful for LDA, otherwise
            false.
        """
        
        for bogus_symbol in DE_SURFACE_TRIGGERS:
            if bogus_symbol in lemma:
                return True
        
        # That's the last resort
        return False
    
    def _normalize_word(self, word_to_normalize):
        """
        This function helps to normalize words, because of encoding
        issues of some LDA tools ...
        @return: Normalized word as str type
        """
        
        # Transform umlauts to ASCII friendly form
        word = word_to_normalize.replace(u"ä","ae").replace(u"ö","oe"). \
            replace(u"ü","ue").replace(u"ß","ss")
        return word
                
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
    
    # Construct string
    text_output_pos_string = 'NONE'
    if WITH_POS_FILTER:
        text_output_pos_string = '-'.join(POS_FILTER[lang])
        
    text_output_lemma_string = 'TRUE'
    if WITH_LEMMATA is False:
        text_output_lemma_string = 'FALSE'
        
    text_output_dirpath = TEXT_OUTPUT_DIR + sep \
                        +'yr=' + str(year_range[0]) \
                        + '-' + str(year_range[-1]) \
                        + '_lc=' + lang \
                        + '_pf=' + text_output_pos_string \
                        + '_lm=' + text_output_lemma_string
    
    if not exists(text_output_dirpath):
        makedirs(text_output_dirpath)
    
    articles_collection = ArticlesCollection(year_range, 
                                             text_output_dirpath,
                                             lang)
    articles_collection.show_lda()
    
if __name__ == '__main__':
	main()
