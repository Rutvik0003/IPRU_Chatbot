import re
from urllib.parse import urlparse


def sanitize_filename(name):

    return re.sub(
        r'[^a-zA-Z0-9._-]',
        '_',
        name
    )



def is_same_domain(base_url, target_url):

    return (
        urlparse(base_url).netloc
        ==
        urlparse(target_url).netloc
    )