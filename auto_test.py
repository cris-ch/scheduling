import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TestHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('scheduling.py'):
            print("Change detected in scheduling.py. Running tests...")
            subprocess.run(['python', '-m', 'unittest', 'test_scheduling.py'])

if __name__ == "__main__":
    event_handler = TestHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()