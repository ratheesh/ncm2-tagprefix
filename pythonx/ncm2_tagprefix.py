# -*- coding: utf-8 -*-

import vim
from ncm2 import Ncm2Source, getLogger
import re
from os import path

logger = getLogger(__name__)

class Source(Ncm2Source):

    def on_complete(self, ctx, cwd, tagfiles):

        base = ctx['base']
        tags = {}

        #  logger.info('base: %s', base)
        for name in tagfiles:
            try:
                p = path.join(cwd, name)
                #  logger.info('path: %s', p)
                for line in binary_search_lines_by_prefix(base, p):
                    #  fields = line.split("\t")
                    #
                    #  if len(fields)<2:
                    #      continue
                    #
                    #  _fsig = fields[2]
                    #  m = re.search(r'/\^(.*?)\$/;"', fields[2])
                    #  if m:
                    #      _fsig = m.group(1)
                    #  else:
                    #      _fsig = ''
                    #  tags[fields[0]] = dict(word=fields[0], menu=_fsig)

                    #  folowing code is lifted from deoplete tag source file
                    cols = line.strip().split('\t', 2)
                    if not cols or cols[0].startswith('!_'):
                        return {}

                    tagfield = {}
                    if ';"' in cols[-1]:
                        cols[-1], fields = cols[-1].split(';"', 1)
                        for pair in fields.split('\t'):
                            if ':' not in pair:
                                tagfield['_kind'] = pair
                            else:
                                k, v = pair.split(':', 1)
                                tagfield[k] = v

                    _kind = tagfield.get('_kind', '')
                    _fsignature=''
                    if _kind == 'f':
                        i = cols[2].find('(')
                        if i != -1 and cols[2].find(')', i+1) != -1:
                            m = re.search(r'(\w+\(.*\))', cols[2])
                            if m:
                                #  logger.info('m.group(1): %s', m.group(1))
                                #  print('word:%s,abbr:%s,_kind:%s' % (cols[0], m.group(1), _kind))
                                #  tags[cols[0]] = dict(word=cols[0], kind=_kind, menu=m.group(1))
                                _fsignature=m.group(1)
                    #  print('word:%s,kind:%s' % (cols[0], kind))
                    tags[cols[0]] = dict(word=cols[0], kind=_kind, abbr=_fsignature)
            except Exception as ex:
                logger.exception('failed searching %s', name)

        # unique
        matches = list(tags.values())

        # there are huge tag files sometimes, be careful here. it's meaningless
        # to have huge amout of results.
        refresh = False
        if len(matches)>100:
            matches = matches[0:100]
            refresh = True

        self.complete(ctx, ctx['startccol'], matches, refresh)


def binary_search_lines_by_prefix(prefix, filename):

    with open(filename, 'r') as f:

        # Calculate sorting mode of tag file. If mode is 2 (foldcase), then when
        # navigating the tags we need to ignore the case
        foldcase = False
        line0 = f.readline()
        while line0.startswith('!'):
            if line0.startswith('!_TAG_FILE_SORTED'):
                sort_mode = int(line0.split('\t')[1])
                if sort_mode == 1:
                    pass
                elif sort_mode == 2:
                    foldcase = True
                else:
                    logger.exception('_TAG_FILE_SORTED=%d is not supported', sort_mode)
                break
            line0 = f.readline()

        prefix_fc = prefix.lower() if foldcase else prefix

        def yield_results():
            while True:
                line = f.readline()
                if not line:
                    return
                if line[:len(prefix)] == prefix:
                    yield line
                else:
                    return

        begin = 0
        f.seek(0, 2)
        end = f.tell()

        while begin < end:

            middle_cursor = int((begin+end)/2)

            f.seek(middle_cursor, 0)
            f.readline()

            line1pos = f.tell()
            line1 = f.readline()

            line2pos = f.tell()
            line2 = f.readline()

            line2end = f.tell()

            key1 = '~~'
            # if f.readline() returns an empty string, the end of the file has
            # been reached
            if line1 != '':
                key1 = line1[:len(prefix)]

            key2 = '~~'
            if line2 != '':
                key2 = line2[:len(prefix)]

            key1_fc = key1.lower() if foldcase else key1
            key2_fc = key2.lower() if foldcase else key2

            if key1_fc >= prefix_fc:
                if line2pos < end:
                    end = line2pos
                else:
                    # (begin) ... | line0 int((begin+end)/2) | line1 (end) | line2 |
                    #
                    # this assignment push the middle_cursor forward, it may
                    # also result in a case where begin==end
                    #
                    # do not use end = line1pos, may results in infinite loop
                    end = int((begin+end)/2)
                    if end == begin:
                        if key1 == prefix:
                            # find success
                            f.seek(line2pos, 0)
                            yield from yield_results()
                        return
            elif key2_fc == prefix_fc:
                # find success
                # key1 < prefix  && next line key2 == prefix
                f.seek(line2pos, 0)
                yield from yield_results()
                return
            elif key2_fc < prefix_fc:
                begin = line2end
                # if begin==end, then exit the loop
            else:
                # key1 < prefix &&  next line key2 > prefix here, not found
                return


source = Source(vim)

on_complete = source.on_complete
