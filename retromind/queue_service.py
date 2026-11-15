"""GUI-independent queue state; no playback or persistence side effects."""
import random


class PlayQueue:
    def __init__(self, shuffle=False, repeat='off', rng=None):
        self.items = []
        self.index = -1
        self.shuffle = shuffle
        self.repeat = repeat if repeat in ('off', 'all', 'one') else 'off'
        self.rng = rng or random.Random()
        self.original = []

    @property
    def current(self):
        return self.items[self.index] if 0 <= self.index < len(self.items) else None

    def start(self, items, current):
        self.original = list(dict.fromkeys(items))
        if current not in self.original:
            self.original.insert(0, current)
        self.items = self.original.copy()
        if self.shuffle:
            self.items.remove(current)
            self.rng.shuffle(self.items)
            self.items.insert(0, current)
        self.index = self.items.index(current)
        return current

    def set_shuffle(self, enabled):
        current = self.current
        self.shuffle = enabled
        if current is not None:
            self.start(self.original, current)

    def advance(self, direction=1, automatic=False):
        if not self.items:
            return None
        if automatic and self.repeat == 'one':
            return self.current
        target = self.index + direction
        if not 0 <= target < len(self.items):
            if self.repeat == 'all':
                target %= len(self.items)
            else:
                return None
        self.index = target
        return self.current

    def remove(self, track_id):
        if track_id == self.current or track_id not in self.items:
            return
        index = self.items.index(track_id)
        self.items.pop(index)
        self.original = [item for item in self.original if item != track_id]
        if index < self.index:
            self.index -= 1

    def select(self, track_id):
        if track_id in self.items:
            self.index = self.items.index(track_id)
            return track_id
        return None

    @property
    def upcoming(self):
        return self.items[self.index + 1:]
