import threading
import time

from app.logger import logger
from app.db.base import Base
from app.db.database import engine
from app.scrape.authentication import get_aspxauth, periodically_update_aspxauth
from app.scrape.courts import CourtsAPI

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    time.sleep(3)

    aspxauth_container = {"ASPXAUTH": get_aspxauth()}
    logger.info(f"ASPXAUTH: {aspxauth_container['ASPXAUTH']}")

    # Run ASPXAUTH update every 10 minutes in a separate thread
    update_aspxauth_thread = threading.Thread(target=periodically_update_aspxauth, args=(30, aspxauth_container))
    update_aspxauth_thread.daemon = True
    update_aspxauth_thread.start()

    courts_scraper = CourtsAPI()

    get_courts_thread = threading.Thread(target=courts_scraper.get_courts_recursively, args=(aspxauth_container,))
    get_courts_thread.daemon = True
    get_courts_thread.start()

    while True:
        pass

