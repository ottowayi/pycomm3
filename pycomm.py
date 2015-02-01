
from cip import Cip
import logging
from cip_base  import setup_logging



if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    setup_logging()
    logger.info('Log setup')
    c = Cip()
    c.open('192.168.1.10')
    # c.open('172.16.32.100')
    # c.register_session()
    # c.list_identity()
    # c.list_interfaces()
    # c.send_rr_data("TotalCount")
    # c.list_services()
    # c.list_identity()
    # c.read_tag('TotalCount')
    # c.read_tag('SQL_ENDPOINT_STATUS')
    # c.get_tags_list()
    print c.read_tag('Counts')
    c.write_tag('Counts', 225, 'INT')
    print c.read_tag('Counts')
    c.write_tag('Counts', 6, 'INT')
    c.close()
    logger.info('Done')
    logging.shutdown()

