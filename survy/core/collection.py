class Collection:
    items = {}
    by_type = {}

    def __init__(self):
        pass

    def add(self, key, item, item_type='_'):
        if item_type not in self.by_type.keys():
            self.by_type[item_type] = []

        self.items[key] = item
        self.by_type[item_type].append(key)

    def get(self, key):
        if key in self.items:
            return self.items[key]

        return None

    def get_list(self, item_type=None):
        if item_type is None:
            return self.items.keys()

        return self.by_type[item_type]
