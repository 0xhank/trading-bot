#!/usr/bin/env python3
import os
import sys
import subprocess
import signal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from lib.logger import default_logger as logger


class RestartHandler(FileSystemEventHandler):
    def __init__(self, command):
        self.command = command
        self.process = None
        self.start_process()
        
    def start_process(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                
        logger.info(f"Starting: {' '.join(self.command)}")
        self.process = subprocess.Popen(self.command)
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        if event.src_path.endswith('.py'):
            logger.info(f"File changed: {event.src_path}")
            logger.info("Restarting process...")
            self.start_process()


def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python watch.py <command> [args...]")
        sys.exit(1)
        
    command = sys.argv[1:]
    handler = RestartHandler(command)
    
    observer = Observer()
    observer.schedule(handler, path='src', recursive=True)
    observer.start()
    
    logger.info("Watching for file changes in src/ directory...")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.warning("Stopping...")
        observer.stop()
        if handler.process:
            handler.process.terminate()
            try:
                handler.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                handler.process.kill()
    
    observer.join()


if __name__ == "__main__":
    main()