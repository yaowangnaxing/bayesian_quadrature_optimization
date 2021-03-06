import gzip
import json
import os
from os import path
from stratified_bayesian_optimization.util.json_file import JSONFile
from stratified_bayesian_optimization.initializers.log import SBOLog
import ujson

logger = SBOLog(__name__)


class ProcessRawData(object):

     _years = [2017, 2016, 2015, 2014, 2013, 2012]
     _data_path = '/data/json/usage/'
     _papers_path = '/data/json/idcat/'
     _store_path = 'problems/arxiv/data/click_data_{year}.json'.format

     @classmethod
     def get_click_data(cls, filenames, store_filename):
          """
          Get click data from filenames. Writes a JSON file with the format:

          {
               'cookie_hash': {'arxiv_id'}
          }

          :param filenames: [str]
          :param store_filename: str

          """
          paper = {}

          process_data = {}

          process_files = []
          store_files = "problems/arxiv/data/store_files.json"

          for filename in filenames:
               logger.info("Processing filename: %s" % filename)

               f = gzip.open(filename, 'rb')

               data = json.load(f)
               entries = data['entries']

               for entry in entries:
                    if 'arxiv_id' in entry and 'cookie_hash' in entry:
                         before_2007 = False
                         arxiv_id = entry['arxiv_id']

                         # if '/' in arxiv_id:
                         #      before_2007 = True
                         #      index = arxiv_id.index('/')
                         #      cat = arxiv_id[0: index]
                         #      arxiv_id = arxiv_id[index + 1:]
                         #
                         # if 'v' in arxiv_id:
                         #     index = arxiv_id.rfind('v')
                         #     arxiv_id = arxiv_id[0: index]
                         #
                         #
                         user = entry['cookie_hash']
                         #
                         # if arxiv_id not in paper:
                         #      if not before_2007:
                         #           cat = cls.get_cats(arxiv_id, arxiv_id[0: 2], arxiv_id[2: 4])

                         if arxiv_id not in paper:
                              paper[arxiv_id] = {'views': 0}

                         paper[arxiv_id]['views'] += 1

                         if user not in process_data:
                              process_data[user] = {}
                              process_data[user][arxiv_id] = 0
                         elif arxiv_id not in process_data[user]:
                              process_data[user][arxiv_id] = 0
                         process_data[user][arxiv_id] += 1

               process_files.append(filename[22:28])
               JSONFile.write(process_files, store_files)

               JSONFile.write([process_data, paper], store_filename)

          JSONFile.write([process_data, paper], store_filename)

     @classmethod
     def generate_filenames_year(cls, year):
          """
          Generate all file names of one year
          :param year: (int)
          :return: [str]
          """
          data_path = path.join(cls._data_path, str(year))

          files = []

          for (dirpath, dirnames, filenames) in os.walk(data_path):
               files = filenames

          files = [path.join(data_path, f) for f in files]

          return files

     @classmethod
     def generate_filenames_month(cls, year, month):
          """
          Generate all file names of one year
          :param year: (int)
          :param month: (int)
          :return: [str]
          """

          if month <= 9:
               month = '0' + str(month)
          else:
               month = str(month)
          data_path = path.join(cls._data_path, str(year))

          files = []

          for (dirpath, dirnames, filenames) in os.walk(data_path):
               files = filenames

          files = [path.join(data_path, f) for f in files if f[2:4] == month]

          return files


     @classmethod
     def get_cats(cls, arxiv_id, year, month):
          """
          Get category of a file

          :param arxiv_id: (str)
          :param year: (str) e.g. '07', '10'
          :param month: (str) e.g. '12', '02'
          :return: str

          """

          filename = path.join(cls._papers_path, '20' + year)
          date = year + month

          cats = None

          for day in xrange(1, 32):
               if day < 10:
                    date_ = date + '0' + str(day)
               else:
                    date_ = date + str(day)

               date_ += '_idcat.json'
               filename_ = path.join(filename, date_)


               data = None
               if path.exists(filename_):
                    with open(filename_) as f:
                         data = ujson.load(f)

               if data is not None:
                    for dicts in data['new']:
                         if dicts['id'] == arxiv_id:
                              cats = [a.lower() for a in dicts["cat"].split(":")]
                              break

               if cats is not None:
                    return cats[0]

          new_month = int(month) + 1

          if new_month == 13:
               new_month = 1
               year = int(year) + 1
               if year < 10:
                    year = '0' + str(year)
               else:
                    year = str(year)

          if new_month < 10:
               new_month = '0' + str(new_month)
          else:
               new_month = str(new_month)

          filename = path.join(cls._papers_path, '20' + year)

          for day in xrange(1, 10):
               date = year + new_month + '0' + str(day) + '_idcat.json'
               filename_ = path.join(filename, date)

               data = None
               if path.exists(filename_):
                    with open(filename_) as f:
                         data = ujson.load(f)

               if data is not None:
                    for dicts in data['new']:
                         if dicts['id'] == arxiv_id:
                              cats = [a.lower() for a in dicts["cat"].split(":")]
                              break

               if cats is not None:
                    return cats[0]

          if cats is None:
               logger.info("Couldn't find category of paper %s" % arxiv_id)

          return cats
