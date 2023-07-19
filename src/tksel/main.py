import sys
from random import randint
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as COptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import requests

import pandas as pd

from pathlib import Path

from tqdm.auto import tqdm
import warnings


def dodo(a: int = 20, b: int = 40):
    sleep(randint(a, b))


def do_request(session, url, headers, verify: bool = False):
    """On sort les requêtes de la fonction principale pour pouvoir ignorer spécifiquement les warnings
    liés aux certificats SSL (verify=False)
    Demande une session requests.Session(), l'url et les headers en paramètres"""

    warnings.filterwarnings("ignore")
    response = session.get(url, stream=True, headers=headers, allow_redirects=True, verify=verify)
    response.raise_for_status()
    return response


def main(
        csv: str | Path,
        output: str | Path,
        *args,
        headless: bool = True,
        verify: bool = False,
        **kwargs
):
    df = pd.read_csv(csv).fillna("")
    id_ = df["id"].tolist()
    author = df["author_unique_id"].tolist()

    folder = Path(output)
    folder.mkdir(exist_ok=True, parents=True)

    headers = {
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-US,en;q=0.8',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'referer': 'https://www.tiktok.com/'
    }

    options = COptions()

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--mute-audio")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 120)

    for i, auth in tqdm(zip(id_, author), total=len(id_)):

        url = f"https://www.tiktok.com/@{auth}/video/{i}"

        driver.get(url)

        sleep(2)

        video = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '/html/body/div[1]/div[2]/div[2]/div/div[2]/div/div[1]/div[1]/div[2]/div/div/div/video')
            )
        ).get_attribute("src")

        cookies = driver.get_cookies()
        s = requests.Session()
        for cookie in cookies:
            s.cookies.set(cookie['name'], cookie['value'])

        # response = s.get(video, stream=True, headers=headers, allow_redirects=True, verify=False)
        response = do_request(s, video, headers, verify=verify)

        with open(folder / f"{i}.mp4", mode='wb') as f:
            f.write(response.content)

        dodo()

    driver.quit()

    meta_path = folder / "meta.csv"

    df_old = pd.read_csv(meta_path).fillna("")
    df_old.update(df)

    df_old.to_csv(meta_path, index=False)


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

    if len(sys.argv) != 3:
        print(f"Usage: python {Path(__file__).name} fichier.csv dossier_de_sortie [--no-headless]")
    else:
        csv_file = sys.argv[1]
        output_folder = sys.argv[2]

        csv_file = Path(csv_file)
        output_folder = Path(output_folder)

        assert csv_file.exists(), f"Le fichier {csv_file.name} n'existe pas"
        assert csv_file.is_file(), f"{csv_file.name} est un dossier, pas un fichier"
        assert csv_file.suffix == ".csv", f"{csv_file.name} n'est pas un fichier csv"
        assert not output_folder.is_file(), f"{output_folder.as_posix()} est un fichier, pas un dossier"

        main(csv_file, output_folder, headless=headless, verify=verify)


if __name__ == "__main__":
    auto_main()
