import sys
from random import randint
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as COptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from chromedriver_autoinstaller_fix import install as install_chrome

import requests

import pandas as pd

from pathlib import Path

from tqdm.auto import tqdm
import warnings


def dodo(a: int = 45, b: int = 70):
    sleep(randint(a, b))


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



def main(
        csv: str | Path,
        output: str | Path,
        *args,
        headless: bool = True,
        verify: bool = False,
        skip: bool = True,
        **kwargs
):
    autoinstall()

    df = pd.read_csv(csv).fillna("")
    try:
        id_ = df["id"].tolist()
    except KeyError:
        id_ = df["video_id"].tolist()
    try:
        author = df["author_unique_id"].tolist()
    except KeyError:
        author = df["author_id"].tolist()

    folder = Path(output)
    folder.mkdir(exist_ok=True, parents=True)

    headers = {
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-US,en;q=0.8',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 '
                      'Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'referer': 'https://www.tiktok.com/'
    }

    options = COptions()

    options.add_argument("--no-sandbox")
    options.add_argument("--start-maximized")

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--mute-audio")

    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    with webdriver.Chrome(options=options) as driver:
        driver.get("https://www.tiktok.com/")

        wait = WebDriverWait(driver, 240)

        pbar = tqdm(zip(id_, author), total=len(id_))

        for i, auth in pbar:
            pbar.set_description(f"Video_id = {i}, author = {auth}")

            file = folder / f"{i}.mp4"
            if file.exists() and skip:
                continue

            url = f"https://www.tiktok.com/@{auth}/video/{i}"

            driver.get(url)

            sleep(10)

            try:
                driver.find_element(By.CSS_SELECTOR, "div.swiper-wrapper")
                continue
            except:
                pass

            video = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//video')
                )
            ).get_attribute("src")

            cookies = driver.get_cookies()
            s = requests.Session()
            for cookie in cookies:
                s.cookies.set(cookie['name'], cookie['value'])

            # response = s.get(video, stream=True, headers=headers, allow_redirects=True, verify=False)
            response = do_request(s, video, headers, verify=verify)

            with file.open(mode='wb') as f:
                f.write(response.content)

            dodo()

    meta_path = folder / "meta.csv"

    if meta_path.exists():
        df_old = pd.read_csv(meta_path).fillna("")
        df_old.update(df)
        df = df_old

    df.to_csv(meta_path, index=False)

    print(f"Les vidéos ont été téléchargées et enregistrées dans {folder}, avec le fichier de métadonnées {meta_path}")

    return df


def auto_main():
    if "--no-headless" in sys.argv:
        headless = False
        sys.argv.remove("--no-headless")
    else:
        headless = True

    if "--no-verify" in sys.argv:
        verify = False
        sys.argv.remove("--no-verify")
    else:
        verify = True

    if "--no-skip" in sys.argv:
        skip = False
        sys.argv.remove("--no-skip")
    else:
        skip = True

    if len(sys.argv) != 3:
        print(f"Usage: python {Path(__file__).name} fichier.csv dossier_de_sortie "
              "[--no-headless] [--no-verify] [--no-skip]")
    else:
        csv_file = sys.argv[1]
        output_folder = sys.argv[2]

        csv_file = Path(csv_file)
        output_folder = Path(output_folder)

        assert csv_file.exists(), f"Le fichier {csv_file.name} n'existe pas"
        assert csv_file.is_file(), f"{csv_file.name} est un dossier, pas un fichier"
        assert csv_file.suffix == ".csv", f"{csv_file.name} n'est pas un fichier csv"
        assert not output_folder.is_file(), f"{output_folder.as_posix()} est un fichier, pas un dossier"

        main(csv_file, output_folder, headless=headless, verify=verify, skip=skip)


if __name__ == "__main__":
    auto_main()
