import warnings
from pathlib import Path
from random import randint
from time import sleep
from typing import Optional, Tuple, Union

from chromedriver_autoinstaller_fix import install as install_chrome
from requests import Session
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options as COptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import polars as pl

def factory_dodo(a: int = 45, b: int = 70):
    """Factory method to generate a dodo function with a custom sleep range"""
    assert isinstance(a, int) and isinstance(b, int), "a and b must be integers"
    assert a >= 0 and b >= 0, "a and b must be positive integers"
    a, b = (a, b) if a < b else (b, a)

    def dodo(a_: int = a, b_: int = b):
        sleep(randint(a_, b_))

    return dodo


def do_request(session, url, headers, verify: bool = False):
    """On sort les requêtes de la fonction principale pour pouvoir ignorer spécifiquement les warnings
    liés aux certificats SSL (verify=False)
    Demande une session requests.Session(), l'url et les headers en paramètres"""

    warnings.filterwarnings("ignore")
    response = session.get(url, stream=True, headers=headers, allow_redirects=True, verify=verify)
    response.raise_for_status()
    return response


def autoinstall():
    """ Installe automatiquement le driver chrome en fonction de la version de chrome installée
    sur l'ordinateur.
    Fonction séparée pour pouvoir ignorer les warnings liés à l'installation du driver"""
    warnings.filterwarnings("ignore")
    warnings.simplefilter("ignore")

    install_chrome()


class TkSel:
    headers = {
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-US,en;q=0.8',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 '
                      'Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Cache-Control': 'max-age=0', 'Connection': 'keep-alive', 'referer': 'https://www.tiktok.com/'
    }
    def __del__(self):
        if self.driver is not None:
            self.driver.quit()

        if self.pedro:
            self.pedro_process.terminate()
            self.pedro_process.join()
            self.pedro_process.close()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__del__()

    def __enter__(self):
        return self

    def __repr__(self):
        return f"<TkSel object at {id(self)}>"

    def __str__(self):
        return f"<TkSel object at {id(self)}>"

    def __init__(
            self,
            /,
            *args,
            headless: bool = True,
            verify: bool = True,
            skip: bool = True,
            sleep_range: Optional[Tuple[int, int]] = None,
            folder: Optional[Union[str, Path]] = None,
            csv: Optional[Union[str, Path]] = None,
            pedro: bool = False,
            **kwargs
    ):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None

        self.pedro: bool = pedro
        if self.pedro:
            from multiprocessing import Process
            self.pedro_process = Process(target=self.pedro_music)
            self.pedro_process.start()
            print("Pedro is playing")

        self.headless: bool = headless
        self.verify: bool = verify
        self.skip: bool = skip

        if sleep_range is not None:
            self.dodo = factory_dodo(*sleep_range)
        else:
            self.dodo = factory_dodo()

        if isinstance(folder, str):
            folder = Path(folder)
        elif folder is None or isinstance(folder, Path):
            pass
        else:
            raise TypeError("folder must be a string or a Path object")

        self.folder: Optional[Path] = folder

        if self.folder is not None:
            self.folder.mkdir(exist_ok=True, parents=True)

        if csv is not None:
            self.csv = Path(csv)
            if not self.csv.exists():
                raise FileNotFoundError(f"File {self.csv} not found")
            self.meta_path = folder / "meta.csv"
            self.read_csv()
        else:
            self.csv = None
            self.meta_path = None

        self.make_driver()

    def pedro_music(self):
        """Pedro, pedro, pedro-pe, praticamente il meglio di Santa Fe"""
        import vlc
        while True:
            player = vlc.MediaPlayer("pedro.mp3")
            player.play()
            sleep(145)
            player.stop()

    def read_csv(self):
        df = pl.read_csv



    def make_driver(self):
        options = COptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--start-maximized")

        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--mute-audio")

        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        self.driver = webdriver.Chrome(options=options)
        # self.driver.implicitly_wait(10)
        self.driver.get("https://www.tiktok.com/")

        self.wait = WebDriverWait(self.driver, 240)

    def get_video_bytes(self, author_id: str, video_id: str, dodo: bool = False) -> bytes:
        """Récupère le contenu d'une vidéo TikTok en bytes"""
        url = f"https://www.tiktok.com/@{author_id}/video/{video_id}"

        self.driver.get(url)

        sleep(10)

        try:
            self.driver.find_element(By.CSS_SELECTOR, "div.swiper-wrapper")
            print("Not a video (carousel)")
            return b""
        except NoSuchElementException:
            pass

        video = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//video')
            )
        ).get_attribute("src")

        cookies = self.driver.get_cookies()
        s = Session()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])

        response = do_request(s, video, self.headers, verify=self.verify)

        if dodo:
            self.dodo()

        return response.content


if __name__ == '__main__':
    autoinstall()
    tksel = TkSel(pedro=True)
    sleep(10)
    tksel.driver.quit()
