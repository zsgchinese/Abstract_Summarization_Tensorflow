from word2vec.w2v import w2v
import logging.config
import string
import numpy as np
import pickle
from seq2seq import seq2seqmodel
from timeit import timeit

"""Log Configuration"""
LOG_FILE = './log/train.log'
handler = logging.FileHandler(LOG_FILE, mode='w')  # 实例化handler
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'
formatter = logging.Formatter(fmt)  # 实例化formatter
handler.setFormatter(formatter)  # 为handler添加formatter
logger = logging.getLogger('trainlogger')  # 获取名为tst的logger
logger.addHandler(handler)  # 为logger添加handler
logger.setLevel(logging.DEBUG)

"""Hyper Parameters(Seq2Seq train)"""
VOVAB_SIZE = 20000
EMBED_SIZE = 128
ENCODER_HIDEEN_UNITS = 128
DECODER_HIDDEN_UNITS = 256
BATCH_SIZE = 32
ENCODER_LAYERS = 1
EPOCH = 100
NUM_TRAIN_STEPS = 205
SKIP_STEPS = 10
LEARNING_RATE_INITIAL = 1.0
KEEP_PROB = 0.2

"""Hyper Parameters(Seq2seq infer)"""
BATCH_SIZE_INFER = 5
EPOCH_INFER = 1
NUM_TRAIN_STEPS_INFER = 1

"""Hyper Parameters(Word2Vec)"""
NUM_SAMPLED = 64
LEARNING_RATE_W2V = 1.0
SKIP_WINDOWS = 1
DATA_NAME_W2V = 'traintext.zip'
NUM_TRAIN_STEPS_W2V = 17000
SKIP_STEPS_W2V = 100


def build_embed_matrix():
    w2vmodel = w2v(vocab_size=VOVAB_SIZE,
                   embed_size=EMBED_SIZE,
                   batch_size=BATCH_SIZE,
                   num_sampled=NUM_SAMPLED,
                   learning_rate=LEARNING_RATE_W2V,
                   skip_windows=SKIP_WINDOWS,
                   data_name=DATA_NAME_W2V,
                   num_train_steps=NUM_TRAIN_STEPS_W2V,
                   skip_steps=SKIP_STEPS_W2V)
    w2vmodel.build_graph()
    return w2vmodel.train()


def save_embed_matrix(embed_matrix, one_hot_dictionary, one_hot_dictionary_index):
    output = open('./save/embed_matrix.pkl', 'wb')
    pickle.dump(embed_matrix, output)
    output.close()
    output = open('./save/one_hot_dictionary.pkl', 'wb')
    pickle.dump(one_hot_dictionary, output)
    output.close()
    output = open('./save/one_hot_dictionary_index.pkl', 'wb')
    pickle.dump(one_hot_dictionary_index, output)
    output.close()


def load_embed_matrix():
    pkl_file = open('./save/embed_matrix.pkl', 'rb')
    embed_matrix = pickle.load(pkl_file)
    pkl_file.close()
    pkl_file = open('./save/one_hot_dictionary.pkl', 'rb')
    one_hot_dictionary = pickle.load(pkl_file)
    pkl_file.close()
    pkl_file = open('./save/one_hot_dictionary_index.pkl', 'rb')
    one_hot_dictionary_index = pickle.load(pkl_file)
    pkl_file.close()
    return embed_matrix, one_hot_dictionary, one_hot_dictionary_index


def get_batch(batch_size, iterator):
    while True:
        encoder_batch = []
        decoder_batch = []
        target_batch = []

        bucket_encoder_length = 0
        bucket_decoder_length = 0

        for index in range(batch_size):
            encoder_input_batch_single, decoder_input_batch_single, target_batch_single, encoder_length_single, decoder_length_single = next(
                iterator)

            if encoder_length_single > bucket_encoder_length:
                bucket_encoder_length = encoder_length_single
            if decoder_length_single > bucket_decoder_length:
                bucket_decoder_length = decoder_length_single

            encoder_batch.append(encoder_input_batch_single)
            decoder_batch.append(decoder_input_batch_single)
            target_batch.append(target_batch_single)

        for index in range(batch_size):
            len_temp = len(encoder_batch[index])
            encoder_batch[index] = np.resize(encoder_batch[index], [bucket_encoder_length])
            encoder_batch[index][len_temp + 1:] = 0

            len_temp = len(decoder_batch[index])
            decoder_batch[index] = np.resize(decoder_batch[index], [bucket_decoder_length])
            target_batch[index] = np.resize(target_batch[index], [bucket_decoder_length])

            decoder_batch[index][len_temp + 1:] = 0
            target_batch[index][len_temp:] = 0
        yield encoder_batch, decoder_batch, target_batch, bucket_encoder_length, bucket_decoder_length


