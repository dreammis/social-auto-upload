# Article renderer attribution

The Markdown theme renderer uses the published `baoyu-md` package, version 0.1.1,
from [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/main/packages/baoyu-md).
The upstream repository and package declare the MIT license; its full text is
preserved in `BAOYU-LICENSE`.

The package's `src/LICENSE` separately identifies code adapted from
[doocs/md](https://github.com/doocs/md) under WTFPL version 2. That notice and
license are preserved in `DOOCS-LICENSE`.

The `plain` renderer uses `marked` (MIT). HTML postprocessing uses `cheerio`
(MIT). npm installs these and their transitive dependencies with their own
license files. Versions and integrity hashes are fixed in `package-lock.json`.
