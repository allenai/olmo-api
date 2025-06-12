# https://stackoverflow.com/a/34073559
class GeneratorWithReturnValue:
    def __init__(self, gen):
        self.gen = gen

    def __iter__(self):
        self.value = yield from self.gen
        return self.value
