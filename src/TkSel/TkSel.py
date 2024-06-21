# SPDX-FileCopyrightText: 2023-present Marceau-h <pypi@marceau-h.fr>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
import warnings
from enum import Enum
from time import sleep
from pathlib import Path
from random import randint
from datetime import datetime
from typing import Optional, Tuple, Union, List, Dict, Any

import polars as pl
from tqdm.auto import tqdm
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


class Status(Enum):
    """Enum to represent the status of a video"""
    SKIPPED = "SKIPPED"
    OK_CARROUSEL = "OK_CARROUSEL"
    OK_VIDEO = "OK_VIDEO"
    ERROR = "ERROR"
    NOT_FOUND = "NOT_FOUND"
    NOT_VIDEO = "NOT_VIDEO"


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
            tqdm: bool = True,
            pedro: bool = False,
            **kwargs
    ) -> None:
        self.to_collect = set()
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.videos: List[Dict[str, Union[str, Optional[datetime]]]] = []

        self.pedro: bool = pedro
        if self.pedro:
            from multiprocessing import Process
            self.pedro_process = Process(target=self.pedro_music)
            self.pedro_process.start()
            print("Pedro is playing")

        self.headless: bool = headless
        self.verify: bool = verify
        self.skip: bool = skip
        self.tqdm: bool = tqdm

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

    def read_csv(self) -> list[dict[str, Any]]:
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
                        for id_, author, timestamp in
                        zip(old_df["video_id"], old_df["author_id"], old_df["collect_timestamp"])
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
    ) -> Tuple[Union[bytes, List[bytes]], Tuple[str, str, Optional[datetime], Status]]:
        """Récupère le contenu d'une vidéo TikTok en bytes"""
        url = f"https://www.tiktok.com/@{author_id}/video/{video_id}"

        self.driver.get(url)

        sleep(10)
        try:
            self.driver.find_element(By.CSS_SELECTOR, "div[class*='DivErrorContainer']")
            print("Can't find video (removed, private, etc.)")
            return b"", (author_id, video_id, None, Status.NOT_FOUND)
        except NoSuchElementException:
            pass

        try:
            self.driver.find_element(By.CSS_SELECTOR, "div.swiper-wrapper")
            print("Not a video (carousel)")
            # return b"", (author_id, video_id, None, Status.NOT_VIDEO)
            carrousel = self.driver.find_elements(By.CSS_SELECTOR, "div.swiper-wrapper > div.swiper-slide")
            video_or_imgs = [slide.find_element(By.CSS_SELECTOR, "img").get_attribute("src") for slide in carrousel]
        except NoSuchElementException:
            video_or_imgs  = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//video')
                )
            ).get_attribute("src")

        cookies = self.driver.get_cookies()
        s = Session()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])

        if isinstance(video_or_imgs, str):
            try:
                response = do_request(s, video_or_imgs, self.headers, verify=self.verify)
                content = response.content
            except ChunkedEncodingError as e:
                print(f"Error with video {video_id} from {author_id}")
                print(e)
                return b"", (author_id, video_id, None, Status.ERROR)
        else:
            content = []
            for idx, img in enumerate(video_or_imgs):
                try:
                    response = do_request(s, img, self.headers, verify=self.verify)
                    content.append(response.content)
                except ChunkedEncodingError as e:
                    print(f"Error with video {video_id} from {author_id}")
                    print(e)
                    return b"", (author_id, video_id, None, Status.ERROR)

        self.videos.append({"video_id": video_id, "author_id": author_id, "collect_timestamp": datetime.now()})

        if dodo:
            self.dodo()

        return content, (
            author_id,
            video_id,
            datetime.now(),
            Status.OK_VIDEO if isinstance(video_or_imgs, str) else Status.OK_CARROUSEL
        )

    def get_video_file(
            self,
            author_id: str,
            video_id: str,
            file_or_folder: Union[Optional[Union[str, Path]]] = None,
            dodo: bool = False,
    ) -> Tuple[Union[Path, List[Path]], Tuple[str, str, Optional[datetime], Status]]:
        """Récupère le contenu d'une vidéo TikTok et l'enregistre dans un fichier"""

        if file_or_folder is not None:
            if isinstance(file_or_folder, (str, Path)):
                if isinstance(file_or_folder, str):
                    file_or_folder = Path(file_or_folder)
                if file_or_folder.is_dir() or (not file_or_folder.suffix and not file_or_folder.exists()):
                    file_or_folder = file_or_folder / f"{author_id}_{video_id}.mp4"

            else:
                raise TypeError("file_or_folder must be a string or a Path object")

        content, tup = self.get_video_bytes(author_id, video_id, dodo)

        if not content:
            return Path(), tup

        if isinstance(content, list):
            for idx, img in enumerate(content):
                this_file = file_or_folder.parent / (file_or_folder.stem + f"_{idx}.jpeg")
                with this_file.open(mode='wb') as f:
                    f.write(img)
        else:
            with file_or_folder.open(mode='wb') as f:
                f.write(content)

        return file_or_folder, tup

    def get_videos_bytes(
            self,
            author_ids: list[str],
            video_ids: list[str],
            dodo: bool = False
    ) -> List[Tuple[Union[bytes], Tuple[str, str, Optional[datetime], Status]]]:
        """Récupère le contenu de plusieurs vidéos TikTok en bytes"""
        assert len(author_ids) == len(video_ids), "author_ids and video_ids must have the same length"

        if self.tqdm:
            it = tqdm(zip(author_ids, video_ids), total=len(author_ids))
        else:
            it = zip(author_ids, video_ids)

        return [
            self.get_video_bytes(author_id, video_id, dodo)
            for author_id, video_id in it
        ]


    def get_videos_files(
            self,
            author_ids: list[str],
            video_ids: list[str],
            files_or_folder: Union[Optional[Union[str, Path]], Optional[list[Union[str, Path]]]] = None,
            dodo: bool = False
    ) -> List[Tuple[Path, Tuple[str, str, Optional[datetime], Status]]]:
        """Récupère le contenu de plusieurs vidéos TikTok et les enregistre dans des fichiers"""
        assert len(author_ids) == len(video_ids), "author_ids and video_ids must have the same length"

        if files_or_folder is not None:
            if isinstance(files_or_folder, (str, Path)):
                if isinstance(files_or_folder, str):
                    files_or_folder = Path(files_or_folder)
                assert files_or_folder.is_dir(), "file_or_folder must be a directory if a single Path is given"
                if not files_or_folder.exists():
                    files_or_folder.mkdir(parents=True)

                files_or_folder = [
                    files_or_folder / f"{author_id}_{video_id}.mp4"
                    for author_id, video_id in zip(author_ids, video_ids)
                ]
            elif isinstance(files_or_folder, list):
                if len(files_or_folder) != len(author_ids):
                    raise ValueError("author_ids , video_ids and files must have the same length")
                if not all(isinstance(file, (str, Path)) for file in files_or_folder):
                    raise TypeError("files must be a string, a Path object or a list of strings or Path objects")
                files_or_folder = [Path(file) for file in files_or_folder]
            else:
                raise TypeError("files must be a string, a Path object or a list of strings or Path objects")
        else:
            files_or_folder = [None] * len(author_ids)

        if self.tqdm:
            it = tqdm(zip(author_ids, video_ids, files_or_folder), total=len(author_ids))
        else:
            it = zip(author_ids, video_ids, files_or_folder)

        return [
            self.get_video_file(author_id, video_id, file, dodo)
            for author_id, video_id, file in it
        ]

    def get_videos_from_self_bytes(
            self,
            dodo: bool = False,
    ) -> list[Tuple[Union[bytes, Path], Tuple[str, str, Optional[datetime], Status]]]:
        self.to_collect = {
            (video["video_id"], video["author_id"])
            for idx, video in enumerate(self.videos)
            if (video["video_id"], video["author_id"]) in self.to_collect
               and (video["collect_timestamp"] is None or not self.skip)
        }
        v_ids, a_ids = zip(*self.to_collect)
        return self.get_videos_bytes(
            list(a_ids),
            list(v_ids),
            dodo,
        )

    def get_videos_from_self_files(
            self,
            dodo: bool = False,
    ) -> list[Tuple[Path, Tuple[str, str, Optional[datetime], Status]]]:
        self.to_collect = {
            (video["video_id"], video["author_id"])
            for idx, video in enumerate(self.videos)
            if (video["video_id"], video["author_id"]) in self.to_collect
               and (video["collect_timestamp"] is None or not self.skip)
        }
        v_ids, a_ids = zip(*self.to_collect)
        return self.get_videos_files(
            list(a_ids),
            list(v_ids),
            dodo=dodo
        )

    def get_videos_from_csv_bytes(
            self,
            csv: Union[str, Path],
            dodo: bool = False,
    ) -> List[tuple[Union[bytes, Path], Tuple[str, str, Optional[datetime], Status]]]:
        """Récupère le contenu de plusieurs vidéos TikTok à partir d'un fichier CSV"""
        self.csv = Path(csv)
        self.read_csv()

        return self.get_videos_from_self_bytes(dodo=dodo)

    def get_videos_from_csv_files(
            self,
            csv: Union[str, Path],
            dodo: bool = False,
    ) -> List[tuple[Path, Tuple[str, str, Optional[datetime], Status]]]:
        """Récupère le contenu de plusieurs vidéos TikTok à partir d'un fichier CSV"""
        self.csv = Path(csv)
        self.read_csv()

        return self.get_videos_from_self_files(dodo=dodo)

    def auto_main(self) -> list[dict[str, Union[str, Optional[datetime]]]]:
        """Fonction principale pour télécharger les vidéos TikTok"""
        if self.folder is None:
            raise ValueError("No folder specified")

        if self.meta_path is None:
            raise ValueError("No meta file specified")

        if self.csv is None:
            raise ValueError("No CSV file specified")

        self.get_videos_from_self_files(dodo=True)

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
    ) -> list[dict[str, Union[str, Optional[datetime]]]]:
        with cls(
                csv=csv,
                folder=folder,
                headless=headless,
                verify=verify,
                skip=skip,
                sleep_range=sleep_range,
                pedro=pedro,
        ) as tksel:
            return tksel.auto_main()


if __name__ == '__main__':
    autoinstall()
    with TkSel(pedro=True, headless=False, skip=False, folder="../../videos", csv="../../meta.csv", sleep_range=(60, 80)) as tksel:
        # tksel.auto_main()
        tksel.get_video_file("lamethodeantoine", "7374863570082762026", "../../videos/antoine.mp4", dodo=True)
        sleep(10)
    sleep(10)
    print("Done")
