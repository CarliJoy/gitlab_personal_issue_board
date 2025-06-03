# Gitlab Personal Issue Board

[![PyPI - Version](https://img.shields.io/pypi/v/gitlab-personal-issue-board.svg)](https://pypi.org/project/gitlab-personal-issue-board)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gitlab-personal-issue-board.svg)](https://pypi.org/project/gitlab-personal-issue-board)

-----

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Installation

Before using the program, you need to [configure `python-gitlab`](https://python-gitlab.readthedocs.io/en/stable/cli-usage.html#configuration-file-format).

To do this, [create a personal access token](https://docs.gitlab.com/user/profile/personal_access_tokens/#create-a-personal-access-token) with at least *api* permissions and add it to the `~/.python-gitlab.cfg` file like this:

```ini
[global]
default = personal
ssl_verify = true  # alternative path to CA file

[personal]
url = https://gitlab.com
private_token = <your access token>
```

⚠️ Instead of storing your access token in plain text, it is strongly recommended to use a [credential helper](https://python-gitlab.readthedocs.io/en/stable/cli-usage.html#credential-helpers).

It is recommended to use [uv](https://docs.astral.sh/uv/getting-started/installation/) to install and run `gitlab-personal-issue-board`:

```console
uvx gitlab-personal-issue-board
```

## Usage

After launching the application, some debug information is printed. A local web server powered by [NiceGUI](https://nicegui.io/) is started and automatically opened in your browser.

First, click *Add new label board*. This creates a new issue board and opens a configuration page.
While the page is opening, all issues assigned to you are loaded, which may take some time.
This step ensures that all available labels are shown.

All loaded issues are cached. After this initial load, only updated issues are retrieved.

Once the page has loaded, you can drag and drop the desired labels from the right side to the left, between the *Opened* and *Closed* sections.
After selecting the desired labels, click *Save and View* to see your board.

Now you can move issues from one column to another just like in a standard GitLab board.

## License

`gitlab-personal-issue-board` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
