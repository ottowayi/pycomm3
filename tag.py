class TagException(Exception):
    pass

class Tag(object):
    def __init__(self):
        self._attributes = {}
        self.name = None
        self.type = None
        self.value = None
        self.status = 0
        self.update_time = 1000
        self.path = None
        self.driver = None

    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.name == other.name \
                and self.type == other.type \
                and self.path == other.path \
                and self.driver == other.driver \
                and self._attributes == other._attributes
        return False

    def setup(self, name, typ, path, driver):
        self.name = name
        self.type = typ
        self.path = path
        self.driver = driver

    def get_attribute(self, atr):
        if atr in self._attributes:
            return self._attributes[atr]
        raise TagException('The tag attribute inquired dose not exist')

    def update_attributes(self, attributes):
        if isinstance(attributes, dict):
            self._attributes.update(attributes)
            return True
        return False

    def remove_attribute(self, item):
        if item in self._attributes:
            del self._attributes[item]
            return True
        return False

    def is_valid(self):
        if self.name is None \
                or self.type is None \
                or self.path is None \
                or self.driver is None:
            return False
        return True