def one_hot_generate(one_hot_dictionary, epoch, is_train):
    for i in range(epoch):
        if is_train:
            file_headline = open('./data/headline_train.txt', 'rb')
            file_article = open('./data/article_train.txt', 'rb')
        else:
            file_headline = open('./data/headline_infer.txt', 'rb')
            file_article = open('./data/article_infer.txt', 'rb')

        sentence_article = bytes.decode(file_article.readline())
        sentence_headline = bytes.decode(file_headline.readline())

        while sentence_article and sentence_headline:
            words_article = []
            words_headline = []
            count_article = 0
            count_headline = 0
            strip = string.whitespace + string.punctuation + "\"'"
            for word in sentence_article.split():
                word = word.strip(strip)
                words_article.append(word)
                count_article += 1
            for word in sentence_headline.split():
                word = word.strip(strip)
                words_headline.append(word)
                count_headline += 1
            one_hot_article = np.zeros([count_article + 1], dtype=int)
            one_hot_headline_input = np.zeros([count_headline + 2], dtype=int)
            one_hot_headline_target = np.zeros([count_headline + 2], dtype=int)

            index = 0

            for index, word in enumerate(words_article):
                one_hot_article[index] = one_hot_dictionary[word] if word in one_hot_dictionary else 0

            one_hot_headline_input[0] = 19654

            for index, word in enumerate(words_headline):
                one_hot_headline_input[index + 1] = one_hot_dictionary[word] if word in one_hot_dictionary else 0
                one_hot_headline_target[index] = one_hot_dictionary[word] if word in one_hot_dictionary else 0
            one_hot_headline_target[index + 2] = 19655

            yield one_hot_article, one_hot_headline_input, one_hot_headline_target, count_article, count_headline
            sentence_article = bytes.decode(file_article.readline())
            sentence_headline = bytes.decode(file_headline.readline())

        file_headline.close()
        file_article.close()


def train(embed_matrix, one_hot_dictionary):
    print("train mode")
    seq2seq_train = seq2seqmodel(vocab_size=VOVAB_SIZE,
                                 embed_size=EMBED_SIZE,
                                 encoder_hidden_units=ENCODER_HIDEEN_UNITS,
                                 decoder_hidden_units=DECODER_HIDDEN_UNITS,
                                 batch_size=BATCH_SIZE,
                                 embed_matrix_init=embed_matrix,
                                 encoder_layers=ENCODER_LAYERS,
                                 learning_rate_initial=LEARNING_RATE_INITIAL,
                                 is_train=1,
                                 keep_prob=KEEP_PROB,
                                 core="bgru"
                                 )

    single_generate = one_hot_generate(one_hot_dictionary=one_hot_dictionary,
                                       epoch=EPOCH,
                                       is_train=1)

    batches = get_batch(batch_size=BATCH_SIZE,
                        iterator=single_generate)
    logger.debug("batch generated")

    seq2seq_train._run(epoch=EPOCH,
                       num_train_steps=NUM_TRAIN_STEPS,
                       batches=batches,
                       skip_steps=SKIP_STEPS)
    logger.debug("seq2seq model trained")


def test(embed_matrix, one_hot_dictionary, one_hot_dictionary_index):
    print("test mode")
    seq2seq_infer = seq2seqmodel(vocab_size=VOVAB_SIZE,
                                 embed_size=EMBED_SIZE,
                                 encoder_hidden_units=ENCODER_HIDEEN_UNITS,
                                 decoder_hidden_units=DECODER_HIDDEN_UNITS,
                                 encoder_layers=ENCODER_LAYERS,
                                 batch_size=BATCH_SIZE_INFER,
                                 learning_rate_initial=LEARNING_RATE_INITIAL,
                                 embed_matrix_init=embed_matrix,
                                 keep_prob=KEEP_PROB,
                                 is_train=0,
                                 core="bgru")

    single_generate = one_hot_generate(one_hot_dictionary,
                                       epoch=EPOCH_INFER,
                                       is_train=0)
    batches = get_batch(batch_size=BATCH_SIZE_INFER,
                        iterator=single_generate)
    logger.debug("batch generated")

    seq2seq_infer._run(epoch=EPOCH_INFER,
                       num_train_steps=NUM_TRAIN_STEPS_INFER,
                       batches=batches,
                       one_hot=one_hot_dictionary_index,
                       skip_steps=1)
    logger.debug("seq2seq model tested")


def main():
    # print("test word2vec model")
    # embed_matrix, one_hot_dictionary, one_hot_dictionary_index = build_embed_matrix()
    # logger.debug("w2v finished")
    #
    # save_embed_matrix(embed_matrix, one_hot_dictionary, one_hot_dictionary_index)
    # logger.debug("w2v saved")

    embed_matrix, one_hot_dictionary, one_hot_dictionary_index = load_embed_matrix()
    logger.debug("w2v restored")

    train(embed_matrix, one_hot_dictionary)
    # test(embed_matrix, one_hot_dictionary, one_hot_dictionary_index)


if __name__ == '__main__':
    # t = timeit('main()', 'from __main__ import main', number=1)
    # print(t)
    main()
