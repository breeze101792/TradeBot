

class StockID:
    code = None
    name = None
    def __init__(self, code=None, name=None):
        self.code = code
        self.name = name
    def __str__(self):
        return "{}({})".format(self.name, self.code)
