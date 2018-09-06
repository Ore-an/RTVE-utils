#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import codecs
import pysrt
import regex as re
import os
import glob
from multiprocessing import Pool

exclude_paren = re.compile(ur'(\(.*\))')
exclude_punct = re.compile(ur'[^\P{P}\']+')  # everything but '


class utterance(object):
    def __init__(self, utt_id, start, end, text):
        self.utt_id = utt_id
        self.start = start/1000.0
        self.end = end/1000.0
        self.text = exclude_punct.sub('', text.lower())


class recording(object):
    def __init__(self, name):
        self.basename = os.path.basename(name)[:-4]
        self.utterances = []
        self.utt_number = 0

    def add_utterance(self, start, end, text):
        if text.strip() and start < end:
            self.utterances.append(utterance(self.utt_number, start, end, text))
            self.utt_number += 1

    def __lt__(self, other):
        return self.basename < other.basename

    def __len__(self):
        return len(self.utterances)


def parse_srt(filename):
    try:
        f = pysrt.open(filename)
    except UnicodeDecodeError:
        f = pysrt.open(filename, 'latin-1')  # some files have a different encoding and newline char
    reco = recording(filename)
    for sub in f:
        sub.text = exclude_paren.sub('', sub.text_without_tags).replace('\n', ' ')
        reco.add_utterance(sub.start.ordinal, sub.end.ordinal, sub.text)  # time in ms
    return reco


def main(srt_dir, audio_dir, out_dir, threads=10):

    thr_pool = Pool(threads)
    recordings = (thr_pool.map(parse_srt, glob.glob(srt_dir + '/*.srt')))

    recordings = [x for x in recordings if len(x) > 0]  # Recordings must have at least one segment

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    seg = codecs.open(out_dir + '/segments', 'w', 'utf-8')
    wav = codecs.open(out_dir + '/wav.scp', 'w', 'utf-8')
    utt2spk = codecs.open(out_dir + '/utt2spk', 'w', 'utf-8')
    txt = codecs.open(out_dir + '/text', 'w', 'utf-8')

    try:
        for reco in sorted(recordings):
            wav.write('{} ffmpeg -loglevel panic -i {}/{}.aac -ac 1 -ar 16000 -f wav - |\n'.format(
                reco.basename, os.path.abspath(audio_dir), reco.basename))

            for utt in reco.utterances:
                txt.write(u'{}-{:04d} {}\n'.format(reco.basename, utt.utt_id, utt.text))

                seg.write('{}-{:04d} {} {} {}\n'.format(reco.basename, utt.utt_id,
                                                  reco.basename, utt.start, utt.end))

                utt2spk.write('{}-{:04d} {}-{:04d}\n'.format(reco.basename, utt.utt_id,
                                                   reco.basename, utt.utt_id))

    finally:
        seg.close()
        wav.close()
        utt2spk.close()
        txt.close()


if __name__ == "__main__":
    srt_dir = sys.argv[1]
    audio_dir = sys.argv[2]
    out_dir = sys.argv[3]

    main(srt_dir, audio_dir, out_dir)
