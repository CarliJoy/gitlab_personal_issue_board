# Gitlab Personal Issue Board

[![PyPI - Version](https://img.shields.io/pypi/v/gitlab-personal-issue-board.svg)](https://pypi.org/project/gitlab-personal-issue-board)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gitlab-personal-issue-board.svg)](https://pypi.org/project/gitlab-personal-issue-board)

-----

## Table of Contents

- [Installation](#installation)
- [License](#license)

## Installation
Before using the program you need to [configure python-gitlab](https://python-gitlab.readthedocs.io/en/stable/cli-usage.html#configuration-file-format).

To do this [create a personal access token](https://docs.gitlab.com/user/profile/personal_access_tokens/#create-a-personal-access-token) with at least *api* permissions and add it to the `~/.python-gitlab.cfg` file like this:

```ini
[global]
default = personal
ssl_verify = true  # alternative Path to CA file

[personal]
url = https://gitlab.com
private_token = <your access token>
```

⚠️ Instead of adding your access token in plain text you are strongly advised to use a [credential helper](https://python-gitlab.readthedocs.io/en/stable/cli-usage.html#credential-helpers)

It is recommended to use [uv](https://docs.astral.sh/uv/getting-started/installation/) to install and run gitlab-personal-issue-board.

```console
uvx gitlab-personal-issue-board
```

# Usage

After starting some debug information is printed, a local webserver with [NiceGUI](https://nicegui.io/) is started and opened in the browser.
First you need *Add new label board*. This creates a new issue board and open a page to configure it.
During opening this pages all issues assigned to you are loaded, so this can take a while.
This is required to show you all available labels.
All loaded issues are cached and only issues changed are loaded afterwards.

Once the page is loaded, you can drag and drop wanted to labels from the right side to the left side between *Opened* and *Closed*.
After you selected the wanted labels, click on *Save and View*, to see the board.

Now you can move Issues from one column to another as with a normal Gitlab board.

## License

`gitlab-personal-issue-board` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
