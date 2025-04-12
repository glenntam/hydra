from collections import defaultdict


class EventManager:
    def __init__(self):
        self.subscribers = defaultdict(list)

    def subscribe(self, event_name, handler):
        self.subscribers[event_name].append(handler)

    def unsubscribe(self, event_name, handler):
        if handler in self.subscribers[event_name]:
            self.subscribers[event_name].remove(handler)

    def publish(self, event_name, payload):
        for each_event in self.subscribers[event_name]:
            each_event(payload)


event_manager = EventManager()
