import logging
import logging.config
import yaml
import os
import yaml


def setup_logging(
    default_path='logging.yaml',
    default_level=logging.INFO
):
    """Setup logging configuration

    """
    path = default_path
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        print(f"Can't load {path}")
        logging.basicConfig(level=default_level)


setup_logging()
logger = logging.getLogger(__name__)
logger.debug('This is a debug message')
logger.info('This is a info message')
logger.error('This is a error message')


