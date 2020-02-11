def tag_only(tag):
    if '{' in tag:
        return tag[:tag.find('{')]
    else:
        return tag