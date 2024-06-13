# SPDX-FileCopyrightText: 2023-present Marceau-h <106751184+Marceau-h@users.noreply.github.com>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import warnings
from enum import Enum
from time import sleep
from pathlib import Path
from random import randint
from datetime import datetime
from typing import Optional, Tuple, Union, List, Generator, Dict, Any

import polars as pl
from requests import Session
from requests.exceptions import ChunkedEncodingError
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.chrome.options import Options as COptions
from chromedriver_autoinstaller_fix import install as install_chrome


def factory_dodo(a: int = 45, b: int = 70):
    """Factory method to generate a dodo function with a custom sleep range"""
    assert isinstance(a, int) and isinstance(b, int), "a and b must be integers"
    assert a >= 0 and b >= 0, "a and b must be positive integers"
    a, b = (a, b) if a < b else (b, a)

    def dodo(a_: int = a, b_: int = b):
        sleep(randint(a_, b_))

    return dodo


def do_request(
        session: Session,
        url: str,
        headers: Dict[str, str],
        verify: bool = False
):
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

    def __del__(self) -> None:
        if self.driver is not None:
            self.driver.quit()

        if self.pedro:
            self.pedro_process.terminate()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.__del__()

    def __enter__(self) -> "TkSel":
        return self

    def __repr__(self) -> str:
        return f"<TkSel object at {id(self)}>"

    def __str__(self) -> str:
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
        self.to_collect = set()
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.videos: List[Dict[str, str, Optional[datetime]]] = []


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
            player = vlc.MediaPlayer(Path(__file__).parent / "pedro.mp3")
            player.play()
            sleep(145)
            player.stop()


    def read_csv(self) -> dict[Any, dict[str, Any]]:
        """Lit le fichier CSV et renvoie un DataFrame Polars"""
        with pl.Config(auto_structify=True):
            df = pl.read_csv(self.csv).fill_nan("")
            if "id" in df.columns and "video_id" not in df.columns:
                df = df.rename({"id": "video_id"})
            if "author_unique_id" in df.columns:
                if "author_id" in df.columns:
                    df.drop_in_place("author_id")
                df = df.rename({"author_unique_id": "author_id"})
            if "collect_timestamp" in df.columns:
                timestamps = df["collect_timestamp"].to_list()
            else:
                timestamps = [None] * len(df)

            ids = df["video_id"].to_list()
            authors = df["author_id"].to_list()

            self.to_collect = {
                (id_, author)
                for id_, author in zip(ids, authors)
            }

            self.videos = [
                {"video_id": id_, "author_id": author, "collect_timestamp": timestamp}
                for id_, author, timestamp in zip(ids, authors, timestamps)
            ]

            if self.meta_path is not None and self.meta_path.exists():
                old_df = pl.read_csv(
                    self.meta_path,
                    schema={"video_id": pl.Int64, "author_id": pl.String, "collect_timestamp": pl.Datetime}
                )
                old_df.filter(
                    pl.col("collect_timestamp").is_not_null()
                )
                self.videos.extend(
                    [
                        {"video_id": id_, "author_id": author, "collect_timestamp": timestamp}
                        for id_, author, timestamp in zip(old_df["video_id"], old_df["author_id"], old_df["collect_timestamp"])
                    ]
                )

            return self.videos

    def write_csv(self, df: Optional[pl.DataFrame] = None) -> None:
        """Écrit le DataFrame dans un fichier CSV à coté des vidéos (si un dossier de sortie a été spécifié)"""
        if self.meta_path is None:
            raise ValueError("No folder specified")

        if df is None:
            with pl.Config(auto_structify=True):
                df = pl.DataFrame(
                    self.videos,
                    schema={"video_id": pl.Int64, "author_id": pl.String, "collect_timestamp": pl.Datetime}
                )

        df.filter(
            pl.col("collect_timestamp").is_not_null()
        )

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

    def get_video_bytes(
            self,
            author_id: str,
            video_id: str,
            dodo: bool = False
    ) -> Tuple[bytes, Tuple[str, str, Optional[datetime]]]:
        """Récupère le contenu d'une vidéo TikTok en bytes"""
        url = f"https://www.tiktok.com/@{author_id}/video/{video_id}"

        self.driver.get(url)

        sleep(10)

        try:
            self.driver.find_element(By.CSS_SELECTOR, "div.swiper-wrapper")
            print("Not a video (carousel)")
            return b"", (author_id, video_id, None)
        except NoSuchElementException:
            pass

        try:
            self.driver.find_element(By.CSS_SELECTOR, "div[class*='DivErrorContainer']")
            print("Can't find video (removed, private, etc.)")
            return b"", (author_id, video_id, None)
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

        try:
            response = do_request(s, video, self.headers, verify=self.verify)
            content = response.content
        except ChunkedEncodingError as e:
            print(f"Error with video {video_id} from {author_id}")
            print(e)
            return b"", (author_id, video_id, None)

        self.videos.append({"video_id": video_id, "author_id": author_id, "collect_timestamp": datetime.now()})

        if dodo:
            self.dodo()

        return content, (author_id, video_id, datetime.now())

    def get_video_file(
            self,
            author_id: str,
            video_id: str,
            dodo: bool = False,
            file: Optional[Union[str, Path]] = None
    ) -> Tuple[Path, Tuple[str, str, datetime]]:
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

        if not content:
            return Path(), tup

        with file.open(mode='wb') as f:
            f.write(content)

        return file, tup

    def get_video(
            self,
            author_id: str,
            video_id: str,
            dodo: bool = False,
            mode: Mode = Mode.BYTES
    ) -> tuple[Union[bytes, Path], tuple[str, str, datetime]]:
        """Récupère le contenu d'une vidéo TikTok"""
        func = self.get_video_bytes if mode == "bytes" else self.get_video_file
        return func(author_id, video_id, dodo)

    def get_videos(
            self,
            author_ids: list[str],
            video_ids: list[str],
            dodo: bool = False,
            mode: Mode = Mode.BYTES
    ) -> list[Tuple[Union[bytes, Path], Tuple[str, str, datetime]]]:
        """Récupère le contenu de plusieurs vidéos TikTok"""
        assert len(author_ids) == len(video_ids), "author_ids and video_ids must have the same length"

        func = self.get_video_bytes if mode == "bytes" else self.get_video_file

        data = []
        for author_id, video_id in zip(author_ids, video_ids):
            data.append(func(author_id, video_id, dodo))

        return data

    def get_videos_from_self(
            self,
            dodo: bool = False,
            mode: Mode = Mode.BYTES
    ) -> list[Tuple[Union[bytes, Path], Tuple[str, str, datetime]]]:
        self.to_collect = {
            (video["video_id"], video["author_id"])
            for idx, video in enumerate(self.videos)
            if (video["video_id"], video["author_id"]) in self.to_collect
            and (video["collect_timestamp"] is None or not self.skip)
        }
        v_ids, a_ids = zip(*self.to_collect)
        return self.get_videos(
            list(a_ids),
            list(v_ids),
            dodo,
            mode
        )

    def get_videos_from_csv(
            self,
            csv: Union[str, Path],
            dodo: bool = False,
            mode: Mode = Mode.BYTES
    ) -> List[tuple[Union[bytes, Path], tuple[str, str, datetime]]]:
        """Récupère le contenu de plusieurs vidéos TikTok à partir d'un fichier CSV"""
        self.csv = Path(csv)
        self.read_csv()

        return self.get_videos_from_self(dodo, mode)

    def auto_main(self) -> list[dict[str, str, Optional[datetime]]]:
        """Fonction principale pour télécharger les vidéos TikTok"""
        if self.folder is None:
            raise ValueError("No folder specified")

        if self.meta_path is None:
            raise ValueError("No meta file specified")

        if self.csv is None:
            raise ValueError("No CSV file specified")

        self.get_videos_from_self(dodo=True, mode=Mode.FILE)

        self.write_csv()

        print(
            f"Les vidéos ont été téléchargées et enregistrées dans {self.folder}, "
            f"avec le fichier de métadonnées {self.meta_path}"
        )

        return self.videos

    def quit(self) -> None:
        self.__del__()

    @classmethod
    def from_csv(
            cls,
            csv: Union[str, Path],
            folder: Union[str, Path],
            headless: bool = True,
            verify: bool = True,
            skip: bool = True,
            sleep_range: Optional[Tuple[int, int]] = None,
            pedro: bool = False
    ) -> list[dict[str, str, datetime | None]]:
        with cls(csv=csv, folder=folder, headless=headless, verify=verify, skip=skip, sleep_range=sleep_range, pedro=pedro) as tksel:
            return tksel.auto_main()

if __name__ == '__main__':
    autoinstall()
    with TkSel(pedro=True, headless=False, folder="../../videos", csv="../../meta.csv", sleep_range=(60, 80)) as tksel:
        tksel.auto_main()
        sleep(10)
    sleep(10)
    print("Done")
