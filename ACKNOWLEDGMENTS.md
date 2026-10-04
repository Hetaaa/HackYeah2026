# Acknowledgments and disclosures

This file lists the AI tools, datasets, models, services and libraries used to build **why.**
(HackYeah 2026), as required by the HackYeah policy on the use of AI and external resources.

## 1. Use of AI tools

| Tool | Provider | Used for |
| --- | --- | --- |
| **Claude Code** with **Claude Opus 5.5** (`claude-opus-5-5`) | Anthropic | algorithm selection, coding assistance |

**No AI at runtime.** The app does not call any language model. All texts the user sees are built
from fixed templates (`backend/app/insights/texts.py`).

## 2. Datasets

### PMData: a sports logging dataset

The demo personas (Alex, Robin, Sam, Kim) are real, anonymous participants of PMData (participants
p06, p01, p10, p16). The algorithm was validated on 12 PMData participants.

- **Source:** <https://datasets.simula.no/pmdata/> (files: <https://osf.io/vx4bk>)
- **Licence:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
- **Article:** <https://dl.acm.org/doi/10.1145/3339825.3394926>
- **Changes we made:**
  - Fitbit data and wellness answers converted to one row per day;
  - main-sleep selection, wear filtering, value validation;
  - aligned to the morning check-in.

  Only derived daily values for 4 participants are stored in the repo
  (`backend/data/demo/*.csv`). The raw data is not redistributed.

