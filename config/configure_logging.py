import logging


log = logging.getLogger()
log.setLevel(logging.DEBUG)

hdlr = logging.StreamHandler()
hdlr.setLevel(logging.DEBUG)

fmtr = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')

hdlr.setFormatter(fmtr)
log.addHandler(hdlr)

###

log = logging.getLogger('urllib3')
log.setLevel(logging.INFO)