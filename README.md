# tksel 

[![PyPI - Version](https://img.shields.io/pypi/v/tksel.svg)](https://pypi.org/project/tksel)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tksel.svg)](https://pypi.org/project/tksel)

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)
- [Description](#description)
- [Usage](#usage)
  - [Example](#example)

## Installation

```console
pip install tksel
```

## License

`tksel` is distributed under the terms of the [AGPLv3 license](https://www.gnu.org/licenses/agpl-3.0.en.html).

## Description

`tksel` is a Python package that provides tool to recover videos from TikTok.
It is intended to be used on the csvs generated by [Minet](https://github.com/medialab/minet) but will work on any csv with the right columns:
- `id` (the id of the video), alias `video_id`
- `author_unique_id` (the id of the author), alias `author_id`

## Usage

```bash
tksel input.csv output_folder [--no-headless] [--no-verify]
```

- `input.csv` is the csv generated by minet or any csv with the right columns
- `output_folder` is the folder where the videos will be downloaded, it will be created if it doesn't exist, the input csv will also be copied there
- `--no-headless` is an optional argument to display the browser while it is downloading the videos
- `--no-verify` is an optional argument to disable the verification of the requests.get()

### Example

```bash
tksel temp.csv videos-collecte1 --no-headless --no-verify
```

