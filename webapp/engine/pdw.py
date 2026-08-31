"""Minimal Pd patch writer: keeps object indices straight so hand-written
netlists stop being a guessing game."""

class Patch:
    def __init__(self, w=900, h=700):
        self.lines = ["#N canvas 0 0 %d %d 10;" % (w, h)]
        self.n = 0
        self.conns = []

    def obj(self, text, x=None, y=None):
        x = 20 if x is None else x
        y = 20 + self.n * 24 if y is None else y
        self.lines.append("#X obj %d %d %s;" % (x, y, text))
        self.n += 1
        return self.n - 1

    def msg(self, text, x=None, y=None):
        # a bare ";" in a message box ends the FILE record and the remainder is
        # read as a top-level message to pd - which silently quits the render.
        text = text.replace(";", "\\;").replace(",", "\\,")
        x = 300 if x is None else x
        y = 20 + self.n * 24 if y is None else y
        self.lines.append("#X msg %d %d %s;" % (x, y, text))
        self.n += 1
        return self.n - 1

    def c(self, a, ao, b, bo):
        self.conns.append("#X connect %d %d %d %d;" % (a, ao, b, bo))

    def write(self, path):
        with open(path, "w") as f:
            f.write("\n".join(self.lines + self.conns) + "\n")
