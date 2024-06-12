import warnings
from pathlib import Path
from random import randint
from time import sleep
from typing import Optional, Tuple, Union
from enum import Enum
from datetime import datetime

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


class Mode(Enum):
    BYTES = "bytes"
    FILE = "file"


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
    ) -> None:
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.df: pl.DataFrame = pl.DataFrame(schema={"video_id": pl.Int64, "author_id": pl.String, "collect_timestamp": pl.Datetime})

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
            self.meta_path = folder / "meta.csv"
        else:
            self.meta_path = None

        if csv is not None:
            self.csv = Path(csv)
            if not self.csv.exists():
                raise FileNotFoundError(f"File {self.csv} not found")
            self.read_csv()
        else:
            self.csv = None
            self.meta_path = None

        self.make_driver()

    def pedro_music(self) -> None:
        """Pedro, pedro, pedro-pe, praticamente il meglio di Santa Fe"""
        import vlc
        while True:
            player = vlc.MediaPlayer("pedro.mp3")
            player.play()
            sleep(145)
            player.stop()

    def read_csv(self) -> pl.DataFrame:
        """Lit le fichier CSV et renvoie un DataFrame Polars"""
        with pl.Config(auto_structify=True):
            self.df = pl.read_csv(self.csv).fill_nan("")
            if "id" in self.df.columns:
                self.df = self.df.rename({"id": "video_id"})
            if "author_unique_id" in self.df.columns:
                self.df = self.df.rename({"author_unique_id": "author_id"})
            if "collect_timestamp" not in self.df.columns:
                self.df = self.df.with_columns(pl.Series("collect_timestamp", [datetime.fromtimestamp(0)] * len(self.df)))
            return self.df.select(["video_id", "author_id", "collect_timestamp"])

    def write_csv(self, df: pl.DataFrame) -> None:
        """Écrit le DataFrame dans un fichier CSV à coté des vidéos (si un dossier de sortie a été spécifié)"""
        if self.meta_path is None:
            raise ValueError("No folder specified")

        if self.meta_path.exists():
            old_df = pl.read_csv(self.meta_path)
            df = old_df.vstack(df)

        df.write_csv(self.meta_path)

    def make_driver(self) -> webdriver.Chrome:
        """Initialise le driver Chrome et ouvre la page TikTok"""
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

        return self.driver

    def get_video_bytes(self, author_id: str, video_id: str, dodo: bool = False) -> Tuple[bytes, Tuple[str, str]]:
        """Récupère le contenu d'une vidéo TikTok en bytes"""
        url = f"https://www.tiktok.com/@{author_id}/video/{video_id}"

        self.driver.get(url)

        sleep(10)

        try:
            self.driver.find_element(By.CSS_SELECTOR, "div.swiper-wrapper")
            print("Not a video (carousel)")
            return b"", (author_id, video_id, datetime.now())
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

        # self.df.vstack(pl.DataFrame(
        #     {"author_id": [author_id], "video_id": [video_id], "collect_timestamp": [datetime.now()]}), in_place=True)

        tup = (author_id, video_id, datetime.now())

        self.df.row(len(self.df)) = tup

        if dodo:
            self.dodo()

        return response.content, tup

    def get_video_file(self, author_id: str, video_id: str, dodo: bool = False,
                       file: Optional[Union[str, Path]] = None) -> Tuple[Path, Tuple[str, str]]:
        """Récupère le contenu d'une vidéo TikTok et l'enregistre dans un fichier"""

        if isinstance(file, str):
            file = Path(file)
        elif file is None and self.folder is not None:
            file = self.folder / f"{video_id}.mp4"
        elif isinstance(file, Path):
            pass
        else:
            raise TypeError("file must be a string or a Path object or a folder must be specified")

        if file.exists() and self.skip:
            return file, (author_id, video_id, datetime.now())

        content, tup = self.get_video_bytes(author_id, video_id, dodo)

        with file.open(mode='wb') as f:
            f.write(content)

        return file, tup

    def get_video(self, author_id: str, video_id: str, dodo: bool = False, mode: Mode = Mode.BYTES) -> Union[
        bytes, Path]:
        """Récupère le contenu d'une vidéo TikTok"""
        func = self.get_video_bytes if mode == "bytes" else self.get_video_file
        return func(author_id, video_id, dodo)

    def get_videos(self, author_ids: list[str], video_ids: list[str], dodo: bool = False, mode: Mode = Mode.BYTES) -> \
            list[Tuple[Union[bytes, Path], Tuple[str, str]]]:
        """Récupère le contenu de plusieurs vidéos TikTok"""
        assert len(author_ids) == len(video_ids), "author_ids and video_ids must have the same length"

        func = self.get_video_bytes if mode == "bytes" else self.get_video_file

        data = []
        for author_id, video_id in zip(author_ids, video_ids):
            data.append(func(author_id, video_id, dodo))

        return data

    def get_videos_from_self(self, dodo: bool = False, mode: Mode = Mode.BYTES) -> list[
        Tuple[Union[bytes, Path], Tuple[str, str]]]:
        """Récupère le contenu de plusieurs vidéos TikTok à partir d'un fichier CSV"""
        return self.get_videos(self.df["author_id"], self.df["video_id"], dodo, mode)

    def get_videos_from_csv(self, csv: Union[str, Path], dodo: bool = False, mode: Mode = Mode.BYTES) -> list[
        Tuple[Union[bytes, Path], Tuple[str, str]]]:
        """Récupère le contenu de plusieurs vidéos TikTok à partir d'un fichier CSV"""
        self.csv = Path(csv)
        self.read_csv()

        return self.get_videos_from_self()

    def auto_main(self):
        """Fonction principale pour télécharger les vidéos TikTok"""
        if self.folder is None:
            raise ValueError("No folder specified")

        if self.meta_path is None:
            raise ValueError("No meta file specified")

        if self.csv is None:
            raise ValueError("No CSV file specified")

        self.get_videos_from_self(dodo=True, mode=Mode.FILE)

        self.write_csv(self.df)

        print(
            f"Les vidéos ont été téléchargées et enregistrées dans {self.folder}, avec le fichier de métadonnées {self.meta_path}")

        return self.df

    def quit(self):
        self.__del__()


if __name__ == '__main__':
    autoinstall()
    with TkSel(pedro=False, headless=False, folder="videos", csv="videos.csv", sleep_range=(10, 20)) as tksel:
        tksel.auto_main()
        sleep(10)
    sleep(10)
    print("Done")