> Thambawita, V., Hicks, S. A., Borgli, H., Stensland, H. K., Jha, D., Svensen, M. K.,
> Pettersen, S.-A., Johansen, D., Johansen, H. D., Pettersen, S. D., Nordvang, S., Pedersen, S.,
> Gjerdrum, A., Grønli, T.-M., Fredriksen, P. M., Eg, R., Hansen, K., Fagernes, S., Claudi, C.,
> Biørn-Hansen, A., Nguyen, D. T. D., Kupka, T., Hammer, H. L., Jain, R., Riegler, M. A., &
> Halvorsen, P. (2020). PMData: A Sports Logging Dataset. In *Proceedings of the 11th ACM
> Multimedia Systems Conference (MMSys '20)* (pp. 231–236). ACM.
> https://doi.org/10.1145/3339825.3394926

```bibtex
@inproceedings{10.1145/3339825.3394926,
  title     = {PMData: A Sports Logging Dataset},
  author    = {Thambawita, Vajira and Hicks, Steven Alexander and Borgli, Hanna and
               Stensland, H\r{a}kon Kvale and Jha, Debesh and Svensen, Martin Kristoffer and
               Pettersen, Svein-Arne and Johansen, Dag and Johansen, H\r{a}vard Dagenborg and
               Pettersen, Susann Dahl and Nordvang, Simon and Pedersen, Sigurd and
               Gjerdrum, Anders and Gr\o{}nli, Tor-Morten and Fredriksen, Per Morten and
               Eg, Ragnhild and Hansen, Kjeld and Fagernes, Siri and
               Claudi, Christine and Bi\o{}rn-Hansen, Andreas and Nguyen, Duc Tien Dang and
               Kupka, Tomas and Hammer, Hugo Lewi and Jain, Ramesh and Riegler, Michael Alexander and
               Halvorsen, P\r{a}l},
  booktitle = {Proceedings of the 11th ACM Multimedia Systems Conference},
  series    = {MMSys '20},
  pages     = {231--236},
  year      = {2020},
  publisher = {Association for Computing Machinery},
  address   = {New York, NY, USA},
  location  = {Istanbul, Turkey},
  doi       = {10.1145/3339825.3394926}
}
```

## 3. Models

- **No pre-trained or external models are used.**
- **Personal patterns** (`backend/app/insights/`) are our own statistical method: threshold rules
  scored with the Wilson score interval and tested with a circular-shift permutation test. They are
  computed per user, from that user's data only.
- **Daily forecast** (`backend/app/wellness/`) is an XGBoost classifier trained inside the app, at
  request time, on past days of all users in the database (PMData personas in the demo), with
  today's answers hidden.

Methods we rely on:

> Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference.
> *Journal of the American Statistical Association*, 22(158), 209–212.
> https://doi.org/10.1080/01621459.1927.10502953

> Chen, T., & Guestrin, C. (2016). XGBoost: A Scalable Tree Boosting System. In *Proceedings of the
> 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining* (pp. 785–794).
> https://doi.org/10.1145/2939672.2939785

## 4. Services

| Service | Use | Data sent |
| --- | --- | --- |
| [GitHub](https://github.com) | code hosting | source code |
| [Render](https://render.com) | backend hosting (free plan, Docker) | the app's API traffic and demo database |
| [Vercel](https://vercel.com) | frontend hosting, `/api` proxy to Render | the app's web traffic |
| [Google Fonts](https://fonts.google.com) | Manrope font, loaded by the browser | standard font request |

No third-party health or wearable APIs are called. Apple Health, Fitbit, Garmin and Oura appear in
the UI only as mock-ups; real integrations are analysed in `backend/docs/watch-sources.md`.

## 5. Libraries

Versions as locked in `backend/uv.lock` and `frontend/package-lock.json`.

### Backend (Python 3.12)

| Library | Version | Licence |
| --- | --- | --- |
| [FastAPI](https://fastapi.tiangolo.com) | 0.142.2 | MIT |
| [SQLModel](https://sqlmodel.tiangolo.com) | 0.0.47 | MIT |
| [SQLAlchemy](https://www.sqlalchemy.org) | 2.0.54 | MIT |
| [Pydantic](https://docs.pydantic.dev) / pydantic-settings | 2.13.5 / 2.15.0 | MIT |
| [Uvicorn](https://www.uvicorn.org) | 0.54.0 | BSD-3-Clause |
| [pandas](https://pandas.pydata.org) | 3.0.6 | BSD-3-Clause |
| [NumPy](https://numpy.org) | 2.5.3 | BSD-3-Clause |
| [scikit-learn](https://scikit-learn.org) | 1.9.1 | BSD-3-Clause |
| [XGBoost](https://xgboost.ai) | 3.4.1 | Apache-2.0 |
| [SciPy](https://scipy.org) (via scikit-learn) | 1.18.1 | BSD-3-Clause |
| [SQLite](https://sqlite.org) | (Python standard library) | Public domain |
| Dev: [pytest](https://pytest.org), [Ruff](https://docs.astral.sh/ruff/), [uv](https://docs.astral.sh/uv/) | 9.1.1, 0.16.10, – | MIT, MIT, MIT / Apache-2.0 |

### Frontend

| Library | Version | Licence |
| --- | --- | --- |
| [React](https://react.dev) / react-dom | 19.3.0 | MIT |
| [React Router](https://reactrouter.com) | 8.4.0 | MIT |
| [Zustand](https://zustand.docs.pmnd.rs) | 5.0.15 | MIT |
| [Motion](https://motion.dev) | 14.0.0 | MIT |
| [Lucide](https://lucide.dev) (lucide-react) | 1.51.0 | ISC |
| [canvas-confetti](https://github.com/catdad/canvas-confetti) | 1.9.4 | ISC |
| [Vite](https://vite.dev) / @vitejs/plugin-react | 8.3.2 / 6.1.1 | MIT |
| [Sass](https://sass-lang.com) | 1.105.1 | MIT |
| Dev: [Oxlint](https://oxc.rs) | 1.86.0 | MIT |
| Font: [Manrope](https://fonts.google.com/specimen/Manrope) | – | SIL Open Font License 1.1 |

### Scientific libraries: citations

> Harris, C. R., Millman, K. J., van der Walt, S. J., et al. (2020). Array programming with NumPy.
> *Nature*, 585, 357–362. https://doi.org/10.1038/s41586-020-2649-2

> McKinney, W. (2010). Data Structures for Statistical Computing in Python. In *Proceedings of the
> 9th Python in Science Conference* (pp. 56–61). https://doi.org/10.25080/Majora-92bf1922-00a

> Pedregosa, F., Varoquaux, G., Gramfort, A., et al. (2011). Scikit-learn: Machine Learning in
> Python. *Journal of Machine Learning Research*, 12, 2825–2830.

> Virtanen, P., Gommers, R., Oliphant, T. E., et al. (2020). SciPy 1.0: Fundamental Algorithms for
> Scientific Computing in Python. *Nature Methods*, 17, 261–272.
> https://doi.org/10.1038/s41592-019-0686-2

XGBoost: see section 3.

## 6. Work done before the event

The first two commits (2026-10-02) are a generic, project-agnostic starter:
- `29edf69 initial`: FastAPI + SQLModel skeleton with an example `items` resource, setup scripts
  `init.sh` / `init.ps1`;
- `b7831c4 initial frontend config`: Vite + React template.

They contain no product logic. Everything specific to why. (concept, data analysis, pattern
engine, forecast, API, UI) was built during HackYeah 2026.
