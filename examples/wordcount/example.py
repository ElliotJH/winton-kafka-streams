"""
Winton Kafka Streams

Main entrypoints

"""

import logging
import time
import collections

from winton_kafka_streams.processor import BaseProcessor, TopologyBuilder
import winton_kafka_streams.kafka_config as kafka_config
import winton_kafka_streams.kafka_stream as kafka_stream

log = logging.getLogger(__name__)

# An example implementation of word count,
# showing where punctuate can be useful
class WordCount(BaseProcessor):

    def initialise(self, _name, _context):
        super().initialise(_name, _context)
        self.word_counts = collections.Counter()
        # dirty_words tracks what words have changed since the last punctuate
        self.dirty_words = set()
        # output updated counts every 10 seconds
        self.context.schedule(10.)

    def process(self, key, value):
        words = value.decode('utf-8').split()
        self.word_counts.update(words)
        self.dirty_words |= set(words)

    def punctuate(self, timestamp):
        for word in self.dirty_words:
            count = str(self.word_counts[word])
            log.debug(f'Forwarding to sink ({word}, {count})')
            self.context.forward(word, count)
        self.dirty_words = set()


def run(config_file):
    kafka_config.read_local_config(config_file)

    # Can also directly set config variables inline in Python
    #kafka_config.KEY_SERDE = MySerde

    with TopologyBuilder() as topology_builder:
        topology_builder. \
            source('input-value', ['wks-wordcount-example-topic']). \
            processor('count', WordCount, 'input-value'). \
            sink('output-count', 'wks-wordcount-example-count', 'count')

    wks = kafka_stream.KafkaStreams(topology_builder, kafka_config)
    wks.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        wks.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Debug runner for Python Kafka Streams")
    parser.add_argument('--config-file', '-c',
                        help="Local configuration - will override internal defaults",
                        default='config.properties')
    parser.add_argument('--verbose', '-v',
                        help="Increase versbosity (repeat to increase level)",
                        action='count', default=0)
    args = parser.parse_args()

    levels = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}
    logging.basicConfig(level=levels.get(args.verbose, logging.DEBUG))

    run(args.config_file)
