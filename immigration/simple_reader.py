from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from cStringIO import StringIO

import re
import urllib2, requests
import os, sys
import argparse
import time
import nltk.data

ERROR = 1
INFO = 2
MONITOR = 3
DEBUG = 4
debug = None
FILE_STORAGE_PATH = './files/'

class Debugger(object):
    """
    Debugger object helps me create tiered printout messages.
    It's used fromt he command-line.
    """
    sensitivity = None

    def __init__(self, s):
        self.sensitivity = s
        return

    def log(self, flag, message, end='\n'):
        if self.sensitivity >= flag:
            if flag == ERROR:
                print("ERROR\t{}".format(message))
            elif flag == INFO:
                print("INFO\t{}".format(message))
            elif flag == MONITOR:
                print("NOTE\t {}".format(message))
            elif flag == DEBUG:
                print("DEBUG\t {}".format(message))
            sys.stdout.flush()

def find_label(text, sentences):
    """
    Given a body of text from a judicial decision (BIA), come up with a label
    """

    # positive_regexes =  [ "appeal.*dismissed"
    #                     , "appeal.*denied"
    #                     , "appeal.*rejected"
    #                     ]

    order_sentence = []
    for sentence in sentences:
        found_order = False
        for word in sentence.split():
            if word.lower() == "order:":
                found_order = True
            if found_order:
                order_sentence.append(word)

    return order_sentence

def pdf_to_text(path):
    """
    given a path to a pdf, converts it to text.
    source for this code: https://stackoverflow.com/questions/26494211/extracting-text-from-a-pdf-file-using-pdfminer-in-python
    """
    mgr = PDFResourceManager()
    retval = StringIO()
    codec = 'utf-8'
    laparams = LAParams()
    device = TextConverter(mgr, retval, codec=codec, laparams=laparams)
    fp = open(path, 'rb')
    interpreter = PDFPageInterpreter(mgr, device)
    password = ""
    maxpages = 0
    caching = True
    pagenos = set()

    for page in PDFPage.get_pages(fp, pagenos, maxpages=maxpages, password=password, caching=caching, check_extractable=True):
        interpreter.process_page(page)

    text = retval.getvalue()

    fp.close()
    device.close()
    retval.close()
    return text

def get_bia_pdfs():
    """
    This downloads pdfs from a specific location on the internet.
    """
    debug.log(INFO, "Beginning to dowload pdfs from the BIA...")
    start = time.time()
    base_url = "https://www.justice.gov"
    link_regex = '<td class=\".*><a href=\"(.*)\">ID (....)<\\/a> \\(PDF\\)<\\/td>'
    urls = [ "https://www.justice.gov/eoir/precedent-decision-alpha-a-e"
            , "https://www.justice.gov/eoir/precedent-decision-alpha-f-j"
            , "https://www.justice.gov/eoir/precedent-decision-alpha-k-o"
            , "https://www.justice.gov/eoir/precedent-decision-alpha-p-t"
            , "https://www.justice.gov/eoir/precedent-decision-alpha-u-z"
            ]

    links = {}
    paths = []
    for url in urls:
        text = ""
        page = urllib2.urlopen(url)
        text = page.read()
        matchers = re.finditer(link_regex, text)
        for matcher in matchers:
            match = matcher.group(1)
            name = matcher.group(2)
            links[name] = base_url + match

    for name in links:
        url = links[name]
        response = requests.get(url)

        my_path = os.path.abspath(__file__)
        my_dir = os.path.split(my_path)[0]
        abs_path = os.path.join(my_dir, '{}{}.pdf'.format(FILE_STORAGE_PATH, name))
        paths.append(abs_path)

        with open('{}{}.pdf'.format(FILE_STORAGE_PATH, name), 'wb') as fp:
            fp.write(response.content)
            debug.log(MONITOR, "Downloaded: {}.pdf".format(name))

    debug.log(INFO, "...Finished downloading pdfs. Time: {}".format(time.time() - start))

    return paths


def main():
    """
    Begin by downloading pdfs from the BIA and storing paths to them.
    """
    #get_bia_pdfs(FILE_STORAGE_PATH)

    my_path = os.path.abspath(__file__)
    my_dir = os.path.split(my_path)[0]
    file_dir = os.path.join(my_dir, FILE_STORAGE_PATH)
    rel_paths = os.listdir(file_dir)
    paths = [os.path.join(file_dir, rel_path) for rel_path in rel_paths]

    """
    Next, we grab the raw text contained in those pdfs and store them in their own files.
    """
    # for i, path in enumerate(paths):
    #     if path[-4:] == '.pdf':
    #         debug.log(MONITOR, "Extracting data at {}".format(path))
    #         text = pdf_to_text(path)
    #         with open('{}{}.txt'.format(file_dir, i), 'wb') as fp:
    #             fp.write(text)
    #             debug.log(MONITOR, "Read text from pdf.")

    """
    Next, for each text file, we choose a label, and then tokenize the text + label
    """

    debug.log(INFO, "Converting text into sentences...")
    start = time.time()
    paths = [os.path.join(file_dir, rel_path) for rel_path in os.listdir(file_dir)]
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    labeled_sentences = []
    for i, path in enumerate(paths):
        if path[-4:] == '.txt':
            debug.log(MONITOR, "Handling text at {}".format(path))
            with open(path, 'rb') as fp:

                text = fp.read().decode('utf8').strip()
                sentences = tokenizer.tokenize(text)
                debug.log(DEBUG, "Got sentences: \n{}".format(sentences))

                label = " ".join(find_label(text, sentences)).encode('utf-8')
                filename = os.path.split(path)[1]
                debug.log(MONITOR, "Label for {}: {}".format(filename, label))

                labeled_sentences += map(lambda x: (x, label), sentences)

    debug.log(INFO, "Finished grabbing sentences. Count: {}. Time: {}".format(len(labeled_sentences), time.time() - start))

    """
    Finally, we build a tsv file of sentence-label pairs.
    """

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbosity", help="set output verbosity", type=int)
    args = parser.parse_args()

    global debug
    if args.verbosity != None:
        debug = Debugger(args.verbosity)
    else:
        debug = Debugger(INFO)

    main()
