# SPDX-FileCopyrightText: 2023-present Marceau-h <pypi@marceau-h.fr>
#
# SPDX-License-Identifier: AGPL-3.0-or-later
from argparse import ArgumentParser
from pathlib import Path

from . import TkSel, __version__


def main() -> None:
    parser = ArgumentParser(description="Télécharge les vidéos TikTok à partir d'un fichier csv")

    parser.add_argument("csv", help="Le fichier csv contenant les ids des vidéos à télécharger")
    parser.add_argument("output", help="Le dossier de sortie où les vidéos seront enregistrées")

    parser.add_argument("--no-headless", action="store_true", help="Ouvre le navigateur en mode visible")
    parser.add_argument("--no-verify", action="store_true", help="Ignore les erreurs de certificat SSL")
    parser.add_argument("--no-skip", action="store_true", help="Ignore les vidéos déjà téléchargées")
    parser.add_argument("--pedro", action="store_true", help="?")

    parser.add_argument("--sleep-min", type=int, help="Temps d'attente minimum entre chaque téléchargement", default=45)
    parser.add_argument("--sleep-max", type=int, help="Temps d'attente maximum entre chaque téléchargement", default=70)

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    csv = args.csv
    try:
        csv = Path(csv)
        assert csv.is_file() and csv.exists()
    except AssertionError:
        print(f"Le fichier csv {csv} n'existe pas ou n'est pas un fichier valide")
        exit(1)
    except Exception as e:
        print(f"Erreur inattendue: {e} pour le fichier csv {csv}")
        exit(1)

    output = args.output
    try:
        output = Path(output)
        assert not output.is_file()
    except AssertionError:
        print(f"Le dossier de sortie {output} est un fichier, veuillez spécifier un dossier valide")
        exit(1)
    except Exception as e:
        print(f"Erreur inattendue: {e} pour le dossier de sortie {output}")
        exit(1)

    TkSel.from_csv(
        args.csv,
        output,
        headless=not args.no_headless,
        verify=not args.no_verify,
        skip=not args.no_skip,
        sleep_range=(args.sleep_min, args.sleep_max),
        pedro=args.pedro
    )

    print("Téléchargement terminé")
    exit(0)
