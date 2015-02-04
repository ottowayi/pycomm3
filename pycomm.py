
from cip import Cip
import logging
from cip_base import setup_logging


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    setup_logging()
    c = Cip()
    c.open('192.168.1.10')
    # c.open('172.16.32.100')
    v = c.read_tag('TEST6[9,9,9].sData.iVal')
    print v
    if v is not None:
        c.write_tag('TEST6[9,9,9].sData.iVal', v[0]+1, 'DINT')
    c.close()
    logger.info('Done')
    logging.shutdown()

