from logging import getLogger, FileHandler, Formatter, INFO


def init_logger(filename):
    logger = getLogger(__name__)
    logger.setLevel(INFO)

    # create a file handler
    handler = FileHandler(filename)
    handler.setLevel(INFO)

    # create a logging format
    formatter = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)
    return logger
