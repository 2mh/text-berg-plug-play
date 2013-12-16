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

# Languages to be used
DE_LANG = 'de'
FR_LANG = 'fr'

# Years available in SAC corpus
YEARS_ALLOWED = range(1864, 2012) # 1864 to 2011

# SAC XML folder path
SAC_XML_DIR = 'Text+Berg_Release_147_v03' + sep + 'XML' + sep \
            + 'SAC' + sep

# Folder to hold word ids for each document's words
WORDIDS_DIR = 'wordid_files' + sep

# Folder where matrix representations of bag-of-words corpora is held
BOWMM_DIR = 'bowmm_files' + sep

# Folder to hold TF*IDF matrices for each document
TFIDF_DIR = 'tfidf_files' + sep

def document_id(filename):
    """Returns document id by stripping away the .xml ending."""
    return filename.replace('.xml', '')

class BookCollection:
    
    def __init__(self, year_or_range, lang=DE_LANG):
        print(str(from_year) + str(to_year))

class BookCorpus:
    
    def __init__(self, filename, lang=DE_LANG):
        self.filename = filename
        self.lang = lang
        self.id = document_id(self.filename)
        self.articles = []
        self.read_texts()
        self.remove_single_words()
        
    def read_texts(self):
            
        sac_xml = etree.parse(SAC_XML_DIR + sys.argv[1])
        #sac_book_xml = sac_xml.xpath('/book')[0]
        #sac_xml_articles_list = sac_book_xml.xpath('article')
        sac_xml_articles_list = sac_xml.xpath('.//article')
        
        # For each article
        for sac_xml_article in sac_xml_articles_list:
            article_word_list = []
            sac_xml_sentences_list = \
                sac_xml_article.xpath('.//s[@lang=\'' + self.lang + '\']')
            # For each sentence (in the article)
            for sac_xml_sentence in sac_xml_sentences_list:
                sac_xml_words_list = \
                    sac_xml_words_list = sac_xml_sentence.xpath('.//w')
                # For each word (in the sentence of the article)
                for sac_xml_word in sac_xml_words_list:
                    # Look for POS tags of FR_LANG
                    if self.lang is not DE_LANG:
                        if sac_xml_word.attrib['pos'] == 'N_P' \
                        or sac_xml_word.attrib['pos'] == 'N_C' \
                        or sac_xml_word.attrib['pos'] == 'V':
                            article_word_list.append(sac_xml_word.attrib['lemma'].lower())
                    # Assume DE_LANG (default lang)
                    else:
                        if sac_xml_word.attrib['pos'] == 'NN' \
                        or sac_xml_word.attrib['pos'] == 'NE' \
                        or sac_xml_word.attrib['pos'] == 'VVFIN':
                            article_word_list.append(sac_xml_word.attrib['lemma'].lower())
            # Save article as bag-of-words (of the sentences)
            self.articles.append(article_word_list)
    
    def remove_single_words(self):
        """Remove words which appear only (up to) a certain number of
           times; code as inspired by gensim website:
           http://radimrehurek.com/gensim/tut1.html#corpus-streaming-one-document-at-a-time
        """
        print("Remove words which appear only up to three times.")
        all_words = sum(self.articles, [])
        words_to_drop = set(word for word in set(all_words) 
                         if all_words.count(word) <= 3)
        self.articles = [[word for word in text 
                          if word not in words_to_drop]
                          for text in self.articles]
                
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
    print("Not allowed year (range).")
    print_help(sys.argv[0])    

def main():
    
    # Create folders (occasionally) used
    if not exists(WORDIDS_DIR):
        makedirs(WORDIDS_DIR)
    if not exists(TFIDF_DIR):
        makedirs(TFIDF_DIR)
    if not exists(BOWMM_DIR):
        makedirs(BOWMM_DIR)
        
    if len(sys.argv) < 2:
        print_help(sys.argv[0])
    
    # Files necessary to do topic analysis
    fileid_infix = document_id(sys.argv[1]) + '_'
    wordsids_filepath = WORDIDS_DIR + fileid_infix + 'wordsids.txt'
    bowmm_filepath = BOWMM_DIR + fileid_infix + 'bow.mm'
    tfidf_filepath = TFIDF_DIR + fileid_infix + 'tfidf.mm'
    
    # Assumption: No processing happened before, if no words ids file
    if not exists(wordsids_filepath):
        
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
        
        for year in year_range:
            print(year)
            
        sys.exit(0)
        
        book_corpus = BookCorpus(sys.argv[1], lang=lang)
        
        # Read in SAC XML file as one corpus (consisting of articles)
        print("Read in SAC XML book.")
        
        # Create dictionary and save it to disk
        print("Create dictionary of SAC XML book.")
        dictionary = Dictionary(book_corpus.articles)
        dictionary.save_as_text(wordsids_filepath)
    
        # Create bag-of-words representation of corpus, and save it in
        # Matrix Matrix format to disk
        print("Create bag-of-words matrix representation of SAC XML book.")
        bow_book_corpus = [dictionary.doc2bow(article) 
                       for article in book_corpus.articles]
        MmCorpus.serialize(bowmm_filepath, bow_book_corpus)
    
        # Create TF-IDF matrix and save it in Matrix Matrix format to disk
        print("Create TF*IDF matrix of words in SAC XML book.")
        tfidf = TfidfModel(bow_book_corpus, 
                       id2word=dictionary, 
                       normalize=True)
        MmCorpus.serialize(tfidf_filepath, tfidf[bow_book_corpus])
    
    
    # Find out and print ten most promising LDA topics
    tfidf = MmCorpus(tfidf_filepath)
    print(tfidf)
    dictionary = Dictionary.load_from_text(wordsids_filepath)
    
    # k = number of documents = number of topics (for now)
    lda = LdaModel(corpus=tfidf,
                   id2word=dictionary,
                   num_topics=tfidf.num_docs,
                   passes=1,
                   distributed=True)
    topic_number = 0
    for topic in lda.print_topics(10):
        topic_number += 1
        print('Topic#' + str(topic_number) + ': ', topic)

if __name__ == '__main__':
	main()
